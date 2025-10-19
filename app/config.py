"""
Configuration Module for Promotional Content Management System

This module manages all application configuration using Pydantic Settings.
Environment variables are loaded from .env file and validated on startup.

Architecture:
    - Pydantic Settings for type validation and environment variable parsing
    - Single global settings instance used throughout the application
    - Sensible defaults for non-critical settings
    - Required values will raise ValidationError if missing

Security Notes:
    - SECRET_KEY must be changed in production (currently uses default)
    - API keys should never be committed to git (use .env file)
    - DATABASE_URL should use strong password in production
    - CORS allowed_origins should be restrictive in production

Usage:
    from app.config import settings

    # Access configuration
    db_url = settings.DATABASE_URL
    api_key = settings.LEONARDO_API_KEY

    # Get parsed list of CORS origins
    origins = settings.allowed_origins_list

Created: October 16, 2025
Updated: October 17, 2025 - Added comprehensive documentation
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables (.env file)

    All configuration is centralized here for easy management and validation.
    Pydantic automatically validates types and converts values on load.

    Required Variables (will fail if not set):
        - DATABASE_URL
        - SECRET_KEY
        - OLLAMA_API_KEY, OLLAMA_API_URL
        - ALLOWED_ORIGINS

    Deprecated Variables (no longer used as of Oct 18, 2025):
        - LEONARDO_API_KEY, LEONARDO_API_URL (image generation removed)
        - IMAGE_UPLOAD_DIR, IMAGE_BASE_URL (text-only system)

    Optional Variables (have defaults):
        - HOST, PORT, DEBUG
        - ALGORITHM
        - ACCESS_TOKEN_EXPIRE_MINUTES
        - MATOMO settings
        - Leonardo/Ollama model parameters
        - Generation limits
    """

    # ===========================================================================
    # Database Configuration
    # ===========================================================================

    DATABASE_URL: str
    """
    PostgreSQL connection string
    Format: postgresql://user:password@host:port/database
    Example: postgresql://strapi_user:password@127.0.0.1:5432/aidailypost_cms

    Security: Use strong password in production, avoid hardcoding credentials
    """

    # ===========================================================================
    # JWT Authentication Configuration
    # ===========================================================================

    SECRET_KEY: str
    """
    Secret key for signing JWT tokens (REQUIRED)

    Security: MUST be changed from default in production!
    Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    Minimum length: 32 characters recommended

    ⚠️ CRITICAL: If this key is compromised, all JWT tokens can be forged!
    ⚠️ CRITICAL: Changing this key will invalidate all existing user sessions!
    """

    ALGORITHM: str = "HS256"
    """
    JWT signing algorithm (default: HS256)

    Options: HS256 (symmetric), RS256 (asymmetric)
    HS256 is faster but requires shared secret
    RS256 uses public/private key pair for better security
    """

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    """
    JWT token expiration time in minutes (default: 1440 = 24 hours)

    Balance between security and user experience:
    - Shorter = more secure but users must login more often
    - Longer = better UX but higher risk if token is compromised

    Recommendation: 24 hours for internal tools, 1 hour for public facing
    """

    # ===========================================================================
    # External API Keys (AI Services)
    # ===========================================================================

    OLLAMA_API_KEY: str
    """
    Ollama Cloud API key for text generation (REQUIRED)

    Used for: Generating promotional text variations with GPT-OSS 120B model
    Rate Limits: Varies by account, configured in slowapi middleware
    Security: Never commit to git, store in .env file only
    """

    OLLAMA_API_URL: str
    """
    Ollama Cloud API base URL (REQUIRED)
    Default: https://ollama.com
    Can be changed to use local Ollama instance or different endpoint
    """

    LEONARDO_API_KEY: str = ""
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Leonardo AI API key for image generation (NO LONGER USED)
    Newsletter promo system is now text-only per user request.

    This setting remains for backwards compatibility but is not required.
    Can be safely removed from .env file.
    """

    LEONARDO_API_URL: str = "https://cloud.leonardo.ai/api/rest/v1"
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Leonardo AI API base URL (NO LONGER USED)
    Kept for backwards compatibility only.
    """

    # ===========================================================================
    # Image Storage Configuration (DEPRECATED)
    # ===========================================================================

    IMAGE_UPLOAD_DIR: str = "/var/www/aidailypost/promo-images"
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Local filesystem path for storing generated images (NO LONGER USED)
    Newsletter promo system is now text-only per user request.

    This setting remains for backwards compatibility but is not required.
    Can be safely removed from .env file.
    """

    IMAGE_BASE_URL: str = "https://promo.aidailypost.com/uploads"
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Public URL prefix for accessing stored images (NO LONGER USED)
    Newsletter promo system is now text-only per user request.

    This setting remains for backwards compatibility but is not required.
    Can be safely removed from .env file.
    """

    # ===========================================================================
    # Server Configuration
    # ===========================================================================

    HOST: str = "127.0.0.1"
    """
    Server bind address (default: 127.0.0.1 - localhost only)

    Options:
    - 127.0.0.1: Only accept connections from localhost (recommended with Nginx proxy)
    - 0.0.0.0: Accept connections from any network interface (direct exposure)

    Recommendation: Use 127.0.0.1 with Nginx reverse proxy for production
    """

    PORT: int = 3003
    """
    Server port number (default: 3003)

    Note: Should be > 1024 to avoid requiring root privileges
    Nginx proxies external requests (443/80) to this internal port
    """

    DEBUG: bool = False
    """
    Debug mode flag (default: False)

    When True:
    - More verbose error messages (may leak sensitive info)
    - Auto-reload on code changes
    - Detailed stack traces in responses

    ⚠️ CRITICAL: Must be False in production for security!
    """

    # ===========================================================================
    # CORS Configuration
    # ===========================================================================

    ALLOWED_ORIGINS: str
    """
    Comma-separated list of allowed CORS origins (REQUIRED)
    Example: "https://promo.aidailypost.com,http://localhost:5173"

    Security: Only add trusted domains to prevent unauthorized API access
    - Production domain: https://promo.aidailypost.com
    - Development: http://localhost:5173 (Vite default port)

    Parsed into list via allowed_origins_list property
    """

    # ===========================================================================
    # Matomo Analytics Configuration (Optional)
    # ===========================================================================

    MATOMO_URL: str = ""
    """
    Matomo analytics instance URL (optional)
    Example: http://127.0.0.1:8080
    Leave empty if not using Matomo tracking
    """

    MATOMO_SITE_ID: int = 1
    """
    Matomo site ID for tracking (default: 1)
    Each site in Matomo has a unique ID
    """

    MATOMO_AUTH_TOKEN: str = ""
    """
    Matomo API authentication token (optional)
    Required if using Matomo API for analytics retrieval
    Leave empty if only using client-side tracking
    """

    # ===========================================================================
    # Leonardo AI Model Configuration (DEPRECATED)
    # ===========================================================================

    LEONARDO_MODEL: str = "aa77f04e-3eec-4034-9c07-d0f619684628"
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Leonardo AI model ID for image generation (NO LONGER USED)
    Newsletter promo system is now text-only per user request.
    """

    LEONARDO_WIDTH: int = 600
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Image width in pixels (NO LONGER USED)
    """

    LEONARDO_HEIGHT: int = 400
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Image height in pixels (NO LONGER USED)
    """

    LEONARDO_NUM_IMAGES: int = 5
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Number of images per generation batch (NO LONGER USED)
    """

    # ===========================================================================
    # Ollama AI Model Configuration
    # ===========================================================================

    OLLAMA_MODEL: str = "gpt-oss:120b-cloud"
    """
    Ollama model identifier for text generation
    Default: GPT-OSS 120B Cloud (high quality, cloud-hosted)

    Model characteristics:
    - 120 billion parameters
    - Cloud-hosted (no local GPU required)
    - Good for marketing copy generation
    - Understands tone and style instructions

    Alternative models:
    - llama2 (open source, lower quality)
    - mistral (faster, less creative)
    - Custom fine-tuned models
    """

    OLLAMA_TEMPERATURE: float = 0.8
    """
    Ollama generation temperature (default: 0.8)

    Controls randomness/creativity of text generation:
    - 0.0: Deterministic, always same output
    - 0.5: Balanced, some variety
    - 0.8: Creative, good variety (recommended for marketing)
    - 1.0: Very creative, less consistent
    - >1.0: Chaotic, may lose coherence

    For promotional text, 0.7-0.9 provides good variety while maintaining quality
    """

    OLLAMA_MAX_TOKENS: int = 500
    """
    Maximum tokens to generate per text variation (default: 500)

    Roughly 500 tokens = 375 words = 2-3 paragraphs
    Sufficient for:
    - Short promotional text (50-100 words)
    - Medium promotional text (100-200 words)
    - Long promotional text (200-300 words)
    - Plus CTA button text

    Higher values increase generation time and cost
    """

    # ===========================================================================
    # Content Generation Limits
    # ===========================================================================

    MAX_TEXT_VARIATIONS: int = 8
    """
    Maximum text variations per generation request (default: 8)

    Enforces reasonable limits to prevent:
    - Excessive API costs (Ollama charges per token)
    - Long generation times (>8 variations = >1 minute)
    - Database bloat (storing too many unused variations)

    Users can generate multiple batches if needed
    """

    MAX_IMAGES: int = 5
    """
    DEPRECATED as of October 18, 2025 - Image generation removed

    Maximum images per generation request (NO LONGER USED)
    Newsletter promo system is now text-only per user request.
    """

    # ===========================================================================
    # Pydantic Configuration
    # ===========================================================================

    class Config:
        """
        Pydantic model configuration

        env_file: Load variables from .env file in project root
        case_sensitive: Environment variables are case-insensitive
        """
        env_file = ".env"
        case_sensitive = False

    # ===========================================================================
    # Computed Properties
    # ===========================================================================

    @property
    def allowed_origins_list(self) -> List[str]:
        """
        Parse ALLOWED_ORIGINS comma-separated string into a list

        Returns:
            List[str]: List of allowed CORS origins

        Example:
            "https://example.com,http://localhost:5173"
            → ["https://example.com", "http://localhost:5173"]

        Used by FastAPI CORS middleware to determine which origins
        can make cross-origin requests to the API.
        """
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# ===========================================================================
# Global Settings Instance
# ===========================================================================

# Instantiate settings once at module import
# This loads and validates all environment variables
# Any missing required variables will raise ValidationError and prevent startup
settings = Settings()
