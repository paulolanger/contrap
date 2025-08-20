# Contrap - Portuguese Government Contract Bidding Data Platform
## Comprehensive Requirements Document

---

## 1. Executive Summary

**Contrap** is a data intelligence platform that aggregates, processes, and delivers valuable insights from Portuguese government bidding announcements and contracts. The platform transforms raw government procurement data into actionable business intelligence for companies seeking government contracts.

### 1.1 Business Model
- **Phase 1**: Newsletter subscription service with freemium model
- **Phase 2**: Full-featured SaaS web application with advanced analytics
- **Target Market**: Portuguese businesses, consultants, and contractors interested in government procurement opportunities
- **Revenue Model**: Subscription-based with trial period and tiered pricing

### 1.2 Key Value Propositions
1. **Real-time Notifications**: Daily updates on new bidding opportunities
2. **Regional Filtering**: Focus on specific regions of Portugal
3. **Category Specialization**: Track specific procurement categories (CPV codes)
4. **Competitive Intelligence**: Analyze competitor bid history and success rates
5. **Market Analytics**: Understand spending patterns and trends

---

## 2. System Architecture Overview

```mermaid
graph TB
    subgraph "Data Sources"
        API[Portuguese Gov API<br/>base.gov.pt]
    end
    
    subgraph "ETL Pipeline"
        Fetcher[API Fetcher<br/>Python]
        Processor[Data Processor<br/>Python]
        Loader[Data Loader<br/>Python]
    end
    
    subgraph "Data Storage"
        Raw[Raw JSON Files]
        Processed[Processed Chunks]
        DB[(PostgreSQL<br/>Database)]
    end
    
    subgraph "Backend Services"
        GraphQL[GraphQL API<br/>Node.js/Prisma]
        Newsletter[Newsletter Service<br/>Python/Node.js]
        Auth[Authentication<br/>Service]
    end
    
    subgraph "Frontend Applications"
        Web[Next.js Web App<br/>React + shadcn/ui]
        Admin[Admin Dashboard]
    end
    
    subgraph "Infrastructure"
        Docker[Docker Compose]
        Cron[Cron Scheduler]
    end
    
    API --> Fetcher
    Fetcher --> Raw
    Raw --> Processor
    Processor --> Processed
    Processed --> Loader
    Loader --> DB
    
    DB --> GraphQL
    DB --> Newsletter
    
    GraphQL --> Web
    GraphQL --> Admin
    
    Newsletter --> Email[Email Subscribers]
    
    Cron --> Fetcher
    Docker --> ETL Pipeline
    Docker --> Backend Services
    Docker --> Frontend Applications
```

---

## 3. Technical Requirements

### 3.1 ETL Pipeline (Python)

#### 3.1.1 API Fetcher Module
**Purpose**: Retrieve data from Portuguese Government Procurement API

**Requirements**:
- Implement async requests with retry logic (already documented in `async_api_implementation.md`)
- Handle API rate limiting (5 requests/second)
- Support for multiple endpoints:
  - `/GetInfoContrato` - Contract information
  - `/GetInfoAnuncio` - Announcement information
  - `/GetInfoEntidades` - Entity information
  - `/GetInfoModContrat` - Contract modifications
- Store raw JSON responses with timestamps
- Implement incremental fetching (only new/updated records)
- Error handling and logging
- Support for historical data backfilling

**Configuration**:
```python
API_CONFIG = {
    "base_url": "https://www.base.gov.pt/APIBase2",
    "access_token": "Nmq28lKgTbr05RaFOJNf",
    "rate_limit": 5,  # requests per second
    "timeout": 300,    # seconds
    "max_retries": 3,
    "batch_size": 1000
}
```

#### 3.1.2 Data Processor Module
**Purpose**: Transform and normalize raw data

**Requirements**:
- Split large JSON files into smaller chunks (already in `data/processed/`)
- Data validation and cleaning:
  - Date format normalization (DD/MM/YYYY to ISO)
  - NIF validation (Portuguese tax ID format)
  - Remove duplicates
  - Handle null/"NULL" values consistently
- Extract and normalize:
  - Contract types from JSON arrays
  - CPV codes from strings
  - Competitor NIFs from concatenated strings
- Create relationships between entities
- Generate processing statistics and quality reports

#### 3.1.3 Data Loader Module
**Purpose**: Load processed data into PostgreSQL

**Requirements**:
- Bulk insert optimization
- Upsert logic for updates
- Transaction management
- Referential integrity validation
- Load order management (lookup tables first)
- Progress tracking and resumability
- Error recovery mechanisms

### 3.2 Database (PostgreSQL)

#### 3.2.1 Schema Requirements
Based on the normalized 10-table structure documented in `database_schema.md`:

**Core Tables**:
1. `entities` - Government entities and competitors
2. `announcements` - Procurement opportunities
3. `contracts` - Awarded contracts

**Lookup Tables**:
4. `contract_types` - Contract categories
5. `cpv_codes` - EU procurement vocabulary

**Association Tables**:
6. `announcement_contract_types`
7. `announcement_cpv_codes`
8. `contract_contract_types`
9. `contract_cpv_codes`
10. `contract_competitors`

**Additional Tables Needed**:
11. `users` - Subscriber information
12. `subscriptions` - Subscription plans and status
13. `notification_preferences` - User notification settings
14. `notification_log` - Sent notifications history
15. `etl_jobs` - ETL execution tracking
16. `api_logs` - API request/response logging

#### 3.2.2 Performance Requirements
- Indexing strategy for fast queries
- Partitioning for large tables (by year/month)
- JSONB columns for flexible metadata
- Full-text search capabilities
- Query performance < 100ms for common operations

### 3.3 Backend Services

#### 3.3.1 GraphQL API (Node.js + Prisma)
**Purpose**: Provide data access for web application

**Requirements**:
- Schema-first development with Prisma
- Authentication/Authorization with JWT
- Query optimization with DataLoader
- Subscription support for real-time updates
- Rate limiting per user/tier
- API documentation with GraphQL Playground

**Key Queries/Mutations**:
```graphql
type Query {
  # Announcements
  announcements(filter: AnnouncementFilter, pagination: Pagination): AnnouncementConnection
  announcement(id: ID!): Announcement
  
  # Contracts
  contracts(filter: ContractFilter, pagination: Pagination): ContractConnection
  contract(id: ID!): Contract
  
  # Analytics
  marketAnalytics(dateRange: DateRange, region: String): Analytics
  competitorAnalysis(nif: String!): CompetitorStats
  
  # User
  mySubscription: Subscription
  myNotifications: [Notification]
}

type Mutation {
  # User Management
  register(input: RegisterInput!): AuthPayload
  login(input: LoginInput!): AuthPayload
  updateProfile(input: ProfileInput!): User
  
  # Subscription
  subscribe(plan: SubscriptionPlan!): Subscription
  cancelSubscription: Subscription
  
  # Preferences
  updateNotificationPreferences(input: PreferencesInput!): Preferences
}

type Subscription {
  # Real-time updates
  newAnnouncements(filter: AnnouncementFilter): Announcement
  contractAwarded(announcementId: ID!): Contract
}
```

#### 3.3.2 Newsletter Service
**Purpose**: Send daily email notifications

**Requirements**:
- Email template engine (React Email or MJML)
- Queue system for email processing (Bull/Redis)
- Personalization based on user preferences:
  - Regions (Districts/Municipalities)
  - Categories (CPV codes)
  - Contract value ranges
  - Entity types
- Unsubscribe management
- Email analytics (open rates, clicks)
- Integration with email service (SendGrid/AWS SES)
- A/B testing capabilities

**Email Types**:
1. Welcome email (with trial information)
2. Daily digest (new opportunities)
3. Weekly summary
4. Trial expiration warning
5. Subscription confirmation
6. Payment reminders

### 3.4 Frontend Application (Next.js + React)

#### 3.4.1 Public Pages
- **Landing Page**: Value proposition, features, pricing
- **Registration/Login**: User authentication
- **Pricing**: Subscription tiers and features
- **Blog/Resources**: SEO content about government contracting

#### 3.4.2 Authenticated User Dashboard
- **Dashboard Home**: 
  - Personalized opportunity feed
  - Saved searches
  - Recent activity
  - Subscription status
  
- **Opportunities Explorer**:
  - Advanced search and filters
  - Saved search management
  - Export functionality (CSV/PDF)
  - Bookmark opportunities
  
- **Contract Browser**:
  - Historical contracts search
  - Competitor analysis
  - Success rate statistics
  
- **Analytics Dashboard**:
  - Market trends
  - Regional analysis
  - Category insights
  - Competitor tracking
  
- **Profile & Settings**:
  - Notification preferences
  - Subscription management
  - API access (for premium tiers)
  - Invoice history

#### 3.4.3 Admin Dashboard
- **ETL Monitoring**: Job status, logs, performance
- **User Management**: Subscribers, plans, usage
- **Content Management**: Email templates, announcements
- **Analytics**: Business metrics, revenue, churn
- **System Health**: API status, database metrics

### 3.5 Infrastructure Requirements

#### 3.5.1 Docker Configuration
```yaml
# docker-compose.yml structure
services:
  # Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: contrap
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  # Redis for queues
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  # ETL Pipeline
  etl:
    build: ./etl
    environment:
      DATABASE_URL: ${DATABASE_URL}
      API_TOKEN: ${API_TOKEN}
    depends_on:
      - postgres
      - redis
  
  # Backend API
  api:
    build: ./backend
    ports:
      - "4000:4000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      - postgres
      - redis
  
  # Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://api:4000
    depends_on:
      - api
  
  # Newsletter Worker
  newsletter:
    build: ./newsletter
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
    depends_on:
      - postgres
      - redis
```

#### 3.5.2 Cron Jobs
```bash
# Crontab configuration
# Fetch new announcements (every 6 hours)
0 */6 * * * docker-compose run etl python fetch_announcements.py

# Fetch new contracts (every 6 hours, offset by 3 hours)
0 3,9,15,21 * * * docker-compose run etl python fetch_contracts.py

# Process and load data (every hour)
0 * * * * docker-compose run etl python process_and_load.py

# Send daily newsletter (every day at 8 AM)
0 8 * * * docker-compose run newsletter python send_daily_digest.py

# Weekly summary (every Monday at 9 AM)
0 9 * * 1 docker-compose run newsletter python send_weekly_summary.py

# Database backup (daily at 2 AM)
0 2 * * * docker-compose exec postgres pg_dump -U $DB_USER contrap > backup_$(date +\%Y\%m\%d).sql
```

---

## 4. Business Requirements

### 4.1 Subscription Tiers

#### 4.1.1 Free Trial (14 days)
- Full access to all features
- Daily email notifications
- Up to 3 saved searches
- Export up to 10 records

#### 4.1.2 Basic Plan (€19/month)
- Daily email notifications
- 5 saved searches
- 1 region filter
- 3 category filters
- Export up to 100 records/month
- 30-day historical data

#### 4.1.3 Professional Plan (€49/month)
- All Basic features
- Unlimited saved searches
- All regions
- Unlimited categories
- Export up to 1000 records/month
- 1-year historical data
- Competitor analysis
- API access (1000 calls/month)

#### 4.1.4 Enterprise Plan (€199/month)
- All Professional features
- Unlimited exports
- Full historical data
- Advanced analytics
- Priority support
- API access (10000 calls/month)
- Custom integrations
- White-label options

### 4.2 User Journey

#### 4.2.1 Acquisition
1. User discovers platform via SEO/Marketing
2. Views landing page with value proposition
3. Signs up for free trial
4. Receives welcome email with onboarding

#### 4.2.2 Activation
1. Sets up notification preferences (regions/categories)
2. Receives first daily digest
3. Explores web dashboard
4. Saves first search
5. Views competitor analysis

#### 4.2.3 Retention
1. Daily valuable notifications
2. Successful bid using platform data
3. Upgrades to paid plan
4. Increases usage over time

#### 4.2.4 Referral
1. Shares success story
2. Refers colleagues
3. Provides testimonials

### 4.3 Key Performance Indicators (KPIs)

#### 4.3.1 Business Metrics
- Monthly Recurring Revenue (MRR)
- Customer Acquisition Cost (CAC)
- Customer Lifetime Value (CLV)
- Churn Rate
- Trial-to-Paid Conversion Rate

#### 4.3.2 Product Metrics
- Daily Active Users (DAU)
- Email Open Rate
- Click-through Rate
- Feature Adoption Rate
- API Usage

#### 4.3.3 Technical Metrics
- ETL Success Rate
- API Response Time
- Database Query Performance
- System Uptime
- Data Freshness

---

## 5. Data Processing Requirements

### 5.1 Data Quality Standards
- **Completeness**: > 95% of fields populated
- **Accuracy**: > 99% NIF validation success
- **Timeliness**: < 6 hours from publication to notification
- **Consistency**: Standardized formats across all data
- **Uniqueness**: No duplicate records

### 5.2 Data Enrichment
- **Entity Enrichment**: Fetch missing entity details via API
- **Geographic Coding**: Add GPS coordinates for locations
- **Category Mapping**: Map CPV codes to business categories
- **Trend Analysis**: Calculate moving averages and trends
- **Scoring**: Opportunity relevance scoring

### 5.3 Data Retention Policy
- **Raw Data**: 90 days
- **Processed Data**: 2 years
- **Aggregated Analytics**: Indefinite
- **User Data**: Per GDPR requirements
- **Backup**: 30-day rolling backups

---

## 6. Security & Compliance

### 6.1 Security Requirements
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: TLS for transport, AES for sensitive data at rest
- **API Security**: Rate limiting, API keys, CORS
- **Input Validation**: Sanitization of all user inputs
- **Audit Logging**: All data access and modifications

### 6.2 GDPR Compliance
- **Data Minimization**: Collect only necessary data
- **User Consent**: Explicit opt-in for communications
- **Right to Access**: User data export functionality
- **Right to Deletion**: Account deletion process
- **Data Portability**: Standard export formats
- **Privacy Policy**: Clear and accessible

### 6.3 Portuguese Legal Requirements
- **Faturação**: Integration with Portuguese invoicing requirements
- **NIF Validation**: Proper Portuguese tax ID handling
- **Data Residency**: Consider Portuguese/EU hosting
- **Terms of Service**: Portuguese language version

---

## 7. Implementation Roadmap

### Phase 0: Foundation (Weeks 1-2)
- [ ] Set up development environment
- [ ] Configure Docker and Docker Compose
- [ ] Initialize Git repository and CI/CD
- [ ] Set up PostgreSQL database
- [ ] Create project structure

### Phase 1: ETL Pipeline (Weeks 3-5)
- [ ] Implement API fetcher with async/retry logic
- [ ] Build data processor for normalization
- [ ] Create data loader with bulk operations
- [ ] Set up cron jobs for automation
- [ ] Implement monitoring and logging

### Phase 2: Database & Backend (Weeks 6-8)
- [ ] Create normalized database schema
- [ ] Set up Prisma ORM
- [ ] Build GraphQL API
- [ ] Implement authentication
- [ ] Create subscription management

### Phase 3: Newsletter System (Weeks 9-10)
- [ ] Design email templates
- [ ] Implement preference management
- [ ] Build email queue system
- [ ] Set up email service integration
- [ ] Create unsubscribe handling

### Phase 4: Web Application (Weeks 11-14)
- [ ] Set up Next.js project
- [ ] Implement authentication flow
- [ ] Build opportunity explorer
- [ ] Create analytics dashboards
- [ ] Develop user settings

### Phase 5: Testing & Launch (Weeks 15-16)
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Production deployment
- [ ] Beta user onboarding

### Phase 6: Growth & Optimization (Ongoing)
- [ ] Feature iterations based on feedback
- [ ] Marketing and SEO
- [ ] API development for integrations
- [ ] Mobile app consideration
- [ ] International expansion planning

---

## 8. Technical Specifications

### 8.1 Development Stack
```yaml
Backend:
  ETL: Python 3.11+
    - aiohttp (async HTTP)
    - pandas (data processing)
    - sqlalchemy (ORM)
    - asyncio (async operations)
    - schedule (cron jobs)
  
  API: Node.js 18+
    - Prisma (ORM)
    - Apollo Server (GraphQL)
    - Express (HTTP server)
    - jsonwebtoken (Auth)
    - bull (Job queues)
  
  Database:
    - PostgreSQL 15
    - Redis 7 (caching/queues)

Frontend:
  - Next.js 14+
  - React 18+
  - TypeScript
  - Tailwind CSS
  - shadcn/ui components
  - React Query
  - Recharts

Infrastructure:
  - Docker & Docker Compose
  - Nginx (reverse proxy)
  - GitHub Actions (CI/CD)
  - Monitoring (Prometheus/Grafana)
```

### 8.2 Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/contrap
REDIS_URL=redis://redis:6379

# API
API_BASE_URL=https://www.base.gov.pt/APIBase2
API_ACCESS_TOKEN=Nmq28lKgTbr05RaFOJNf

# Authentication
JWT_SECRET=your-secret-key
JWT_REFRESH_SECRET=your-refresh-secret

# Email
SENDGRID_API_KEY=your-sendgrid-key
EMAIL_FROM=noreply@contrap.pt

# Payment (Future)
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_WEBHOOK_SECRET=your-webhook-secret

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=info

# App
NEXT_PUBLIC_APP_URL=https://contrap.pt
NEXT_PUBLIC_API_URL=https://api.contrap.pt
```

### 8.3 API Rate Limits
```yaml
Anonymous:
  - 10 requests/minute
  
Free Trial:
  - 60 requests/minute
  - 1000 requests/day
  
Basic:
  - 120 requests/minute
  - 5000 requests/day
  
Professional:
  - 300 requests/minute
  - 30000 requests/day
  
Enterprise:
  - 600 requests/minute
  - Unlimited daily
```

---

## 9. Success Criteria

### 9.1 MVP Success Metrics
- [ ] ETL pipeline processing 100% of daily data
- [ ] Database with > 10,000 contracts and announcements
- [ ] Newsletter system sending to 100+ subscribers
- [ ] Web app with core features functional
- [ ] 50+ beta users signed up
- [ ] 10% trial-to-paid conversion

### 9.2 6-Month Goals
- [ ] 500+ active subscribers
- [ ] €5,000+ MRR
- [ ] < 5% monthly churn
- [ ] 99.9% uptime
- [ ] Mobile app released
- [ ] API partner integrations

### 9.3 1-Year Vision
- [ ] 2,000+ active subscribers
- [ ] €30,000+ MRR
- [ ] Expansion to Spanish market
- [ ] AI-powered bid recommendations
- [ ] Government entity accounts
- [ ] Market leader in Portugal

---

## 10. Risk Assessment & Mitigation

### 10.1 Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API changes/downtime | High | Medium | Robust error handling, monitoring, fallback data sources |
| Data quality issues | Medium | High | Validation rules, manual review process |
| Scaling challenges | Medium | Medium | Horizontal scaling, caching, CDN |
| Security breach | High | Low | Security audits, encryption, compliance |

### 10.2 Business Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low conversion rate | High | Medium | A/B testing, user feedback, iterate |
| Competition | Medium | Medium | Unique features, better UX, pricing |
| Regulatory changes | High | Low | Legal consultation, adaptable architecture |
| Market size | Medium | Low | Expand to other markets/countries |

### 10.3 Operational Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Key person dependency | High | Medium | Documentation, knowledge sharing |
| Infrastructure costs | Medium | Medium | Cost optimization, efficient architecture |
| Support burden | Medium | High | Self-service docs, automation |

---

## 11. Appendices

### Appendix A: Useful Resources
- [Portuguese Government Procurement API Documentation](https://www.base.gov.pt/APIBase2/api.wadl)
- [EU CPV Codes](https://simap.ted.europa.eu/cpv)
- [GDPR Compliance Checklist](https://gdpr.eu/checklist/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)

### Appendix B: Glossary
- **CPV**: Common Procurement Vocabulary (EU standard classification)
- **NIF**: Número de Identificação Fiscal (Portuguese Tax ID)
- **INCM**: Imprensa Nacional-Casa da Moeda (National Printing Office)
- **ETL**: Extract, Transform, Load
- **MRR**: Monthly Recurring Revenue
- **CAC**: Customer Acquisition Cost
- **CLV**: Customer Lifetime Value

### Appendix C: Contact Information
- **API Support**: base.gov.pt support team
- **Technical Lead**: [Your contact]
- **Business Owner**: [Your contact]

---

## Document Control

- **Version**: 1.0
- **Date**: January 2025
- **Author**: Contrap Development Team
- **Status**: Draft
- **Next Review**: February 2025

---

## Approval

This requirements document needs approval from:
- [ ] Technical Lead
- [ ] Product Owner
- [ ] Business Stakeholder
- [ ] Legal/Compliance (if applicable)

---

*This is a living document and will be updated as the project evolves and new requirements emerge.*
