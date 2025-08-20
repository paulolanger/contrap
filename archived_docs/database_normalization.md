# Database Normalization Summary

## Overview
Based on your excellent insights, we've identified several normalization opportunities that will create a much more robust and queryable database schema.

## Normalized Schema: 10 Tables Total

### Core Tables (3)
1. **`entities`** - Government entities + competitors (reused table)
2. **`announcements`** - Procurement opportunities 
3. **`contracts`** - Awarded contracts

### Lookup Tables (2)
4. **`contract_types`** - Standardized contract categories
5. **`cpv_codes`** - EU Common Procurement Vocabulary codes

### Association Tables (5) 
6. **`announcement_contract_types`** - Announcements ↔ Contract Types
7. **`announcement_cpv_codes`** - Announcements ↔ CPV Codes
8. **`contract_contract_types`** - Contracts ↔ Contract Types  
9. **`contract_cpv_codes`** - Contracts ↔ CPV Codes
10. **`contract_competitors`** - Contracts ↔ Competing Entities

## Key Insights from Data Analysis

### 1. Contract Types Normalization
**Current**: JSON arrays like `["Aquisição de serviços", "Aquisição de bens móveis"]`  
**Normalized**: Lookup table with categories
- **Services**: "Aquisição de serviços"
- **Goods**: "Aquisição de bens móveis"  
- **Works**: "Empreitadas de obras públicas"
- **Rental**: "Locação de bens móveis"

### 2. CPV Codes Normalization  
**Current**: JSON arrays like `["63510000-7 - Serviços de agências de viagens"]`  
**Normalized**: Structured CPV table with EU standard hierarchy
- **Code**: "63510000-7"
- **Description**: "Serviços de agências de viagens e serviços similares"
- **Level 1 Category**: "63000000" (Transport services)

### 3. Competitors as Entities
**Key Discovery**: **19,914 unique competitor entities** found!
```
Pattern: "500035121-Caetano Formula, S.A."
├── NIF: 500035121  
└── Name: Caetano Formula, S.A.
```

**Challenges Identified**:
- **Data Quality Issues**: Some invalid NIFs ("000000000", "ESA28125078", "0.760.604.615")
- **International Entities**: Non-Portuguese entities (ESA*, FI*)
- **Duplicates**: "_duplicado" suffix indicates duplicates

## ETL Processing Strategy

### Phase 1: Lookup Tables
```sql
-- Extract unique contract types
INSERT INTO contract_types (type_name, category)
SELECT DISTINCT unnest(tiposContrato), 
       CASE 
         WHEN 'serviços' THEN 'services'
         WHEN 'bens móveis' THEN 'goods'
         WHEN 'obras' THEN 'works'
       END
FROM announcements_raw;
```

### Phase 2: Entity Enrichment
```bash
# Extract all unique NIFs
1. From announcements: nifEntidade  
2. From competitors: split concorrentes by '-', take [0]
3. Clean invalid NIFs (length, format validation)
4. Call API for each valid NIF
5. Store in entities table
```

### Phase 3: Data Loading with Referential Integrity
```sql
-- Load core tables first
entities → announcements → contracts

-- Then load associations
announcement_contract_types
announcement_cpv_codes  
contract_contract_types
contract_cpv_codes
contract_competitors
```

## Query Examples with Normalized Schema

### Business Intelligence Queries

**1. Most Active Contractors**
```sql
SELECT e.desigEntidade, COUNT(*) as total_bids,
       SUM(CASE WHEN cc.won_contract THEN 1 ELSE 0 END) as wins,
       ROUND(SUM(CASE WHEN cc.won_contract THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate
FROM contract_competitors cc
JOIN entities e ON cc.competitor_nif = e.nifEntidade  
GROUP BY e.nifEntidade
ORDER BY total_bids DESC;
```

**2. Procurement by Category**
```sql
SELECT cpv.category_name_1, COUNT(*) as contracts, SUM(c.precoContratual) as total_value
FROM contracts c
JOIN contract_cpv_codes ccc ON c.idcontrato = ccc.contract_id
JOIN cpv_codes cpv ON ccc.cpv_code = cpv.code
GROUP BY cpv.category_level_1, cpv.category_name_1
ORDER BY total_value DESC;
```

**3. Entity Procurement Analysis**
```sql
SELECT e.desigEntidade,
       COUNT(a.nAnuncio) as announcements_issued,
       COUNT(c.idcontrato) as contracts_awarded,
       SUM(c.precoContratual) as total_spending
FROM entities e
LEFT JOIN announcements a ON e.nifEntidade = a.nifEntidade
LEFT JOIN contracts c ON a.nAnuncio = c.nAnuncio
GROUP BY e.nifEntidade
ORDER BY total_spending DESC;
```

## Data Quality Improvements

### 1. NIF Validation
```regex
Portuguese NIF Pattern: ^[0-9]{9}$
Valid: 500035121, 512021155
Invalid: 000000000, ESA28125078, 0.760.604.615
```

### 2. Competitor Data Cleaning
- **Remove duplicates**: "_duplicado" entries
- **Validate format**: Must contain "-" separator
- **International entities**: Special handling for non-PT entities
- **Missing data**: Handle empty or null competitor arrays

### 3. CPV Code Enrichment
- **EU CPV Database**: Validate against official EU CPV codes
- **Hierarchy**: Build proper category hierarchy (Level 1, 2, 3)
- **Inactive codes**: Mark deprecated CPV codes

## Benefits of Normalized Schema

### 1. Query Performance
- **Indexed lookups**: Fast searches by category, entity, CPV
- **Efficient joins**: Proper foreign key relationships
- **Aggregation**: Easy GROUP BY operations

### 2. Data Integrity
- **No duplicates**: Centralized lookup tables
- **Referential integrity**: All foreign keys validated
- **Consistent naming**: Standardized categories and descriptions

### 3. Analytics Capabilities
- **Market analysis**: Who competes in which sectors
- **Success rates**: Win/loss analysis by entity
- **Spending patterns**: Government spending by category/time
- **Competition analysis**: Market concentration metrics

## Implementation Priorities

### Phase 1 (Week 1)
- [ ] Create PostgreSQL schema for all 10 tables
- [ ] Build NIF extraction and validation logic
- [ ] Implement contract type normalization

### Phase 2 (Week 2)  
- [ ] CPV code extraction and enrichment
- [ ] Entity API integration with rate limiting
- [ ] Data quality validation rules

### Phase 3 (Week 3)
- [ ] Full ETL pipeline with proper ordering
- [ ] Association table population
- [ ] Performance optimization and indexing

This normalized approach transforms your raw JSON data into a professional, queryable database that enables sophisticated business intelligence and market analysis.
