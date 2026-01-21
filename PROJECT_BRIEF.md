# Daňový Poradce Pro - Project Brief

## Executive Summary

**Daňový Poradce Pro** is an AI-powered tax optimization and accounting platform specifically designed for Czech small businesses (s.r.o. - limited liability companies) and individuals. The platform provides intelligent tax advisory, financial management, and compliance tools powered by Claude AI.

---

## 1. Project Overview

### 1.1 Purpose
A comprehensive financial management solution that helps Czech entrepreneurs:
- Optimize tax strategies (dividend vs. salary decisions)
- Track income, expenses, and cash flow
- Manage invoices and assets
- Get AI-powered tax advice based on Czech tax law
- Handle multi-currency transactions (with App Store income support)

### 1.2 Target Users
- Czech s.r.o. (limited liability company) owners
- Individual entrepreneurs (OSVČ)
- Small business accountants
- Freelancers with international income (App Store developers)

### 1.3 Current Status
- **Version**: 0.1.0 (Alpha)
- **Development Stage**: MVP with core features implemented
- **Deployment**: Configured for Railway deployment

---

## 2. Technology Stack

### 2.1 Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.109.0+ |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0.25+ |
| Database | SQLite (dev) / PostgreSQL (prod) | - |
| AI Engine | Anthropic Claude API | claude-sonnet-4-20250514 |
| Validation | Pydantic | 2.6.0+ |
| Auth (JWT) | PyJWT | 2.8.0+ |

### 2.2 Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 18.2.0 |
| Language | TypeScript | 5.2.2 |
| Build Tool | Vite | 5.0.8 |
| Routing | React Router | 6.21.0 |
| State | Zustand | 4.4.7 |
| Data Fetching | TanStack Query | 5.17.0 |
| Styling | Tailwind CSS | 3.4.0 |
| Charts | Recharts | 2.10.3 |

### 2.3 Infrastructure
| Component | Technology |
|-----------|------------|
| Containerization | Docker + Docker Compose |
| Web Server | Nginx (frontend), Uvicorn (backend) |
| CI/CD | Railway auto-deploy |

---

## 3. Core Features

### 3.1 Implemented Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Dashboard** | Financial overview with income/expense charts | Implemented |
| **Transactions** | CRUD for income/expenses with categorization | Implemented |
| **Invoices** | Issue and receive invoices with VAT tracking | Implemented |
| **Tax Optimizer** | Dividend vs. salary comparison calculator | Implemented |
| **Reports** | Financial reports and tax estimations | Implemented |
| **AI Tax Advisor** | Claude-powered tax consultation | Implemented |
| **Company Settings** | Company profile management | Implemented |
| **Multi-currency** | CZK conversion with CNB exchange rates | Implemented |
| **App Store Income** | Special handling for Apple developer income | Implemented |
| **Asset Management** | Fixed asset tracking with depreciation | Implemented |
| **OCR Processing** | Document scanning (endpoint only) | Partial |
| **Memory System** | Persistent AI context storage | Implemented |

### 3.2 Recently Implemented Features

| Feature | Priority | Status |
|---------|----------|--------|
| **User Authentication** | CRITICAL | IMPLEMENTED - JWT-based auth with bcrypt |
| **Multi-tenancy** | CRITICAL | IMPLEMENTED - User-Company relationship |
| **Password Management** | CRITICAL | IMPLEMENTED - bcrypt hashing |
| **Session Management** | HIGH | IMPLEMENTED - JWT tokens with refresh |
| **Role-Based Access** | HIGH | IMPLEMENTED - Admin/User/Viewer roles |
| **Knowledge Base Upload** | HIGH | IMPLEMENTED - Tax law document management |
| **AI Knowledge Integration** | HIGH | IMPLEMENTED - AI uses uploaded knowledge |
| **Email Verification** | MEDIUM | Endpoint ready (needs SMTP config) |
| **Password Reset** | MEDIUM | Endpoint ready (needs SMTP config) |

---

## 4. Identified Issues & Proposed Fixes

### 4.1 CRITICAL: No Authentication System

**Current State**:
- Anyone can access all data
- No user registration/login
- No data isolation between users
- Companies are not linked to user accounts

**Proposed Fix**:
```
1. Create User model with:
   - id, email, password_hash, created_at
   - is_active, is_verified, role

2. Create UserCompany relationship:
   - user_id, company_id, role (owner/admin/viewer)

3. Implement endpoints:
   - POST /auth/register
   - POST /auth/login
   - POST /auth/refresh
   - POST /auth/logout
   - POST /auth/forgot-password
   - POST /auth/reset-password

4. Add JWT middleware for protected routes

5. Frontend auth pages:
   - Login page
   - Registration page
   - Password reset flow
```

**Effort**: 2-3 days of development

---

### 4.2 HIGH: Database Scalability

**Current State**:
- SQLite used in development
- PostgreSQL configured for Railway
- No migrations system

**Proposed Fix**:
```
1. Add Alembic for migrations:
   pip install alembic
   alembic init migrations

2. Create initial migration from models

3. Set up migration scripts in CI/CD
```

**Effort**: 0.5 day

---

### 4.3 HIGH: API Security

**Current State**:
- No rate limiting
- No API key management
- CORS is permissive
- No request validation on some endpoints

**Proposed Fix**:
```
1. Add slowapi for rate limiting
2. Implement API key system for external access
3. Tighten CORS in production
4. Add request size limits
```

**Effort**: 1 day

---

### 4.4 MEDIUM: Error Handling

**Current State**:
- Basic error responses
- No structured error codes
- Limited logging

**Proposed Fix**:
```
1. Create standardized error response schema
2. Add error codes dictionary
3. Implement structured logging (structlog)
4. Add Sentry integration for error tracking
```

**Effort**: 1 day

---

### 4.5 MEDIUM: Test Coverage

**Current State**:
- Only tax_calculator tests exist
- No API endpoint tests
- No frontend tests

**Proposed Fix**:
```
1. Add pytest fixtures for database
2. Write API integration tests
3. Add Jest for frontend unit tests
4. Add Playwright for E2E tests
```

**Effort**: 3-5 days

---

### 4.6 LOW: Performance Optimization

**Current State**:
- No caching
- N+1 queries in some endpoints
- No pagination on list endpoints

**Proposed Fix**:
```
1. Add Redis for caching
2. Optimize SQLAlchemy queries with joinedload
3. Implement cursor-based pagination
```

**Effort**: 2 days

---

## 5. Deployment Options

### Option A: Railway (Recommended for MVP)

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│                    Railway                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Frontend   │  │   Backend   │  │PostgreSQL│ │
│  │   (Nginx)   │──│  (FastAPI)  │──│   DB    │ │
│  │   $5/mo     │  │   $5/mo     │  │  $5/mo  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
```

| Pros | Cons |
|------|------|
| Already configured | Limited free tier ($5 credit/month) |
| Auto-deploy from Git | Less control over infrastructure |
| Managed PostgreSQL | No custom domain on free tier |
| Easy scaling | EU region only (good for CZ) |
| SSL included | |

**Estimated Cost**: $5-20/month
- Frontend: ~$5/mo
- Backend: ~$5/mo
- PostgreSQL: ~$5/mo
- Custom domain: Free (if you have one)

**Setup Time**: 30 minutes

---

### Option B: DigitalOcean App Platform

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│              DigitalOcean App Platform          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Static    │  │   Service   │  │ Managed │ │
│  │    Site     │──│  (Backend)  │──│  Postgres│ │
│  │   $3/mo     │  │   $5/mo     │  │  $15/mo │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
```

| Pros | Cons |
|------|------|
| Reliable infrastructure | More expensive for DB |
| Good documentation | Manual config needed |
| Global CDN | No auto-deploy without setup |
| Managed DB backups | |

**Estimated Cost**: $23-40/month

**Setup Time**: 1-2 hours

---

### Option C: Vercel + Render

**Architecture**:
```
┌─────────────┐     ┌─────────────────────────────┐
│   Vercel    │     │          Render             │
│ ┌─────────┐ │     │ ┌─────────┐   ┌───────────┐│
│ │Frontend │ │────▶│ │ Backend │───│ PostgreSQL ││
│ │  Free   │ │     │ │  Free*  │   │   Free*   ││
│ └─────────┘ │     │ └─────────┘   └───────────┘│
└─────────────┘     └─────────────────────────────┘
                    *Sleeps after 15min inactivity
```

| Pros | Cons |
|------|------|
| Free tier available | Cold starts on Render free tier |
| Excellent frontend DX | DB sleeps on free tier |
| Automatic HTTPS | Split infrastructure |
| Edge functions | Complex CORS setup |

**Estimated Cost**: $0-14/month
- Free tier: $0 (with limitations)
- Paid: ~$7/mo (Render) + $0 (Vercel)

**Setup Time**: 1-2 hours

---

### Option D: VPS (Hetzner/Contabo)

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│              VPS (4GB RAM, 2 vCPU)              │
│  ┌──────────────────────────────────────────┐  │
│  │              Docker Compose               │  │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐  │  │
│  │  │ Nginx   │ │ FastAPI │ │ PostgreSQL│  │  │
│  │  │ +React  │─│ Backend │─│    DB     │  │  │
│  │  └─────────┘ └─────────┘ └───────────┘  │  │
│  └──────────────────────────────────────────┘  │
│                    Traefik                      │
│                 (SSL/Proxy)                     │
└─────────────────────────────────────────────────┘
```

| Pros | Cons |
|------|------|
| Cheapest long-term | Self-managed |
| Full control | Security responsibility |
| EU servers (GDPR) | Manual backups |
| No vendor lock-in | Requires DevOps knowledge |

**Estimated Cost**: €4-8/month
- Hetzner CX22: €4.51/mo (2 vCPU, 4GB RAM, 40GB SSD)
- Contabo VPS S: €5.99/mo (4 vCPU, 8GB RAM, 200GB SSD)

**Setup Time**: 4-8 hours (including SSL, backups)

---

### Option E: Fly.io

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│                    Fly.io                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Frontend   │  │   Backend   │  │ Postgres│ │
│  │  (static)   │──│  (machine)  │──│  (Fly)  │ │
│  │    Free     │  │   $5/mo     │  │  Free*  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
                    * 3GB storage free
```

| Pros | Cons |
|------|------|
| Free tier generous | Learning curve |
| Global edge network | CLI-based deployment |
| Auto-scaling | Pricing can be unpredictable |
| Great for APIs | |

**Estimated Cost**: $0-10/month

**Setup Time**: 2-3 hours

---

## 6. Recommended Solution

### For Your Requirements:
- Online access
- User registration (multiple accounts)
- Cost-effective

### Recommendation: **Railway (Option A)** + Authentication Implementation

**Why Railway?**
1. Already configured in the codebase
2. Quick deployment (30 min)
3. Managed PostgreSQL included
4. Auto-deploy on git push
5. SSL/HTTPS automatic
6. Reasonable cost (~$15/mo)
7. EU region available (GDPR compliance)

**Implementation Roadmap**:

```
Phase 1: Authentication (Priority)
├── Add User model
├── Implement auth endpoints
├── Add JWT middleware
├── Create login/register pages
└── Test multi-user isolation

Phase 2: Deploy to Railway
├── Set up PostgreSQL
├── Configure environment variables
├── Deploy backend + frontend
├── Set up custom domain
└── Enable auto-deploy

Phase 3: Polish
├── Add email verification
├── Implement password reset
├── Add rate limiting
├── Set up monitoring
└── Create user onboarding
```

---

## 7. Database Schema (Proposed with Auth)

```
┌─────────────────┐     ┌─────────────────┐
│      User       │     │   UserCompany   │
├─────────────────┤     ├─────────────────┤
│ id              │────▶│ user_id         │
│ email           │     │ company_id      │◀────┐
│ password_hash   │     │ role            │     │
│ is_active       │     │ created_at      │     │
│ is_verified     │     └─────────────────┘     │
│ created_at      │                              │
└─────────────────┘                              │
                                                 │
┌─────────────────┐                              │
│    Company      │──────────────────────────────┘
├─────────────────┤
│ id              │
│ name            │────▶ Transactions
│ ico             │────▶ Invoices
│ dic             │────▶ Assets
│ ...             │────▶ Documents
└─────────────────┘
```

---

## 8. API Endpoints (Current + Proposed)

### Current Endpoints
```
GET/POST   /api/v1/companies
GET/PUT/DEL /api/v1/companies/{id}
GET/POST   /api/v1/transactions
GET/POST   /api/v1/invoices
POST       /api/v1/tax/calculate
POST       /api/v1/ai/query
GET        /api/v1/reports/dashboard
GET        /api/v1/exchange/rates
GET        /api/v1/system/health
```

### Proposed Auth Endpoints
```
POST /api/v1/auth/register     - Create new account
POST /api/v1/auth/login        - Get access token
POST /api/v1/auth/refresh      - Refresh token
POST /api/v1/auth/logout       - Invalidate token
POST /api/v1/auth/forgot       - Request password reset
POST /api/v1/auth/reset        - Reset password
GET  /api/v1/auth/me           - Get current user
PUT  /api/v1/auth/me           - Update profile
```

---

## 9. Environment Variables

### Backend (.env)
```env
# Application
DEBUG=false
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# AI
ANTHROPIC_API_KEY=sk-ant-...

# CORS
CORS_ORIGINS=["https://your-domain.com"]

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=pass
```

### Frontend (.env)
```env
VITE_API_URL=https://api.your-domain.com
```

---

## 10. Security Considerations

### Must Have
- [ ] Password hashing (bcrypt/argon2)
- [ ] JWT with short expiration
- [ ] HTTPS enforced
- [ ] SQL injection prevention (SQLAlchemy handles this)
- [ ] XSS prevention (React handles this)
- [ ] CSRF tokens for forms
- [ ] Rate limiting on auth endpoints
- [ ] Input validation (Pydantic handles this)

### Should Have
- [ ] Two-factor authentication
- [ ] Audit logging
- [ ] IP-based rate limiting
- [ ] Security headers (already in nginx.conf)
- [ ] Regular dependency updates

### GDPR Compliance (Czech/EU)
- [ ] Cookie consent banner
- [ ] Privacy policy page
- [ ] Data export feature
- [ ] Account deletion feature
- [ ] Data processing agreement

---

## 11. Cost Summary

| Platform | Monthly Cost | Setup Time | Maintenance |
|----------|-------------|------------|-------------|
| Railway | $15-20 | 30 min | Low |
| DigitalOcean | $23-40 | 1-2 hours | Low |
| Vercel+Render | $0-14 | 1-2 hours | Medium |
| VPS (Hetzner) | €4-8 | 4-8 hours | High |
| Fly.io | $0-10 | 2-3 hours | Medium |

---

## 12. Next Steps

1. **Immediate**: Implement authentication system
2. **Short-term**: Deploy to Railway with PostgreSQL
3. **Medium-term**: Add monitoring, backups, email
4. **Long-term**: Scale based on user growth

---

## Appendix A: File Structure

```
danovy-poradce-pro/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── agents/           # AI agents
│   │   └── memory/           # AI memory system
│   ├── knowledge_base/       # Tax rules & laws
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/            # React pages
│   │   ├── components/       # UI components
│   │   ├── stores/           # Zustand stores
│   │   └── services/         # API calls
│   └── nginx.conf
├── docker-compose.yml
└── Makefile
```

---

## Appendix B: Knowledge Base Structure

```
knowledge_base/
├── laws/2025/
│   ├── income_tax.json       # DPPO/DPFO rates
│   ├── vat.json              # DPH rules
│   ├── social_insurance.json # Social contributions
│   └── health_insurance.json # Health contributions
└── rules/
    ├── dividends.json        # Dividend taxation
    ├── depreciation.json     # Asset depreciation
    └── appstore_income.json  # App Store specifics
```

---

*Document generated: 2026-01-21*
*Version: 1.0*
