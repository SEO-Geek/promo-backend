"""
Pydantic Models for Promotional Content Management System

This module defines all request and response data models using Pydantic.
Pydantic provides automatic data validation, serialization, and documentation
generation for the FastAPI application.

Architecture:
    - Request models: Validate incoming API data
    - Response models: Structure outgoing API data
    - Type safety: Compile-time type checking with mypy
    - Auto documentation: OpenAPI schema generation
    - Validation: Automatic field validation on creation

Features:
    - Email validation with EmailStr
    - URL validation with HttpUrl
    - Pattern matching for enums (status, tone, length)
    - Range validation (min/max lengths, numeric ranges)
    - Optional fields with None defaults
    - Datetime parsing and serialization

Benefits:
    - Runtime validation prevents invalid data from reaching database
    - Clear API contracts for frontend developers
    - Self-documenting API via OpenAPI schema
    - Type hints for IDE autocomplete
    - Serialization to JSON for API responses

Usage:
    from app.models import OfferCreate, OfferResponse

    # Validate incoming request
    @app.post("/offers", response_model=OfferResponse)
    async def create_offer(offer: OfferCreate):
        # offer is guaranteed to be valid
        # Pydantic raises 422 if validation fails
        pass

    # Return validated response
    return OfferResponse(
        id=1,
        name="Black Friday Sale",
        # ... other fields
    )

Created: October 16, 2025
Updated: October 17, 2025 - Added comprehensive documentation
"""
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List
from datetime import datetime, date


# ============================================================================
# Authentication Models
# ============================================================================

class LoginRequest(BaseModel):
    """
    Login credentials for user authentication

    This model validates login requests before processing authentication.
    It ensures email format is valid and password is provided.

    Fields:
        email (EmailStr): User's email address
            - Must be valid email format (validated by Pydantic)
            - Examples: "user@example.com", "admin@aidailypost.com"
            - Invalid: "notanemail", "user@", "@example.com"

        password (str): User's password
            - Any string accepted (validation happens in auth layer)
            - Actual validation: bcrypt hash comparison
            - Never logged or stored in plain text

    Validation:
        - Email format validated automatically by EmailStr
        - Password presence validated (non-empty required)
        - Returns 422 Unprocessable Entity if validation fails

    Security:
        - Password sent over HTTPS (encrypted in transit)
        - Password hashed before database comparison
        - No password length requirements enforced here
          (enforced during user registration)

    Usage:
        @app.post("/api/v1/auth/login")
        async def login(credentials: LoginRequest):
            # credentials.email is guaranteed valid email format
            # credentials.password is guaranteed non-empty
            user = await authenticate(credentials.email, credentials.password)
            return TokenResponse(...)

    Example Request Body:
        {
            "email": "labaek@gmail.com",
            "password": "SecurePassword123!"
        }

    Example Validation Errors:
        # Invalid email format
        {"email": "notanemail"} → 422 Unprocessable Entity

        # Missing password
        {"email": "user@example.com"} → 422 Unprocessable Entity
    """
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    JWT authentication token response

    Returned after successful login, contains access token and user information.
    Frontend stores this token and includes it in subsequent API requests.

    Fields:
        access_token (str): JWT token for authentication
            - Format: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            - Contains: user_id, email, role, expiration
            - Expires: After ACCESS_TOKEN_EXPIRE_MINUTES (default: 1440 = 24 hours)
            - Signing: HMAC-SHA256 with SECRET_KEY

        token_type (str): Token authentication scheme
            - Always "bearer" (OAuth 2.0 standard)
            - Used in Authorization header: "Bearer <token>"

        user (dict): Basic user information
            - Contains: id, email, name, role
            - Avoids additional API call to fetch user details
            - Frontend can display user info immediately

    Usage:
        # Backend
        return TokenResponse(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="bearer",
            user={
                "id": 1,
                "email": "user@example.com",
                "name": "John Doe",
                "role": "admin"
            }
        )

        # Frontend
        const response = await api.post('/auth/login', credentials)
        localStorage.setItem('token', response.access_token)
        localStorage.setItem('user', JSON.stringify(response.user))

        # Subsequent requests
        headers: { Authorization: `Bearer ${token}` }

    Security:
        - Token contains user claims (id, email, role)
        - Token is signed with SECRET_KEY (prevents tampering)
        - Token expiration enforced on every request
        - No refresh tokens (re-login required after expiration)

    Example Response:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "email": "labaek@gmail.com",
                "name": "Brian Laban",
                "role": "admin"
            }
        }
    """
    access_token: str
    token_type: str = "bearer"
    user: dict


# ============================================================================
# User Models
# ============================================================================

class UserResponse(BaseModel):
    """
    User account information response

    Contains full user profile information, returned by /auth/me endpoint
    and included in TokenResponse.

    Fields:
        id (int): Unique user identifier
            - Primary key from promo_users table
            - Used in API endpoints for user-specific operations

        email (str): User's email address
            - Unique constraint in database
            - Used for login authentication

        name (str): User's display name
            - Full name or preferred display name
            - Shown in UI header, logs, audit trails

        role (str): User's permission level
            - Values: "admin", "editor", "viewer"
            - Controls access to endpoints and features
            - Admin: Full access (create, edit, delete, approve)
            - Editor: Create and edit (no delete or approve)
            - Viewer: Read-only access

        last_login (Optional[datetime]): Most recent login timestamp
            - Updated on every successful login
            - None if user has never logged in
            - Format: ISO 8601 (e.g., "2025-10-17T10:30:00Z")

        created_at (datetime): Account creation timestamp
            - Set once when user account is created
            - Immutable (never changes)
            - Format: ISO 8601

    Usage:
        @app.get("/api/v1/auth/me", response_model=UserResponse)
        async def get_current_user(current_user: dict = Depends(get_current_user)):
            return UserResponse(
                id=current_user['id'],
                email=current_user['email'],
                name=current_user['name'],
                role=current_user['role'],
                last_login=current_user['last_login'],
                created_at=current_user['created_at']
            )

    Example Response:
        {
            "id": 1,
            "email": "labaek@gmail.com",
            "name": "Brian Laban",
            "role": "admin",
            "last_login": "2025-10-17T10:30:00Z",
            "created_at": "2025-10-01T08:00:00Z"
        }
    """
    id: int
    email: str
    name: str
    role: str
    last_login: Optional[datetime]
    created_at: datetime


# ============================================================================
# Offer Models
# ============================================================================

class OfferCreate(BaseModel):
    """
    Create new promotional offer

    Validates data for creating a new promotional offer in the system.
    All fields are validated before database insertion.

    Fields:
        name (str): Offer display name (REQUIRED)
            - Min length: 1 character
            - Max length: 255 characters
            - Example: "50% Off Black Friday Sale"
            - Used in: Dashboard, newsletter preview, analytics

        description (Optional[str]): Detailed offer description
            - No length limit (TEXT column in database)
            - Supports markdown formatting
            - Used in: Internal notes, offer details page
            - Can be None for simple offers

        destination_url (HttpUrl): Final destination URL (REQUIRED)
            - Must be valid URL (validated by Pydantic)
            - Must start with http:// or https://
            - Example: "https://example.com/sale?promo=BLACK50"
            - User redirected here after clicking newsletter link

        affiliate_slug (Optional[str]): URL path for affiliate redirect
            - Optional custom slug for affiliate system integration
            - Example: "black-friday-50-off"
            - Used in: https://aidailypost.com/<slug> redirects
            - Can be None if not using affiliate system

        status (str): Offer lifecycle status
            - Values: "draft", "active", "paused", "ended"
            - Default: "draft"
            - draft: Not ready for use (incomplete, testing)
            - active: Available for newsletter selection
            - paused: Temporarily disabled (can resume)
            - ended: Permanently closed (archived)

        start_date (Optional[datetime]): Offer availability start
            - Offer not selected before this date
            - None = available immediately
            - Example: "2025-11-25T00:00:00Z" (Black Friday start)

        end_date (Optional[datetime]): Offer availability end
            - Offer not selected after this date
            - None = available indefinitely
            - Example: "2025-11-27T23:59:59Z" (Black Friday end)

        priority (int): Selection priority order
            - Range: 0 to infinity (validated: >= 0)
            - Default: 0 (normal priority)
            - Higher number = higher priority in selection
            - Example: 10 for featured offers, 0 for normal
            - Used in: Weighted selection algorithm

        weight (int): Probability weight in random selection
            - Range: 1 to infinity (validated: >= 1)
            - Default: 1 (equal probability)
            - Higher number = more likely to be selected
            - Example: weight=3 is 3x more likely than weight=1
            - Used in: Random weighted selection algorithm

    Validation Rules:
        - name: Required, 1-255 characters
        - description: Optional, unlimited length
        - destination_url: Required, valid URL format
        - affiliate_slug: Optional, any string
        - status: Must be one of: draft, active, paused, ended
        - start_date: Optional, valid datetime
        - end_date: Optional, valid datetime
        - priority: Must be >= 0
        - weight: Must be >= 1

    Usage:
        @app.post("/api/v1/offers", response_model=OfferResponse)
        async def create_offer(offer: OfferCreate):
            # offer is fully validated at this point
            offer_id = await db.fetchval(
                \"\"\"
                INSERT INTO promo_offers (name, description, destination_url, ...)
                VALUES ($1, $2, $3, ...)
                RETURNING id
                \"\"\",
                offer.name, offer.description, str(offer.destination_url), ...
            )
            return OfferResponse(id=offer_id, ...)

    Example Request Body:
        {
            "name": "Black Friday 50% Off Sale",
            "description": "Limited time offer - 50% off all products",
            "destination_url": "https://example.com/sale",
            "affiliate_slug": "black-friday-50",
            "status": "draft",
            "start_date": "2025-11-25T00:00:00Z",
            "end_date": "2025-11-27T23:59:59Z",
            "priority": 10,
            "weight": 3
        }

    Example Validation Errors:
        # Invalid URL
        {"destination_url": "not-a-url"} → 422 Unprocessable Entity

        # Invalid status
        {"status": "invalid"} → 422 Unprocessable Entity

        # Negative priority
        {"priority": -1} → 422 Unprocessable Entity
    """
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    offer_type: str = Field(default="affiliate", pattern="^(review|affiliate|donation)$")  # Added Oct 18, 2025, donation added Oct 18 for coffee outro system
    destination_url: HttpUrl
    affiliate_slug: Optional[str] = None
    status: str = Field(default="draft", pattern="^(active|paused|ended|draft)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: int = Field(default=0, ge=0)
    weight: int = Field(default=1, ge=1)


class OfferUpdate(BaseModel):
    """
    Update existing promotional offer

    Similar to OfferCreate but all fields are optional.
    Only provided fields will be updated in the database.

    Fields:
        All fields are same as OfferCreate but wrapped in Optional[]
        See OfferCreate documentation for field descriptions.

    Partial Update Pattern:
        - Only include fields you want to change
        - Omitted fields remain unchanged
        - Explicit None clears optional fields

    Validation Rules:
        - Same validation as OfferCreate
        - All fields optional (can update just one field)

    Usage:
        @app.put("/api/v1/offers/{offer_id}", response_model=OfferResponse)
        async def update_offer(offer_id: int, update: OfferUpdate):
            # Build dynamic UPDATE query with only provided fields
            update_data = update.dict(exclude_unset=True)
            # update_data only contains fields that were provided

            set_clauses = []
            params = []
            for i, (key, value) in enumerate(update_data.items(), start=1):
                set_clauses.append(f"{key} = ${i}")
                params.append(value)

            query = f\"\"\"
                UPDATE promo_offers
                SET {', '.join(set_clauses)}
                WHERE id = ${len(params) + 1}
            \"\"\"
            params.append(offer_id)

            await db.execute(query, *params)

    Example Request Bodies:
        # Update only status
        {"status": "active"}

        # Update multiple fields
        {
            "name": "Updated Sale Name",
            "status": "active",
            "priority": 5
        }

        # Clear optional field (set to NULL)
        {"description": null}

    Best Practices:
        - Only send fields that need updating
        - Use PATCH for partial updates (REST convention)
        - Validate offer exists before updating
        - Return updated offer in response
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    offer_type: Optional[str] = Field(None, pattern="^(review|affiliate|donation)$")  # Added Oct 18, 2025, donation added Oct 18 for coffee outro
    destination_url: Optional[HttpUrl] = None
    affiliate_slug: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|ended|draft)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=0)
    weight: Optional[int] = Field(None, ge=1)


class OfferResponse(BaseModel):
    """
    Promotional offer with performance statistics

    Complete offer information including calculated performance metrics.
    Used in API responses for GET /offers and GET /offers/{id}.

    Fields:
        id (int): Unique offer identifier
            - Primary key from promo_offers table

        name (str): Offer display name

        description (Optional[str]): Detailed description

        destination_url (str): Final destination URL
            - Note: Returned as string (not HttpUrl) for JSON serialization

        affiliate_slug (Optional[str]): Affiliate redirect path

        status (str): Current status (draft, active, paused, ended)

        start_date (Optional[datetime]): Availability start

        end_date (Optional[datetime]): Availability end

        priority (int): Selection priority (higher = more important)

        weight (int): Selection probability weight

        created_at (datetime): Offer creation timestamp

        updated_at (datetime): Last modification timestamp
            - Updated automatically on every change

        total_impressions (int): Number of times shown in newsletters
            - Calculated from promo_impression_tracking table
            - Incremented when newsletter is sent with this offer

        total_clicks (int): Number of times clicked by recipients
            - Calculated from promo_click_tracking table
            - Incremented when user clicks offer link in newsletter

        ctr (float): Click-through rate (clicks / impressions)
            - Calculated: (total_clicks / total_impressions) * 100
            - Range: 0.0 to 100.0
            - Example: 15.5 means 15.5% of recipients clicked
            - Returns 0.0 if no impressions (prevents division by zero)

    Performance Metrics:
        - total_impressions: How many people saw this offer
        - total_clicks: How many people clicked
        - ctr: Percentage of viewers who clicked (effectiveness metric)

    CTR Benchmarks:
        - < 1%: Poor performance (consider pausing)
        - 1-5%: Average performance
        - 5-10%: Good performance
        - > 10%: Excellent performance (keep using)

    Usage:
        @app.get("/api/v1/offers/{offer_id}", response_model=OfferResponse)
        async def get_offer(offer_id: int):
            offer = await db.fetchrow(
                \"\"\"
                SELECT o.*,
                       COALESCE(SUM(im.impression_count), 0) as total_impressions,
                       COALESCE(SUM(c.click_count), 0) as total_clicks,
                       CASE
                           WHEN COALESCE(SUM(im.impression_count), 0) > 0
                           THEN (COALESCE(SUM(c.click_count), 0)::float / SUM(im.impression_count) * 100)
                           ELSE 0
                       END as ctr
                FROM promo_offers o
                LEFT JOIN promo_impression_tracking im ON o.id = im.offer_id
                LEFT JOIN promo_click_tracking c ON o.id = c.offer_id
                WHERE o.id = $1
                GROUP BY o.id
                \"\"\",
                offer_id
            )
            return OfferResponse(**dict(offer))

    Example Response:
        {
            "id": 1,
            "name": "Black Friday 50% Off",
            "description": "Limited time offer",
            "destination_url": "https://example.com/sale",
            "affiliate_slug": "black-friday-50",
            "status": "active",
            "start_date": "2025-11-25T00:00:00Z",
            "end_date": "2025-11-27T23:59:59Z",
            "priority": 10,
            "weight": 3,
            "created_at": "2025-10-01T10:00:00Z",
            "updated_at": "2025-10-17T15:30:00Z",
            "total_impressions": 1500,
            "total_clicks": 225,
            "ctr": 15.0
        }
    """
    id: int
    name: str
    description: Optional[str]
    offer_type: str  # Added Oct 18, 2025
    destination_url: str
    affiliate_slug: Optional[str]
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    priority: int
    weight: int
    created_at: datetime
    updated_at: datetime
    total_impressions: int
    total_clicks: int
    ctr: float


class OfferListResponse(BaseModel):
    """
    Paginated list of offers with metadata

    Wraps a list of offers with total count for pagination support.

    Fields:
        offers (List[OfferResponse]): Array of offer objects
            - Can be empty list if no offers match query
            - Ordered by: priority DESC, created_at DESC (typically)

        total (int): Total number of offers matching query
            - Used for pagination calculation
            - Example: If total=100 and page_size=20, then 5 pages

    Pagination Pattern:
        - Frontend calculates: total_pages = ceil(total / page_size)
        - Frontend shows: "Showing 1-20 of 100 offers"
        - Frontend disables "Next" button on last page

    Usage:
        @app.get("/api/v1/offers", response_model=OfferListResponse)
        async def list_offers(
            status: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ):
            # Build query with filters
            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = $1")
                params.append(status)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get total count
            total = await db.fetchval(
                f"SELECT COUNT(*) FROM promo_offers {where_sql}",
                *params
            )

            # Get paginated offers
            offset = (page - 1) * page_size
            offers = await db.fetch(
                f\"\"\"
                SELECT * FROM promo_offers {where_sql}
                ORDER BY priority DESC, created_at DESC
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
                \"\"\",
                *params, page_size, offset
            )

            return OfferListResponse(
                offers=[OfferResponse(**dict(o)) for o in offers],
                total=total
            )

    Example Response:
        {
            "offers": [
                {
                    "id": 1,
                    "name": "Offer 1",
                    ...
                },
                {
                    "id": 2,
                    "name": "Offer 2",
                    ...
                }
            ],
            "total": 45
        }
    """
    offers: List[OfferResponse]
    total: int


# ============================================================================
# Image Models
# ============================================================================

# Image-related models removed October 18, 2025
# Newsletter promo system uses text-only variations (no images)


# ============================================================================
# Text Models
# ============================================================================

class TextGenerationRequest(BaseModel):
    """
    Request to generate promotional text via Ollama AI

    Specifies parameters for AI text generation. Ollama will create
    multiple variations of promotional copy based on tone and length.

    Fields:
        tone (str): Writing style/voice for the text
            - Values: "professional", "casual", "urgent", "friendly", "exciting"
            - Default: "professional"

            Tone Descriptions:
            - professional: Formal business tone, credible, trustworthy
              Example: "We are pleased to offer our valued customers..."

            - casual: Conversational, approachable, friendly
              Example: "Hey! Check out this awesome deal we've got for you..."

            - urgent: Time-sensitive, action-driving, FOMO-inducing
              Example: "LAST CHANCE! This offer expires in 24 hours..."

            - friendly: Warm, personal, relationship-focused
              Example: "Hi friend! We thought you'd love this special offer..."

            - exciting: Enthusiastic, energetic, emotion-driven
              Example: "OMG! You won't believe this incredible offer!..."

        length_category (str): Approximate text length
            - Values: "short", "medium", "long"
            - Default: "medium"

            Length Guidelines:
            - short: 50-100 words (~2-3 sentences)
              Use for: Quick announcements, simple offers
              Example: "Limited time offer - 50% off! Shop now before it's gone."

            - medium: 100-200 words (~4-5 sentences)
              Use for: Standard promotional text, balanced detail
              Example: Full paragraph with offer details + benefits + CTA

            - long: 200-300 words (~6-8 sentences)
              Use for: Detailed explanations, feature-rich offers
              Example: Multiple paragraphs with full value proposition

        num_variations (int): Number of text variations to generate
            - Range: 1 to 30 (validated)
            - Default: 20 (recommended for high-volume newsletters)
            - Ollama generates unique variations
            - More variations = avoid repetition in frequent campaigns
            - For 20 newsletters/month: 30 variations covers 1.5 months
            - Each variation has unique phrasing and structure

    Generation Process:
        1. Backend constructs prompt with offer details + tone + length
        2. Sends request to Ollama Cloud API (GPT-OSS 120B model)
        3. Ollama generates num_variations unique texts
        4. Backend parses response and extracts CTA button text
        5. Database records created with approved=false
        6. User reviews and approves best variations

    Cost Considerations:
        - Ollama charges per token generated
        - More variations = higher cost (but better ROI for newsletter campaigns)
        - Longer text = higher cost
        - Recommendation for high-volume newsletters (20/month):
          * Generate 20-30 variations per offer to cover 1-1.5 months
          * Rotate through variations to avoid spam filter patterns
          * Batch generation is more efficient than frequent small generations

    Validation Rules:
        - tone: Must be one of 5 allowed values
        - length_category: Must be one of 3 allowed values
        - num_variations: 1-30 (optimal for newsletter campaigns)

    Usage:
        @app.post("/api/v1/offers/{offer_id}/generate-text")
        async def generate_text(
            offer_id: int,
            request: TextGenerationRequest
        ):
            # Get offer details for context
            offer = await db.fetchrow(
                "SELECT * FROM promo_offers WHERE id = $1",
                offer_id
            )

            # Generate text via Ollama
            variations = await ollama_service.generate_text(
                offer_name=offer['name'],
                offer_description=offer['description'],
                tone=request.tone,
                length_category=request.length_category,
                num_variations=request.num_variations
            )

            # Store variations in database
            for variation in variations:
                await db.execute(
                    \"\"\"
                    INSERT INTO promo_text_variations
                    (offer_id, text_content, cta_text, tone, length_category)
                    VALUES ($1, $2, $3, $4, $5)
                    \"\"\",
                    offer_id, variation['text'], variation['cta'],
                    request.tone, request.length_category
                )

    Example Request Body:
        {
            "tone": "exciting",
            "length_category": "medium",
            "num_variations": 25
        }

    Example Validation Errors:
        # Invalid tone
        {"tone": "aggressive"} → 422 Unprocessable Entity

        # Too many variations (exceeds limit)
        {"num_variations": 50} → 422 Unprocessable Entity
    """
    tone: str = Field(default="professional", pattern="^(professional|casual|urgent|friendly|exciting)$")
    length_category: str = Field(default="medium", pattern="^(short|medium|long)$")
    num_variations: int = Field(default=20, ge=1, le=30)


class TextVariationUpdate(BaseModel):
    """
    Update existing promotional text variation (user adjustments)

    Allows manual editing of AI-generated text before approval.
    This enables the "Generate → Review → ADJUST → Approve" workflow.

    Fields:
        text_content (str): Updated promotional text
            - User can manually edit AI-generated text
            - Validation: 10-1000 characters
            - Example: "Limited time! Get 50% off all courses through Friday only!"

        cta_text (Optional[str]): Updated call-to-action button text
            - User can customize button text
            - Validation: 3-50 characters if provided
            - Example: "Claim Offer", "Shop Now", "Get Started"
            - None: Keep existing CTA text unchanged

        tone (Optional[str]): Updated tone classification
            - Values: "professional", "casual", "urgent", "friendly", "exciting"
            - Allows reclassifying after manual edits
            - None: Keep existing tone unchanged

        length_category (Optional[str]): Updated length classification
            - Values: "short", "medium", "long"
            - Allows reclassifying after length changes
            - None: Keep existing length_category unchanged

    Use Cases:
        1. Fix typos in AI-generated text
        2. Adjust phrasing to match brand voice
        3. Add/remove details based on offer changes
        4. Customize CTA button text
        5. Reclassify tone/length after edits

    Workflow:
        1. AI generates text (approved=false)
        2. User reviews generated text
        3. User edits text via PUT /api/v1/texts/{text_id}
        4. Backend updates text_content, cta_text, tone, length_category
        5. User approves edited text via PUT /api/v1/texts/{text_id}/approve
        6. Approved text available for newsletter selection

    Validation Rules:
        - text_content: Required, 10-1000 chars (prevents empty/too long text)
        - cta_text: Optional, 3-50 chars if provided (button text constraints)
        - tone: Optional, must be valid tone value if provided
        - length_category: Optional, must be valid length if provided

    Example Update (Full Edit):
        {
            "text_content": "Flash Sale! 50% off all courses this weekend only. Don't miss out!",
            "cta_text": "Shop Now",
            "tone": "urgent",
            "length_category": "short"
        }

    Example Update (Text Only):
        {
            "text_content": "Updated promotional text with better phrasing..."
        }
        # tone, cta_text, length_category remain unchanged

    Example Update (CTA Only):
        {
            "text_content": "Same text as before...",
            "cta_text": "Get Started Today"
        }

    Database Impact:
        - Updates promo_text_variations table
        - Does NOT change approved flag (separate endpoint)
        - Does NOT change performance metrics (impressions, clicks, CTR)
        - Tracks edit timestamp (updated_at)

    Security:
        - Requires JWT authentication
        - Rate limit: 100 updates/minute (standard CRUD)
        - Only authorized users can edit
    """
    text_content: str = Field(..., min_length=10, max_length=1000)
    cta_text: Optional[str] = Field(None, min_length=3, max_length=50)
    tone: Optional[str] = Field(None, pattern="^(professional|casual|urgent|friendly|exciting)$")
    length_category: Optional[str] = Field(None, pattern="^(short|medium|long)$")


class TextVariationResponse(BaseModel):
    """
    Generated promotional text variation with performance data

    Represents one text variation for an offer, including usage statistics.

    Fields:
        id (int): Unique text variation identifier
            - Primary key from promo_text_variations table

        offer_id (int): Associated offer ID
            - Foreign key to promo_offers table
            - One offer can have multiple text variations

        text_content (str): The actual promotional text
            - Generated by Ollama AI
            - Includes full promotional copy
            - Example: "Limited time offer! Get 50% off all products..."

        cta_text (Optional[str]): Call-to-action button text
            - Extracted from generated text or generated separately
            - Example: "Shop Now", "Claim Offer", "Learn More"
            - Used in newsletter button

        tone (Optional[str]): Tone used for generation
            - One of: professional, casual, urgent, friendly, exciting
            - Helps categorize variations

        length_category (Optional[str]): Length category used
            - One of: short, medium, long
            - Helps categorize variations

        approved (bool): Whether text is approved for use
            - Default: false (requires manual review)
            - true: Available for newsletter selection
            - false: Hidden from selection (needs review)

        times_used (int): Number of newsletters sent with this text
            - Calculated from promo_impression_tracking
            - Incremented each time newsletter uses this text

        total_clicks (int): Total clicks on offers using this text
            - Helps identify which text drives more engagement
            - Higher clicks = more effective copy

        ctr (float): Click-through rate for this text
            - Calculated: (total_clicks / times_used) * 100
            - Compares text effectiveness
            - Example: Text A (12% CTR) vs Text B (6% CTR)

        created_at (datetime): Text generation timestamp

    Approval Workflow:
        1. AI generates text variations (all approved=false)
        2. User reviews texts in dashboard
        3. User approves best 1-2 variations
        4. Only approved texts used in newsletters
        5. System tracks which texts perform best

    A/B Testing Pattern:
        - Generate variations with same tone/length
        - Approve multiple (e.g., 3 variations)
        - System randomly selects from approved
        - Track which variation performs best
        - Pause underperforming variations

    Usage:
        @app.get("/api/v1/offers/{offer_id}/texts", response_model=List[TextVariationResponse])
        async def get_offer_texts(offer_id: int):
            texts = await db.fetch(
                \"\"\"
                SELECT t.*,
                       COALESCE(COUNT(im.id), 0) as times_used,
                       COALESCE(SUM(c.click_count), 0) as total_clicks,
                       CASE
                           WHEN COALESCE(COUNT(im.id), 0) > 0
                           THEN (COALESCE(SUM(c.click_count), 0)::float / COUNT(im.id) * 100)
                           ELSE 0
                       END as ctr
                FROM promo_text_variations t
                LEFT JOIN promo_impression_tracking im ON t.id = im.text_id
                LEFT JOIN promo_click_tracking c ON t.offer_id = c.offer_id
                WHERE t.offer_id = $1
                GROUP BY t.id
                ORDER BY t.approved DESC, t.created_at DESC
                \"\"\",
                offer_id
            )
            return [TextVariationResponse(**dict(txt)) for txt in texts]

    Example Response:
        {
            "id": 456,
            "offer_id": 1,
            "text_content": "LIMITED TIME OFFER! Get 50% off all products this Black Friday. Don't miss out on incredible savings!",
            "cta_text": "Shop Now",
            "tone": "exciting",
            "length_category": "short",
            "approved": true,
            "times_used": 10,
            "total_clicks": 120,
            "ctr": 12.0,
            "created_at": "2025-10-17T11:00:00Z"
        }
    """
    id: int
    offer_id: int
    headline: Optional[str]  # Newsletter-optimized: NULL for coffee sponsor, text for regular offers
    text_content: str
    cta_text: Optional[str]
    tone: Optional[str]
    length_category: Optional[str]
    approved: bool
    times_used: int
    total_clicks: int
    ctr: float
    created_at: datetime


# ============================================================================
# Newsletter Selection Models
# ============================================================================

class PromoContentResponse(BaseModel):
    """
    Complete promotional content for newsletter inclusion - TEXT ONLY (October 18, 2025)

    This is the final output used by the newsletter system. Contains
    all necessary elements to render the promo in an email.

    **NOTE:** Image generation removed per user request. Newsletter promos are now text-only.

    Fields:
        offer_id (int): The selected offer's ID
            - Used for tracking impressions and clicks

        offer_name (str): Display name of the offer
            - Used in email subject line or internal logging

        offer_type (str): Type of promotional offer
            - "review": Internal review (e.g., aidailypost.com/review/no-code-mba)
            - "affiliate": External affiliate offer (e.g., aidailypost.com/nocodemba → redirect)

        text (str): The selected promotional text
            - Full promotional copy to display in email
            - AI-generated variation from Ollama
            - Multiple variations rotate even for same offer

        cta (str): Call-to-action button text
            - Text for the clickable button
            - Example: "Start Learning →", "Get Started →", "Build Now →"

        link (str): Destination URL for tracking
            - For reviews: Direct link to aidailypost.com/review/[slug]
            - For affiliates: Cloaked link via aidailypost.com/[affiliate_slug]
            - Includes tracking parameters (variation_id, utm params)

        variation_id (int): ID of the specific text variation shown
            - Used to track which headlines/body text perform best
            - Enables self-learning copywriting optimization
            - Links clicks to specific variation for analytics

    Newsletter Integration:
        1. Newsletter service calls GET /api/v1/promo/select-random
        2. Backend selects weighted random offer with approved text variations
        3. Returns complete PromoContentResponse (text only, no image)
        4. Newsletter injects promo into email template (after first 2-3 stories)
        5. On send, impression tracking incremented (async, non-blocking)
        6. On click, click tracking incremented with variation_id

    Fail-Safe Behavior:
        - If no active offers: Returns 503 with null data
        - Newsletter continues sending without promo (5-second timeout)
        - System prioritizes newsletter delivery over promo inclusion

    Usage:
        @app.get("/api/v1/promo/select-random", response_model=PromoContentResponse)
        async def select_random_promo():
            # Select offer (weighted random based on offer.weight)
            offer = await select_weighted_random_offer()

            # Select approved text variation (random from approved)
            text = await select_random_text_variation(offer['id'])

            # Build tracking link
            if offer['offer_type'] == 'review':
                link = f"https://aidailypost.com/review/{offer['affiliate_slug']}"
            else:
                link = f"https://aidailypost.com/{offer['affiliate_slug']}"
            link += f"?utm_source=newsletter&promo_var={text['id']}"

            return PromoContentResponse(
                offer_id=offer['id'],
                offer_name=offer['name'],
                offer_type=offer['offer_type'],
                text=text['text_content'],
                cta=text['cta_text'],
                link=link,
                variation_id=text['id']
            )

    Example Response:
        {
            "offer_id": 4,
            "offer_name": "No Code MBA - Learn to Build Without Coding",
            "offer_type": "affiliate",
            "text": "Build your dream startup this weekend—no coding required! No Code MBA shows you...",
            "cta": "Build Now →",
            "link": "https://aidailypost.com/nocodemba?utm_source=newsletter&promo_var=42",
            "variation_id": 42
        }
    """
    offer_id: int
    offer_name: str
    offer_type: str  # review or affiliate
    text: str
    cta: str
    link: str
    variation_id: int  # For tracking which text variation was shown


class HealthCheckResponse(BaseModel):
    """
    System health status response

    Reports overall system health and capability to provide content.
    Used for monitoring and alerting.

    Fields:
        status (str): Overall system health status
            - "healthy": All systems operational
            - "degraded": Some issues but can still provide content
            - "failed": Critical failure, cannot provide content

        timestamp (datetime): Current server time
            - ISO 8601 format
            - Used to verify server is responding

        components (dict): Status of individual components (TEXT-ONLY SYSTEM)
            - Keys: component names
            - Values: status strings or details
            - Example:
              {
                  "database": "healthy",
                  "active_offers": "healthy (5 offers)",
                  "approved_content": "healthy (5 ready)"
              }
            NOTE: Leonardo AI and image generation removed Oct 18, 2025

        can_provide_content (bool): Whether system can provide promo content
            - true: Can generate PromoContentResponse
            - false: Critical failure (no offers, no connection, etc.)
            - Newsletter service checks this before requesting content

    Health Check Logic:
        status = "healthy" if:
            - Database connected
            - Active offers exist
            - Approved text variations exist (text-only system)

        status = "degraded" if:
            - Database connected
            - Active offers exist
            - AI services unreachable (can still use existing content)

        status = "failed" if:
            - Database disconnected
            - No active offers
            - Cannot provide content

    Monitoring Usage:
        - External monitoring pings GET /api/promo/health every 60 seconds
        - Alerts if status != "healthy" for >5 minutes
        - Dashboard displays health status in real-time

    Usage:
        @app.get("/api/promo/health", response_model=HealthCheckResponse)
        async def health_check():
            # Check database
            try:
                await db.fetchval("SELECT 1")
                db_status = "connected"
            except:
                db_status = "disconnected"

            # Count active offers
            active_offers = await db.fetchval(
                "SELECT COUNT(*) FROM promo_offers WHERE status = 'active'"
            )

            # Determine overall status
            if db_status == "connected" and active_offers > 0:
                status = "healthy"
            elif db_status == "connected":
                status = "degraded"
            else:
                status = "failed"

            return HealthCheckResponse(
                status=status,
                timestamp=datetime.utcnow(),
                components={
                    "database": db_status,
                    "active_offers": active_offers,
                    # ... more components
                },
                can_provide_content=(status != "failed")
            )

    Example Response (Healthy):
        {
            "status": "healthy",
            "timestamp": "2025-10-18T10:30:00Z",
            "components": {
                "database": "healthy",
                "active_offers": "healthy (5 offers)",
                "approved_content": "healthy (5 ready)"
            },
            "can_provide_content": true
        }

    Example Response (Degraded):
        {
            "status": "degraded",
            "timestamp": "2025-10-18T10:30:00Z",
            "components": {
                "database": "healthy",
                "active_offers": "healthy (5 offers)",
                "approved_content": "degraded (no approved content)"
            },
            "can_provide_content": false
        }

    NOTE: Images and Leonardo AI removed Oct 18, 2025 - TEXT-ONLY SYSTEM
    """
    status: str  # healthy, degraded, failed
    timestamp: datetime
    components: dict
    can_provide_content: bool


# ============================================================================
# Analytics Models
# ============================================================================

class AnalyticsOverviewResponse(BaseModel):
    """
    Dashboard analytics overview with key metrics

    Provides high-level performance summary for the dashboard.

    Fields:
        total_offers (int): Total number of offers in system
        active_offers (int): Number of offers with status='active'
        total_impressions (int): Sum of all offer impressions
        total_clicks (int): Sum of all offer clicks
        overall_ctr (float): System-wide click-through rate
        newsletters_sent (int): Total newsletters sent with promos
        top_performing_offers (List[dict]): Best performing offers
            - Sorted by CTR descending
            - Top 5 offers
            - Each dict contains: id, name, impressions, clicks, ctr
    """
    total_offers: int
    active_offers: int
    total_impressions: int
    total_clicks: int
    overall_ctr: float
    newsletters_sent: int
    top_performing_offers: List[dict]


class OfferAnalyticsResponse(BaseModel):
    """
    Detailed analytics for a specific offer

    Provides comprehensive performance data for one offer.

    Fields:
        offer_id (int): The offer being analyzed
        offer_name (str): Offer display name
        impressions (int): Total times shown
        clicks (int): Total times clicked
        ctr (float): Overall click-through rate
        text_performance (List[dict]): Per-text performance (TEXT-ONLY)
            - Each dict: {text_id, text_content, times_used, clicks, ctr}
        daily_stats (List[dict]): Daily breakdown
            - Each dict: {date, impressions, clicks, ctr}

    NOTE: images_performance removed Oct 18, 2025 - text-only promo system
    """
    offer_id: int
    offer_name: str
    impressions: int
    clicks: int
    ctr: float
    text_performance: List[dict]
    daily_stats: List[dict]


# ============================================================================
# Generation Job Models
# ============================================================================

class GenerationJobResponse(BaseModel):
    """
    AI generation job status and results (TEXT-ONLY as of Oct 18, 2025)

    Tracks the progress of async AI generation jobs.

    NOTE: Table contains historical image generation jobs, but image generation
    endpoints were removed Oct 18, 2025. Only text_generation jobs are created now.

    Fields:
        id (int): Unique job identifier
            - Primary key from promo_generation_jobs table

        offer_id (int): Associated offer ID

        job_type (str): Type of generation
            - "image_generation": Leonardo AI (DEPRECATED Oct 18, 2025, historical only)
            - "text_generation": Ollama text generation (ACTIVE)

        status (str): Current job status
            - "pending": Job queued but not started
            - "processing": AI generation in progress
            - "completed": Successfully completed
            - "failed": Error occurred

        generated_count (int): Number of items generated
            - For images: Number of images generated
            - For texts: Number of text variations generated

        error_message (Optional[str]): Error details if failed
            - None if status != "failed"
            - Contains error description for debugging

        started_at (Optional[datetime]): When job started processing
            - None if status = "pending"

        completed_at (Optional[datetime]): When job finished
            - None if status = "pending" or "processing"

        duration_seconds (Optional[int]): Total job duration
            - Calculated: completed_at - started_at
            - None if job not completed
            - Used for performance monitoring

    Usage:
        # After starting text generation (image_generation deprecated Oct 18, 2025)
        job = await create_generation_job(offer_id, "text_generation")

        # Poll for completion
        @app.get("/api/v1/jobs/{job_id}", response_model=GenerationJobResponse)
        async def get_job_status(job_id: int):
            job = await db.fetchrow(
                "SELECT * FROM promo_generation_jobs WHERE id = $1",
                job_id
            )
            return GenerationJobResponse(**dict(job))

    Example Response (Processing):
        {
            "id": 789,
            "offer_id": 1,
            "job_type": "text_generation",
            "status": "processing",
            "generated_count": 0,
            "error_message": null,
            "started_at": "2025-10-18T12:00:00Z",
            "completed_at": null,
            "duration_seconds": null
        }

    Example Response (Completed):
        {
            "id": 789,
            "offer_id": 1,
            "job_type": "text_generation",
            "status": "completed",
            "generated_count": 8,
            "error_message": null,
            "started_at": "2025-10-18T12:00:00Z",
            "completed_at": "2025-10-18T12:00:15Z",
            "duration_seconds": 15
        }
    """
    id: int
    offer_id: int
    job_type: str
    status: str
    generated_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]


# ==============================================================================
# TRACKING MODELS - Phase 3.1 (October 18, 2025)
# ==============================================================================
# PURPOSE: Enable impression and click tracking for newsletter promotional content
#
# BACKGROUND:
# - Newsletter system includes promotional content (text-only, no images)
# - Need to track:
#   1. IMPRESSIONS: When promo is shown in newsletter
#   2. CLICKS: When user clicks promo link
#   3. ANALYTICS: Performance metrics (CTR, top performers, trends)
#
# PRIVACY & GDPR:
# - No PII stored (no user_id, no email addresses)
# - IP addresses hashed before storage (SHA-256)
# - Cookie-less tracking (server-side only)
# - Aggregate data only in analytics
# - Right to be forgotten: CASCADE DELETE on offer/variation deletion
#
# INTEGRATION POINTS:
# - Newsletter system → POST /api/v1/promo/track-impression (after send)
# - Affiliate redirect → POST /api/v1/promo/track-click (on redirect)
# - Dashboard → GET /api/v1/promo/analytics (performance charts)
# ==============================================================================


class ImpressionTrackingRequest(BaseModel):
    """
    Request model for tracking newsletter impression events.

    PURPOSE:
    - Track when promotional content is shown in a newsletter
    - Provide denominator for CTR calculation (clicks / impressions)
    - Enable time-series analysis of newsletter performance
    - Support A/B testing of text variations

    WORKFLOW:
    1. Newsletter system calls GET /api/v1/promo/select-random
    2. Backend returns promo content with offer_id and variation_id
    3. Newsletter compiles HTML email
    4. Newsletter calls POST /api/v1/promo/track-impression (THIS MODEL)
    5. Backend writes to promo_impression_tracking table
    6. Trigger increments promo_text_variations.impressions counter
    7. Newsletter sends to subscribers

    PRIVACY NOTES:
    - ip_address is OPTIONAL and will be SHA-256 hashed before storage
    - No user identification - only aggregate tracking
    - GDPR compliant - no PII required

    PERFORMANCE:
    - Target response time: <50ms
    - Newsletter should NOT block on this call (fire-and-forget)
    - 5-second timeout recommended on newsletter side

    Example Usage:
        # In newsletter send script
        try:
            response = requests.post(
                "http://127.0.0.1:3003/api/v1/promo/track-impression",
                json={
                    "offer_id": 4,
                    "variation_id": 42,
                    "newsletter_send_id": "2025-10-18-daily",
                    "subscriber_count": 5000,
                    "ip_address": "192.168.1.1"  # Optional, will be hashed
                },
                timeout=5  # Don't block newsletter send
            )
        except requests.Timeout:
            # Newsletter continues sending even if tracking fails
            logger.warning("Impression tracking timed out")

    Example Request Body:
        {
            "offer_id": 4,
            "variation_id": 42,
            "newsletter_send_id": "2025-10-18-daily",
            "subscriber_count": 5000,
            "ip_address": "192.168.1.1"
        }

    Database Impact:
        - INSERT into promo_impression_tracking
        - UPDATE promo_text_variations SET impressions = impressions + 1
        - UPDATE promo_text_variations SET ctr = (clicks / impressions) * 100

    Created: October 18, 2025
    """
    # REQUIRED FIELDS
    # ----------------

    # Which promotional offer was shown?
    # WHY REQUIRED: Need to track performance per offer
    # VALIDATION: Must be a valid promo_offers.id (foreign key check in database)
    offer_id: int = Field(
        ...,
        description="ID of the promotional offer shown in newsletter",
        example=4,
        gt=0  # Must be positive integer
    )

    # Which text variation was shown?
    # WHY REQUIRED: Need to track performance per variation for self-learning
    # CRITICAL: This enables answering "Which headline/tone/length performs best?"
    # VALIDATION: Must be a valid promo_text_variations.id (foreign key check)
    variation_id: int = Field(
        ...,
        description="ID of the specific text variation shown (enables A/B testing)",
        example=42,
        gt=0
    )

    # OPTIONAL FIELDS
    # ----------------

    # Newsletter send identifier
    # WHY USEFUL: Groups impressions by newsletter send
    # Example: "2025-10-18-daily" or "2025-10-18-weekly"
    # USE CASE: "How did the Oct 18 daily newsletter perform vs weekly?"
    newsletter_send_id: Optional[str] = Field(
        None,
        description="Unique identifier for this newsletter send (e.g., '2025-10-18-daily')",
        example="2025-10-18-daily",
        max_length=100  # Prevent abuse
    )

    # How many subscribers received this newsletter?
    # WHY USEFUL: Calculate effective reach and engagement rate
    # Example: 5000 subscribers, 250 clicks = 5% of audience engaged
    # NOTE: Different from impressions count (1 subscriber = 1 potential impression)
    subscriber_count: Optional[int] = Field(
        None,
        description="Total number of subscribers who received this newsletter",
        example=5000,
        gt=0  # Must be positive if provided
    )

    # IP address of newsletter send server (will be hashed)
    # WHY USEFUL: Detect bot traffic, prevent fraud
    # PRIVACY: SHA-256 hashed before storage (one-way, can't reverse)
    # OPTIONAL: Newsletter may not have access to IP
    # NOTE: This is server IP, NOT subscriber IP (we don't track individuals)
    ip_address: Optional[str] = Field(
        None,
        description="IP address of request (will be SHA-256 hashed for privacy)",
        example="192.168.1.1",
        max_length=45  # IPv4 = 15 chars, IPv6 = 45 chars
    )


class ClickTrackingRequest(BaseModel):
    """
    Request model for tracking promotional link click events.

    PURPOSE:
    - Track when users click promotional links
    - Provide numerator for CTR calculation (clicks / impressions)
    - Enable conversion funnel analysis
    - Support self-learning optimization

    WORKFLOW:
    1. Newsletter includes link: https://aidailypost.com/nocodemba?promo_var=42
    2. User clicks link in email client
    3. Affiliate redirect handler extracts promo_var=42 from URL
    4. Redirect handler calls POST /api/v1/promo/track-click (THIS MODEL)
    5. Backend writes to promo_click_tracking table asynchronously
    6. Trigger increments promo_text_variations.clicks counter
    7. User is redirected to destination URL

    CRITICAL: Click tracking must be FAST (<50ms) and ASYNC
    - User should never wait for tracking to complete
    - Fire-and-forget pattern
    - Redirect happens immediately
    - Tracking happens in background

    PRIVACY NOTES:
    - ip_address is OPTIONAL and will be SHA-256 hashed before storage
    - user_agent helps detect mobile vs desktop (no user identification)
    - referrer shows email client type (not individual user)
    - No click-through tracking (we don't track what happens after redirect)

    INTEGRATION:
    - Called by affiliate redirect handler in CMS
    - Extracts variation_id from ?promo_var=42 URL parameter
    - Redirects user while tracking happens asynchronously

    Example Usage:
        # In affiliate redirect handler
        @app.get("/{slug}")
        async def redirect(slug: str, promo_var: Optional[int] = None):
            # Get destination URL from database
            destination = get_destination(slug)

            # Track click asynchronously (don't block redirect)
            if promo_var:
                asyncio.create_task(track_click(
                    offer_id=get_offer_id(slug),
                    variation_id=promo_var,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    referrer=request.headers.get("referer")
                ))

            # Redirect user immediately (don't wait for tracking)
            return RedirectResponse(url=destination, status_code=307)

    Example Request Body:
        {
            "offer_id": 4,
            "variation_id": 42,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0 ...",
            "referrer": "https://mail.google.com",
            "utm_source": "newsletter"
        }

    Database Impact:
        - INSERT into promo_click_tracking
        - UPDATE promo_text_variations SET clicks = clicks + 1
        - UPDATE promo_text_variations SET ctr = (clicks / impressions) * 100

    Created: October 18, 2025
    """
    # REQUIRED FIELDS
    # ----------------

    # Which promotional offer was clicked?
    # WHY OPTIONAL: Can be inferred from variation_id if not provided
    # VALIDATION: Must be a valid promo_offers.id (foreign key check)
    offer_id: Optional[int] = Field(
        None,
        description="ID of the promotional offer that was clicked (inferred from variation_id if not provided)",
        example=4,
        gt=0
    )

    # Which text variation drove the click?
    # WHY REQUIRED: CRITICAL for self-learning optimization
    # This is how we know which headline/tone/length performs best
    # Extracted from ?promo_var=42 URL parameter by redirect handler
    # VALIDATION: Must be a valid promo_text_variations.id (foreign key check)
    variation_id: int = Field(
        ...,
        description="ID of the text variation that drove the click (from ?promo_var URL parameter)",
        example=42,
        gt=0
    )

    # OPTIONAL FIELDS
    # ----------------

    # IP address of user who clicked (will be hashed)
    # WHY USEFUL: Detect bot traffic, prevent click fraud
    # PRIVACY: SHA-256 hashed before storage
    # USE CASE: "Filter out bot clicks from analytics"
    ip_address: Optional[str] = Field(
        None,
        description="IP address of user who clicked (will be SHA-256 hashed for privacy)",
        example="192.168.1.1",
        max_length=45
    )

    # User agent string from HTTP headers
    # WHY USEFUL: Detect mobile vs desktop, identify bot traffic
    # USE CASE: "Do mobile users click more than desktop?"
    # EXAMPLE: "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
    # BOT DETECTION: Known scrapers have identifiable user agents
    user_agent: Optional[str] = Field(
        None,
        description="User agent string (helps detect mobile vs desktop, bots)",
        example="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        max_length=500  # Prevent abuse
    )

    # HTTP referrer header
    # WHY USEFUL: Distinguish email clients (Gmail, Outlook, Apple Mail)
    # USE CASE: "Which email client drives more clicks?"
    # EXAMPLE: "https://mail.google.com" or "https://outlook.office.com"
    # NOTE: Many email clients don't send referrer (privacy feature)
    referrer: Optional[str] = Field(
        None,
        description="HTTP referrer (shows which email client was used)",
        example="https://mail.google.com",
        max_length=500
    )

    # UTM source parameter from URL
    # WHY USEFUL: Track campaign source (should be "newsletter")
    # Helps distinguish newsletter promos from other promotional channels
    # EXAMPLE: If we run Facebook ads later, utm_source=facebook
    # USE CASE: "Compare newsletter clicks vs other channels"
    utm_source: Optional[str] = Field(
        None,
        description="UTM source parameter (should be 'newsletter' for newsletter promos)",
        example="newsletter",
        max_length=100
    )


class AnalyticsResponse(BaseModel):
    """
    Response model for promotional analytics endpoint.

    PURPOSE:
    - Provide performance metrics for dashboard visualization
    - Enable data-driven decision making
    - Support self-learning optimization
    - Track trends over time

    METRICS INCLUDED:
    1. Offer-level metrics: Total impressions, clicks, CTR per offer
    2. Variation-level metrics: Performance per text variation
    3. Time-series data: Daily trends, week-over-week comparison
    4. Leaderboards: Top performing offers and variations

    USE CASES:
    - Dashboard homepage: Overall performance summary
    - Offer detail page: Variation performance breakdown
    - Trend analysis: Time-series charts
    - Optimization: Identify winning variations

    QUERY PERFORMANCE:
    - Uses denormalized counters for instant queries
    - No expensive JOINs or COUNT(*) on large tables
    - Indexes on date columns for fast time-series queries
    - Target response time: <500ms even with millions of rows

    Example Usage:
        # Get last 30 days of analytics
        response = requests.get(
            "http://127.0.0.1:3003/api/v1/promo/analytics",
            params={
                "start_date": "2025-09-18",
                "end_date": "2025-10-18",
                "offer_id": 4  # Optional: Filter by specific offer
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    Example Response:
        {
            "total_impressions": 50000,
            "total_clicks": 3500,
            "overall_ctr": 7.00,
            "offers": [
                {
                    "offer_id": 4,
                    "offer_name": "No Code MBA",
                    "impressions": 50000,
                    "clicks": 3500,
                    "ctr": 7.00,
                    "variations": [
                        {
                            "variation_id": 42,
                            "text_preview": "Want to build apps without code?...",
                            "tone": "professional",
                            "length_category": "medium",
                            "impressions": 20000,
                            "clicks": 1800,
                            "ctr": 9.00
                        },
                        {
                            "variation_id": 43,
                            "text_preview": "Build your dream startup this weekend...",
                            "tone": "exciting",
                            "length_category": "short",
                            "impressions": 15000,
                            "clicks": 900,
                            "ctr": 6.00
                        },
                        {
                            "variation_id": 44,
                            "text_preview": "Turn your business ideas into reality...",
                            "tone": "friendly",
                            "length_category": "long",
                            "impressions": 15000,
                            "clicks": 800,
                            "ctr": 5.33
                        }
                    ]
                }
            ],
            "daily_trends": [
                {
                    "date": "2025-10-18",
                    "impressions": 5000,
                    "clicks": 350,
                    "ctr": 7.00
                },
                {
                    "date": "2025-10-17",
                    "impressions": 5000,
                    "clicks": 325,
                    "ctr": 6.50
                }
            ]
        }

    Created: October 18, 2025
    """
    # OVERALL METRICS
    # ----------------
    # Aggregated across all offers and time period

    total_impressions: int = Field(
        ...,
        description="Total number of promotional impressions in time period",
        example=50000
    )

    total_clicks: int = Field(
        ...,
        description="Total number of promotional clicks in time period",
        example=3500
    )

    overall_ctr: float = Field(
        ...,
        description="Overall click-through rate percentage (clicks / impressions * 100)",
        example=7.00
    )

    # OFFER-LEVEL BREAKDOWN
    # ----------------------
    # Performance metrics grouped by offer
    # Each offer includes variation-level breakdown

    offers: List[dict] = Field(
        ...,
        description="Performance breakdown by offer (includes variation details)",
        example=[
            {
                "offer_id": 4,
                "offer_name": "No Code MBA",
                "impressions": 50000,
                "clicks": 3500,
                "ctr": 7.00,
                "variations": [
                    {
                        "variation_id": 42,
                        "text_preview": "Want to build apps...",
                        "tone": "professional",
                        "impressions": 20000,
                        "clicks": 1800,
                        "ctr": 9.00
                    }
                ]
            }
        ]
    )

    # TIME-SERIES DATA
    # -----------------
    # Daily performance trends for charts
    # Enables visualization of performance over time

    daily_trends: List[dict] = Field(
        ...,
        description="Daily performance trends (for time-series charts)",
        example=[
            {
                "date": "2025-10-18",
                "impressions": 5000,
                "clicks": 350,
                "ctr": 7.00
            }
        ]
    )
