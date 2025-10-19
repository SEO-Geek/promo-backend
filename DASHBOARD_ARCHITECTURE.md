# Promotional Content Management Dashboard
## Complete Architecture - TEXT-ONLY System

**Version:** 1.0.0
**Created:** October 19, 2025
**Technology Stack:** Vue 3 + TypeScript + Vite + TailwindCSS
**Backend:** FastAPI at http://127.0.0.1:3003
**Purpose:** User-friendly interface for managing promotional content in AI Daily Post newsletter

---

## 🎯 Executive Summary

This is a **TEXT-ONLY** promotional content management system (no images). The dashboard provides a complete interface for:
1. Managing promotional offers (affiliate, donation, review types)
2. Generating AI-powered text variations with Ollama
3. Viewing performance analytics (impressions, clicks, CTR)
4. Approving/rejecting variations
5. Tracking which content performs best

---

## 🏗️ System Overview

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROMO MANAGEMENT DASHBOARD                    │
│                    (Vue.js @ port 5173)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND API @ port 3003                       │
│  - Offer CRUD                                                    │
│  - AI Text Generation (Ollama GPT-OSS 120B)                     │
│  - Analytics Endpoints                                           │
│  - Click Tracking                                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              POSTGRESQL DATABASE (aidailypost_cms)               │
│  - promo_offers                                                  │
│  - promo_text_variations                                         │
│  - promo_click_tracking                                          │
│  - promo_impression_tracking                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│          DAILY NEWSLETTER @ 7 AM (generate-daily-newsletter.py)  │
│  - Fetches promo via /api/v1/promo/select-random                │
│  - Inserts between stories 2-3                                   │
│  - Tracks impressions                                            │
│  - Sends via Mautic                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│          AFFILIATE REDIRECT (aidailypost.com/[slug])             │
│  - Tracks clicks with promo_var parameter                       │
│  - Records variation performance                                 │
│  - 307 redirects to destination                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dashboard Views (5 Main Screens)

### 1. Dashboard Home / Analytics Overview
**Route:** `/`
**Purpose:** High-level metrics and insights
**Components:** `DashboardHome.vue`

**Content:**
- **Overview Cards** (4 total):
  - Total Active Offers
  - Total Newsletter Impressions (Last 30 Days)
  - Total Clicks (Last 30 Days)
  - Overall CTR (Last 30 Days)

- **Top Performers Table**:
  - Offer name
  - Type (affiliate/donation/review)
  - Impressions
  - Clicks
  - CTR
  - Last used date

- **CTR Trend Chart**:
  - Line graph showing CTR over last 30 days
  - Tooltips with daily breakdown

- **Quick Actions**:
  - "Create New Offer" button
  - "View All Offers" button
  - "Generate Text Variations" button

---

### 2. Offers List
**Route:** `/offers`
**Purpose:** Manage all promotional offers
**Components:** `OffersList.vue`

**Features:**
- **Table View** with columns:
  - ID
  - Name
  - Type (badge: affiliate/donation/review)
  - Status (badge: active/draft/paused)
  - Approved Texts (count)
  - Priority
  - Weight
  - Last Used
  - Actions (Edit, Pause/Activate, Delete)

- **Filters**:
  - Filter by status (all/active/draft/paused)
  - Filter by type (all/affiliate/donation/review)
  - Search by name

- **Sorting**:
  - Sort by CTR (desc)
  - Sort by impressions (desc)
  - Sort by clicks (desc)
  - Sort by last used (desc)

- **Bulk Actions**:
  - Select multiple offers
  - Bulk activate/pause
  - Bulk delete

---

### 3. Offer Editor (Create/Edit)
**Route:** `/offers/new` or `/offers/:id/edit`
**Purpose:** Create or modify promotional offers
**Components:** `OfferEditor.vue`

**Form Fields:**

**Basic Information:**
- Name (required, text input)
- Description (required, textarea)
- Offer Type (required, select: affiliate/donation/review)
- Status (select: draft/active/paused)

**Affiliate Details:**
- Destination URL (required for affiliate/donation, URL input)
- Affiliate Slug (required, text input, validates uniqueness)

**Scheduling:**
- Start Date (optional, date picker)
- End Date (optional, date picker)

**Weighting:**
- Priority (number, 1-10, default: 5)
- Weight (number, 1-10, default: 5)
- Explanation tooltip: "Higher values = more likely to be shown"

**Actions:**
- Save as Draft
- Save & Activate
- Cancel

**Preview Section:**
- Shows how offer will look in newsletter
- Real-time preview as you type
- Mobile and desktop preview toggle

---

### 4. Text Variation Generator
**Route:** `/offers/:id/variations`
**Purpose:** Generate and manage AI text variations
**Components:** `TextVariationGenerator.vue`

**Sections:**

**A) Generation Controls:**
- Tone selector (5 options):
  - Professional
  - Casual
  - Urgent
  - Friendly
  - Exciting
- Length category (3 options):
  - Short (50-75 words)
  - Medium (75-100 words)
  - Long (100-125 words)
- Number of variations (slider: 1-8)
- "Generate Variations" button (with loading state)

**B) Generation Results:**
- Real-time progress indicator
- Shows each variation as it's generated
- For each variation:
  - Headline
  - Body text
  - CTA button text
  - Word count
  - Preview in newsletter context
  - Actions: Approve, Reject, Edit

**C) Approved Variations List:**
- Shows all approved variations for this offer
- For each:
  - Text content
  - Performance metrics (impressions, clicks, CTR)
  - Status (active/paused)
  - Actions: Pause, Edit, Delete

---

### 5. Analytics & Performance
**Route:** `/analytics`
**Purpose:** Deep dive into performance metrics
**Components:** `AnalyticsView.vue`

**Sections:**

**A) Time Period Selector:**
- Last 7 days
- Last 30 days
- Last 90 days
- Custom date range

**B) Performance Charts:**
1. **CTR Over Time** (line chart)
   - Compare multiple offers
   - Show industry benchmark line

2. **Clicks by Offer** (bar chart)
   - Top 10 offers by clicks
   - Color-coded by offer type

3. **Variation Performance** (table)
   - All variations sorted by CTR
   - Show which text performs best
   - Highlight top performers

**C) Insights Panel:**
- "Best Performing Offer" card
- "Best Performing Variation" card
- "Recommended Actions" list:
  - "Pause low-performing variation X"
  - "Create more variations for offer Y"
  - "Increase weight for offer Z"

---

## 🎨 UI/UX Design Principles

### Color Scheme
- **Primary:** Blue (#0ea5e9) - for CTAs and active states
- **Success:** Green (#10b981) - for approved, active
- **Warning:** Yellow (#fbbf24) - for draft, paused
- **Danger:** Red (#ef4444) - for delete actions
- **Neutral:** Gray scale (#f3f4f6 to #1f2937) - for backgrounds and text

### Typography
- **Headings:** Inter font, bold (700)
- **Body:** Inter font, regular (400)
- **Monospace:** 'Courier New' for IDs, slugs

### Components (TailwindCSS)
- Cards with shadow-md
- Buttons with hover effects
- Form inputs with focus rings
- Tables with striped rows
- Badges for status/type
- Loading spinners for async operations
- Toast notifications for actions

---

## 🔌 API Integration

### Authentication
All API calls require JWT token in Authorization header:
```typescript
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

**Login Endpoint:**
```
POST /api/v1/auth/login
Body: { "username": "user", "password": "pass" }
Response: { "access_token": "...", "token_type": "bearer" }
```

### Key Endpoints Used by Dashboard

**Offers Management:**
```
GET    /api/v1/offers              # List all offers
POST   /api/v1/offers              # Create offer
GET    /api/v1/offers/{id}         # Get single offer
PUT    /api/v1/offers/{id}         # Update offer
DELETE /api/v1/offers/{id}         # Delete offer
```

**Text Generation:**
```
POST   /api/v1/offers/{id}/generate-text
Body: {
  "tone": "professional",
  "length_category": "medium",
  "num_variations": 5
}
Response: {
  "job_id": "...",
  "status": "completed",
  "variations": [...]
}
```

**Text Variations:**
```
GET    /api/v1/offers/{id}/texts   # List variations
PUT    /api/v1/texts/{id}/approve  # Approve variation
DELETE /api/v1/texts/{id}          # Delete variation
```

**Analytics (TO BE IMPLEMENTED):**
```
GET    /api/v1/analytics/overview
  ?start_date=2025-10-01&end_date=2025-10-31
Response: {
  "total_impressions": 150,
  "total_clicks": 45,
  "overall_ctr": 30.0,
  "top_offers": [...]
}

GET    /api/v1/analytics/offers/{id}
Response: {
  "offer_id": 1,
  "impressions": 50,
  "clicks": 15,
  "ctr": 30.0,
  "variations": [...]
}
```

---

## 🛠️ Technology Stack

### Frontend
```json
{
  "framework": "Vue 3.4+ with Composition API",
  "language": "TypeScript 5.3+",
  "build": "Vite 5.0+",
  "styling": "TailwindCSS 3.4+",
  "routing": "Vue Router 4.2+",
  "state": "Pinia 2.1+ (optional, may use composables)",
  "http": "Axios 1.6+",
  "charts": "Chart.js 4.4+ with vue-chartjs",
  "icons": "Heroicons or Lucide Vue",
  "forms": "Vee-Validate + Yup (optional)",
  "notifications": "Vue Toastification"
}
```

### Development Setup
```bash
# Project initialization
cd /opt/aidailypost/promo-backend
npm create vue@latest promo-dashboard

# Selected options:
# ✔ Add TypeScript? Yes
# ✔ Add JSX Support? No
# ✔ Add Vue Router? Yes
# ✔ Add Pinia for state management? Yes
# ✔ Add Vitest for Unit Testing? Yes
# ✔ Add ESLint for code quality? Yes

cd promo-dashboard
npm install

# Additional dependencies
npm install axios vue-chartjs chart.js
npm install @heroicons/vue
npm install vue-toastification

# TailwindCSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

## 📁 Project Structure

```
/opt/aidailypost/promo-backend/promo-dashboard/
├── src/
│   ├── assets/           # Static assets (images, fonts)
│   ├── components/       # Reusable components
│   │   ├── common/
│   │   │   ├── Button.vue
│   │   │   ├── Card.vue
│   │   │   ├── Badge.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── Table.vue
│   │   ├── offers/
│   │   │   ├── OfferCard.vue
│   │   │   ├── OfferTable.vue
│   │   │   └── OfferPreview.vue
│   │   ├── variations/
│   │   │   ├── VariationCard.vue
│   │   │   ├── VariationList.vue
│   │   │   └── GenerationProgress.vue
│   │   └── analytics/
│   │       ├── StatCard.vue
│   │       ├── CTRChart.vue
│   │       └── PerformanceTable.vue
│   ├── views/            # Page components
│   │   ├── DashboardHome.vue
│   │   ├── OffersList.vue
│   │   ├── OfferEditor.vue
│   │   ├── TextVariationGenerator.vue
│   │   ├── AnalyticsView.vue
│   │   └── LoginView.vue
│   ├── router/
│   │   └── index.ts      # Vue Router config
│   ├── stores/           # Pinia stores (optional)
│   │   ├── auth.ts
│   │   ├── offers.ts
│   │   └── analytics.ts
│   ├── composables/      # Reusable composition functions
│   │   ├── useAuth.ts
│   │   ├── useOffers.ts
│   │   ├── useAnalytics.ts
│   │   └── useToast.ts
│   ├── services/         # API service layer
│   │   ├── api.ts        # Axios instance config
│   │   ├── auth.service.ts
│   │   ├── offers.service.ts
│   │   ├── variations.service.ts
│   │   └── analytics.service.ts
│   ├── types/            # TypeScript interfaces
│   │   ├── offer.ts
│   │   ├── variation.ts
│   │   ├── analytics.ts
│   │   └── api.ts
│   ├── utils/            # Helper functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   ├── App.vue           # Root component
│   └── main.ts           # Entry point
├── public/               # Static files
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## 🔐 Authentication Flow

```typescript
// On app load (main.ts)
1. Check if token exists in localStorage
2. If yes, validate with /api/v1/auth/me
3. If valid, set user state and proceed
4. If invalid, redirect to /login

// On login (LoginView.vue)
1. User enters credentials
2. POST /api/v1/auth/login
3. Store token in localStorage
4. Store user info in auth state
5. Redirect to dashboard

// On API request (api.ts interceptor)
1. Attach token to Authorization header
2. If 401 response, clear token and redirect to login
3. If 403 response, show permission error

// On logout
1. Clear token from localStorage
2. Clear auth state
3. Redirect to /login
```

---

## 📱 Responsive Design

### Breakpoints (TailwindCSS)
- `sm:` 640px - Mobile landscape
- `md:` 768px - Tablet
- `lg:` 1024px - Desktop
- `xl:` 1280px - Large desktop

### Mobile-First Approach
- All layouts start mobile (single column)
- Add grid/flex at `md:` breakpoint
- Full multi-column at `lg:` breakpoint
- Touch-friendly buttons (min 48px height)
- Collapsible sidebar on mobile

---

## 🚀 Implementation Plan

### Phase 1: Project Setup (30 minutes)
- [x] Backend API operational ✅
- [ ] Create Vue 3 + TypeScript + Vite project
- [ ] Install dependencies (TailwindCSS, Axios, Chart.js)
- [ ] Configure TailwindCSS
- [ ] Set up Vue Router
- [ ] Create base layout structure

### Phase 2: Authentication (1 hour)
- [ ] Create LoginView.vue
- [ ] Implement auth service (login, logout, validate)
- [ ] Create auth composable
- [ ] Set up route guards
- [ ] Test login flow

### Phase 3: Dashboard Home (1.5 hours)
- [ ] Create DashboardHome.vue
- [ ] Implement StatCard component
- [ ] Create overview API service
- [ ] Display metrics cards
- [ ] Add top performers table
- [ ] Implement CTR trend chart

### Phase 4: Offers Management (2 hours)
- [ ] Create OffersList.vue
- [ ] Implement OfferTable component
- [ ] Add filters and sorting
- [ ] Create OfferEditor.vue
- [ ] Implement form validation
- [ ] Add preview section
- [ ] Test CRUD operations

### Phase 5: Text Variation Generator (2 hours)
- [ ] Create TextVariationGenerator.vue
- [ ] Implement generation controls
- [ ] Add loading states
- [ ] Display generated variations
- [ ] Implement approve/reject actions
- [ ] Show approved variations list

### Phase 6: Analytics View (1.5 hours)
- [ ] Create AnalyticsView.vue
- [ ] Implement time period selector
- [ ] Add CTR chart component
- [ ] Create clicks bar chart
- [ ] Build variation performance table
- [ ] Add insights panel

### Phase 7: Backend Analytics Endpoints (1.5 hours)
- [ ] Implement `/api/v1/analytics/overview` endpoint
- [ ] Implement `/api/v1/analytics/offers/{id}` endpoint
- [ ] Add click tracking aggregation
- [ ] Calculate CTR metrics
- [ ] Test with sample data

### Phase 8: Integration & Testing (1 hour)
- [ ] Test full create-to-newsletter flow
- [ ] Verify analytics accuracy
- [ ] Test mobile responsiveness
- [ ] Fix bugs
- [ ] Polish UI/UX

### Phase 9: Deployment (30 minutes)
- [ ] Build production bundle
- [ ] Configure Nginx for dashboard
- [ ] Set up systemd service (if needed)
- [ ] Document access URL
- [ ] Create user guide

**Total Estimated Time:** 11-12 hours

---

## 🌐 Deployment Strategy

### Option 1: Standalone Dev Server (Recommended for MVP)
```bash
# Run on port 5173 (Vite default)
cd /opt/aidailypost/promo-backend/promo-dashboard
npm run dev -- --host 0.0.0.0 --port 5173

# Access at: http://127.0.0.1:5173
```

### Option 2: Production Build with Nginx
```bash
# Build production bundle
npm run build

# Output: dist/ folder with static files

# Nginx configuration
# Add to /etc/nginx/sites-available/aidailypost

location /promo-admin {
    alias /opt/aidailypost/promo-backend/promo-dashboard/dist;
    try_files $uri $uri/ /promo-admin/index.html;
}

# Restart Nginx
nginx -t && systemctl reload nginx

# Access at: https://aidailypost.com/promo-admin
```

### Environment Variables
Create `.env` file:
```bash
VITE_API_URL=http://127.0.0.1:3003/api/v1
VITE_API_TIMEOUT=10000
VITE_APP_TITLE="AI Daily Post - Promo Manager"
```

---

## 📝 User Guide (For Documentation)

### Creating a New Offer

1. **Navigate to Offers List**
   - Click "Offers" in sidebar
   - Click "Create New Offer" button

2. **Fill in Basic Information**
   - Name: "No Code MBA"
   - Description: "Learn to build apps without coding"
   - Type: "affiliate"
   - Destination URL: "https://www.nocode.mba/?via=brian"
   - Affiliate Slug: "nocodemba" (must be unique)

3. **Set Weighting**
   - Priority: 5 (1-10 scale, affects selection frequency)
   - Weight: 5 (1-10 scale, affects random selection)

4. **Save**
   - "Save as Draft" (won't appear in newsletter)
   - "Save & Activate" (eligible for newsletter)

### Generating Text Variations

1. **Open Variation Generator**
   - From offers list, click "Generate Texts" action
   - Or navigate to `/offers/{id}/variations`

2. **Configure Generation**
   - Select tone: Professional, Casual, Urgent, Friendly, or Exciting
   - Select length: Short (50-75), Medium (75-100), or Long (100-125) words
   - Choose number: 1-8 variations

3. **Generate**
   - Click "Generate Variations"
   - Wait for AI to generate (usually 5-15 seconds per variation)
   - Preview each variation in newsletter context

4. **Approve Variations**
   - Review each variation
   - Click "Approve" for variations you like
   - Click "Reject" to discard
   - Edit if needed before approving

5. **Manage Approved Variations**
   - View all approved variations
   - Pause underperforming ones
   - Delete outdated ones

### Viewing Analytics

1. **Navigate to Analytics**
   - Click "Analytics" in sidebar

2. **Select Time Period**
   - Last 7 days, 30 days, 90 days, or custom range

3. **Review Metrics**
   - Overview cards: Impressions, clicks, CTR
   - CTR trend chart
   - Top performing offers
   - Variation performance breakdown

4. **Take Action**
   - Follow "Recommended Actions" insights
   - Pause low performers
   - Create more variations for high performers

---

## 🔧 Maintenance & Operations

### Monitoring
- Backend API health: `curl http://127.0.0.1:3003/api/promo/health`
- Frontend dev server: Check Vite console output
- Database: `psql -d aidailypost_cms -c "SELECT COUNT(*) FROM promo_offers"`

### Backup
- Database: Automatic daily backups via existing backup system
- Dashboard code: Git repository (commit regularly)
- No state stored in frontend (stateless)

### Troubleshooting
**Problem:** Dashboard can't connect to API
**Solution:** Check if backend is running on port 3003, check CORS settings

**Problem:** Authentication fails
**Solution:** Verify JWT_SECRET_KEY in backend `.env` matches

**Problem:** Text generation slow
**Solution:** Ollama Cloud may be rate limited, check logs

---

## 📚 Additional Resources

- Vue 3 Docs: https://vuejs.org/guide/
- TailwindCSS: https://tailwindcss.com/docs
- Chart.js: https://www.chartjs.org/docs/latest/
- Vite: https://vitejs.dev/guide/

---

**Document Status:** Complete and ready for implementation
**Next Step:** Begin Phase 1 - Project Setup
**Estimated MVP Delivery:** 11-12 hours from start

