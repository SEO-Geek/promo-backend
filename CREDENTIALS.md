# Promo Backend Credentials

## Admin Login

**Email:** labaek@gmail.com
**Password:** PromoAdmin@2025$ecure

## API Access

**Base URL:** http://127.0.0.1:3003/api/v1

**Login Endpoint:**
```bash
curl -X POST http://127.0.0.1:3003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "labaek@gmail.com", "password": "PromoAdmin@2025$ecure"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Database Credentials

**Connection:** Same as main system
**Database:** aidailypost_cms
**User:** strapi_user
**Password:** AiDaily@2025$ecure

---

*Last Updated: October 18, 2025*
*Password reset after Phase 9 testing*
