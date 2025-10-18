# Promotional System - Testing Guide

## Quick Start Testing

### 1. Check Backend is Running
```bash
ps aux | grep "python -m app.main" | grep -v grep
# Should show: python -m app.main (PID 510424 or similar)

# Check port
netstat -tlnp 2>/dev/null | grep :3003
# Should show: 127.0.0.1:3003 LISTEN
```

### 2. Test Health Check
```bash
curl -s http://127.0.0.1:3003/api/promo/health | jq .
```

**Expected Response:**
```json
{
  "status": "degraded",
  "timestamp": "2025-10-16T21:22:19.017384",
  "components": {
    "database": "healthy",
    "active_offers": "degraded (no active offers)",
    "approved_content": "degraded (no approved content)"
  },
  "can_provide_content": false
}
```
✅ Status "degraded" is EXPECTED (no offers created yet)
✅ Database should be "healthy"

### 3. Test Root Endpoint
```bash
curl -s http://127.0.0.1:3003/ | jq .
```

**Expected Response:**
```json
{
  "name": "Promotional Content Management API",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/api/docs",
  "health": "/api/promo/health"
}
```

### 4. Test Login
```bash
# Create credentials file
cat > /tmp/login.json << 'EOF'
{
  "email": "labaek@gmail.com",
  "password": "ChangeMe2025!"
}
EOF

# Test login
curl -s -X POST http://127.0.0.1:3003/api/auth/login \
  -H "Content-Type: application/json" \
  -d @/tmp/login.json | jq .
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGci...(long JWT token)...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "labaek@gmail.com",
    "name": "Admin User",
    "role": "admin"
  }
}
```

### 5. Test via Browser
Open in your browser:
- **API Documentation:** http://127.0.0.1:3003/api/docs
- **Alternative Docs:** http://127.0.0.1:3003/api/redoc

You can test all endpoints interactively in the Swagger UI!

### 6. Test Through Nginx (External)
```bash
# If you want to test via the subdomain (requires Cloudflare)
curl -s https://promo.aidailypost.com/api/promo/health | jq .
```

---

## Database Verification

### Check Tables
```bash
PGPASSWORD='AiDaily@2025$ecure' psql -h 127.0.0.1 -U strapi_user -d aidailypost_cms -c "\dt promo_*"
```

**Expected Output:**
```
List of relations
 Schema |              Name               | Type  |    Owner
--------+---------------------------------+-------+--------------
 public | promo_analytics                 | table | strapi_user
 public | promo_generation_jobs           | table | strapi_user
 public | promo_images                    | table | strapi_user
 public | promo_newsletter_usage          | table | strapi_user
 public | promo_offers                    | table | strapi_user
 public | promo_system_health             | table | strapi_user
 public | promo_text_variations           | table | strapi_user
 public | promo_users                     | table | strapi_user
(8 rows)
```

### Check Default User
```bash
PGPASSWORD='AiDaily@2025$ecure' psql -h 127.0.0.1 -U strapi_user -d aidailypost_cms -c "
SELECT id, email, name, role, is_active
FROM promo_users
WHERE email = 'labaek@gmail.com';
"
```

**Expected Output:**
```
 id |      email       |    name    | role  | is_active
----+------------------+------------+-------+-----------
  1 | labaek@gmail.com | Admin User | admin | t
(1 row)
```

### Check Offers (Should be empty initially)
```bash
PGPASSWORD='AiDaily@2025$ecure' psql -h 127.0.0.1 -U strapi_user -d aidailypost_cms -c "
SELECT id, name, status FROM promo_offers;
"
```

**Expected Output:**
```
 id | name | status
----+------+--------
(0 rows)
```

---

## Troubleshooting

### Backend Not Running
```bash
cd /opt/aidailypost/promo-backend
source venv/bin/activate
nohup python -m app.main >> /var/log/promo-backend.log 2>&1 &
echo "Backend started with PID: $!"
```

### Check Logs for Errors
```bash
tail -50 /var/log/promo-backend.log
```

### Port Already in Use
```bash
# Find what's using port 3003
sudo netstat -tlnp | grep :3003

# Kill the process if needed
sudo kill <PID>
```

### Database Connection Issues
```bash
# Test database connection
PGPASSWORD='AiDaily@2025$ecure' psql -h 127.0.0.1 -U strapi_user -d aidailypost_cms -c "SELECT 1;"

# Should return:
 ?column?
----------
        1
(1 row)
```

### Nginx Not Proxying
```bash
# Test Nginx configuration
nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check Nginx logs
tail -f /var/log/nginx/error.log
```

---

## Success Criteria ✅

Your backend is working correctly if:

1. ✅ Backend process is running (PID visible)
2. ✅ Port 3003 is listening
3. ✅ Health check returns JSON with "status" field
4. ✅ Root endpoint returns API information
5. ✅ Login returns JWT token
6. ✅ Database has 8 promo_* tables
7. ✅ Default admin user exists
8. ✅ Swagger UI loads at /api/docs

---

## Next: Create Your First Offer

Once Phase 2 is complete, you'll be able to create offers like this:

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://127.0.0.1:3003/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "labaek@gmail.com", "password": "ChangeMe2025!"}' | jq -r .access_token)

# Create offer
curl -s -X POST http://127.0.0.1:3003/api/offers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "No Code MBA Course",
    "description": "Learn to build startups without code",
    "destination_url": "https://aidailypost.com/nocodemba",
    "status": "draft"
  }' | jq .
```

But first, we need to implement the CRUD endpoints in Phase 2!

---

**Status:** Ready for testing ✅
**Backend:** Operational
**Database:** Connected
**Authentication:** Working
