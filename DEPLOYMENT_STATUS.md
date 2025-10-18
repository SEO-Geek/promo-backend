# Deployment Status - v3.3.0

**Deployed:** October 18, 2025 - 17:03 CEST
**Status:** ✅ PRODUCTION OPERATIONAL
**Version:** 3.3.0 (Bulletproof Text Editing Workflow)

---

## 🚀 Service Status

**Process:**
- PID: 2583692
- Command: `venv/bin/python -m app.main`
- Status: Running
- Uptime: Active since 17:56 CEST

**Network:**
- Port: 3003
- Bind: 127.0.0.1 (localhost only)
- Protocol: HTTP
- Access: Internal only (proxied via Nginx if needed)

**Health Check:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-18T16:03:15.122972",
  "components": {
    "database": "healthy",
    "active_offers": "healthy (2 offers)",
    "approved_content": "healthy (2 ready)"
  },
  "can_provide_content": true
}
```

---

## 📋 API Endpoints (18 Total)

### Authentication (2)
- `POST /api/v1/auth/login` - Login with credentials
- `GET /api/v1/auth/me` - Get current user info

### Offers (5)
- `POST /api/v1/offers` - Create new offer
- `GET /api/v1/offers` - List all offers
- `GET /api/v1/offers/{offer_id}` - Get offer details
- `PUT /api/v1/offers/{offer_id}` - Update offer
- `DELETE /api/v1/offers/{offer_id}` - Delete offer

### Text Generation (5)
- `POST /api/v1/offers/{offer_id}/generate-text` - Generate AI text variations
- `GET /api/v1/offers/{offer_id}/texts` - List text variations
- **`PUT /api/v1/texts/{text_id}` - 🆕 Edit text variation (v3.3.0)**
- `PUT /api/v1/texts/{text_id}/approve` - Approve/unapprove text
- `DELETE /api/v1/texts/{text_id}` - Delete text variation

### Newsletter Integration (4)
- `GET /api/v1/promo/select-random` - Select random approved promo
- `POST /api/v1/promo/track-impression` - Track newsletter impression
- `POST /api/v1/promo/track-click` - Track user click
- `GET /api/v1/promo/preview` - Preview newsletter HTML

### System (2)
- `GET /` - API info
- `GET /api/v1/promo/health` - Health check

---

## 🔐 Authentication

**Admin Credentials:**
- Email: `labaek@gmail.com`
- Password: `PromoAdmin@2025$ecure`
- Token Type: JWT (24-hour expiration)

**Login Example:**
```bash
curl -X POST http://127.0.0.1:3003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "labaek@gmail.com",
    "password": "PromoAdmin@2025$ecure"
  }'
```

---

## 🆕 What's New in v3.3.0

### Text Editing Endpoint
**Feature:** Manual editing of AI-generated text before approval

**Endpoint:** `PUT /api/v1/texts/{text_id}`

**Use Cases:**
- Fix typos in AI-generated text
- Adjust phrasing to match brand voice
- Customize CTA button text
- Reclassify tone/length after edits

**Example:**
```bash
# Login first
TOKEN=$(curl -s -X POST http://127.0.0.1:3003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "labaek@gmail.com", "password": "PromoAdmin@2025$ecure"}' \
  | jq -r '.access_token')

# Edit text
curl -X PUT http://127.0.0.1:3003/api/v1/texts/6 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Flash Sale! 50% off all courses this weekend only!",
    "cta_text": "Shop Now",
    "tone": "urgent",
    "length_category": "short"
  }'
```

---

## 📊 Database

**Connection:** PostgreSQL 16
- Host: 127.0.0.1:5432
- Database: `aidailypost_cms`
- User: `strapi_user`
- Password: `AiDaily@2025$ecure`

**Tables (9):**
1. `promo_users` - Authentication
2. `promo_offers` - Promotional offers
3. `promo_text_variations` - AI-generated text
4. `promo_generation_jobs` - Job tracking
5. `promo_impression_tracking` - Newsletter impressions
6. `promo_click_tracking` - Click analytics
7. `promo_newsletter_usage` - Newsletter history
8. `promo_analytics` - Performance metrics
9. `promo_system_health` - Health monitoring

---

## 🔄 Complete Workflow

### Step 1: Create Offer
```bash
curl -X POST http://127.0.0.1:3003/api/v1/offers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "No Code MBA Course",
    "description": "Learn to build apps without coding using Bubble, Webflow, Airtable",
    "offer_type": "affiliate",
    "destination_url": "https://aidailypost.com/nocodemba",
    "affiliate_slug": "nocodemba",
    "status": "active"
  }'
```

### Step 2: Generate Text Variations
```bash
curl -X POST http://127.0.0.1:3003/api/v1/offers/4/generate-text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "exciting",
    "length_category": "medium",
    "num_variations": 5
  }'
```

### Step 3: 🆕 ADJUST Text (NEW!)
```bash
curl -X PUT http://127.0.0.1:3003/api/v1/texts/14 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Edited promotional text with better phrasing...",
    "cta_text": "Get Started"
  }'
```

### Step 4: Approve
```bash
curl -X PUT http://127.0.0.1:3003/api/v1/texts/14/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approve": true}'
```

### Step 5: Newsletter Integration
```bash
# Newsletter system calls this endpoint
curl http://127.0.0.1:3003/api/v1/promo/select-random?offer_type=affiliate

# Track impression after send
curl -X POST http://127.0.0.1:3003/api/v1/promo/track-impression \
  -H "Content-Type: application/json" \
  -d '{
    "offer_id": 4,
    "variation_id": 14,
    "newsletter_send_id": "2025-10-18-daily",
    "subscriber_count": 10000
  }'
```

---

## 📈 Performance

**Response Times:**
- Health check: <10ms
- Login: <50ms
- Text generation: ~15s (Ollama AI)
- Text update: <100ms
- Random selection: <50ms
- Impression tracking: <50ms

**Rate Limits:**
- Authentication: 10/minute
- Text generation: 20/hour (Ollama API)
- Text updates: 100/minute
- Tracking: 200/minute

---

## 🛠️ Service Management

### Start Service
```bash
cd /opt/aidailypost/promo-backend
venv/bin/python -m app.main >> /var/log/promo-backend.log 2>&1 &
```

### Stop Service
```bash
ps aux | grep "python -m app.main" | grep -v grep | awk '{print $2}' | xargs kill
```

### Restart Service
```bash
# Stop
ps aux | grep "python -m app.main" | grep -v grep | awk '{print $2}' | xargs kill

# Wait
sleep 2

# Start
cd /opt/aidailypost/promo-backend
venv/bin/python -m app.main >> /var/log/promo-backend.log 2>&1 &
```

### Check Status
```bash
# Process
ps aux | grep "python -m app.main" | grep -v grep

# Port
netstat -tlnp | grep :3003

# Health
curl http://127.0.0.1:3003/api/v1/promo/health
```

---

## 📝 Logs

**Location:** `/var/log/promo-backend.log`

**View Recent Logs:**
```bash
tail -f /var/log/promo-backend.log
```

**Search for Errors:**
```bash
grep -i "error\|failed" /var/log/promo-backend.log | tail -20
```

---

## 🔍 API Documentation

**Swagger UI:** http://127.0.0.1:3003/api/v1/docs
**ReDoc:** http://127.0.0.1:3003/api/v1/redoc
**OpenAPI Schema:** http://127.0.0.1:3003/openapi.json

---

## 📦 Git Repository

**Location:** `/opt/aidailypost/promo-backend/.git`
**Latest Commit:** `8acdc05` (v3.3.0)
**Tag:** `v3.3.0`
**Files:** 27 files, 18,083 lines

**View History:**
```bash
cd /opt/aidailypost/promo-backend
git log --oneline
git tag -l
```

---

## ✅ Deployment Checklist

- [x] Service running (PID 2583692)
- [x] Port binding confirmed (3003)
- [x] Health check passing
- [x] Database connection working
- [x] Authentication functional
- [x] All 18 endpoints operational
- [x] New text editing endpoint tested
- [x] Git repository initialized
- [x] Code committed and tagged
- [x] Documentation complete
- [x] Credentials documented
- [x] Logs accessible

---

## 🚨 Troubleshooting

### Service Not Responding
```bash
# Check if running
ps aux | grep "python -m app.main"

# Check logs
tail -50 /var/log/promo-backend.log

# Restart
cd /opt/aidailypost/promo-backend
ps aux | grep "python -m app.main" | grep -v grep | awk '{print $2}' | xargs kill
sleep 2
venv/bin/python -m app.main >> /var/log/promo-backend.log 2>&1 &
```

### Database Connection Error
```bash
# Test connection
PGPASSWORD='AiDaily@2025$ecure' psql -U strapi_user -h 127.0.0.1 -d aidailypost_cms -c "SELECT 1;"
```

### Port Already in Use
```bash
# Find process using port 3003
lsof -i :3003

# Kill it
kill $(lsof -t -i :3003)
```

---

## 📞 Support

**Documentation:**
- Main: `/opt/aidailypost/promo-backend/CHANGELOG.md`
- Credentials: `/opt/aidailypost/promo-backend/CREDENTIALS.md`
- Testing: `/opt/aidailypost/promo-backend/TESTING.md`

**Contact:**
- Admin: labaek@gmail.com

---

**Deployment Status:** ✅ OPERATIONAL
**Last Updated:** 2025-10-18 17:03 CEST
**Next Review:** As needed

*Deployed by Claude Code*
