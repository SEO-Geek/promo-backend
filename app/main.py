"""
Promotional Content Management System - FastAPI Application
Main application entry point with authentication and core endpoints
Created: October 16, 2025
Updated: October 17, 2025 - Added rate limiting
"""
from fastapi import FastAPI, HTTPException, Depends, status, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from datetime import datetime, timedelta
from typing import List
from pathlib import Path
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Internal imports
from app.config import settings
from app.database import db, get_db, Database
from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash
)
from app.ollama_service import OllamaService
from app.models import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    OfferCreate,
    OfferUpdate,
    OfferResponse,
    OfferListResponse,
    HealthCheckResponse,
    PromoContentResponse,
    TextGenerationRequest,
    TextVariationUpdate,
    TextVariationResponse,
    ImpressionTrackingRequest,
    ClickTrackingRequest,
    AnalyticsResponse
)
# Leonardo AI service and image models removed October 18, 2025
# Newsletter promo system uses text-only variations

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

# Initialize rate limiter with IP-based tracking
limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Promotional Content Management API",
    description="AI-powered newsletter promotional system with fail-safe architecture",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    logger.info("🚀 Starting Promotional Content Management System")
    await db.connect()
    logger.info("✅ Application started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown"""
    logger.info("Shutting down application")
    await db.disconnect()


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("5/minute")  # Strict limit to prevent brute force attacks
async def login(
    request: Request,
    credentials: LoginRequest,
    database: Database = Depends(get_db)
):
    """
    User login endpoint

    Returns JWT access token valid for 24 hours
    """
    user = await authenticate_user(credentials.email, credentials.password, database)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user['email']}
    )

    # Update last login
    await database.execute(
        "UPDATE promo_users SET last_login = $1 WHERE id = $2",
        datetime.utcnow(),
        user['id']
    )

    logger.info(f"✅ User logged in: {user['email']}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role']
        }
    }


@app.get("/api/v1/auth/me", response_model=UserResponse, tags=["Authentication"])
@limiter.limit("100/minute")  # Standard rate limit for authenticated queries
async def get_current_user_info(request: Request, current_user = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "role": current_user['role'],
        "last_login": current_user['last_login'],
        "created_at": current_user['created_at']
    }


# ============================================================================
# Health Check Endpoint (Fail-Safe System)
# ============================================================================

@app.get("/api/v1/promo/health", response_model=HealthCheckResponse, tags=["Fail-Safe"])
@limiter.limit("60/minute")  # Allow frequent health check polling
async def health_check(request: Request, database: Database = Depends(get_db)):
    """
    Comprehensive health check for fail-safe system

    Checks:
    - Database connectivity
    - Active offers availability
    - Approved content availability

    Returns health status for newsletter generation system
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
        "can_provide_content": True
    }

    # Check database
    try:
        await database.fetchval("SELECT 1")
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"failed: {str(e)}"
        health["status"] = "failed"
        health["can_provide_content"] = False

    # Check active offers
    try:
        active_count = await database.fetchval("""
            SELECT COUNT(*) FROM promo_offers
            WHERE status = 'active'
            AND (start_date IS NULL OR start_date <= NOW())
            AND (end_date IS NULL OR end_date >= NOW())
        """)

        if active_count > 0:
            health["components"]["active_offers"] = f"healthy ({active_count} offers)"
        else:
            health["components"]["active_offers"] = "degraded (no active offers)"
            health["status"] = "degraded"
            health["can_provide_content"] = False

    except Exception as e:
        health["components"]["active_offers"] = f"failed: {str(e)}"
        health["status"] = "failed"
        health["can_provide_content"] = False

    # Check approved content availability (text-only, images removed Oct 18, 2025)
    try:
        content_check = await database.fetchrow("""
            SELECT
                COUNT(DISTINCT o.id) as offers_with_content
            FROM promo_offers o
            WHERE o.status = 'active'
            AND (o.start_date IS NULL OR o.start_date <= NOW())
            AND (o.end_date IS NULL OR o.end_date >= NOW())
            AND EXISTS (
                SELECT 1 FROM promo_text_variations t
                WHERE t.offer_id = o.id AND t.approved = TRUE
            )
        """)

        if content_check['offers_with_content'] > 0:
            health["components"]["approved_content"] = f"healthy ({content_check['offers_with_content']} ready)"
        else:
            health["components"]["approved_content"] = "degraded (no approved content)"
            health["status"] = "degraded"
            health["can_provide_content"] = False

    except Exception as e:
        health["components"]["approved_content"] = f"failed: {str(e)}"
        health["status"] = "failed"
        health["can_provide_content"] = False

    status_code = 200 if health["status"] == "healthy" else 503

    return JSONResponse(content=health, status_code=status_code)


# ============================================================================
# Newsletter Integration Endpoint (NO AUTH - Called by newsletter system)
# ============================================================================

@app.get("/api/v1/promo/select-random", response_model=PromoContentResponse, tags=["Newsletter"])
@limiter.limit("120/minute")  # High limit for automated newsletter generation
async def select_random_promo(request: Request, database: Database = Depends(get_db)):
    """
    Select random promotional content for newsletter

    **NO AUTHENTICATION REQUIRED** - Called by newsletter generation system

    Selection Algorithm:
    - Only active offers (status='active')
    - Only offers within date range (start_date <= NOW <= end_date)
    - Only offers with approved text variations
    - Weighted random selection (higher weight = higher probability)

    Returns:
        PromoContentResponse with offer info and selected text variation

    Fail-Safe:
        Returns 503 with null data if no offers available
        Newsletter system will send without promo (5-second timeout)
    """
    try:
        # STEP 1: Query for eligible offers
        # -----------------------------------
        # We need offers that meet ALL these criteria:
        # - Active status (manually set by user in dashboard)
        # - Within date range (optional start/end dates for seasonal offers)
        # - Has at least one approved text variation (can't show offer without copy)
        #
        # Why DISTINCT? Technically not needed since we're selecting from offers table,
        # but included as defensive programming in case future JOIN logic changes.
        #
        # Why include weight? Used for weighted random selection - higher weight =
        # higher probability of selection. Allows user to prioritize certain offers.
        eligible_offers = await database.fetch("""
            SELECT DISTINCT
                o.id,
                o.name,
                o.offer_type,        -- 'review' or 'affiliate' (added Oct 18, 2025)
                o.affiliate_slug,    -- Used to build tracking link
                o.weight,            -- For weighted random selection
                o.destination_url
            FROM promo_offers o
            WHERE o.status = 'active'
            AND (o.start_date IS NULL OR o.start_date <= NOW())  -- NULL = no start constraint
            AND (o.end_date IS NULL OR o.end_date >= NOW())      -- NULL = no end constraint
            AND EXISTS (
                -- CRITICAL: Offer must have approved content to be selectable
                -- This prevents showing offers with only draft variations
                SELECT 1 FROM promo_text_variations t
                WHERE t.offer_id = o.id AND t.approved = TRUE
            )
        """)

        # STEP 2: Handle no eligible offers (fail-safe behavior)
        # -------------------------------------------------------
        # If no offers are eligible, return 503 with null data.
        # Newsletter system has 5-second timeout on this endpoint and will
        # send newsletter WITHOUT promo content if this happens.
        #
        # This is by design - we prioritize newsletter delivery over promo inclusion.
        # Better to send newsletter without promo than to delay/fail the entire send.
        if not eligible_offers:
            logger.warning("⚠️ No eligible offers for newsletter selection")
            return JSONResponse(
                content={
                    "offer_id": None,
                    "name": None,
                    "offer_type": None,
                    "affiliate_slug": None,
                    "approved_text": None,
                    "message": "No active offers available"
                },
                status_code=503  # Service Unavailable - tells newsletter to skip promo
            )

        # STEP 3: Weighted random selection of offer
        # -------------------------------------------
        # Algorithm: Each offer has a weight (default 1, user-configurable).
        # Higher weight = higher probability of selection.
        #
        # Example: Offers with weights [10, 5, 1]
        # - Total weight = 16
        # - Random number between 0 and 16
        # - 0-10 → selects offer 1 (62.5% chance)
        # - 10-15 → selects offer 2 (31.25% chance)
        # - 15-16 → selects offer 3 (6.25% chance)
        #
        # This allows user to prioritize high-value offers without completely
        # excluding lower-priority offers (maintains variety).
        import random
        total_weight = sum(offer['weight'] for offer in eligible_offers)
        rand = random.uniform(0, total_weight)

        cumulative_weight = 0
        selected_offer = None

        for offer in eligible_offers:
            cumulative_weight += offer['weight']
            if rand <= cumulative_weight:
                selected_offer = offer
                break

        # Defensive fallback: If somehow no offer selected (floating point rounding?),
        # just use the first eligible offer. This should never happen in practice.
        if not selected_offer:
            selected_offer = eligible_offers[0]
            logger.warning(f"⚠️ Weighted selection failed, using first offer as fallback")

        # STEP 4: Select random text variation for the chosen offer
        # ----------------------------------------------------------
        # Why random selection? This is the variation rotation system.
        # - Offer may have 3-8 AI-generated text variations (different headlines/copy)
        # - Each newsletter send randomly picks one variation
        # - Same product, fresh copy every time
        # - Reduces subscriber fatigue from seeing identical promos
        # - Enables A/B testing of copywriting styles
        #
        # ORDER BY RANDOM() is PostgreSQL-specific and efficient for small result sets.
        # Since we LIMIT 1, this is very fast (<1ms typically).
        text_variations = await database.fetch("""
            SELECT id, text_content, cta_text, tone, length_category
            FROM promo_text_variations
            WHERE offer_id = $1 AND approved = TRUE
            ORDER BY RANDOM()  -- Random selection for variation rotation
            LIMIT 1
        """, selected_offer['id'])

        # STEP 5: Handle data integrity issue (should never happen)
        # ----------------------------------------------------------
        # We already verified in STEP 1 that this offer has approved text.
        # If we somehow don't find any here, it's a race condition or database issue.
        # Fail gracefully and log for investigation.
        if not text_variations:
            logger.error(f"❌ Offer {selected_offer['id']} has no approved text (data integrity issue)")
            return JSONResponse(
                content={
                    "offer_id": None,
                    "name": None,
                    "offer_type": None,
                    "affiliate_slug": None,
                    "approved_text": None,
                    "message": "Selected offer has no approved content"
                },
                status_code=503
            )

        selected_text = text_variations[0]

        # STEP 6: Build tracking link with variation ID
        # ----------------------------------------------
        # Link format depends on offer type:
        #
        # REVIEW OFFERS:
        # - Direct link to internal review article
        # - Example: https://aidailypost.com/review/no-code-mba
        # - Drives traffic to our own content, builds authority
        #
        # AFFILIATE OFFERS:
        # - Cloaked redirect link (handled by CMS affiliate link system)
        # - Example: https://aidailypost.com/nocodemba → external destination
        # - Looks like internal link but redirects to affiliate URL
        # - CMS handles the actual redirect (existing system)
        #
        # TRACKING PARAMETERS:
        # - utm_source=newsletter: Standard UTM tracking
        # - promo_var={variation_id}: CRITICAL for variation performance tracking
        #   This allows us to track which specific text variation drove the click.
        #   Future Phase 3.1: Affiliate redirect will extract this and log asynchronously.
        #   Future Phase 3.2: Use this data for self-learning optimization.
        base_domain = "https://aidailypost.com"
        if selected_offer['offer_type'] == 'review':
            link = f"{base_domain}/review/{selected_offer['affiliate_slug']}"
        else:
            link = f"{base_domain}/{selected_offer['affiliate_slug']}"

        # Add tracking parameters (will be URL-encoded by HTTP client)
        link += f"?utm_source=newsletter&promo_var={selected_text['id']}"

        # STEP 7: Log successful selection for monitoring/debugging
        # ----------------------------------------------------------
        # This log line is crucial for:
        # - Verifying system is working correctly
        # - Debugging if users report seeing wrong offers
        # - Analytics on which offers are being selected
        # - Audit trail for business intelligence
        logger.info(
            f"✅ Newsletter promo selected: Offer {selected_offer['id']} ({selected_offer['name']}) "
            f"with text variation {selected_text['id']}"
        )

        # STEP 8: Return complete promo content for newsletter
        # -----------------------------------------------------
        # This response is consumed directly by the newsletter generation system.
        # Newsletter template will inject this into HTML email after first 2-3 stories.
        #
        # Response format matches PromoContentResponse model (text-only as of Oct 18, 2025):
        # - No image_url (removed from model)
        # - Includes variation_id for tracking
        # - Includes offer_type for proper link handling
        return {
            "offer_id": selected_offer['id'],
            "offer_name": selected_offer['name'],
            "offer_type": selected_offer['offer_type'],
            "text": selected_text['text_content'],
            "cta": selected_text['cta_text'],
            "link": link,
            "variation_id": selected_text['id']
        }

    except Exception as e:
        # EXCEPTION HANDLER: Catch-all for unexpected errors
        # ---------------------------------------------------
        # If ANYTHING goes wrong (database connection, query error, etc.),
        # fail gracefully with 503 so newsletter can proceed without promo.
        #
        # This is critical - we NEVER want promo system to break newsletter delivery.
        # Newsletter system has 5-second timeout, so even slow queries will trigger this.
        logger.error(f"❌ Failed to select newsletter promo: {e}")
        return JSONResponse(
            content={
                "offer_id": None,
                "name": None,
                "offer_type": None,
                "affiliate_slug": None,
                "approved_text": None,
                "message": f"Selection failed: {str(e)}"
            },
            status_code=503  # Service Unavailable - newsletter will skip promo
        )


# ============================================================================
# Offer Management Endpoints (CRUD)
# ============================================================================

@app.post("/api/v1/offers", response_model=OfferResponse, tags=["Offers"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def create_offer(
    request: Request,
    offer: OfferCreate,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Create a new promotional offer

    Requires authentication. Creates offer in 'draft' status by default.
    """
    try:
        result = await database.fetchrow("""
            INSERT INTO promo_offers (
                name, description, offer_type, destination_url, affiliate_slug,
                status, start_date, end_date, priority, weight,
                created_by, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
            RETURNING id, name, description, offer_type, destination_url, affiliate_slug, status,
                      start_date, end_date, priority, weight,
                      total_impressions, total_clicks, ctr,
                      created_at, updated_at
        """, offer.name, offer.description, offer.offer_type, str(offer.destination_url),
            offer.affiliate_slug, offer.status, offer.start_date, offer.end_date,
            offer.priority, offer.weight, current_user['id']
        )

        logger.info(f"✅ Offer created: {result['name']} (ID: {result['id']}) by {current_user['email']}")

        return dict(result)

    except Exception as e:
        logger.error(f"Failed to create offer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create offer: {str(e)}")


@app.get("/api/v1/offers", response_model=OfferListResponse, tags=["Offers"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def list_offers(
    request: Request,
    status_filter: str = None,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    List all promotional offers

    Optional filter by status: active, paused, ended, draft
    """
    try:
        # Build query with parameterized WHERE clause to prevent SQL injection
        query = """
            SELECT id, name, description, offer_type, destination_url, affiliate_slug, status,
                   start_date, end_date, priority, weight,
                   total_impressions, total_clicks, ctr,
                   created_at, updated_at
            FROM promo_offers
        """

        params = []
        if status_filter:
            query += " WHERE status = $1"
            params.append(status_filter)

        query += " ORDER BY priority DESC, created_at DESC"

        offers = await database.fetch(query, *params)

        return {
            "offers": [dict(offer) for offer in offers],
            "total": len(offers)
        }

    except Exception as e:
        logger.error(f"Failed to list offers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list offers: {str(e)}")


@app.get("/api/v1/offers/{offer_id}", response_model=OfferResponse, tags=["Offers"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def get_offer(
    request: Request,
    offer_id: int,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Get a single promotional offer by ID

    Includes full details and statistics
    """
    try:
        offer = await database.fetchrow("""
            SELECT id, name, description, offer_type, destination_url, affiliate_slug, status,
                   start_date, end_date, priority, weight,
                   total_impressions, total_clicks, ctr,
                   created_at, updated_at
            FROM promo_offers
            WHERE id = $1
        """, offer_id)

        if not offer:
            raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

        return dict(offer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get offer: {str(e)}")


@app.put("/api/v1/offers/{offer_id}", response_model=OfferResponse, tags=["Offers"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def update_offer(
    request: Request,
    offer_id: int,
    offer: OfferUpdate,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Update an existing promotional offer

    Only provided fields will be updated
    """
    try:
        # Build dynamic UPDATE query
        updates = []
        params = []
        param_count = 1

        if offer.name is not None:
            updates.append(f"name = ${param_count}")
            params.append(offer.name)
            param_count += 1

        if offer.description is not None:
            updates.append(f"description = ${param_count}")
            params.append(offer.description)
            param_count += 1

        if offer.offer_type is not None:
            updates.append(f"offer_type = ${param_count}")
            params.append(offer.offer_type)
            param_count += 1

        if offer.destination_url is not None:
            updates.append(f"destination_url = ${param_count}")
            params.append(str(offer.destination_url))
            param_count += 1

        if offer.affiliate_slug is not None:
            updates.append(f"affiliate_slug = ${param_count}")
            params.append(offer.affiliate_slug)
            param_count += 1

        if offer.status is not None:
            updates.append(f"status = ${param_count}")
            params.append(offer.status)
            param_count += 1

        if offer.start_date is not None:
            updates.append(f"start_date = ${param_count}")
            params.append(offer.start_date)
            param_count += 1

        if offer.end_date is not None:
            updates.append(f"end_date = ${param_count}")
            params.append(offer.end_date)
            param_count += 1

        if offer.priority is not None:
            updates.append(f"priority = ${param_count}")
            params.append(offer.priority)
            param_count += 1

        if offer.weight is not None:
            updates.append(f"weight = ${param_count}")
            params.append(offer.weight)
            param_count += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.append(offer_id)

        query = f"""
            UPDATE promo_offers
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING id, name, description, offer_type, destination_url, affiliate_slug, status,
                      start_date, end_date, priority, weight,
                      total_impressions, total_clicks, ctr,
                      created_at, updated_at
        """

        result = await database.fetchrow(query, *params)

        if not result:
            raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

        logger.info(f"✅ Offer updated: {result['name']} (ID: {result['id']}) by {current_user['email']}")

        return dict(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update offer: {str(e)}")


@app.delete("/api/v1/offers/{offer_id}", tags=["Offers"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def delete_offer(
    request: Request,
    offer_id: int,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Delete a promotional offer (TEXT-ONLY SYSTEM)

    Cascades to delete all associated text variations and tracking data.
    NOTE: Images removed Oct 18, 2025 - newsletter promo system is text-only.
    """
    try:
        # Get offer name before deletion
        offer = await database.fetchrow(
            "SELECT name FROM promo_offers WHERE id = $1",
            offer_id
        )

        if not offer:
            raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

        await database.execute(
            "DELETE FROM promo_offers WHERE id = $1",
            offer_id
        )

        logger.info(f"✅ Offer deleted: {offer['name']} (ID: {offer_id}) by {current_user['email']}")

        return {
            "success": True,
            "message": f"Offer '{offer['name']}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete offer: {str(e)}")


# ============================================================================
# Newsletter Preview Endpoint
# ============================================================================

@app.get("/api/v1/promo/preview/{offer_id}", tags=["Preview"])
@limiter.limit("50/minute")  # Moderate limit for preview generation
async def preview_newsletter(
    request: Request,
    offer_id: int,
    text_id: int = None,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Preview how a promotional offer will look in the newsletter (TEXT-ONLY)

    If text_id is not provided, uses first approved text variation.
    Returns HTML ready to be displayed in an iframe or new window.

    NOTE: Images removed Oct 18, 2025 - newsletter promo system is text-only.
    """
    try:
        # Get offer details
        offer = await database.fetchrow("""
            SELECT id, name, description, destination_url
            FROM promo_offers
            WHERE id = $1
        """, offer_id)

        if not offer:
            raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

        # Get text variation (use provided ID or first approved text variation)
        # WHY: Text-only promo system (images removed Oct 18, 2025)
        if text_id:
            text = await database.fetchrow("""
                SELECT text_content, cta_text
                FROM promo_text_variations
                WHERE id = $1 AND offer_id = $2
            """, text_id, offer_id)
        else:
            text = await database.fetchrow("""
                SELECT text_content, cta_text
                FROM promo_text_variations
                WHERE offer_id = $1 AND approved = TRUE
                ORDER BY created_at ASC
                LIMIT 1
            """, offer_id)

        # VALIDATION: Ensure offer has approved text variation
        # WHY: Can't preview newsletter without text content
        if not text:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing content",
                    "message": "This offer needs at least one approved text variation",
                    "has_text": False
                }
            )

        # Generate preview HTML (newsletter template)
        preview_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Preview: {offer['name']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f4f4f4;
            margin: 0;
            padding: 20px;
        }}
        .newsletter-container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .promo-section {{
            padding: 30px 20px;
            background: linear-gradient(to bottom, #f8f9ff 0%, white 100%);
            border-bottom: 3px solid #667eea;
        }}
        .promo-label {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 15px;
        }}
        .promo-text {{
            font-size: 16px;
            line-height: 1.8;
            color: #2d3748;
            margin-bottom: 20px;
        }}
        .promo-cta {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 16px;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .promo-cta:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }}
        .content-section {{
            padding: 30px 20px;
        }}
        .content-section h2 {{
            color: #1a202c;
            margin-top: 0;
            font-size: 24px;
        }}
        .article {{
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .article:last-child {{
            border-bottom: none;
        }}
        .article h3 {{
            color: #2d3748;
            margin: 0 0 8px 0;
            font-size: 18px;
        }}
        .article p {{
            color: #4a5568;
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .article a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
        }}
        .footer {{
            background: #2d3748;
            color: #cbd5e0;
            padding: 30px 20px;
            text-align: center;
            font-size: 13px;
        }}
        .preview-badge {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f59e0b;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div class="preview-badge">📧 PREVIEW MODE</div>

    <div class="newsletter-container">
        <!-- Header -->
        <div class="header">
            <h1>AI Daily Post</h1>
            <p>Monday, October 16, 2025 | Your Daily AI News Briefing</p>
        </div>

        <!-- Promotional Section -->
        <div class="promo-section">
            <span class="promo-label">⭐ Featured</span>

            <!-- Image removed Oct 18, 2025: Text-only promo system -->

            <div class="promo-text">
                {text['text_content']}
            </div>

            <a href="{offer['destination_url']}" class="promo-cta">
                {text['cta_text'] or 'Learn More →'}
            </a>
        </div>

        <!-- Sample Newsletter Content -->
        <div class="content-section">
            <h2>📰 Today's Top Stories</h2>

            <div class="article">
                <h3>OpenAI Announces GPT-5 Breakthrough</h3>
                <p>OpenAI has unveiled significant improvements in its latest language model, featuring enhanced reasoning capabilities and multimodal understanding.</p>
                <a href="#">Read More →</a>
            </div>

            <div class="article">
                <h3>Meta Releases Open-Source AI Research Tools</h3>
                <p>Meta's AI research division has open-sourced a suite of tools designed to accelerate machine learning research and development.</p>
                <a href="#">Read More →</a>
            </div>

            <div class="article">
                <h3>AI Regulation Framework Gains Support</h3>
                <p>The European Union's proposed AI Act receives backing from major tech companies, setting new standards for AI development.</p>
                <a href="#">Read More →</a>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>AI Daily Post</strong></p>
            <p>Curated AI news delivered to your inbox every weekday</p>
            <p style="margin-top: 15px; opacity: 0.7;">© 2025 AI Daily Post. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        logger.info(f"📧 Preview generated for offer {offer_id} by {current_user['email']}")

        # RESPONSE: Return preview HTML and metadata (text-only)
        # WHY: Newsletter promo system is text-only (images removed Oct 18, 2025)
        return JSONResponse(
            content={
                "html": preview_html,
                "offer": dict(offer),
                "text_used": dict(text)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate preview for offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


# ============================================================================
# Text Generation Endpoints (Ollama AI)
# ============================================================================

@app.post("/api/v1/offers/{offer_id}/generate-text", tags=["Text"])
@limiter.limit("20/hour")  # More generous than images but still limited for AI operations
async def generate_text_variations(
    http_request: Request,
    offer_id: int,
    request: TextGenerationRequest,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Generate promotional text variations using Ollama AI

    Creates multiple text variations with different wording but same message.
    Typically completes in 10-20 seconds.
    """
    try:
        # Verify offer exists
        offer = await database.fetchrow(
            "SELECT id, name, description, destination_url FROM promo_offers WHERE id = $1",
            offer_id
        )

        if not offer:
            raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

        # Create generation job record
        import json
        job = await database.fetchrow("""
            INSERT INTO promo_generation_jobs (
                offer_id, job_type, status, parameters,
                started_at, created_at
            ) VALUES ($1, 'text', 'processing', $2::jsonb, NOW(), NOW())
            RETURNING id
        """, offer_id, json.dumps(request.dict()))

        job_id = job['id']

        try:
            # Initialize Ollama service
            ollama = OllamaService()

            # Generate text variations
            logger.info(f"✍️  Starting text generation for offer {offer_id}")
            variations = await ollama.generate_text_variations(
                offer_name=offer['name'],
                offer_description=offer['description'] or '',
                destination_url=str(offer['destination_url']),
                tone=request.tone,
                length_category=request.length_category,
                num_variations=request.num_variations
            )

            # Store variations in database
            generated_texts = []
            for variation in variations:
                db_text = await database.fetchrow("""
                    INSERT INTO promo_text_variations (
                        offer_id, text_content, cta_text,
                        tone, length_category, approved,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, FALSE, NOW())
                    RETURNING id, text_content, cta_text, approved, created_at
                """, offer_id, variation.get('text', ''), variation.get('cta', ''),
                    request.tone, request.length_category)

                generated_texts.append(dict(db_text))

            # Update job status
            await database.execute("""
                UPDATE promo_generation_jobs
                SET status = 'completed',
                    generated_count = $1,
                    completed_at = NOW(),
                    duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INT
                WHERE id = $2
            """, len(generated_texts), job_id)

            logger.info(f"✅ Generated {len(generated_texts)} text variations for offer {offer_id} by {current_user['email']}")

            return {
                "success": True,
                "offer_id": offer_id,
                "job_id": job_id,
                "variations_generated": len(generated_texts),
                "variations": generated_texts
            }

        except Exception as gen_error:
            # Update job with error
            await database.execute("""
                UPDATE promo_generation_jobs
                SET status = 'failed',
                    error_message = $1,
                    completed_at = NOW(),
                    duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INT
                WHERE id = $2
            """, str(gen_error), job_id)

            raise gen_error

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text generation failed for offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")


@app.get("/api/v1/offers/{offer_id}/texts", response_model=List[TextVariationResponse], tags=["Text"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def list_offer_texts(
    request: Request,
    offer_id: int,
    approved_only: bool = False,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    List all text variations for a promotional offer

    Optional filter to show only approved texts
    """
    try:
        query = """
            SELECT id, offer_id, text_content, cta_text,
                   tone, length_category, approved,
                   times_used, total_clicks, ctr,
                   created_at
            FROM promo_text_variations
            WHERE offer_id = $1
        """

        if approved_only:
            query += " AND approved = TRUE"

        query += " ORDER BY created_at DESC"

        texts = await database.fetch(query, offer_id)

        return [dict(text) for text in texts]

    except Exception as e:
        logger.error(f"Failed to list texts for offer {offer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list texts: {str(e)}")


@app.put("/api/v1/texts/{text_id}/approve", response_model=TextVariationResponse, tags=["Text"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def approve_text(
    request: Request,
    text_id: int,
    approve: bool = True,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Approve or unapprove a promotional text variation

    Only approved texts can be used in newsletters
    """
    try:
        result = await database.fetchrow("""
            UPDATE promo_text_variations
            SET approved = $1
            WHERE id = $2
            RETURNING id, offer_id, text_content, cta_text,
                      tone, length_category, approved,
                      times_used, total_clicks, ctr,
                      created_at
        """, approve, text_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Text {text_id} not found")

        action = "approved" if approve else "unapproved"
        logger.info(f"✅ Text {text_id} {action} by {current_user['email']}")

        return dict(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve text {text_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve text: {str(e)}")


@app.put("/api/v1/texts/{text_id}", response_model=TextVariationResponse, tags=["Text"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def update_text(
    request: Request,
    text_id: int,
    update_data: TextVariationUpdate,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Update promotional text variation (user adjustments)

    Enables the "Generate → Review → ADJUST → Approve" workflow.
    User can manually edit AI-generated text before approval.

    **Use Cases:**
    - Fix typos in AI-generated text
    - Adjust phrasing to match brand voice
    - Add/remove details based on offer changes
    - Customize CTA button text
    - Reclassify tone/length after edits

    **What Can Be Updated:**
    - text_content: The promotional text (required, 10-1000 chars)
    - cta_text: Call-to-action button (optional, 3-50 chars)
    - tone: Tone classification (optional)
    - length_category: Length classification (optional)

    **What CANNOT Be Updated:**
    - approved flag (use /approve endpoint)
    - performance metrics (impressions, clicks, CTR)
    - creation timestamp

    **Example Request:**
    ```json
    {
        "text_content": "Flash Sale! 50% off all courses this weekend only. Don't miss out!",
        "cta_text": "Shop Now",
        "tone": "urgent",
        "length_category": "short"
    }
    ```

    **Response:** Updated TextVariationResponse with all fields
    """
    try:
        # Verify text exists
        existing = await database.fetchrow(
            "SELECT id, offer_id FROM promo_text_variations WHERE id = $1",
            text_id
        )

        if not existing:
            raise HTTPException(status_code=404, detail=f"Text variation {text_id} not found")

        # Build UPDATE query dynamically (only update provided fields)
        update_fields = ["text_content = $1"]
        params = [update_data.text_content]
        param_count = 2

        if update_data.cta_text is not None:
            update_fields.append(f"cta_text = ${param_count}")
            params.append(update_data.cta_text)
            param_count += 1

        if update_data.tone is not None:
            update_fields.append(f"tone = ${param_count}")
            params.append(update_data.tone)
            param_count += 1

        if update_data.length_category is not None:
            update_fields.append(f"length_category = ${param_count}")
            params.append(update_data.length_category)
            param_count += 1

        # Add text_id as last parameter
        params.append(text_id)

        # Execute UPDATE
        query = f"""
            UPDATE promo_text_variations
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, offer_id, text_content, cta_text,
                      tone, length_category, approved,
                      impressions as times_used,
                      clicks as total_clicks,
                      ctr,
                      created_at
        """

        result = await database.fetchrow(query, *params)

        logger.info(f"✅ Text {text_id} updated by {current_user['email']}")
        logger.debug(f"Updated fields: {', '.join([f.split(' = ')[0] for f in update_fields])}")

        return dict(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update text {text_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update text: {str(e)}")


@app.delete("/api/v1/texts/{text_id}", tags=["Text"])
@limiter.limit("100/minute")  # Standard CRUD operation limit
async def delete_text(
    request: Request,
    text_id: int,
    current_user = Depends(get_current_user),
    database: Database = Depends(get_db)
):
    """
    Delete a promotional text variation

    Removes from database
    """
    try:
        # Get text info before deletion
        text = await database.fetchrow(
            "SELECT offer_id, text_content FROM promo_text_variations WHERE id = $1",
            text_id
        )

        if not text:
            raise HTTPException(status_code=404, detail=f"Text {text_id} not found")

        # Delete from database
        await database.execute(
            "DELETE FROM promo_text_variations WHERE id = $1",
            text_id
        )

        logger.info(f"✅ Text {text_id} deleted by {current_user['email']}")

        return {
            "success": True,
            "message": f"Text variation deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete text {text_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete text: {str(e)}")


# ============================================================================
# TRACKING ENDPOINTS - Phase 3.1 (October 18, 2025)
# ============================================================================
# PURPOSE: Track newsletter promo impressions and clicks for analytics
#
# ENDPOINTS:
# 1. POST /api/v1/promo/track-impression - When promo shown in newsletter
# 2. POST /api/v1/promo/track-click - When user clicks promo link
# 3. GET /api/v1/promo/analytics - Performance metrics and trends
#
# INTEGRATION POINTS:
# - Newsletter system calls track-impression after newsletter send
# - Affiliate redirect calls track-click on link click (async)
# - Dashboard calls analytics for performance charts
#
# PRIVACY & PERFORMANCE:
# - No PII stored (IP hashed, no user IDs)
# - Fast response times (<50ms for tracking, <500ms for analytics)
# - Non-blocking (newsletter/redirect never waits)
# - GDPR compliant (aggregate data only)
# ============================================================================

@app.post("/api/v1/promo/track-impression", status_code=204, tags=["Tracking"])
@limiter.limit("200/minute")  # High limit for newsletter sends (multiple impressions per send)
async def track_impression(
    request: Request,
    tracking: ImpressionTrackingRequest,
    database: Database = Depends(get_db)
):
    """
    Track promotional content impression (when shown in newsletter)

    **NO AUTHENTICATION REQUIRED** - Called by newsletter system

    PURPOSE:
    - Record when promotional content is displayed in a newsletter
    - Provide denominator for CTR calculation (clicks / impressions)
    - Enable time-series analysis of newsletter performance
    - Support A/B testing of text variations

    WORKFLOW:
    1. Newsletter system calls GET /select-random to get promo
    2. Newsletter compiles HTML email with promo content
    3. Newsletter calls THIS endpoint to track impression
    4. Backend writes to promo_impression_tracking table
    5. Database trigger increments promo_text_variations.impressions
    6. Database trigger recalculates CTR
    7. Newsletter sends to subscribers

    CRITICAL REQUIREMENTS:
    - Response time MUST be <50ms (doesn't block newsletter send)
    - Newsletter has 5-second timeout on this call
    - If tracking fails, newsletter STILL sends (fail-safe design)

    PRIVACY:
    - IP address is SHA-256 hashed before storage (if provided)
    - No user identification or tracking
    - Only aggregate metrics collected
    - GDPR compliant

    Request Body:
        {
            "offer_id": 4,
            "variation_id": 42,
            "newsletter_send_id": "2025-10-18-daily",  # Optional
            "subscriber_count": 5000,                   # Optional
            "ip_address": "192.168.1.1"                # Optional, will be hashed
        }

    Response:
        204 No Content (success, no response body)

    Error Responses:
        400: Invalid request (missing required fields)
        500: Database error (logged, but newsletter continues sending)

    Database Impact:
        - INSERT into promo_impression_tracking
        - UPDATE promo_text_variations SET impressions = impressions + 1
        - UPDATE promo_text_variations SET ctr = (clicks / impressions) * 100

    Created: October 18, 2025
    """
    try:
        # STEP 1: Hash IP address for privacy (if provided)
        # --------------------------------------------------
        # WHY: GDPR compliance - never store plain IP addresses
        # HOW: SHA-256 one-way hash (can't reverse to get real IP)
        # USE CASE: Detect bot traffic, prevent fraud (not user tracking)
        ip_hash = None
        if tracking.ip_address:
            import hashlib
            ip_hash = hashlib.sha256(tracking.ip_address.encode()).hexdigest()
            logger.debug(f"Hashed IP: {tracking.ip_address[:10]}... → {ip_hash[:10]}...")

        # STEP 2: Insert impression record into database
        # -----------------------------------------------
        # WHY: Need permanent record of each impression for analytics
        # DATABASE TRIGGER: Automatically increments variation.impressions counter
        # PERFORMANCE: Single INSERT, ~10-20ms typical response time
        await database.execute("""
            INSERT INTO promo_impression_tracking (
                offer_id,
                variation_id,
                newsletter_send_id,
                ip_hash,
                subscriber_count,
                tracked_at,
                tracked_date
            ) VALUES ($1, $2, $3, $4, $5, NOW(), CURRENT_DATE)
        """, tracking.offer_id, tracking.variation_id,
             tracking.newsletter_send_id, ip_hash, tracking.subscriber_count)

        # STEP 3: Log successful tracking (for debugging and monitoring)
        # --------------------------------------------------------------
        # WHY: Helps diagnose issues ("Was impression recorded?")
        # EXAMPLE LOG: "✅ Tracked impression: offer=4, var=42, newsletter=2025-10-18-daily"
        logger.info(
            f"✅ Tracked impression: "
            f"offer={tracking.offer_id}, "
            f"variation={tracking.variation_id}, "
            f"newsletter={tracking.newsletter_send_id or 'unknown'}"
        )

        # STEP 4: Return 204 No Content (fast, no response body)
        # -------------------------------------------------------
        # WHY 204? Standard for successful POST/PUT with no response data
        # PERFORMANCE: No JSON serialization needed (faster than 200 OK)
        # NEWSLETTER: Can ignore response (fire-and-forget pattern)
        return Response(status_code=204)

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise

    except Exception as e:
        # STEP 5: Error handling (log but don't fail newsletter)
        # -------------------------------------------------------
        # WHY CRITICAL: Newsletter MUST continue sending even if tracking fails
        # BEHAVIOR: Log error, return 500, but newsletter ignores this
        # MONITORING: Check logs for recurring impression tracking failures
        logger.error(
            f"❌ Failed to track impression: "
            f"offer={tracking.offer_id}, "
            f"variation={tracking.variation_id}, "
            f"error={str(e)}"
        )

        # Return 500 but newsletter continues (has timeout)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track impression: {str(e)}"
        )


@app.post("/api/v1/promo/track-click", status_code=204, tags=["Tracking"])
@limiter.limit("500/minute")  # Higher limit - users can click multiple times
async def track_click(
    request: Request,
    tracking: ClickTrackingRequest,
    database: Database = Depends(get_db)
):
    """
    Track promotional link click (when user clicks CTA)

    **NO AUTHENTICATION REQUIRED** - Called by affiliate redirect handler

    PURPOSE:
    - Record when users click promotional links
    - Provide numerator for CTR calculation (clicks / impressions)
    - Enable conversion funnel analysis
    - Support self-learning optimization (which variations perform best?)

    WORKFLOW:
    1. User clicks link: https://aidailypost.com/nocodemba?promo_var=42
    2. Affiliate redirect handler extracts promo_var=42 from URL
    3. Redirect handler calls THIS endpoint asynchronously
    4. Backend writes to promo_click_tracking table (this endpoint)
    5. Database trigger increments promo_text_variations.clicks
    6. Database trigger recalculates CTR
    7. User is redirected to destination (doesn't wait for tracking)

    CRITICAL REQUIREMENTS:
    - Response time MUST be <50ms (doesn't block redirect)
    - Redirect happens IMMEDIATELY (fire-and-forget pattern)
    - User never waits for tracking to complete
    - Async call from redirect handler (asyncio.create_task)

    PRIVACY:
    - IP address is SHA-256 hashed before storage (if provided)
    - user_agent helps detect mobile vs desktop (not user identification)
    - referrer shows email client type (not individual user)
    - No click-through tracking (don't track what happens after)
    - GDPR compliant

    Request Body:
        {
            "offer_id": 4,
            "variation_id": 42,
            "ip_address": "192.168.1.1",           # Optional, will be hashed
            "user_agent": "Mozilla/5.0 ...",       # Optional
            "referrer": "https://mail.google.com", # Optional
            "utm_source": "newsletter"             # Optional
        }

    Response:
        204 No Content (success, no response body)

    Error Responses:
        400: Invalid request (missing required fields)
        500: Database error (logged, but redirect continues)

    Database Impact:
        - INSERT into promo_click_tracking
        - UPDATE promo_text_variations SET clicks = clicks + 1
        - UPDATE promo_text_variations SET ctr = (clicks / impressions) * 100

    Analytics Use Cases:
        - "Which text variation drives most clicks?"
        - "Do mobile users click more than desktop?"
        - "Which email clients drive more engagement?"
        - "What time of day gets most clicks?"

    Created: October 18, 2025
    """
    try:
        # STEP 1: Lookup offer_id from variation_id if not provided
        # ----------------------------------------------------------
        # WHY: Simplifies affiliate redirect handler (only needs variation_id)
        # USE CASE: Redirect handler extracts promo_var from URL, doesn't know offer_id
        offer_id = tracking.offer_id
        if not offer_id:
            # Query variation to get its offer_id
            result = await database.fetchrow("""
                SELECT offer_id FROM promo_text_variations
                WHERE id = $1
            """, tracking.variation_id)

            if not result:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid variation_id: {tracking.variation_id}"
                )

            offer_id = result['offer_id']

        # STEP 2: Hash IP address for privacy (if provided)
        # --------------------------------------------------
        # WHY: GDPR compliance - never store plain IP addresses
        # USE CASE: Bot detection, click fraud prevention
        ip_hash = None
        if tracking.ip_address:
            import hashlib
            ip_hash = hashlib.sha256(tracking.ip_address.encode()).hexdigest()

        # STEP 3: Insert click record into database
        # ------------------------------------------
        # WHY: Permanent record for analytics and self-learning
        # DATABASE TRIGGER: Automatically increments variation.clicks counter
        # PERFORMANCE: Single INSERT, ~10-20ms typical response time
        await database.execute("""
            INSERT INTO promo_click_tracking (
                offer_id,
                variation_id,
                ip_hash,
                user_agent,
                referrer,
                utm_source,
                clicked_at,
                clicked_date
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), CURRENT_DATE)
        """, offer_id, tracking.variation_id, ip_hash,
             tracking.user_agent, tracking.referrer, tracking.utm_source)

        # STEP 3: Log successful tracking
        # --------------------------------
        # WHY: Debugging and monitoring
        # EXAMPLE: "✅ Tracked click: offer=4, var=42, source=newsletter"
        logger.info(
            f"✅ Tracked click: "
            f"offer={tracking.offer_id}, "
            f"variation={tracking.variation_id}, "
            f"source={tracking.utm_source or 'unknown'}"
        )

        # STEP 4: Return 204 No Content (fast, no response body)
        # -------------------------------------------------------
        # WHY 204? Standard for successful action with no data to return
        # REDIRECT: User is already redirected (doesn't see this response)
        return Response(status_code=204)

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # STEP 5: Error handling (log but don't fail redirect)
        # -----------------------------------------------------
        # WHY CRITICAL: User MUST be redirected even if tracking fails
        # BEHAVIOR: Log error, return 500, but redirect already happened
        logger.error(
            f"❌ Failed to track click: "
            f"offer={tracking.offer_id}, "
            f"variation={tracking.variation_id}, "
            f"error={str(e)}"
        )

        # Return 500 but redirect already happened (async call)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track click: {str(e)}"
        )


@app.get("/api/v1/promo/analytics/{offer_id}", response_model=AnalyticsResponse, tags=["Analytics"])
@limiter.limit("60/minute")  # Moderate limit for analytics queries
async def get_analytics(
    request: Request,
    offer_id: int,
    days: int = 30,  # Default: last 30 days of data
    database: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive performance analytics for a promotional offer

    **AUTHENTICATION REQUIRED** - Dashboard and reporting use only

    PURPOSE:
    - Retrieve performance metrics for promotional content
    - Compare text variation performance (A/B testing results)
    - Identify top-performing variations for optimization
    - Generate performance reports for stakeholders

    USE CASES:
    - Dashboard: Real-time performance visualization
    - A/B Testing: Compare variation effectiveness
    - Optimization: Identify and promote best performers
    - Reporting: Generate stakeholder performance reports

    WORKFLOW:
    1. Validate user is authenticated (JWT token required)
    2. Query database for offer details
    3. Fetch all text variations for this offer
    4. Retrieve aggregated metrics (impressions, clicks, CTR)
    5. Calculate performance rankings (best to worst)
    6. Return structured analytics response

    Query Parameters:
        offer_id (path): ID of promotional offer to analyze
        days (query): Number of days to analyze (default: 30, max: 365)

    Response Example:
        {
            "offer_id": 4,
            "offer_name": "No Code MBA - Learn to Build Without Coding",
            "offer_type": "affiliate",
            "date_range": {
                "start_date": "2025-09-18",
                "end_date": "2025-10-18"
            },
            "total_impressions": 15000,
            "total_clicks": 1200,
            "overall_ctr": 8.00,
            "variation_analytics": [
                {
                    "variation_id": 42,
                    "text_preview": "Build your dream startup this weekend—no coding required! No Code MBA shows you...",
                    "tone": "exciting",
                    "length_category": "short",
                    "impressions": 5500,
                    "clicks": 550,
                    "ctr": 10.00,
                    "performance_rank": 1
                },
                {
                    "variation_id": 43,
                    "text_preview": "Want to build apps without code? No Code MBA teaches you...",
                    "tone": "professional",
                    "length_category": "medium",
                    "impressions": 5200,
                    "clicks": 416,
                    "ctr": 8.00,
                    "performance_rank": 2
                },
                {
                    "variation_id": 44,
                    "text_preview": "Turn your business ideas into reality with No Code MBA...",
                    "tone": "friendly",
                    "length_category": "long",
                    "impressions": 4300,
                    "clicks": 234,
                    "ctr": 5.44,
                    "performance_rank": 3
                }
            ]
        }

    Performance Insights:
        - Variation #42 (exciting/short) outperforms others by 25%
        - Short copy drives higher engagement than long copy
        - Exciting tone resonates better than professional/friendly

    Optimization Recommendations:
        - Increase weight for variation #42 (top performer)
        - Generate more "exciting" tone variations
        - Favor short copy over long copy
        - Consider deprecating variation #44 (lowest CTR)

    Error Responses:
        401: Unauthorized (no valid JWT token)
        404: Offer not found
        500: Database error

    Performance:
        - Target: <500ms response time
        - Database: Single query with JOIN
        - Caching: Consider Redis for frequently accessed analytics

    Created: October 18, 2025
    """
    try:
        # STEP 1: Validate days parameter (prevent excessive queries)
        # ------------------------------------------------------------
        # WHY: Prevent users from querying years of data (performance)
        # LIMIT: Maximum 365 days (1 year of analytics)
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days parameter must be between 1 and 365"
            )

        # Calculate date range for analytics query
        # -----------------------------------------
        # WHY: Time-boxed queries are faster (indexed by date)
        # EXAMPLE: Last 30 days = 2025-09-18 to 2025-10-18
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # STEP 2: Fetch offer details
        # ----------------------------
        # WHY: Need offer name and type for response context
        # VALIDATION: Returns 404 if offer doesn't exist
        offer = await database.fetchrow("""
            SELECT id, name, offer_type
            FROM promo_offers
            WHERE id = $1
        """, offer_id)

        if not offer:
            raise HTTPException(
                status_code=404,
                detail=f"Offer {offer_id} not found"
            )

        # STEP 3: Fetch variation analytics with aggregated metrics
        # -----------------------------------------------------------
        # WHY: Need per-variation performance data for comparison
        # QUERY OPTIMIZATION:
        # - Uses denormalized counters (fast, no JOINs needed)
        # - Filters to variations with impressions > 0 (active only)
        # - Orders by CTR DESC (best performers first)
        # PERFORMANCE: Typical query time <50ms for 10 variations
        variations = await database.fetch("""
            SELECT
                id as variation_id,
                LEFT(text_content, 100) as text_preview,
                tone,
                length_category,
                impressions,
                clicks,
                ctr
            FROM promo_text_variations
            WHERE offer_id = $1
              AND approved = TRUE
              AND impressions > 0  -- Only variations that have been shown
            ORDER BY ctr DESC  -- Best performers first
        """, offer_id)

        # STEP 4: Calculate aggregate metrics across all variations
        # -----------------------------------------------------------
        # WHY: Need overall offer performance (not just per-variation)
        # CALCULATION: Sum all impressions and clicks, calculate overall CTR
        total_impressions = sum(v["impressions"] for v in variations)
        total_clicks = sum(v["clicks"] for v in variations)
        overall_ctr = round(
            (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0,
            2
        )

        # STEP 5: Add performance ranking to each variation
        # --------------------------------------------------
        # WHY: Dashboard needs to show "Top Performer", "2nd Best", etc.
        # RANKING: 1 = best CTR, 2 = second best, etc.
        # TIE HANDLING: If CTRs equal, maintain database order
        variation_analytics = []
        for rank, variation in enumerate(variations, start=1):
            variation_analytics.append({
                "variation_id": variation["variation_id"],
                "text_preview": variation["text_preview"],
                "tone": variation["tone"],
                "length_category": variation["length_category"],
                "impressions": variation["impressions"],
                "clicks": variation["clicks"],
                "ctr": float(variation["ctr"]),  # Convert Decimal to float
                "performance_rank": rank
            })

        # STEP 6: Query daily trends for time-series visualization
        # ----------------------------------------------------------
        # WHY: Dashboard needs trend charts showing performance over time
        # QUERY: Join impressions and clicks, group by date
        daily_trends_data = await database.fetch("""
            SELECT
                COALESCE(i.date, c.date) as date,
                COALESCE(i.impressions, 0) as impressions,
                COALESCE(c.clicks, 0) as clicks
            FROM (
                SELECT DATE(tracked_at) as date, COUNT(*) as impressions
                FROM promo_impression_tracking
                WHERE offer_id = $1
                  AND tracked_at >= $2
                  AND tracked_at <= $3
                GROUP BY DATE(tracked_at)
            ) i
            FULL OUTER JOIN (
                SELECT DATE(clicked_at) as date, COUNT(*) as clicks
                FROM promo_click_tracking
                WHERE offer_id = $1
                  AND clicked_at >= $2
                  AND clicked_at <= $3
                GROUP BY DATE(clicked_at)
            ) c ON i.date = c.date
            ORDER BY date DESC
        """, offer_id, start_date, end_date)

        # Build daily trends array
        daily_trends = []
        for row in daily_trends_data:
            clicks = row["clicks"] or 0
            impressions = row["impressions"] or 0
            ctr = round((clicks / impressions * 100) if impressions > 0 else 0.0, 2)
            daily_trends.append({
                "date": row["date"].isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr
            })

        # STEP 7: Build and return analytics response
        # --------------------------------------------
        # WHY: Structured response model for consistent API
        # VALIDATION: Pydantic validates response structure
        logger.info(
            f"📊 Analytics retrieved: "
            f"offer={offer_id}, "
            f"variations={len(variation_analytics)}, "
            f"total_impressions={total_impressions}, "
            f"overall_ctr={overall_ctr}%"
        )

        return AnalyticsResponse(
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            overall_ctr=overall_ctr,
            offers=[
                {
                    "offer_id": offer_id,
                    "offer_name": offer["name"],
                    "impressions": total_impressions,
                    "clicks": total_clicks,
                    "ctr": overall_ctr,
                    "variations": [
                        {
                            "variation_id": v["variation_id"],
                            "text_preview": v["text_preview"],
                            "tone": v["tone"],
                            "length_category": v["length_category"],
                            "impressions": v["impressions"],
                            "clicks": v["clicks"],
                            "ctr": v["ctr"],
                            "performance_rank": v["performance_rank"]
                        }
                        for v in variation_analytics
                    ]
                }
            ],
            daily_trends=daily_trends
        )

    except HTTPException:
        # Re-raise HTTP exceptions (401, 404, 400)
        raise

    except Exception as e:
        # STEP 7: Error handling
        # -----------------------
        # WHY: Log failures for debugging
        # BEHAVIOR: Return 500 with error details
        logger.error(
            f"❌ Failed to retrieve analytics: "
            f"offer={offer_id}, "
            f"error={str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["System"])
@limiter.limit("100/minute")  # Standard rate limit for informational endpoint
async def root(request: Request):
    """Root endpoint - API information"""
    return {
        "name": "Promotional Content Management API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/v1/docs",
        "health": "/api/v1/promo/health"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
