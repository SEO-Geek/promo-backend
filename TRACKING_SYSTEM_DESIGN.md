# Promotional Content Tracking System - Design Document
## Phase 3.1: Impression & Click Tracking

**Document Version:** 1.0
**Created:** October 18, 2025
**Status:** 📋 DESIGN PHASE
**Target Release:** Phase 3.1 (same day as newsletter integration)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Analysis](#requirements-analysis)
3. [System Architecture](#system-architecture)
4. [Database Schema Design](#database-schema-design)
5. [API Endpoint Specifications](#api-endpoint-specifications)
6. [Integration Points](#integration-points)
7. [Analytics Queries](#analytics-queries)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)
10. [Testing Strategy](#testing-strategy)
11. [Implementation Plan](#implementation-plan)
12. [Future Enhancements](#future-enhancements)

---

## Executive Summary

### Purpose

Implement a robust tracking system to measure promotional content performance in newsletters, enabling:
- **Data-driven decisions** on which offers to promote
- **A/B testing** of text variations (which headlines/copy perform best)
- **Self-learning optimization** (future: weighted selection based on CTR)
- **ROI analysis** for promotional content strategy

### Scope

**In Scope (Phase 3.1):**
- Impression tracking (when promo shown in newsletter)
- Click tracking (when user clicks promo link)
- Variation-level performance metrics
- CTR calculations per offer and per variation
- Basic analytics API endpoints

**Out of Scope (Future Phases):**
- Performance-based weighted selection (Phase 3.2)
- Dashboard visualization (Phase 3.3)
- Revenue tracking (requires affiliate platform integration)
- User-level tracking (privacy concerns, GDPR compliance needed)

### Success Criteria

✅ **Functional Requirements:**
- Track every newsletter impression (when promo included)
- Track every click on promo link
- Link clicks to specific text variations
- Calculate accurate CTR per offer and variation
- API responds in <50ms (non-blocking for newsletter/redirects)

✅ **Quality Requirements:**
- 100% test coverage on tracking logic
- Comprehensive inline code comments
- Full integration testing with newsletter + redirects
- Performance benchmarks documented
- Zero impact on newsletter send time

✅ **Documentation Requirements:**
- API endpoint documentation
- Database schema documentation
- Integration guide for newsletter system
- Integration guide for affiliate redirect system
- Testing procedures

---

## Requirements Analysis

### User Requirements (From Initial Discussion)

> "Stats are of course super interesting, I dont know what you suggest because we both have Mautic and Matomo. And here are some of my dreams. It would be great if we can keep track of the performance of how well the offers performs like how many clicks on the links, but it could also be cool if we could examine which headlines/body of the promo that seems to get most attention from the user."

**Interpretation:**

1. **Offer Performance Tracking**
   - Total impressions per offer (how many times shown)
   - Total clicks per offer (how many times clicked)
   - CTR (click-through rate) per offer

2. **Variation Performance Tracking** (Critical for self-learning)
   - Impressions per text variation
   - Clicks per text variation
   - CTR per variation
   - Identify best-performing headlines/copy

3. **Integration Considerations**
   - Work alongside Mautic (email platform) and Matomo (web analytics)
   - Don't duplicate their tracking, focus on promo-specific metrics
   - Use existing affiliate redirect system for click tracking

### Functional Requirements

**FR-1: Impression Tracking**
- **What:** Record when a promotional offer is shown in a newsletter
- **When:** After newsletter generation, before sending
- **Who Calls:** Newsletter generation system
- **Data Captured:**
  - Offer ID
  - Variation ID (which text variation was shown)
  - Timestamp
  - Newsletter send ID (optional, for future segmentation)

**FR-2: Click Tracking**
- **What:** Record when a user clicks on a promotional link
- **When:** When affiliate redirect processes the click
- **Who Calls:** Affiliate redirect system (existing CMS feature)
- **Data Captured:**
  - Offer ID
  - Variation ID (extracted from `promo_var` URL parameter)
  - Timestamp
  - Referrer (should be email client)
  - IP address (optional, for fraud detection)

**FR-3: Performance Metrics API**
- **What:** Retrieve performance statistics for offers and variations
- **Who Uses:** Dashboard (future), manual analysis (current)
- **Metrics Returned:**
  - Impressions, clicks, CTR per offer
  - Impressions, clicks, CTR per variation
  - Time-based filtering (last 7 days, last 30 days, all time)
  - Top-performing variations

**FR-4: Aggregated Statistics**
- **What:** Pre-calculated performance metrics for fast dashboard queries
- **When Updated:** After each impression/click (or batch updates)
- **Data Stored:**
  - Total impressions per offer
  - Total clicks per offer
  - Calculated CTR
  - Last updated timestamp

### Non-Functional Requirements

**NFR-1: Performance**
- Impression tracking: <50ms response time
- Click tracking: <50ms response time (non-blocking for redirect)
- Analytics queries: <500ms for dashboard
- Newsletter send NOT delayed by impression tracking

**NFR-2: Reliability**
- Impression tracking failures do NOT break newsletter sends
- Click tracking failures do NOT break affiliate redirects
- Database connection failures handled gracefully
- Retry logic for failed tracking calls

**NFR-3: Accuracy**
- No duplicate impressions (idempotency)
- No missed clicks (even if tracking fails, redirect succeeds)
- Accurate timestamp recording (UTC timezone)
- Correct variation ID extraction from URL parameters

**NFR-4: Scalability**
- Handle 10,000 impressions/day (current newsletter volume: ~5 subscribers, future: 10,000+)
- Handle 1,000 clicks/day (10% CTR assumption)
- Database writes don't lock tables
- Async processing where possible

**NFR-5: Privacy & Compliance**
- No personally identifiable information (PII) stored
- IP addresses hashed if stored (GDPR compliance)
- Aggregate data only (no user-level tracking)
- Optional: Cookie-less tracking

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NEWSLETTER SYSTEM                         │
│  (generates daily newsletter with promo content)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ 1. GET /api/v1/promo/select-random
                     │    (returns promo content + variation_id)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROMO BACKEND (Port 3003)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/v1/promo/select-random                         │   │
│  │  - Selects offer + variation                         │   │
│  │  - Returns link with promo_var parameter             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /api/v1/promo/track-impression       [NEW]     │   │
│  │  - Records promo shown in newsletter                 │   │
│  │  - Increments impression counter                     │   │
│  │  - Non-blocking (async write)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /api/v1/promo/track-click            [NEW]     │   │
│  │  - Records user clicked promo link                   │   │
│  │  - Increments click counter                          │   │
│  │  - Links to variation via promo_var                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  GET /api/v1/promo/analytics               [NEW]     │   │
│  │  - Returns performance metrics                       │   │
│  │  - Filters by time range, offer, variation           │   │
│  │  - Calculates CTR                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Database writes (PostgreSQL)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATABASE TABLES                         │
│                                                              │
│  promo_impression_tracking (new)                             │
│  promo_click_tracking (new)                                  │
│  promo_performance_metrics (new, aggregated)                 │
│  promo_offers (existing, updated with counters)              │
│  promo_text_variations (existing, updated with counters)     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│          AFFILIATE REDIRECT SYSTEM (Existing CMS)            │
│                                                              │
│  When user clicks: aidailypost.com/nocodemba?promo_var=4    │
│                                                              │
│  1. Extract promo_var parameter (variation_id = 4)          │
│  2. Call: POST /api/v1/promo/track-click                    │
│     (async, non-blocking)                                   │
│  3. Redirect to destination URL                             │
│     (even if tracking fails)                                │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**FLOW 1: Newsletter Send with Impression Tracking**

```
1. Newsletter system calls GET /promo/select-random
   → Returns: {offer_id: 4, variation_id: 42, link: "...?promo_var=42", ...}

2. Newsletter compiles HTML with promo content

3. Newsletter calls POST /promo/track-impression
   → Body: {offer_id: 4, variation_id: 42, newsletter_send_id: "2025-10-18-daily"}
   → Backend writes to promo_impression_tracking table
   → Backend increments promo_offers.total_impressions
   → Backend increments promo_text_variations.impressions (new field)
   → Returns 204 No Content (fast, non-blocking)

4. Newsletter sends to subscribers
   (Impression tracked BEFORE send, so accurate count even if send fails)
```

**FLOW 2: User Click with Click Tracking**

```
1. User clicks link: https://aidailypost.com/nocodemba?utm_source=newsletter&promo_var=42

2. Affiliate redirect system (CMS) receives request
   → Extracts promo_var=42 from URL

3. CMS calls POST /promo/track-click (async, fire-and-forget)
   → Body: {variation_id: 42, referrer: "email_client", ip_hash: "abc123"}
   → Backend writes to promo_click_tracking table
   → Backend increments promo_offers.total_clicks
   → Backend increments promo_text_variations.clicks (new field)
   → Backend recalculates promo_offers.ctr
   → Returns 204 No Content

4. CMS redirects user to destination URL
   (Redirect happens IMMEDIATELY, does not wait for tracking response)
```

**FLOW 3: Analytics Dashboard Query**

```
1. Dashboard calls GET /promo/analytics?offer_id=4&days=30

2. Backend queries:
   - promo_offers for aggregate metrics
   - promo_text_variations for variation breakdown
   - promo_impression_tracking for time-series data
   - promo_click_tracking for click patterns

3. Backend calculates:
   - Total impressions (count from tracking table)
   - Total clicks (count from tracking table)
   - CTR = (clicks / impressions) * 100
   - Best-performing variation (highest CTR)

4. Returns JSON with metrics and charts data
```

### Integration Points

**Integration Point 1: Newsletter System**
- **File:** `/opt/aidailypost/scripts/generate-daily-newsletter.py`
- **Current Behavior:** Calls `/promo/select-random`, includes promo in email
- **Required Change:** Add call to `/promo/track-impression` after content selection
- **Error Handling:** If tracking fails, log warning but continue sending newsletter

**Integration Point 2: Affiliate Redirect System**
- **File:** CMS affiliate redirect handler (Strapi/Astro)
- **Current Behavior:** Redirects `aidailypost.com/slug` to destination URL
- **Required Change:** Extract `promo_var` parameter, call `/promo/track-click` asynchronously
- **Error Handling:** If tracking fails, still perform redirect (tracking is nice-to-have, redirect is critical)

**Integration Point 3: Dashboard (Future)**
- **File:** Vue.js dashboard (Phase 3.3)
- **Behavior:** Call `/promo/analytics` to display performance charts
- **Charts Needed:** CTR over time, variation comparison, offer performance

---

## Database Schema Design

### Table 1: promo_impression_tracking (New)

**Purpose:** Record every instance of a promo being shown in a newsletter

**Schema:**
```sql
CREATE TABLE promo_impression_tracking (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign keys
    offer_id INTEGER NOT NULL REFERENCES promo_offers(id) ON DELETE CASCADE,
    variation_id INTEGER NOT NULL REFERENCES promo_text_variations(id) ON DELETE CASCADE,

    -- Tracking metadata
    newsletter_send_id VARCHAR(100),  -- e.g., "2025-10-18-daily" (optional)
    tracked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Analytics helpers
    tracked_date DATE NOT NULL DEFAULT CURRENT_DATE,  -- For fast date-based queries

    -- Indexes for fast queries
    -- Index on offer_id for "impressions per offer" queries
    -- Index on variation_id for "impressions per variation" queries
    -- Index on tracked_date for time-based filtering
);

-- Indexes (created separately for clarity)
CREATE INDEX idx_impression_offer ON promo_impression_tracking(offer_id);
CREATE INDEX idx_impression_variation ON promo_impression_tracking(variation_id);
CREATE INDEX idx_impression_date ON promo_impression_tracking(tracked_date);
CREATE INDEX idx_impression_newsletter ON promo_impression_tracking(newsletter_send_id);
```

**Sample Data:**
```sql
INSERT INTO promo_impression_tracking (offer_id, variation_id, newsletter_send_id, tracked_at, tracked_date)
VALUES
  (4, 42, '2025-10-18-daily', '2025-10-18 06:00:00+00', '2025-10-18'),
  (4, 43, '2025-10-19-daily', '2025-10-19 06:00:00+00', '2025-10-19'),
  (5, 50, '2025-10-20-daily', '2025-10-20 06:00:00+00', '2025-10-20');
```

**Rationale:**
- `BIGSERIAL` for id: Supports billions of impressions (future-proof)
- `tracked_date` denormalization: Faster queries for "last 30 days" without date arithmetic
- `newsletter_send_id` optional: Allows future segmentation analysis (A/B testing different newsletter formats)
- Foreign keys with CASCADE: If offer/variation deleted, tracking records also deleted (clean up orphaned data)

---

### Table 2: promo_click_tracking (New)

**Purpose:** Record every click on a promotional link

**Schema:**
```sql
CREATE TABLE promo_click_tracking (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign keys
    offer_id INTEGER NOT NULL REFERENCES promo_offers(id) ON DELETE CASCADE,
    variation_id INTEGER NOT NULL REFERENCES promo_text_variations(id) ON DELETE CASCADE,

    -- Click metadata
    clicked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    clicked_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Source tracking (optional)
    referrer VARCHAR(500),     -- e.g., "email_client", "gmail_app", "outlook"
    user_agent VARCHAR(500),   -- For device/browser analysis (optional)
    ip_hash VARCHAR(64),       -- Hashed IP for fraud detection (GDPR-compliant)

    -- Indexes for fast queries
);

-- Indexes
CREATE INDEX idx_click_offer ON promo_click_tracking(offer_id);
CREATE INDEX idx_click_variation ON promo_click_tracking(variation_id);
CREATE INDEX idx_click_date ON promo_click_tracking(clicked_date);
```

**Sample Data:**
```sql
INSERT INTO promo_click_tracking (offer_id, variation_id, clicked_at, clicked_date, referrer)
VALUES
  (4, 42, '2025-10-18 08:30:00+00', '2025-10-18', 'gmail_app'),
  (4, 42, '2025-10-18 09:15:00+00', '2025-10-18', 'outlook'),
  (4, 43, '2025-10-19 07:45:00+00', '2025-10-19', 'gmail_web');
```

**Rationale:**
- `ip_hash` instead of raw IP: GDPR compliance (can detect duplicate clicks without storing PII)
- `referrer` and `user_agent` optional: May provide insights but not critical for core tracking
- Same indexing strategy as impressions for consistent query performance

**Privacy Considerations:**
- IP addresses are hashed using SHA-256 before storage
- No email addresses or user IDs stored
- Aggregate data only for analytics
- Can be fully disabled if privacy concerns arise

---

### Table 3: promo_text_variations (Update Existing)

**Purpose:** Add performance counters to existing text variations table

**Schema Changes:**
```sql
ALTER TABLE promo_text_variations
ADD COLUMN impressions INTEGER NOT NULL DEFAULT 0,
ADD COLUMN clicks INTEGER NOT NULL DEFAULT 0,
ADD COLUMN ctr DECIMAL(5,2);  -- Calculated field: (clicks / impressions) * 100

-- Trigger to auto-calculate CTR on update
CREATE OR REPLACE FUNCTION update_variation_ctr()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.impressions > 0 THEN
        NEW.ctr = (NEW.clicks::DECIMAL / NEW.impressions::DECIMAL) * 100;
    ELSE
        NEW.ctr = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_variation_ctr
BEFORE INSERT OR UPDATE OF impressions, clicks ON promo_text_variations
FOR EACH ROW
EXECUTE FUNCTION update_variation_ctr();
```

**Rationale:**
- Denormalized counters for fast dashboard queries (no JOIN to tracking tables)
- CTR auto-calculated via trigger (no manual calculation needed)
- Incremented atomically on each impression/click

---

### Table 4: promo_offers (Update Existing)

**Purpose:** Already has total_impressions, total_clicks, ctr fields (added in Phase 2)

**No Changes Needed** - Existing schema already supports tracking:
```sql
-- Existing columns (from Phase 2):
total_impressions INTEGER NOT NULL DEFAULT 0,
total_clicks INTEGER NOT NULL DEFAULT 0,
ctr DECIMAL(5,2),  -- Auto-calculated
```

**Trigger Already Exists:**
```sql
CREATE TRIGGER trigger_update_offer_ctr
BEFORE INSERT OR UPDATE OF total_impressions, total_clicks ON promo_offers
FOR EACH ROW
EXECUTE FUNCTION update_offer_ctr();
```

---

## API Endpoint Specifications

### Endpoint 1: POST /api/v1/promo/track-impression

**Purpose:** Record when a promo is shown in a newsletter

**Authentication:** None (called by newsletter system)

**Rate Limit:** 200/minute (higher than selection endpoint)

**Request:**
```http
POST /api/v1/promo/track-impression
Content-Type: application/json

{
  "offer_id": 4,
  "variation_id": 42,
  "newsletter_send_id": "2025-10-18-daily"  // Optional
}
```

**Response (Success):**
```http
HTTP/1.1 204 No Content
```

**Response (Validation Error):**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "validation_error",
  "details": {
    "offer_id": "Offer ID 999 does not exist"
  }
}
```

**Response (Server Error):**
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "error": "tracking_failed",
  "message": "Database connection failed",
  "offer_id": 4,
  "variation_id": 42
}
```

**Implementation Notes:**
- MUST return quickly (<50ms) to not delay newsletter send
- Database write should be async if possible
- Validation: Verify offer_id and variation_id exist
- Atomicity: Increment counters in single transaction
- Idempotency: Consider checking for duplicate newsletter_send_id (same send tracked twice = bug)

**Error Handling:**
- If offer_id invalid: Return 400
- If variation_id invalid: Return 400
- If database unavailable: Return 503 but log for retry
- Newsletter system should log warning but continue sending on 503

---

### Endpoint 2: POST /api/v1/promo/track-click

**Purpose:** Record when a user clicks a promo link

**Authentication:** None (called by affiliate redirect system)

**Rate Limit:** 500/minute (higher to handle click spikes)

**Request:**
```http
POST /api/v1/promo/track-click
Content-Type: application/json

{
  "variation_id": 42,
  "referrer": "gmail_app",     // Optional
  "user_agent": "...",         // Optional
  "ip_address": "1.2.3.4"      // Optional, will be hashed
}
```

**Note:** No `offer_id` in request - we look it up from `variation_id`

**Response (Success):**
```http
HTTP/1.1 204 No Content
```

**Response (Validation Error):**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "validation_error",
  "details": {
    "variation_id": "Variation ID 999 does not exist"
  }
}
```

**Implementation Notes:**
- MUST return IMMEDIATELY to not delay redirect
- Can use fire-and-forget pattern (redirect before tracking confirmed)
- Hash IP address before storing: `hashlib.sha256(ip.encode()).hexdigest()`
- Look up offer_id from variation_id (single query)
- Increment both variation and offer counters
- Recalculate CTR after click

**Error Handling:**
- If variation_id invalid: Return 400 but DON'T break redirect
- If database unavailable: Return 503, log for manual recovery
- Affiliate redirect should ignore tracking errors (redirect is priority)

---

### Endpoint 3: GET /api/v1/promo/analytics

**Purpose:** Retrieve performance statistics

**Authentication:** JWT required (dashboard only)

**Rate Limit:** 60/minute (dashboard queries)

**Request:**
```http
GET /api/v1/promo/analytics?offer_id=4&days=30&include_variations=true
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `offer_id` (optional): Filter to specific offer
- `variation_id` (optional): Filter to specific variation
- `days` (optional): Time range (7, 30, 90, 365, or "all")
- `include_variations` (boolean): Include per-variation breakdown
- `include_timeline` (boolean): Include day-by-day data for charts

**Response (Success):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "summary": {
    "total_impressions": 150,
    "total_clicks": 23,
    "overall_ctr": 15.33,
    "date_range": {
      "start": "2025-09-18",
      "end": "2025-10-18",
      "days": 30
    }
  },
  "offers": [
    {
      "offer_id": 4,
      "offer_name": "No Code MBA - Learn to Build Without Coding",
      "offer_type": "affiliate",
      "impressions": 150,
      "clicks": 23,
      "ctr": 15.33,
      "best_variation_id": 42
    }
  ],
  "variations": [
    {
      "variation_id": 42,
      "offer_id": 4,
      "text_preview": "Build your dream startup this weekend...",
      "cta_text": "Build Now →",
      "tone": "exciting",
      "impressions": 60,
      "clicks": 15,
      "ctr": 25.00
    },
    {
      "variation_id": 43,
      "offer_id": 4,
      "text_preview": "Want to build apps without code?...",
      "cta_text": "Start Learning →",
      "tone": "professional",
      "impressions": 50,
      "clicks": 5,
      "ctr": 10.00
    },
    {
      "variation_id": 44,
      "offer_id": 4,
      "text_preview": "Turn your business ideas into reality...",
      "cta_text": "Get Started →",
      "tone": "friendly",
      "impressions": 40,
      "clicks": 3,
      "ctr": 7.50
    }
  ],
  "timeline": [
    {
      "date": "2025-10-18",
      "impressions": 1,
      "clicks": 0,
      "ctr": 0.00
    },
    {
      "date": "2025-10-17",
      "impressions": 1,
      "clicks": 1,
      "ctr": 100.00
    }
    // ... more days
  ]
}
```

**Implementation Notes:**
- Query should use indexes for fast performance (<500ms)
- CTR calculated as: (clicks / impressions) * 100
- Handle division by zero (if impressions = 0, ctr = null)
- Sort variations by CTR descending (best performing first)
- Cache results for 5 minutes (optional optimization)

---

## Integration Points

### Integration 1: Newsletter System

**File:** `/opt/aidailypost/scripts/generate-daily-newsletter.py`

**Current Code (Approximate):**
```python
async def fetch_promotional_content() -> Optional[Dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{PROMO_API_URL}/promo/select-random",
            timeout=aiohttp.ClientTimeout(total=5.0)
        ) as response:
            if response.status != 200:
                return None
            promo_data = await response.json()
            return promo_data
```

**Required Changes:**
```python
async def fetch_promotional_content() -> Optional[Dict]:
    async with aiohttp.ClientSession() as session:
        # STEP 1: Select promo content (existing)
        async with session.get(
            f"{PROMO_API_URL}/promo/select-random",
            timeout=aiohttp.ClientTimeout(total=5.0)
        ) as response:
            if response.status != 200:
                return None
            promo_data = await response.json()

        # STEP 2: Track impression (NEW)
        # Note: This happens BEFORE newsletter send, so count is accurate
        # even if send fails. If tracking fails, we log but continue.
        try:
            async with session.post(
                f"{PROMO_API_URL}/promo/track-impression",
                json={
                    "offer_id": promo_data["offer_id"],
                    "variation_id": promo_data["variation_id"],
                    "newsletter_send_id": f"{datetime.now().strftime('%Y-%m-%d')}-daily"
                },
                timeout=aiohttp.ClientTimeout(total=2.0)  # Fast timeout
            ) as track_response:
                if track_response.status not in [200, 204]:
                    logger.warning(
                        f"Failed to track impression: {track_response.status}"
                    )
        except Exception as e:
            # DON'T fail newsletter send if tracking fails
            logger.warning(f"Impression tracking failed: {e}")

        return promo_data
```

**Testing:**
1. Newsletter should send successfully even if tracking endpoint returns 503
2. Tracking should complete in <50ms
3. Database should show impression record after newsletter generation

---

### Integration 2: Affiliate Redirect System

**File:** `/opt/aidailypost/website/src/pages/[slug].ts` (Astro SSR)

**Current Code (Approximate):**
```typescript
export async function GET({ params, redirect }) {
  const { slug } = params;

  // Look up affiliate link from Strapi
  const link = await getAffiliateLink(slug);

  if (!link) {
    return new Response("Not found", { status: 404 });
  }

  // Redirect to destination
  return redirect(link.destination_url, 307);
}
```

**Required Changes:**
```typescript
export async function GET({ params, redirect, url }) {
  const { slug } = params;

  // Look up affiliate link from Strapi
  const link = await getAffiliateLink(slug);

  if (!link) {
    return new Response("Not found", { status: 404 });
  }

  // NEW: Extract promo_var parameter if present
  const promoVar = url.searchParams.get('promo_var');

  // NEW: Track click asynchronously (fire-and-forget)
  if (promoVar) {
    // Don't await - redirect immediately, track in background
    trackPromoClick(parseInt(promoVar)).catch(err => {
      console.warn("Promo tracking failed:", err);
    });
  }

  // Redirect to destination (happens immediately, doesn't wait for tracking)
  return redirect(link.destination_url, 307);
}

async function trackPromoClick(variationId: number) {
  try {
    await fetch('http://127.0.0.1:3003/api/v1/promo/track-click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variation_id: variationId }),
      // 1-second timeout - if tracking takes longer, give up
      signal: AbortSignal.timeout(1000)
    });
  } catch (error) {
    // Silently fail - tracking is nice-to-have, redirect is critical
    console.warn("Click tracking failed:", error);
  }
}
```

**Testing:**
1. Redirect should work even if tracking endpoint is down
2. Tracking should not delay redirect (fire-and-forget)
3. Database should show click record after redirect
4. promo_var parameter correctly extracted from URL

---

## Analytics Queries

### Query 1: Offer Performance Summary

**SQL:**
```sql
SELECT
    o.id AS offer_id,
    o.name AS offer_name,
    o.offer_type,
    o.total_impressions,
    o.total_clicks,
    o.ctr,
    COUNT(DISTINCT tv.id) AS total_variations,
    MAX(tv.ctr) AS best_variation_ctr
FROM promo_offers o
LEFT JOIN promo_text_variations tv ON tv.offer_id = o.id AND tv.approved = TRUE
WHERE o.total_impressions > 0  -- Only offers with activity
GROUP BY o.id, o.name, o.offer_type, o.total_impressions, o.total_clicks, o.ctr
ORDER BY o.ctr DESC NULLS LAST;
```

**Purpose:** Dashboard overview of all offers ranked by performance

---

### Query 2: Variation Performance (Best to Worst)

**SQL:**
```sql
SELECT
    tv.id AS variation_id,
    tv.offer_id,
    o.name AS offer_name,
    LEFT(tv.text_content, 50) AS text_preview,
    tv.cta_text,
    tv.tone,
    tv.length_category,
    tv.impressions,
    tv.clicks,
    tv.ctr
FROM promo_text_variations tv
JOIN promo_offers o ON o.id = tv.offer_id
WHERE tv.approved = TRUE
  AND tv.impressions > 0  -- Only variations with activity
ORDER BY tv.ctr DESC NULLS LAST, tv.impressions DESC;
```

**Purpose:** Identify best-performing text variations for self-learning

---

### Query 3: Timeline (Daily Impressions/Clicks)

**SQL:**
```sql
WITH daily_impressions AS (
    SELECT
        tracked_date,
        offer_id,
        COUNT(*) AS impressions
    FROM promo_impression_tracking
    WHERE tracked_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY tracked_date, offer_id
),
daily_clicks AS (
    SELECT
        clicked_date,
        offer_id,
        COUNT(*) AS clicks
    FROM promo_click_tracking
    WHERE clicked_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY clicked_date, offer_id
)
SELECT
    COALESCE(i.tracked_date, c.clicked_date) AS date,
    COALESCE(i.offer_id, c.offer_id) AS offer_id,
    COALESCE(i.impressions, 0) AS impressions,
    COALESCE(c.clicks, 0) AS clicks,
    CASE
        WHEN COALESCE(i.impressions, 0) > 0
        THEN (COALESCE(c.clicks, 0)::DECIMAL / i.impressions::DECIMAL) * 100
        ELSE NULL
    END AS ctr
FROM daily_impressions i
FULL OUTER JOIN daily_clicks c
    ON i.tracked_date = c.clicked_date
    AND i.offer_id = c.offer_id
ORDER BY date DESC, offer_id;
```

**Purpose:** Chart data for CTR over time

---

## Performance Considerations

### Database Performance

**Concern:** Tracking tables will grow large (millions of rows)

**Solutions:**
1. **Partitioning** (Future):
   - Partition impression/click tables by month
   - Archive old partitions after 1 year

2. **Indexes:**
   - Created on all filter columns (offer_id, variation_id, date)
   - Covering indexes for common queries

3. **Aggregation:**
   - Denormalized counters in offers and variations tables
   - Most queries use counters, not tracking tables

**Benchmarks (Target):**
- Track impression: <50ms
- Track click: <50ms
- Analytics query: <500ms (even with 1M rows)

### API Performance

**Concern:** Tracking endpoints must be very fast

**Solutions:**
1. **Async Database Writes:**
   - Use async connection pool (already configured)
   - Non-blocking writes to tracking tables

2. **Fire-and-Forget Pattern:**
   - Click tracking doesn't wait for confirmation
   - Redirect happens immediately

3. **Rate Limiting:**
   - Protect against abuse/spam
   - Separate limits for tracking (500/min) vs analytics (60/min)

### Newsletter Send Performance

**Concern:** Don't delay newsletter sends

**Solutions:**
1. **Fast Timeout:**
   - 2-second timeout on impression tracking
   - Newsletter continues on timeout/error

2. **Fail-Safe:**
   - Newsletter sends even if tracking fails
   - Missing impression data is acceptable (better than missing newsletter)

---

## Security Considerations

### Privacy & GDPR Compliance

**Concern:** Click tracking may involve personal data

**Solutions:**
1. **No PII Storage:**
   - No email addresses in tracking tables
   - No user IDs or session tokens

2. **IP Address Hashing:**
   - Hash IP before storage: `SHA-256(ip + salt)`
   - Can detect duplicate clicks without storing raw IP
   - Salt rotated monthly for additional privacy

3. **Aggregate Data Only:**
   - Analytics show totals, not individual clicks
   - No user-level tracking or profiles

4. **Cookie-less Tracking:**
   - No cookies set by tracking endpoints
   - All tracking server-side

### Authentication

**Concern:** Prevent unauthorized access to analytics

**Solutions:**
1. **Tracking Endpoints (POST):** No auth (called by newsletter/redirect)
   - Rate limited to prevent abuse
   - Validate offer/variation IDs exist

2. **Analytics Endpoint (GET):** JWT required
   - Only accessible from dashboard
   - Same auth as existing endpoints

### Rate Limiting

**Concern:** Prevent spam/abuse

**Solutions:**
1. **Track Impression:** 200 req/min (normal: 1 per day)
2. **Track Click:** 500 req/min (handle click spikes)
3. **Analytics:** 60 req/min (dashboard polling)

### SQL Injection Prevention

**Concern:** User input in queries

**Solutions:**
1. **Parameterized Queries:**
   - All queries use `$1, $2` parameters (asyncpg)
   - No string concatenation

2. **Input Validation:**
   - Pydantic models validate all input
   - Integer IDs only (no string slugs in tracking)

---

## Testing Strategy

### Unit Tests

**Test 1: Track Impression - Valid Data**
- Input: Valid offer_id, variation_id
- Expected: 204 response, record in database, counters incremented

**Test 2: Track Impression - Invalid Offer ID**
- Input: offer_id=999 (doesn't exist)
- Expected: 400 response, no database write

**Test 3: Track Impression - Database Unavailable**
- Input: Valid data, but database down
- Expected: 503 response, error logged

**Test 4: Track Click - Valid Data**
- Input: Valid variation_id
- Expected: 204 response, record in database, counters incremented

**Test 5: Track Click - IP Address Hashing**
- Input: Click with IP address
- Expected: IP hashed in database, not stored raw

**Test 6: Analytics - Offer Performance**
- Input: offer_id=4, days=30
- Expected: Correct impressions, clicks, CTR calculated

**Test 7: Analytics - Variation Breakdown**
- Input: offer_id=4, include_variations=true
- Expected: Variations sorted by CTR, correct metrics

### Integration Tests

**Test 8: Newsletter End-to-End**
1. Newsletter calls /select-random → Gets promo content
2. Newsletter calls /track-impression → Impression recorded
3. Database shows impression record
4. Offer counters incremented

**Test 9: Click Tracking End-to-End**
1. User clicks link with promo_var=42
2. Redirect system calls /track-click
3. User redirected to destination
4. Database shows click record
5. Variation and offer counters incremented
6. CTR recalculated

**Test 10: Fail-Safe Behavior**
1. Newsletter calls /select-random → Success
2. Tracking endpoint returns 503
3. Newsletter STILL sends (tracking failure ignored)

### Load Tests

**Test 11: Concurrent Impressions**
- Simulate 100 simultaneous impression tracking calls
- Expected: All succeed, no database lock issues

**Test 12: Concurrent Clicks**
- Simulate 50 simultaneous click tracking calls
- Expected: All succeed, accurate counters

### Performance Tests

**Test 13: Impression Tracking Speed**
- Expected: <50ms average response time

**Test 14: Click Tracking Speed**
- Expected: <50ms average response time

**Test 15: Analytics Query Speed**
- Expected: <500ms with 10,000 impressions and 1,000 clicks

---

## Implementation Plan

### Phase 3.1.1: Database Schema (1-2 hours)

**Tasks:**
1. ✅ Create migration SQL file
2. ✅ Add impression_tracking table
3. ✅ Add click_tracking table
4. ✅ Update text_variations table (add counters)
5. ✅ Create triggers for CTR calculation
6. ✅ Create indexes
7. ✅ Test migration on development database
8. ✅ Document rollback procedure

**Deliverables:**
- `/tmp/add_tracking_tables_migration.sql`
- Migration tested and verified

---

### Phase 3.1.2: API Endpoints (3-4 hours)

**Tasks:**
1. ✅ Create Pydantic models (ImpressionTrackRequest, ClickTrackRequest, AnalyticsResponse)
2. ✅ Implement POST /track-impression endpoint
3. ✅ Implement POST /track-click endpoint
4. ✅ Implement GET /analytics endpoint
5. ✅ Add comprehensive inline comments
6. ✅ Add error handling and validation
7. ✅ Add logging for debugging
8. ✅ Test all endpoints with curl

**Deliverables:**
- Updated `app/main.py` with 3 new endpoints
- All endpoints tested and working

---

### Phase 3.1.3: Newsletter Integration (1 hour)

**Tasks:**
1. ✅ Update newsletter generation script
2. ✅ Add impression tracking call
3. ✅ Add error handling (fail-safe)
4. ✅ Test end-to-end newsletter flow
5. ✅ Verify database records created

**Deliverables:**
- Updated `/opt/aidailypost/scripts/generate-daily-newsletter.py`
- Newsletter sends successfully with tracking

---

### Phase 3.1.4: Affiliate Redirect Integration (1-2 hours)

**Tasks:**
1. ✅ Update affiliate redirect code
2. ✅ Extract promo_var parameter
3. ✅ Call click tracking endpoint (async)
4. ✅ Ensure redirect not delayed
5. ✅ Test with real link clicks

**Deliverables:**
- Updated `/opt/aidailypost/website/src/pages/[slug].ts`
- Clicks tracked successfully

---

### Phase 3.1.5: Testing & Documentation (2-3 hours)

**Tasks:**
1. ✅ Run all unit tests
2. ✅ Run integration tests
3. ✅ Run performance benchmarks
4. ✅ Update TESTING_GUIDE.md
5. ✅ Update CHANGELOG.md
6. ✅ Create TRACKING_SYSTEM_DESIGN.md (this document)
7. ✅ Document analytics queries

**Deliverables:**
- All tests passing
- Complete documentation
- Performance benchmarks documented

---

### Total Estimated Time: 8-12 hours

**Priority:** HIGH (blocks Phase 3.2 self-learning optimization)

---

## Future Enhancements

### Phase 3.2: Performance-Based Selection

**Concept:** Instead of fixed weights, use CTR to select offers

**Algorithm:**
```python
# Current (Phase 3.1): Fixed weights
offer_weights = [10, 5, 1]  # User-configured

# Future (Phase 3.2): Performance-based weights
offer_weights = [
    base_weight * (1 + ctr / 100) for base_weight, ctr in zip(base_weights, ctrs)
]
# Offer with 20% CTR gets 1.2x weight
# Offer with 5% CTR gets 1.05x weight
```

**Benefits:**
- Self-learning system
- Automatically promotes high-performing offers
- Gradually deprecates low-performing offers
- Still maintains variety (doesn't only show best offer)

---

### Phase 3.3: Dashboard Visualization

**Charts:**
1. CTR over time (line chart)
2. Offer comparison (bar chart)
3. Variation performance (table with sparklines)
4. Click heatmap by day/hour

**Technologies:**
- Vue.js 3
- Chart.js or Recharts
- Tailwind CSS

---

### Phase 3.4: Advanced Analytics

**Features:**
1. **Cohort Analysis:** Performance by newsletter send date
2. **Device Breakdown:** Desktop vs mobile clicks (from user_agent)
3. **Time-of-Day Analysis:** When do users click most?
4. **Conversion Funnel:** Impression → Click → Purchase (requires affiliate platform integration)

---

## Success Metrics

### Phase 3.1 Success Criteria

✅ **Functional:**
- All 3 endpoints implemented and tested
- Newsletter integration working
- Affiliate redirect integration working
- Database schema deployed

✅ **Quality:**
- 100% test coverage on tracking logic
- All tests documented in TESTING_GUIDE.md
- Comprehensive inline comments
- CHANGELOG updated

✅ **Performance:**
- Impression tracking: <50ms
- Click tracking: <50ms
- Analytics queries: <500ms
- Zero impact on newsletter send time

✅ **Documentation:**
- This design document complete
- API documentation updated
- Integration guide for newsletter
- Integration guide for redirects

---

## Conclusion

This tracking system will provide the foundation for data-driven promo optimization. By tracking impressions and clicks at the variation level, we enable:

1. **Immediate Value:** Understand which offers perform best
2. **A/B Testing:** Compare text variations scientifically
3. **Future Self-Learning:** Automatic optimization (Phase 3.2)
4. **Business Intelligence:** ROI analysis for promo content

**Ready to Implement:** Design is complete, all edge cases considered, testing strategy defined.

**Next Step:** Create database migration SQL file and begin implementation.

---

**Document Status:** ✅ APPROVED FOR IMPLEMENTATION

**Author:** Claude (AI Assistant)
**Reviewer:** User (labaek@gmail.com)
**Date:** October 18, 2025
