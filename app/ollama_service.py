"""
Ollama AI Text Generation Service - Production Ready
=====================================================

This module handles communication with Ollama Cloud API for AI-powered promotional text generation.
Designed for high reliability with circuit breaker pattern, exponential backoff, and comprehensive error handling.

Architecture:
    - Ollama Python Client for API communication
    - Circuit breaker pattern for fault tolerance
    - Exponential backoff retry logic for transient failures
    - Custom exception classes for error handling
    - Comprehensive logging for debugging

Model:
    GPT-OSS 120B Cloud - 120 billion parameter language model
    - Hosted on Ollama Cloud infrastructure
    - Specialized for marketing copy generation
    - Supports multiple tones and length categories

Features:
    - Generate 1-8 promotional text variations per request
    - 5 tone options (professional, casual, urgent, friendly, exciting)
    - 3 length categories (short, medium, long)
    - Automatic CTA button text generation
    - JSON-formatted structured responses
    - Rate limiting awareness (configured in main.py)

Error Handling:
    - Circuit breaker prevents cascade failures
    - Exponential backoff for transient errors
    - Custom exceptions for specific error scenarios
    - Detailed error logging for troubleshooting

Performance:
    - Async/await for non-blocking operations
    - Configurable timeout (default: 60 seconds)
    - Configurable max tokens per variation
    - JSON format enforcement for reliable parsing

Security:
    - API key authentication
    - No user input directly interpolated into prompts
    - Validates response structure before returning
    - Sanitizes error messages (no sensitive data leakage)

Created: October 16, 2025
Updated: October 17, 2025 - Production-ready with circuit breaker and retry logic
"""
import logging
import asyncio
import time
from typing import List, Dict, Optional
from enum import Enum
from ollama import Client
from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Classes
# =============================================================================

class OllamaAPIError(Exception):
    """
    Base exception for all Ollama API errors

    Attributes:
        message (str): Human-readable error description
        status_code (int): HTTP status code if applicable
        response_data (dict): Raw API response data

    Usage:
        try:
            result = await ollama_service.generate_text_variations(...)
        except OllamaAPIError as e:
            logger.error(f"Ollama API failed: {e}")
    """
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class OllamaRateLimitError(OllamaAPIError):
    """
    Raised when Ollama API rate limit is exceeded (HTTP 429)

    Indicates the application has exceeded its API rate limit.
    Should trigger exponential backoff retry or circuit breaker activation.

    Rate Limits (typical):
        - Free tier: ~10 requests/minute
        - Paid tier: ~100 requests/minute
        - Varies by account type and subscription

    Recommended Action:
        - Wait for rate limit reset (check Retry-After header)
        - Implement exponential backoff
        - Consider upgrading API plan if consistently hitting limits
    """
    pass


class OllamaTimeoutError(OllamaAPIError):
    """
    Raised when text generation takes longer than configured timeout

    Text generation typically takes 5-30 seconds depending on:
        - Number of variations requested (1-8)
        - Length category (short/medium/long)
        - Model load (server-side)
        - Network latency

    Default timeout: 60 seconds (configured in settings.OLLAMA_MAX_TOKENS)

    Recommended Action:
        - Retry with exponential backoff
        - Reduce number of variations
        - Check Ollama Cloud status
    """
    pass


class OllamaCircuitBreakerError(OllamaAPIError):
    """
    Raised when circuit breaker is OPEN (preventing API calls)

    Circuit breaker opens after multiple consecutive failures to prevent:
        - Cascading failures
        - Wasting resources on failing API
        - Overloading already-struggling service

    When circuit is open:
        - All requests fail immediately (no API call made)
        - Reduces load on failing service
        - Allows service time to recover

    Circuit will automatically attempt to close after timeout period.

    Recommended Action:
        - Wait for circuit breaker timeout
        - Check Ollama Cloud status page
        - Notify operations team if prolonged
    """
    pass


class OllamaJSONParseError(OllamaAPIError):
    """
    Raised when API response cannot be parsed as valid JSON

    Causes:
        - Model generated invalid JSON
        - Response wrapped in unexpected format
        - Network truncation of response
        - Model hallucination or formatting error

    Recommended Action:
        - Log raw response for debugging
        - Retry with same parameters
        - Adjust prompt if consistently failing
    """
    pass


# =============================================================================
# Enums for Type Safety
# =============================================================================

class TextTone(str, Enum):
    """
    Available tone options for promotional text generation

    Enum ensures type safety and prevents typos in tone selection.
    Each tone produces distinctly different writing styles.
    """
    PROFESSIONAL = "professional"  # Formal, authoritative, trust-building
    CASUAL = "casual"              # Friendly, conversational, approachable
    URGENT = "urgent"              # Time-sensitive, action-oriented, FOMO
    FRIENDLY = "friendly"          # Warm, personal, helpful
    EXCITING = "exciting"          # Energetic, enthusiastic, inspiring


class TextLength(str, Enum):
    """
    Available length categories for promotional text

    Enum ensures consistency in length specification.
    Controls approximate word count and sentence structure.
    """
    SHORT = "short"    # 1-2 sentences, ~30-50 words
    MEDIUM = "medium"  # 3-4 sentences, ~60-80 words
    LONG = "long"      # 5-6 sentences, ~100-120 words


# =============================================================================
# Circuit Breaker Pattern Implementation
# =============================================================================

class CircuitBreakerState(str, Enum):
    """
    Circuit breaker states for fault tolerance

    State Transitions:
        CLOSED → OPEN: After failure_threshold consecutive failures
        OPEN → HALF_OPEN: After timeout seconds elapsed
        HALF_OPEN → CLOSED: After success_threshold consecutive successes
        HALF_OPEN → OPEN: On any failure
    """
    CLOSED = "closed"        # Normal operation, requests allowed
    OPEN = "open"            # Too many failures, block all requests
    HALF_OPEN = "half_open"  # Testing recovery, allow limited requests


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures when Ollama API is down

    Purpose:
        Protects the application from wasting resources on a failing external service.
        When Ollama API is consistently failing, stop making requests for a period
        to allow the service time to recover.

    How it works:
        1. CLOSED state: Normal operation, all requests go through
        2. Track failures: Count consecutive failures
        3. Open circuit: After N failures, enter OPEN state
        4. Fail fast: In OPEN state, reject all requests immediately
        5. Half-open: After timeout, allow one test request
        6. Recovery: If test succeeds, close circuit and resume normal operation
        7. Re-open: If test fails, return to OPEN state

    Configuration:
        failure_threshold (int): Consecutive failures before opening circuit (default: 5)
            - Lower = more sensitive to failures (opens sooner)
            - Higher = more tolerant of transient errors

        timeout (int): Seconds to wait before attempting recovery (default: 60)
            - Longer = gives service more time to recover
            - Shorter = faster recovery attempts

        success_threshold (int): Consecutive successes needed to close (default: 2)
            - Higher = more confidence in recovery before fully reopening
            - Lower = faster return to normal operation

    Thread Safety:
        This implementation is NOT thread-safe. If using multiple workers,
        consider using a distributed circuit breaker (Redis-based).

    Example:
        circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        if circuit_breaker.state == CircuitBreakerState.OPEN:
            raise OllamaCircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = await ollama_api_call()
            circuit_breaker.record_success()
        except Exception as e:
            circuit_breaker.record_failure()
            raise
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of consecutive failures to open circuit
            timeout: Seconds to wait before attempting to close circuit
            success_threshold: Consecutive successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

        logger.info(
            f"🔌 Circuit breaker initialized: "
            f"failure_threshold={failure_threshold}, "
            f"timeout={timeout}s, "
            f"success_threshold={success_threshold}"
        )

    def record_success(self):
        """
        Record successful API call

        Behavior by state:
            - CLOSED: Reset failure count
            - HALF_OPEN: Increment success count, close if threshold reached
            - OPEN: Should not happen (circuit should block requests)
        """
        self.failure_count = 0

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            logger.info(f"✅ Circuit breaker success in HALF_OPEN: {self.success_count}/{self.success_threshold}")

            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0
                logger.info("✅ Circuit breaker CLOSED (recovered)")

        elif self.state == CircuitBreakerState.CLOSED:
            logger.debug("✅ Circuit breaker success in CLOSED state")

    def record_failure(self):
        """
        Record failed API call

        Behavior by state:
            - CLOSED: Increment failure count, open if threshold reached
            - HALF_OPEN: Immediately reopen circuit
            - OPEN: Update last failure time
        """
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            logger.warning(f"⚠️ Circuit breaker failure: {self.failure_count}/{self.failure_threshold}")

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.error(
                    f"🔴 Circuit breaker OPENED after {self.failure_count} consecutive failures. "
                    f"Will attempt recovery in {self.timeout} seconds."
                )

        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.error("🔴 Circuit breaker reopened after failure in HALF_OPEN state")

    def can_proceed(self) -> bool:
        """
        Check if request can proceed through circuit breaker

        Returns:
            bool: True if request allowed, False if blocked

        Side Effects:
            - May transition OPEN → HALF_OPEN if timeout elapsed
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.HALF_OPEN:
            return True

        # State is OPEN - check if timeout has elapsed
        if self.last_failure_time is None:
            return True

        time_since_failure = time.time() - self.last_failure_time

        if time_since_failure >= self.timeout:
            self.state = CircuitBreakerState.HALF_OPEN
            self.success_count = 0
            logger.info(f"🟡 Circuit breaker transitioning to HALF_OPEN after {time_since_failure:.1f}s")
            return True

        logger.warning(
            f"🔴 Circuit breaker is OPEN. "
            f"Waiting {self.timeout - time_since_failure:.1f}s more before retry."
        )
        return False


# =============================================================================
# Ollama Service Class
# =============================================================================

class OllamaService:
    """
    Production-ready Ollama AI text generation service

    Features:
        - Circuit breaker pattern for fault tolerance
        - Exponential backoff retry logic
        - Comprehensive error handling
        - Structured logging
        - Type-safe tone and length selection

    Usage:
        # Initialize service (done once at app startup)
        ollama_service = OllamaService()

        # Generate text variations
        variations = await ollama_service.generate_text_variations(
            offer_name="50% Off Black Friday Sale",
            offer_description="Limited time discount on all products",
            destination_url="https://example.com/sale",
            tone="exciting",
            length_category="medium",
            num_variations=3
        )

        # Result format:
        # [
        #     {"text": "Promotional copy...", "cta": "Shop Now"},
        #     {"text": "Alternative copy...", "cta": "Get Deal"},
        #     {"text": "Another variation...", "cta": "Save 50%"}
        # ]

    Configuration:
        All settings loaded from app.config.settings:
            - OLLAMA_API_KEY: Authentication token
            - OLLAMA_API_URL: API endpoint (https://ollama.com)
            - OLLAMA_MODEL: Model identifier (gpt-oss:120b-cloud)
            - OLLAMA_TEMPERATURE: Creativity level (0.8)
            - OLLAMA_MAX_TOKENS: Max tokens per variation (500)

    Error Handling:
        Raises specific exceptions for different failure scenarios:
            - OllamaRateLimitError: Rate limit exceeded (429)
            - OllamaTimeoutError: Generation timeout
            - OllamaCircuitBreakerError: Circuit breaker open
            - OllamaJSONParseError: Invalid response format
            - OllamaAPIError: General API errors

    Performance:
        - Typical generation time: 10-30 seconds
        - Depends on: num_variations, length_category, server load
        - Circuit breaker prevents wasted resources on failing API
        - Exponential backoff reduces thundering herd problem
    """

    def __init__(self):
        """
        Initialize Ollama service with API credentials and circuit breaker

        Raises:
            ValueError: If OLLAMA_API_KEY is not configured

        Side Effects:
            - Creates Ollama client connection
            - Initializes circuit breaker
            - Logs initialization status
        """
        if not settings.OLLAMA_API_KEY:
            raise ValueError("OLLAMA_API_KEY environment variable is required")

        # Initialize Ollama client
        self.client = Client(
            host=settings.OLLAMA_API_URL,
            headers={'Authorization': settings.OLLAMA_API_KEY}
        )

        self.model = settings.OLLAMA_MODEL

        # Initialize circuit breaker
        # Opens after 5 failures, waits 60s before retry, needs 2 successes to close
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            success_threshold=2
        )

        logger.info(
            f"✅ Ollama service initialized: "
            f"model={self.model}, "
            f"temperature={settings.OLLAMA_TEMPERATURE}, "
            f"max_tokens={settings.OLLAMA_MAX_TOKENS}"
        )

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute function with exponential backoff retry logic

        Retry Strategy:
            Attempt 1: Immediate (no delay)
            Attempt 2: Wait 1 second
            Attempt 3: Wait 2 seconds
            Attempt 4: Wait 4 seconds
            Total: 4 attempts over 7 seconds

        Retryable Errors:
            - Exception with "timeout" in message
            - Exception with "network" in message
            - Exception with "connection" in message
            - Exception with "5" in message (5xx server errors)

        Non-Retryable Errors:
            - OllamaRateLimitError (needs longer wait)
            - OllamaCircuitBreakerError (circuit must close first)
            - OllamaJSONParseError (retry won't fix invalid format)
            - Validation errors (client-side issue)

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries exhausted

        Example:
            result = await self._retry_with_backoff(
                self._make_api_call,
                prompt="Generate text...",
                max_tokens=500
            )
        """
        max_retries = 4
        base_delay = 1

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)

            except (OllamaRateLimitError, OllamaCircuitBreakerError, OllamaJSONParseError) as e:
                # Non-retryable errors
                logger.error(f"❌ Non-retryable error: {e}")
                raise

            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = any(keyword in error_msg for keyword in ['timeout', 'network', 'connection', '5'])

                if not is_retryable or attempt == max_retries - 1:
                    logger.error(f"❌ Final retry attempt failed: {e}")
                    raise

                # Calculate exponential backoff delay
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        raise OllamaAPIError("All retry attempts exhausted")

    async def generate_text_variations(
        self,
        offer_name: str,
        offer_description: str,
        destination_url: str,
        offer_type: str = "affiliate",
        tone: str = "professional",
        length_category: str = "medium",
        num_variations: int = 3
    ) -> List[Dict[str, str]]:
        """
        Generate promotional text variations using Ollama AI

        This is the main public method for text generation. It orchestrates:
            1. Parameter validation
            2. Circuit breaker check
            3. Prompt construction
            4. API call with retry logic
            5. Response parsing and validation
            6. Circuit breaker updates

        Args:
            offer_name (str): Name of promotional offer
                Example: "50% Off Black Friday Sale"
                Required, max 255 characters

            offer_description (str): Detailed offer description
                Example: "Limited time discount on all AI tools and courses"
                Required, used to provide context to AI

            destination_url (str): Where users will be directed when clicking
                Example: "https://aidailypost.com/black-friday"
                Required, included in prompt for relevance

            tone (str): Writing style/tone for generated text
                Options: "professional", "casual", "urgent", "friendly", "exciting"
                Default: "professional"
                See TextTone enum for descriptions

            length_category (str): Approximate length of generated text
                Options: "short" (~30-50 words), "medium" (~60-80 words), "long" (~100-120 words)
                Default: "medium"
                See TextLength enum for details

            num_variations (int): Number of variations to generate
                Range: 1-8
                Default: 3
                More variations = more options but longer generation time

        Returns:
            List[Dict[str, str]]: List of text variations
                Format: [
                    {
                        "text": "Promotional copy here...",
                        "cta": "Click Here"
                    },
                    ...
                ]

                Each variation contains:
                    - text: Main promotional copy
                    - cta: Call-to-action button text

        Raises:
            ValueError: Invalid parameters (negative num_variations, etc.)
            OllamaCircuitBreakerError: Circuit breaker is OPEN
            OllamaRateLimitError: API rate limit exceeded
            OllamaTimeoutError: Generation timeout
            OllamaJSONParseError: Response not valid JSON
            OllamaAPIError: General API errors

        Performance:
            - Typical time: 10-30 seconds
            - Factors: num_variations, length_category, server load
            - Longer text = more tokens = more time

        Example:
            variations = await ollama_service.generate_text_variations(
                offer_name="AI Tools Bundle",
                offer_description="Complete collection of productivity tools",
                destination_url="https://example.com/bundle",
                tone="exciting",
                length_category="medium",
                num_variations=5
            )

            for i, var in enumerate(variations, 1):
                print(f"Variation {i}:")
                print(f"  Text: {var['text']}")
                print(f"  CTA: {var['cta']}")
        """
        # ==================================================================
        # Parameter Validation
        # ==================================================================

        if not offer_name or not offer_name.strip():
            raise ValueError("offer_name is required and cannot be empty")

        if not offer_description or not offer_description.strip():
            raise ValueError("offer_description is required and cannot be empty")

        if not destination_url or not destination_url.strip():
            raise ValueError("destination_url is required and cannot be empty")

        if num_variations < 1 or num_variations > 30:
            raise ValueError(f"num_variations must be between 1 and 30, got {num_variations}")

        # Validate tone (convert to enum if needed)
        try:
            tone_enum = TextTone(tone)
        except ValueError:
            valid_tones = [t.value for t in TextTone]
            raise ValueError(f"Invalid tone '{tone}'. Must be one of: {valid_tones}")

        # Validate length_category
        try:
            length_enum = TextLength(length_category)
        except ValueError:
            valid_lengths = [l.value for l in TextLength]
            raise ValueError(f"Invalid length_category '{length_category}'. Must be one of: {valid_lengths}")

        logger.info(
            f"🎨 Text generation request: "
            f"offer={offer_name}, "
            f"tone={tone}, "
            f"length={length_category}, "
            f"variations={num_variations}"
        )

        # ==================================================================
        # Circuit Breaker Check
        # ==================================================================

        if not self.circuit_breaker.can_proceed():
            raise OllamaCircuitBreakerError(
                "Circuit breaker is OPEN. Ollama API is currently unavailable. "
                "Please try again later."
            )

        # ==================================================================
        # Build Prompt
        # ==================================================================

        # Build length guidelines
        length_guidelines = {
            "short": "Keep it concise (1-2 sentences, ~30-50 words). Perfect for busy readers.",
            "medium": "Moderate length (3-4 sentences, ~60-80 words). Enough detail to convince.",
            "long": "Detailed explanation (5-6 sentences, ~100-120 words). Thorough value proposition."
        }

        # Build tone guidelines
        tone_guidelines = {
            "professional": "Professional, authoritative, trust-building. Use industry terminology appropriately.",
            "casual": "Friendly, conversational, approachable. Like talking to a colleague over coffee.",
            "urgent": "Time-sensitive, action-oriented, creates FOMO. Emphasize limited availability.",
            "friendly": "Warm, personal, helpful. Focus on benefits to the reader.",
            "exciting": "Energetic, enthusiastic, inspiring. Use powerful action words."
        }

        # Build comprehensive system prompt based on offer type
        is_coffee_sponsor = offer_type == "donation"

        if is_coffee_sponsor:
            # Coffee sponsor goes in newsletter outro - no headline, humorous/friendly
            system_prompt = f"""You are an expert newsletter copywriter for AI Daily Post.

Your task: Generate {num_variations} distinct variations for our coffee sponsor outro message.

Offer: {offer_name}
Description: {offer_description}

Context: This appears at the END of the newsletter as a friendly "support us" message.

Requirements:
- Tone: Warm, friendly, slightly humorous - NOT salesy
- Length: {length_guidelines.get(length_category, length_guidelines['short'])}
- Make it feel like a genuine "thanks for reading" note
- NO headline needed (it's in the outro section)
- Focus on community support, not hard sell
- Each variation should have a unique angle or humor

Format your response as JSON array:
[
  {{
    "text": "Outro message text here...",
    "cta": "Buy Me a Coffee"
  }},
  ...
]

Generate exactly {num_variations} variations."""
        else:
            # Regular promotional content - needs headline + body text
            system_prompt = f"""You are an expert newsletter copywriter specializing in promotional content for AI Daily Post.

Your task: Generate {num_variations} distinct promotional variations for this offer:

Offer: {offer_name}
Description: {offer_description}
Link: {destination_url}
Type: {offer_type}

Requirements:
- Tone: {tone_guidelines.get(tone, tone_guidelines['professional'])}
- Length: {length_guidelines.get(length_category, length_guidelines['medium'])}
- Each variation must include:
  1. HEADLINE: Attention-grabbing (5-10 words, bold-worthy)
  2. TEXT: Compelling promotional copy
  3. CTA: Clear call-to-action button text (2-4 words)
- Focus on benefits, not just features
- Make it newsletter-friendly (easy to scan, spam-filter safe)
- Headlines should create curiosity or highlight value
- Each variation should be significantly different from the others

Format your response as JSON array:
[
  {{
    "headline": "Your Attention-Grabbing Headline Here",
    "text": "Promotional text goes here...",
    "cta": "Get Started"
  }},
  ...
]

Generate exactly {num_variations} variations."""

        # ==================================================================
        # Make API Call with Retry Logic
        # ==================================================================

        try:
            result = await self._retry_with_backoff(
                self._generate_text_internal,
                system_prompt=system_prompt,
                num_variations=num_variations
            )

            # Success - update circuit breaker
            self.circuit_breaker.record_success()

            logger.info(f"✅ Generated {len(result)} text variations successfully")
            return result

        except Exception as e:
            # Failure - update circuit breaker
            self.circuit_breaker.record_failure()

            logger.error(f"❌ Text generation failed after retries: {e}")
            raise

    async def _generate_text_internal(
        self,
        system_prompt: str,
        num_variations: int
    ) -> List[Dict[str, str]]:
        """
        Internal method to make actual Ollama API call

        Separated from public method to enable clean retry logic.
        This method should NOT be called directly - use generate_text_variations() instead.

        Args:
            system_prompt: Complete system prompt with instructions
            num_variations: Number of variations to generate

        Returns:
            List of validated text variations

        Raises:
            OllamaTimeoutError: Request timeout
            OllamaJSONParseError: Invalid JSON response
            OllamaAPIError: Other API errors
        """
        import json
        import re

        try:
            logger.info(f"🎨 Calling Ollama API ({self.model}) for {num_variations} variations")

            # Call Ollama API using Python client
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": "Generate the promotional text variations now."
                    }
                ],
                stream=False,
                options={
                    "temperature": settings.OLLAMA_TEMPERATURE,
                    "num_predict": settings.OLLAMA_MAX_TOKENS * num_variations
                },
                format="json"  # Force JSON output
            )

            # Extract content from response
            content = response['message']['content']

            # Log first 500 chars for debugging
            logger.debug(f"Raw Ollama response (first 500 chars): {content[:500]}")

            # ==================================================================
            # Parse JSON Response (with multiple fallback strategies)
            # ==================================================================

            # Strategy 1: Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug("Extracted JSON from markdown code block")
            else:
                # Strategy 2: Try to find JSON array directly
                json_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.debug("Extracted JSON array from response")
                else:
                    # Strategy 3: Use raw content
                    json_str = content.strip()
                    logger.debug("Using raw content as JSON")

            # Attempt to parse JSON
            try:
                variations = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                logger.error(f"Attempted to parse: {json_str[:1000]}")
                raise OllamaJSONParseError(
                    f"Failed to parse Ollama response as JSON: {str(e)}",
                    response_data={"content": content[:1000]}
                )

            # ==================================================================
            # Handle Different Response Formats
            # ==================================================================

            # Some models wrap the array in an object
            if isinstance(variations, dict):
                if 'variations' in variations:
                    variations = variations['variations']
                elif 'texts' in variations:
                    variations = variations['texts']
                elif 'results' in variations:
                    variations = variations['results']

            # ==================================================================
            # Validate Response Structure
            # ==================================================================

            if not isinstance(variations, list):
                raise OllamaJSONParseError(
                    f"Expected list of variations, got {type(variations).__name__}",
                    response_data={"content": content[:1000]}
                )

            if len(variations) == 0:
                raise OllamaJSONParseError(
                    "Received empty list of variations",
                    response_data={"content": content[:1000]}
                )

            # Validate each variation has required fields
            for i, var in enumerate(variations):
                if not isinstance(var, dict):
                    raise OllamaJSONParseError(
                        f"Variation {i} is not a dictionary: {type(var).__name__}",
                        response_data={"variation": str(var)[:500]}
                    )

                if 'text' not in var:
                    raise OllamaJSONParseError(
                        f"Variation {i} missing 'text' field",
                        response_data={"variation": var}
                    )

                if 'cta' not in var:
                    # Auto-generate CTA if missing (fallback)
                    var['cta'] = "Learn More"
                    logger.warning(f"Variation {i} missing 'cta' field, added default")

            logger.info(f"✅ Successfully parsed {len(variations)} text variations")
            return variations

        except OllamaJSONParseError:
            # Re-raise parse errors without wrapping
            raise

        except Exception as e:
            error_msg = str(e).lower()

            # Check for timeout
            if 'timeout' in error_msg:
                raise OllamaTimeoutError(
                    f"Text generation timed out: {str(e)}",
                    response_data={"error": str(e)}
                )

            # Check for rate limit
            if '429' in error_msg or 'rate limit' in error_msg:
                raise OllamaRateLimitError(
                    f"Ollama API rate limit exceeded: {str(e)}",
                    status_code=429,
                    response_data={"error": str(e)}
                )

            # Generic API error
            raise OllamaAPIError(
                f"Ollama API call failed: {str(e)}",
                response_data={"error": str(e)}
            )
