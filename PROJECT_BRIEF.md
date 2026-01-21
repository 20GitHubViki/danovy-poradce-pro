# Daňový Poradce Pro - Project Brief

## Executive Summary

**Daňový Poradce Pro** is an AI-powered tax optimization and accounting platform designed for:
1. **Czech s.r.o. (limited liability companies)** - corporate tax optimization
2. **OSVČ (self-employed individuals)** - personal income tax for freelancers with App Store income

The platform provides intelligent tax advisory, financial management, and compliance tools powered by Claude AI.

---

## 1. Project Overview

### 1.1 Purpose
A comprehensive financial management solution that helps Czech entrepreneurs:
- **For s.r.o.**: Optimize tax strategies (dividend vs. salary decisions)
- **For OSVČ**: Track App Store income and compute tax obligations
- Track income, expenses, and cash flow
- Manage invoices and assets
- Get AI-powered tax advice based on Czech tax law
- Handle multi-currency transactions (with App Store income support)
- Generate tax filing documents (DPFO, VZP, ČSSZ)

### 1.2 Target Users
| User Type | Description |
|-----------|-------------|
| s.r.o. owners | Limited liability company owners |
| OSVČ vedlejší | Self-employed with secondary activity (employed + freelance) |
| OSVČ hlavní | Self-employed as primary activity |
| App Store developers | iOS/macOS developers receiving Apple payouts |
| Freelancers | Independent contractors with international income |

### 1.3 Current Status
- **Version**: 0.2.0 (Beta)
- **Development Stage**: Core features + OSVČ support implemented
- **Deployment**: Railway (recommended)

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
| Auth | JWT + bcrypt | PyJWT 2.8.0+ |
| Password | passlib[bcrypt] | 1.7.4+ |

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
| Deployment | Railway (recommended) |
| Database | PostgreSQL on Railway |

---

## 3. Core Features

### 3.1 Implemented Features (s.r.o.)

| Feature | Description | Status |
|---------|-------------|--------|
| Dashboard | Financial overview with income/expense charts | Implemented |
| Transactions | CRUD for income/expenses with categorization | Implemented |
| Invoices | Issue and receive invoices with VAT tracking | Implemented |
| Tax Optimizer | Dividend vs. salary comparison calculator | Implemented |
| Reports | Financial reports and tax estimations | Implemented |
| AI Tax Advisor | Claude-powered tax consultation | Implemented |
| Company Settings | Company profile management | Implemented |
| Multi-currency | CZK conversion with CNB exchange rates | Implemented |
| App Store Income | Special handling for Apple developer income | Implemented |
| Asset Management | Fixed asset tracking with depreciation | Implemented |
| Memory System | Persistent AI context storage | Implemented |

### 3.2 Implemented Features (Authentication & Knowledge)

| Feature | Status |
|---------|--------|
| User Authentication | Implemented - JWT-based auth with bcrypt |
| Multi-tenancy | Implemented - User-Company relationship |
| Role-Based Access | Implemented - Admin/User/Viewer roles |
| Knowledge Base Upload | Implemented - Tax law document management |
| AI Knowledge Integration | Implemented - AI uses uploaded knowledge |

### 3.3 OSVČ Features (NEW)

| Feature | Description | Status |
|---------|-------------|--------|
| Tax Year Setup | Year-specific settings wizard | Implemented |
| Income Entry | Track App Store & other income | Implemented |
| CSV Import | Import App Store payout reports | Implemented |
| Paušální výdaje | 60% flat-rate expenses calculation | Implemented |
| DPFO Calculator | Income tax calculation | Implemented |
| VZP Calculator | Health insurance calculation | Implemented |
| ČSSZ Calculator | Social security calculation | Implemented |
| Tax Ruleset | Year-specific tax parameters | Implemented |
| Export Packs | PDF + CSV exports for filings | Implemented |
| Due Date Checklist | Filing deadline reminders | Implemented |

---

## 4. OSVČ Tax System (Czech Republic)

### 4.1 Supported Modes
- **OSVČ vedlejší** - Secondary self-employment (user is also employed)
- **OSVČ hlavní** - Primary self-employment

### 4.2 Expense Modes
| Mode | Rate | Max Cap (2025) | Description |
|------|------|----------------|-------------|
| Paušál 60% | 60% | 2,000,000 CZK | For sales of goods, App Store |
| Paušál 40% | 40% | 800,000 CZK | For services, consulting |
| Paušál 30% | 30% | 600,000 CZK | For rentals |
| Paušál 80% | 80% | 1,600,000 CZK | For agricultural |
| Skutečné výdaje | - | - | Actual documented expenses |

### 4.3 Tax Calculations

#### Income Tax (DPFO)
```
Příjmy (P) = Total income in CZK
Výdaje (E) = P × expense_rate (or actual)
Základ daně (Z) = P - E
Daň = Z × 0.15 (or 0.23 for income above threshold)
```

#### Health Insurance (VZP)
```
Vyměřovací základ = Z × 0.50
Pojistné = Vyměřovací základ × 0.135
```

#### Social Security (ČSSZ)
```
For OSVČ vedlejší:
- If Z > rozhodná částka (threshold): pay social insurance
- Vyměřovací základ = Z × 0.55
- Pojistné = Vyměřovací základ × 0.292
```

### 4.4 2025 Tax Parameters (Ruleset)
| Parameter | Value |
|-----------|-------|
| expense_rate_60 | 0.60 |
| expense_cap_60 | 2,000,000 CZK |
| health_base_rate | 0.50 |
| health_contrib_rate | 0.135 |
| social_base_rate | 0.55 |
| social_contrib_rate | 0.292 |
| social_secondary_threshold | 105,520 CZK (2025) |
| income_tax_rate | 0.15 |
| income_tax_rate_high | 0.23 |
| income_tax_threshold | 1,582,812 CZK |

---

## 5. Data Model

### 5.1 Core Models

```
User
├── id, email, password_hash
├── full_name, role (admin/user/viewer)
├── is_active, is_verified
└── companies[] (via UserCompany)

Company (for s.r.o.)
├── id, name, ico, dic
├── address, bank_account
├── is_vat_payer, accounting_type
└── transactions[], invoices[], assets[]

TaxYear (for OSVČ)
├── id, user_id, year
├── is_employed, is_osvc_secondary
├── start_month, expenses_mode
├── income_entries[], computation_results[]
└── ruleset_id

IncomeEntry
├── id, tax_year_id
├── source (appstore_paid, appstore_sub, affiliate, other)
├── payout_date, period_start, period_end
├── currency, amount_gross, amount_net
├── platform_fees, fx_rate, amount_czk
├── notes, attachments[]
└── created_at, updated_at

TaxRuleset
├── id, year, version
├── expense_rate, expense_cap
├── health_base_rate, health_contrib_rate
├── social_base_rate, social_contrib_rate
├── social_secondary_threshold
├── income_tax_rate, income_tax_threshold
└── effective_from

ComputationResult
├── id, tax_year_id, ruleset_id
├── total_income, total_expenses, profit
├── health_base, health_due
├── social_threshold_hit, social_base, social_due
├── income_tax_base, income_tax_due
└── generated_at

KnowledgeDocument
├── id, title, category, content
├── source, year, keywords
├── is_active, is_verified
└── uploaded_by_id
```

---

## 6. API Endpoints

### 6.1 Authentication
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

### 6.2 Companies (s.r.o.)
```
GET/POST   /api/v1/companies
GET/PUT/DEL /api/v1/companies/{id}
```

### 6.3 Tax Years (OSVČ)
```
GET/POST   /api/v1/tax-years
GET/PUT/DEL /api/v1/tax-years/{id}
POST       /api/v1/tax-years/{id}/compute
GET        /api/v1/tax-years/{id}/summary
```

### 6.4 Income Entries
```
GET/POST   /api/v1/tax-years/{id}/income
GET/PUT/DEL /api/v1/income/{id}
POST       /api/v1/tax-years/{id}/income/import-csv
```

### 6.5 Tax Calculations
```
GET  /api/v1/tax/rulesets
GET  /api/v1/tax/rulesets/{year}
POST /api/v1/tax/calculate-dpfo
POST /api/v1/tax/calculate-vzp
POST /api/v1/tax/calculate-cssz
```

### 6.6 Exports
```
GET /api/v1/tax-years/{id}/export/dpfo
GET /api/v1/tax-years/{id}/export/vzp
GET /api/v1/tax-years/{id}/export/cssz
GET /api/v1/tax-years/{id}/export/all
```

### 6.7 Knowledge Base
```
GET/POST   /api/v1/knowledge
GET        /api/v1/knowledge/search
GET/PUT/DEL /api/v1/knowledge/{id}
```

### 6.8 AI Advisor
```
POST /api/v1/ai/analyze
POST /api/v1/ai/recommend
```

---

## 7. Frontend Pages

### 7.1 Public Pages
- `/login` - User login
- `/register` - User registration

### 7.2 Protected Pages (Common)
- `/dashboard` - Main overview
- `/settings` - User and company settings

### 7.3 s.r.o. Pages
- `/transactions` - Transaction management
- `/invoices` - Invoice management
- `/tax-optimizer` - Dividend vs salary optimizer
- `/reports` - Financial reports

### 7.4 OSVČ Pages
- `/tax-years` - Tax year list and setup
- `/tax-years/{id}` - Year dashboard
- `/tax-years/{id}/income` - Income entries
- `/tax-years/{id}/import` - CSV import wizard
- `/tax-years/{id}/calculations` - Tax calculations
- `/tax-years/{id}/export` - Export packs

---

## 8. Deployment (Railway)

### 8.1 Services
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

### 8.2 Environment Variables
```env
# Backend
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=your-secure-secret
CORS_ORIGINS=["https://your-app.up.railway.app"]

# Frontend
VITE_API_URL=https://your-api.up.railway.app
```

### 8.3 Estimated Cost: ~$15-20/month

---

## 9. Filing Checklist (Czech Republic)

### 9.1 Annual Deadlines
| Filing | Deadline | Form |
|--------|----------|------|
| DPFO (online) | April 2 | DAP DPFO |
| DPFO (paper) | March 31 | DAP DPFO |
| Přehled VZP | May 2 | Přehled OSVČ |
| Přehled ČSSZ | May 2 | Přehled OSVČ |

---

## 10. Knowledge Base Categories

| Category | Czech Name | Description |
|----------|------------|-------------|
| income_tax | Daň z příjmu | DPFO rules |
| vat | DPH | VAT regulations |
| social_insurance | Sociální pojištění | ČSSZ rules |
| health_insurance | Zdravotní pojištění | VZP rules |
| accounting | Účetnictví | Accounting standards |
| dividends | Dividendy | Dividend taxation |
| depreciation | Odpisy | Asset depreciation |
| appstore | App Store | Apple income specifics |
| osvc | OSVČ | Self-employment rules |

---

*Document Version: 2.0*
*Last Updated: 2026-01-21*
