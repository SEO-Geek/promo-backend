# Promotional Content Management System - Deployment Checklist

**System:** AI Daily Post - Promotional Content Backend
**Version:** 1.0.0
**Last Updated:** October 17, 2025

---

## Pre-Deployment Checks

### Security Audit
- [ ] All API keys and secrets stored in environment variables (never hardcoded)
- [ ] `.env` file added to `.gitignore` and never committed
- [ ] SQL injection protection verified (parameterized queries throughout)
- [ ] Rate limiting configured on all endpoints
- [ ] CORS origins properly configured (no wildcard `*` in production)
- [ ] Authentication required on all sensitive endpoints
- [ ] JWT secret key is strong and unique (min 32 characters)
- [ ] Password hashing using bcrypt with proper salt rounds

### Configuration Review
- [ ] Environment variables documented in `.env.example`
- [ ] Production database credentials configured
- [ ] Leonardo AI API key valid and has sufficient credits
- [ ] Ollama service running and accessible
- [ ] Image upload directory exists with proper permissions
- [ ] Image base URL points to correct CDN/static server
- [ ] Log directory exists and is writable

### Code Quality
- [ ] All deprecation warnings resolved
- [ ] No `TODO` or `FIXME` comments in critical paths
- [ ] Error handling implemented on all endpoints
- [ ] Logging configured for production (INFO level)
- [ ] No debug print statements left in code
- [ ] Code follows PEP 8 style guidelines

---

## Database Setup

### PostgreSQL Configuration
- [ ] PostgreSQL 14+ installed and running
- [ ] Database `aidailypost_promo` created
- [ ] Database user `promo_user` created with strong password
- [ ] User has appropriate permissions (not superuser)
- [ ] Connection pooling configured (asyncpg)
- [ ] Database backup strategy in place

### Schema Migration
- [ ] Run schema creation script:
  ```bash
  cd /opt/aidailypost/promo-backend
  PGPASSWORD='your_password' psql -h localhost -U promo_user -d aidailypost_promo -f database/schema.sql
  ```
- [ ] Verify all tables created:
  - `promo_users`
  - `promo_offers`
  - `promo_images`
  - `promo_text_variations`
  - `promo_generation_jobs`
  - `promo_newsletter_sends`
- [ ] Verify all indexes created
- [ ] Verify foreign key constraints in place

### Initial Data
- [ ] Create admin user account:
  ```bash
  python scripts/create_admin_user.py --email labaek@gmail.com --name "Admin User"
  ```
- [ ] Verify admin user can login
- [ ] Test database connection from application

---

## Application Deployment

### Environment Setup
- [ ] Python 3.11+ installed
- [ ] Virtual environment created:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- [ ] Dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Dependencies pinned to specific versions

### File Permissions
- [ ] Application directory owned by `aidailypost` user
- [ ] Image upload directory: `755` permissions
- [ ] Log directory: `755` permissions
- [ ] `.env` file: `600` permissions (readable only by owner)
- [ ] Service files: `644` permissions

### Systemd Service
- [ ] Service file created: `/etc/systemd/system/promo-backend.service`
- [ ] Service configured to run as `aidailypost` user
- [ ] Service configured to restart on failure
- [ ] Working directory set correctly
- [ ] Environment file path configured
- [ ] Service enabled:
  ```bash
  systemctl enable promo-backend
  ```
- [ ] Service started:
  ```bash
  systemctl start promo-backend
  ```
- [ ] Service status verified:
  ```bash
  systemctl status promo-backend
  ```

---

## Web Server Configuration

### Nginx Setup
- [ ] Nginx installed and running
- [ ] SSL certificates installed (Let's Encrypt or custom)
- [ ] Server block configured for `promo.aidailypost.com`
- [ ] Reverse proxy to `127.0.0.1:3003` configured
- [ ] Rate limiting configured at Nginx level
- [ ] Security headers configured:
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security` (HSTS)
- [ ] Gzip compression enabled for JSON responses
- [ ] Nginx configuration tested:
  ```bash
  nginx -t
  ```
- [ ] Nginx reloaded:
  ```bash
  systemctl reload nginx
  ```

### Firewall Configuration
- [ ] UFW enabled
- [ ] SSH port allowed (22)
- [ ] HTTP allowed (80)
- [ ] HTTPS allowed (443)
- [ ] Backend port NOT exposed externally (3003 localhost only)
- [ ] PostgreSQL port NOT exposed externally (5432 localhost only)

---

## External Services

### Leonardo AI
- [ ] API key configured in `.env`
- [ ] Account has sufficient credits
- [ ] Test image generation successful
- [ ] Rate limits understood (10/hour configured)
- [ ] Error handling tested

### Ollama AI
- [ ] Ollama service installed and running
- [ ] llama3.2:latest model downloaded
- [ ] Service accessible at `http://localhost:11434`
- [ ] Test text generation successful
- [ ] Rate limits configured (20/hour)

### Image Storage
- [ ] Image upload directory exists: `/var/www/aidailypost/promo-images`
- [ ] Directory writable by application user
- [ ] Static file serving configured in Nginx
- [ ] CDN configured (if applicable)
- [ ] Image cleanup cron job configured (optional)

---

## Monitoring & Logging

### Application Logs
- [ ] Log file location: `/var/log/promo-backend.log`
- [ ] Log rotation configured (logrotate)
- [ ] Log level appropriate for production (INFO)
- [ ] Sensitive data NOT logged (passwords, API keys)
- [ ] Error notifications configured (optional)

### System Monitoring
- [ ] systemd service monitoring active
- [ ] Health check endpoint accessible: `/api/v1/promo/health`
- [ ] Uptime monitoring configured (optional)
- [ ] Performance metrics tracking (optional)
- [ ] Database connection pool monitoring

### Backup Strategy
- [ ] Daily database backups configured
- [ ] Image files backed up regularly
- [ ] Backup retention policy defined (30 days recommended)
- [ ] Backup restoration tested
- [ ] Configuration files backed up

---

## Testing Procedures

### Pre-Deployment Testing
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Load testing completed (if applicable)
- [ ] Security scan completed (no critical vulnerabilities)

### Post-Deployment Verification
- [ ] **Health Check:**
  ```bash
  curl https://promo.aidailypost.com/api/v1/promo/health
  ```
  Expected: `{"status": "healthy"}` or `{"status": "degraded"}`

- [ ] **Root Endpoint:**
  ```bash
  curl https://promo.aidailypost.com/
  ```
  Expected: API information with version 1.0.0

- [ ] **API Documentation:**
  ```bash
  curl https://promo.aidailypost.com/api/v1/docs
  ```
  Expected: Swagger UI loads

- [ ] **Authentication:**
  ```bash
  curl -X POST https://promo.aidailypost.com/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"labaek@gmail.com","password":"your_password"}'
  ```
  Expected: JWT token returned

- [ ] **Rate Limiting:**
  Test that rate limits are enforced (101st request blocked)

- [ ] **CORS:**
  Verify allowed origins work, others blocked

- [ ] **SSL Certificate:**
  ```bash
  openssl s_client -connect promo.aidailypost.com:443 -servername promo.aidailypost.com
  ```
  Expected: Valid certificate chain

### Functional Testing
- [ ] Create a test offer via API
- [ ] Generate test images (verify Leonardo AI integration)
- [ ] Generate test text (verify Ollama integration)
- [ ] Approve content (images and text)
- [ ] Generate newsletter preview
- [ ] Delete test data after verification

---

## Rollback Procedures

### Quick Rollback Steps
1. **Stop new service:**
   ```bash
   systemctl stop promo-backend
   ```

2. **Restore previous code:**
   ```bash
   cd /opt/aidailypost/promo-backend
   git reset --hard <previous_commit_hash>
   ```

3. **Restore database backup (if schema changed):**
   ```bash
   pg_restore -U promo_user -d aidailypost_promo /path/to/backup.sql
   ```

4. **Restart service:**
   ```bash
   systemctl start promo-backend
   ```

5. **Verify rollback:**
   ```bash
   curl https://promo.aidailypost.com/api/v1/promo/health
   ```

### Emergency Contacts
- **System Admin:** labaek@gmail.com
- **Database Admin:** [Contact Info]
- **DevOps Team:** [Contact Info]

---

## Post-Deployment Tasks

### Documentation
- [ ] Update system documentation with new version
- [ ] Document any configuration changes
- [ ] Update API documentation if endpoints changed
- [ ] Notify stakeholders of deployment

### Monitoring Setup
- [ ] First 24 hours: Monitor error logs hourly
- [ ] First week: Check performance metrics daily
- [ ] Set up alerts for:
  - Service crashes
  - High error rates (>5% of requests)
  - Database connection failures
  - External API failures (Leonardo, Ollama)

### Performance Baseline
- [ ] Record baseline metrics:
  - Average response time
  - Requests per second
  - Database query performance
  - Memory usage
  - CPU usage
- [ ] Compare with expected performance

---

## Deployment Sign-Off

**Deployment Date:** _________________

**Deployed By:** _________________

**Verified By:** _________________

**Notes/Issues:**
_________________________________________________
_________________________________________________
_________________________________________________

**Deployment Status:** [ ] Success  [ ] Partial Success  [ ] Failed

---

## Version History

| Version | Date | Changes | Deployed By |
|---------|------|---------|-------------|
| 1.0.0 | 2025-10-17 | Initial release with rate limiting, API versioning, SQL injection fixes | System |

---

## References

- **Main Application:** `/opt/aidailypost/promo-backend/app/main.py`
- **Configuration:** `/opt/aidailypost/promo-backend/.env`
- **Database Schema:** `/opt/aidailypost/promo-backend/database/schema.sql`
- **Service File:** `/etc/systemd/system/promo-backend.service`
- **Nginx Config:** `/etc/nginx/sites-available/promo-aidailypost`
- **API Documentation:** `https://promo.aidailypost.com/api/v1/docs`

---

**End of Deployment Checklist**
