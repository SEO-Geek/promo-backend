# 📰 Newsletter Promotional System - Comprehensive Implementation Plan
## Text-Only AI-Powered Promotional Content Management

**Created:** October 18, 2025
**Status:** Ready for Implementation
**Priority:** HIGH - Complete promotional system for newsletter monetization

---

## 📋 Executive Summary

This plan outlines the transformation of the current image-based promotional system into a **text-only, AI-powered newsletter promotional system** with advanced analytics and self-learning capabilities.

### Key Changes:
- ✅ **Remove images** - Eliminate Leonardo AI integration entirely
- ✅ **Two offer types** - Reviews vs. Affiliate offers
- ✅ **AI variation generation** - Multiple headlines/body text per offer using Ollama
- ✅ **Multi-offer rotation** - System selects one offer per newsletter
- ✅ **Advanced analytics** - Click tracking per offer, per variation, self-learning
- ✅ **Newsletter integration** - Seamless placement after first 2-3 stories

---

## 🎯 System Requirements Analysis

### Current State (What We Have):
1. ✅ **Promo Backend API** - FastAPI on port 3003, 17 endpoints
2. ✅ **Ollama Service** - GPT-OSS 120B for text generation (PERFECT!)
3. ✅ **Database** - PostgreSQL with 8 tables ready
4. ✅ **Newsletter System** - Fully automated with Mautic integration
5. ✅ **Affiliate System** - Link cloaking built into CMS
6. ⚠️ **Leonardo Service** - Image generation (TO BE REMOVED)

### User Requirements (What You Need):
1. **Text-Only Promos**
   - No images (remove Leonardo)
   - AI-generated headlines and body text
   - Multiple variations for freshness
   - CTA button text generation

2. **Two Offer Types**
   - **Reviews**: Internal content (e.g., https://aidailypost.com/review/no-code-mba)
   - **Affiliate Offers**: External offers via cloaked links (e.g., https://aidailypost.com/no-code-mba)

3. **AI Variation Management**
   - Generate 3-8 variations per offer
   - Different headlines + body text combinations
   - Approve/reject workflow
   - Rotation prevents repetition

4. **Intelligent Selection**
   - Multiple active offers in system
   - Weighted random selection
   - Performance-based selection (future: self-learning)
   - One offer per newsletter

5. **Advanced Analytics**
   - Clicks per offer (overall performance)
   - Clicks per variation (headline/body combo performance)
   - CTR by variation
   - Self-learning: promote high-performing variations
   - Integration with Mautic and Matomo

6. **Newsletter Integration**
   - Placement: After first 2-3 stories (top 50% of newsletter)
   - 80/20 content/promo ratio
   - Fail-safe: Newsletter always sends even if promo fails

---

## 📊 Best Practices Research Findings

### Newsletter Promotion Best Practices:

1. **80/20 Content-to-Promo Ratio** ✅
   - 80% editorial content (5-7 stories)
   - 20% promotional content (1 promo)
   - Current newsletter: 7 stories + 1 promo = **87.5% content** ✅

2. **Top 50% Placement** ✅
   - Primary ad should be in top 50% of newsletter
   - **Your current placement**: After first 2-3 stories = **~40% depth** ✅
   - Studies show ads below 50% get significantly fewer clicks

3. **Text-Only Advantage**
   - More authentic and genuine
   - Feels less "salesy"
   - Higher trust from readers
   - Better mobile experience
   - Faster load times

4. **CTR Benchmarks**
   - Newsletter CTR: 6-17% is healthy
   - Click-to-open rate: Target 10%+
   - Text-only promos often outperform image-heavy ads

5. **A/B Testing Strategy**
   - Test 3 variations minimum
   - Headlines have 50%+ impact on CTR
   - CTA button text can improve CTR by 20-30%
   - Rotate variations to prevent "banner blindness"

---

## 🏗️ Implementation Plan

### Phase 1: Clean Up & Prepare (2 hours)

**Goal**: Remove image functionality, prepare database

**Tasks:**

1. **Remove Leonardo Service** (30 min)
   ```bash
   # Delete Leonardo AI integration
   rm /opt/aidailypost/promo-backend/app/leonardo_service.py

   # Remove image endpoints from main.py
   # Lines to delete: Image generation, image listing, image approval, image deletion
   ```

2. **Update Database Schema** (30 min)
   ```sql
   -- Add offer_type column to promo_offers
   ALTER TABLE promo_offers
   ADD COLUMN offer_type VARCHAR(20) DEFAULT 'affiliate'
   CHECK (offer_type IN ('review', 'affiliate'));

   -- Add index for faster filtering
   CREATE INDEX idx_promo_offers_type_status ON promo_offers(offer_type, status);

   -- Deprecate image columns (keep for now, remove later)
   -- promo_images table can remain for legacy data
   ```

3. **Update Models** (30 min)
   - Remove `ImageGenerationRequest` and `ImageResponse` from `models.py`
   - Add `offer_type` field to `OfferCreate` and `OfferResponse`
   - Add validation: `offer_type: str = Field(pattern="^(review|affiliate)$")`

4. **Clean Up Config** (30 min)
   - Remove `LEONARDO_API_KEY` from `.env`
   - Remove Leonardo-related settings from `config.py`
   - Update documentation to remove image references

---

### Phase 2: Variation Selection Endpoint (3 hours)

**Goal**: Create endpoint for newsletter to fetch random promo

**Current Newsletter Expectation** (from `generate-daily-newsletter.py:1057-1127`):
```python
# Newsletter calls: GET /api/v1/promo/select-random
# Expects response:
{
    "offer_id": 1,
    "name": "Offer Name",
    "affiliate_slug": "no-code-mba",  # For link cloaking
    "approved_text": {
        "headline": "AI-generated headline",
        "body": "AI-generated promotional text...",
        "cta_button_text": "Enroll Now"
    }
}
```

**Implementation:**

1. **Create Selection Algorithm** (1 hour)
   ```python
   # File: /opt/aidailypost/promo-backend/app/main.py

   @app.get("/api/v1/promo/select-random")
   async def select_random_promo():
       """
       Select random active promo for newsletter inclusion

       Algorithm:
       1. Fetch all ACTIVE offers (status='active')
       2. Filter by date range (start_date <= now <= end_date)
       3. Filter by offer_type (both 'review' and 'affiliate' eligible)
       4. Weighted random selection (use weight and priority fields)
       5. Select one approved text variation randomly
       6. Return formatted response

       Fail-Safe:
       - Returns 404 if no active offers available
       - Newsletter handles this gracefully (sends without promo)
       """

       # Weighted random selection
       offers = await db.fetch("""
           SELECT * FROM promo_offers
           WHERE status = 'active'
           AND (start_date IS NULL OR start_date <= NOW())
           AND (end_date IS NULL OR end_date >= NOW())
       """)

       if not offers:
           raise HTTPException(404, "No active offers available")

       # Weighted random choice
       weights = [o['weight'] * (o['priority'] + 1) for o in offers]
       selected = random.choices(offers, weights=weights, k=1)[0]

       # Get approved text variation
       variation = await db.fetchrow("""
           SELECT text_content, cta_text, tone, length_category
           FROM promo_text_variations
           WHERE offer_id = $1 AND approved = TRUE
           ORDER BY RANDOM()
           LIMIT 1
       """, selected['id'])

       if not variation:
           # Fallback: use offer name + description
           return {
               "offer_id": selected['id'],
               "name": selected['name'],
               "affiliate_slug": selected['affiliate_slug'],
               "approved_text": {
                   "headline": selected['name'],
                   "body": selected['description'] or "Check out this offer!",
                   "cta_button_text": "Learn More"
               }
           }

       return {
           "offer_id": selected['id'],
           "name": selected['name'],
           "affiliate_slug": selected['affiliate_slug'] or 'default',
           "approved_text": {
               "headline": selected['name'],  # Could extract from text_content
               "body": variation['text_content'],
               "cta_button_text": variation['cta_text'] or "Learn More"
           }
       }
   ```

2. **Add Newsletter Tracking Endpoint** (1 hour)
   ```python
   @app.post("/api/v1/promo/track-impression")
   async def track_impression(
       offer_id: int,
       text_variation_id: Optional[int] = None,
       newsletter_date: str = None
   ):
       """
       Track when a promo is included in newsletter

       Called by newsletter script AFTER successful send
       """
       await db.execute("""
           INSERT INTO promo_impression_tracking
           (offer_id, text_id, newsletter_date, impression_count)
           VALUES ($1, $2, $3, 1)
           ON CONFLICT (offer_id, newsletter_date)
           DO UPDATE SET impression_count = promo_impression_tracking.impression_count + 1
       """, offer_id, text_variation_id, newsletter_date or datetime.now().date())

       return {"status": "tracked"}
   ```

3. **Test Endpoint** (1 hour)
   ```bash
   # Test selection endpoint
   curl -s http://127.0.0.1:3003/api/v1/promo/select-random | jq .

   # Expected output:
   {
     "offer_id": 1,
     "name": "No-Code MBA",
     "affiliate_slug": "no-code-mba",
     "approved_text": {
       "headline": "Master AI Tools in 30 Days",
       "body": "Join 10,000+ professionals...",
       "cta_button_text": "Enroll Now"
     }
   }
   ```

---

### Phase 3: Analytics & Click Tracking (4 hours)

**Goal**: Track performance of offers and variations

**Architecture:**

```
User clicks newsletter link
    ↓
Link: https://aidailypost.com/{affiliate_slug}?utm_source=newsletter&utm_campaign=daily
    ↓
Affiliate redirect system (already built in CMS)
    ↓
Logs click + redirects to destination
    ↓
Promo backend API receives click event
    ↓
Updates promo_click_tracking table
    ↓
Analytics dashboard shows performance
```

**Implementation:**

1. **Modify Affiliate Redirect to Track Promo Clicks** (2 hours)

   Current: Affiliate system in CMS logs clicks to Matomo

   Add: Also send click event to promo backend API

   ```javascript
   // In affiliate redirect handler (Astro SSR)
   // File: /opt/aidailypost/website/src/pages/[slug].ts

   // After tracking click in Matomo...

   // Check if this is a promo link (has utm_source=newsletter)
   if (params.get('utm_source') === 'newsletter') {
       // Look up offer by affiliate_slug
       const offer = await fetch(`http://127.0.0.1:3003/api/v1/promo/by-slug/${slug}`)

       if (offer) {
           // Track click in promo system
           await fetch('http://127.0.0.1:3003/api/v1/promo/track-click', {
               method: 'POST',
               body: JSON.stringify({
                   offer_id: offer.id,
                   source: 'newsletter',
                   newsletter_date: new Date().toISOString().split('T')[0]
               })
           })
       }
   }
   ```

2. **Create Click Tracking Endpoint** (1 hour)
   ```python
   @app.post("/api/v1/promo/track-click")
   async def track_click(
       offer_id: int,
       source: str = 'newsletter',
       newsletter_date: Optional[str] = None
   ):
       """
       Track click on promotional link

       Called by affiliate redirect system when user clicks newsletter promo
       """
       date = newsletter_date or datetime.now().date()

       await db.execute("""
           INSERT INTO promo_click_tracking
           (offer_id, click_date, click_count, source)
           VALUES ($1, $2, 1, $3)
           ON CONFLICT (offer_id, click_date)
           DO UPDATE SET click_count = promo_click_tracking.click_count + 1
       """, offer_id, date, source)

       return {"status": "tracked"}
   ```

3. **Create Analytics Endpoints** (1 hour)
   ```python
   @app.get("/api/v1/analytics/overview")
   async def get_analytics_overview():
       """
       Dashboard analytics overview

       Returns:
       - Total offers
       - Active offers
       - Total impressions (newsletters sent with promos)
       - Total clicks
       - Overall CTR
       - Top performing offers (by CTR)
       """

       stats = await db.fetchrow("""
           SELECT
               COUNT(DISTINCT o.id) as total_offers,
               COUNT(DISTINCT CASE WHEN o.status = 'active' THEN o.id END) as active_offers,
               COALESCE(SUM(i.impression_count), 0) as total_impressions,
               COALESCE(SUM(c.click_count), 0) as total_clicks,
               CASE
                   WHEN COALESCE(SUM(i.impression_count), 0) > 0
                   THEN (COALESCE(SUM(c.click_count), 0)::float / SUM(i.impression_count) * 100)
                   ELSE 0
               END as overall_ctr
           FROM promo_offers o
           LEFT JOIN promo_impression_tracking i ON o.id = i.offer_id
           LEFT JOIN promo_click_tracking c ON o.id = c.offer_id
       """)

       # Top performers
       top_offers = await db.fetch("""
           SELECT
               o.id,
               o.name,
               COALESCE(SUM(i.impression_count), 0) as impressions,
               COALESCE(SUM(c.click_count), 0) as clicks,
               CASE
                   WHEN COALESCE(SUM(i.impression_count), 0) > 0
                   THEN (COALESCE(SUM(c.click_count), 0)::float / SUM(i.impression_count) * 100)
                   ELSE 0
               END as ctr
           FROM promo_offers o
           LEFT JOIN promo_impression_tracking i ON o.id = i.offer_id
           LEFT JOIN promo_click_tracking c ON o.id = c.offer_id
           GROUP BY o.id, o.name
           HAVING COALESCE(SUM(i.impression_count), 0) > 0
           ORDER BY ctr DESC
           LIMIT 5
       """)

       return {
           "total_offers": stats['total_offers'],
           "active_offers": stats['active_offers'],
           "total_impressions": stats['total_impressions'],
           "total_clicks": stats['total_clicks'],
           "overall_ctr": round(stats['overall_ctr'], 2),
           "top_performing_offers": [dict(r) for r in top_offers]
       }
   ```

---

### Phase 4: Variation Performance Tracking (3 hours)

**Goal**: Track which headlines/body combinations perform best

**Challenge**: How to know which variation was shown when tracking clicks?

**Solution**: Include variation ID in tracking

**Implementation:**

1. **Update Selection Endpoint** (1 hour)
   ```python
   # Modified selection endpoint returns variation_id
   @app.get("/api/v1/promo/select-random")
   async def select_random_promo():
       # ... existing code ...

       return {
           "offer_id": selected['id'],
           "variation_id": variation['id'],  # 🆕 NEW: Track which variation
           "name": selected['name'],
           "affiliate_slug": selected['affiliate_slug'],
           "approved_text": {
               "headline": variation['text_content'][:100],  # Extract headline
               "body": variation['text_content'],
               "cta_button_text": variation['cta_text']
           }
       }
   ```

2. **Newsletter Passes Variation ID in Link** (1 hour)
   ```python
   # File: /opt/aidailypost/scripts/generate-daily-newsletter.py
   # Modified promo link generation

   promo_link = f"{WEBSITE_URL}/{affiliate_slug}?utm_source=newsletter&utm_campaign=daily&promo_var={promo['variation_id']}"
   ```

3. **Affiliate Redirect Extracts Variation ID** (30 min)
   ```javascript
   // In affiliate redirect handler
   const variation_id = params.get('promo_var')

   await fetch('http://127.0.0.1:3003/api/v1/promo/track-click', {
       method: 'POST',
       body: JSON.stringify({
           offer_id: offer.id,
           variation_id: variation_id,  // 🆕 Track specific variation
           source: 'newsletter'
       })
   })
   ```

4. **Update Database Schema** (30 min)
   ```sql
   -- Add variation tracking to click_tracking table
   ALTER TABLE promo_click_tracking
   ADD COLUMN variation_id INTEGER REFERENCES promo_text_variations(id);

   -- Update unique constraint
   DROP INDEX IF EXISTS idx_promo_click_tracking_unique;
   CREATE UNIQUE INDEX idx_promo_click_tracking_unique
   ON promo_click_tracking(offer_id, variation_id, click_date);
   ```

5. **Create Variation Performance Endpoint** (30 min)
   ```python
   @app.get("/api/v1/offers/{offer_id}/variation-performance")
   async def get_variation_performance(offer_id: int):
       """
       Get performance breakdown by variation

       Shows which headlines/body text perform best
       """

       variations = await db.fetch("""
           SELECT
               v.id,
               v.text_content,
               v.cta_text,
               v.tone,
               v.length_category,
               COALESCE(SUM(i.impression_count), 0) as times_shown,
               COALESCE(SUM(c.click_count), 0) as total_clicks,
               CASE
                   WHEN COALESCE(SUM(i.impression_count), 0) > 0
                   THEN (COALESCE(SUM(c.click_count), 0)::float / SUM(i.impression_count) * 100)
                   ELSE 0
               END as ctr
           FROM promo_text_variations v
           LEFT JOIN promo_impression_tracking i ON v.id = i.text_id
           LEFT JOIN promo_click_tracking c ON v.id = c.variation_id
           WHERE v.offer_id = $1 AND v.approved = TRUE
           GROUP BY v.id
           ORDER BY ctr DESC
       """, offer_id)

       return [dict(v) for v in variations]
   ```

---

### Phase 5: Self-Learning Optimization (2 hours)

**Goal**: Automatically promote high-performing variations

**Strategy**: Weighted selection based on historical CTR

**Implementation:**

1. **Smart Variation Selection** (1 hour)
   ```python
   # Modified variation selection with performance weighting

   async def select_variation_smart(offer_id: int) -> dict:
       """
       Select variation using performance-based weighting

       Algorithm:
       1. Get all approved variations with performance data
       2. Weight by CTR (higher CTR = higher probability)
       3. New variations get baseline weight (no penalty for being new)
       4. Return weighted random selection
       """

       variations = await db.fetch("""
           SELECT
               v.*,
               COALESCE(SUM(i.impression_count), 0) as times_shown,
               COALESCE(SUM(c.click_count), 0) as total_clicks,
               CASE
                   WHEN COALESCE(SUM(i.impression_count), 0) >= 10
                   THEN (COALESCE(SUM(c.click_count), 0)::float / SUM(i.impression_count) * 100)
                   ELSE 10.0  -- Baseline CTR for new variations
               END as ctr
           FROM promo_text_variations v
           LEFT JOIN promo_impression_tracking i ON v.id = i.text_id
           LEFT JOIN promo_click_tracking c ON v.id = c.variation_id
           WHERE v.offer_id = $1 AND v.approved = TRUE
           GROUP BY v.id
       """, offer_id)

       if not variations:
           return None

       # Weighted selection based on CTR
       weights = [max(v['ctr'], 1.0) for v in variations]  # Min weight = 1.0
       selected = random.choices(variations, weights=weights, k=1)[0]

       logger.info(f"Selected variation {selected['id']} (CTR: {selected['ctr']:.2f}%)")

       return selected
   ```

2. **Performance Insights Endpoint** (1 hour)
   ```python
   @app.get("/api/v1/analytics/insights")
   async def get_performance_insights():
       """
       AI-powered insights about promotional performance

       Returns:
       - Best performing tone (professional, casual, urgent, etc.)
       - Best performing length (short, medium, long)
       - Best performing CTAs
       - Underperforming offers (recommend pausing)
       - Top performers (recommend increasing weight)
       """

       # Best tone
       tone_performance = await db.fetch("""
           SELECT
               v.tone,
               COUNT(*) as variation_count,
               AVG(CASE
                   WHEN SUM(i.impression_count) >= 10
                   THEN (SUM(c.click_count)::float / SUM(i.impression_count) * 100)
                   ELSE NULL
               END) as avg_ctr
           FROM promo_text_variations v
           LEFT JOIN promo_impression_tracking i ON v.id = i.text_id
           LEFT JOIN promo_click_tracking c ON v.id = c.variation_id
           WHERE v.approved = TRUE
           GROUP BY v.tone
           HAVING COUNT(*) >= 3
           ORDER BY avg_ctr DESC
       """)

       # Similar for length, CTAs, etc.

       return {
           "best_tone": tone_performance[0]['tone'] if tone_performance else None,
           "best_tone_ctr": tone_performance[0]['avg_ctr'] if tone_performance else 0,
           # ... more insights
       }
   ```

---

### Phase 6: Frontend Dashboard (8-12 hours)

**Goal**: Vue.js dashboard for offer management

**Stack**: Vue 3 + TypeScript + TailwindCSS

**Pages:**

1. **Offers List** (2 hours)
   - Table of all offers
   - Filter by status, type (review/affiliate)
   - Sort by CTR, impressions, clicks
   - Quick actions: Edit, Pause, Delete

2. **Offer Editor** (3 hours)
   - Create/edit offer form
   - Fields: Name, Description, Type, Affiliate Slug, Dates, Priority, Weight
   - Preview section

3. **Text Variation Generator** (2 hours)
   - Generate variations button
   - Select tone, length, number of variations
   - Loading state with progress
   - Preview generated variations
   - Approve/reject buttons

4. **Analytics Dashboard** (3 hours)
   - Overview cards: Total offers, impressions, clicks, CTR
   - Charts: CTR over time, clicks by offer, variation performance
   - Top performers table
   - Insights section

5. **Variation Performance View** (2 hours)
   - Per-offer variation breakdown
   - Side-by-side comparison
   - Pause underperforming variations
   - Promote top performers

---

## 📈 Success Metrics

### KPIs to Track:

1. **Newsletter Engagement**
   - Overall newsletter CTR (clicks on stories)
   - Promo CTR (clicks on promotional links)
   - Target: 10%+ promo CTR

2. **Variation Performance**
   - Average CTR by tone
   - Average CTR by length
   - Best performing variations

3. **Self-Learning Effectiveness**
   - CTR improvement over time
   - Variation rotation efficiency
   - Top performers vs. baseline

4. **System Reliability**
   - Newsletter send success rate (target: 100%)
   - Promo system uptime (target: 99%+)
   - Fallback usage rate (target: <5%)

---

## 🚀 Deployment Strategy

### Phase Rollout:

**Week 1: Foundation**
- Day 1-2: Phase 1 (Clean up images)
- Day 3-4: Phase 2 (Selection endpoint)
- Day 5: Testing & bug fixes

**Week 2: Analytics**
- Day 1-2: Phase 3 (Click tracking)
- Day 3-4: Phase 4 (Variation tracking)
- Day 5: Testing & validation

**Week 3: Intelligence**
- Day 1-2: Phase 5 (Self-learning)
- Day 3-5: Testing with real data

**Week 4+: Frontend**
- Phase 6 (Vue.js dashboard)
- User acceptance testing
- Launch

---

## 🎯 Quick Wins (Can Implement Today)

1. **Add offer_type field** to database (30 min)
2. **Remove Leonardo service** files (15 min)
3. **Create selection endpoint** skeleton (1 hour)
4. **Test newsletter integration** with mock promo (30 min)

**Total Quick Start: ~2-3 hours to basic functionality**

---

## 🔧 Technical Decisions

### Why Text-Only?
- ✅ More authentic, less "salesy"
- ✅ Better mobile experience
- ✅ Faster generation (no AI image wait)
- ✅ Lower costs (no Leonardo API)
- ✅ Easier variation creation
- ✅ Aligns with newsletter tone

### Why Ollama for Text?
- ✅ Already integrated and working
- ✅ GPT-OSS 120B Cloud model is excellent
- ✅ Fast generation (10-30 seconds)
- ✅ JSON format support
- ✅ Circuit breaker protection

### Why Weighted Random vs. Pure Performance?
- ✅ Prevents "winner takes all" (one variation always shown)
- ✅ Allows new variations to get tested
- ✅ Prevents overfitting to small sample sizes
- ✅ Balances exploration vs. exploitation

### Why Track Variation ID in URL?
- ✅ No database writes during newsletter send
- ✅ Click tracking happens async
- ✅ Can track even if click happens days later
- ✅ Compatible with email client link scanning

---

## 🎬 Next Steps

1. **Review this plan** - Let me know if you want any changes
2. **Approve architecture** - Confirm approach aligns with vision
3. **Start Phase 1** - I can implement clean-up immediately
4. **Test Phase 2** - Create selection endpoint and test with newsletter
5. **Iterate** - Add analytics and self-learning incrementally

---

**Ready to start?** Let me know which phase you'd like to begin with, or if you want me to implement the "Quick Wins" to get basic functionality working today!
