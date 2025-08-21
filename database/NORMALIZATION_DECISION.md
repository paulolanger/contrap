# Contract Categories: Normalization Decision Guide

## Current State
- Categories are stored as a simple VARCHAR field in `contract_types` table
- Only 4 categories exist: `goods`, `services`, `works`, `mixed`
- No additional attributes needed currently

## Option 1: Keep As-Is (Simple VARCHAR)
✅ **RECOMMENDED for now**

### Pros:
- ✅ Simple and sufficient for current needs
- ✅ No additional JOINs required
- ✅ Easy to understand and maintain
- ✅ Can use CHECK constraint for validation

### Cons:
- ❌ No place for category-specific attributes
- ❌ Harder to add multilingual support for categories
- ❌ No hierarchical categories possible

### Implementation:
```sql
-- Add a CHECK constraint to ensure valid categories
ALTER TABLE contract_types 
ADD CONSTRAINT check_valid_category 
CHECK (category IN ('goods', 'services', 'works', 'mixed'));
```

## Option 2: Normalize to `contract_categories` Table

### Pros:
- ✅ Can add category-specific business rules
- ✅ Support for hierarchical categories (main → sub)
- ✅ UI attributes (colors, icons) in one place
- ✅ Multilingual category names
- ✅ Category-level statistics and reporting

### Cons:
- ❌ Additional complexity for only 4 values
- ❌ Extra JOIN in most queries
- ❌ Over-engineering for current requirements

### When to Choose This:
- If you need procurement rules per category (min tender days, max direct award)
- If you want subcategories (IT Goods, Medical Supplies, etc.)
- If you need UI customization per category
- If categories will grow beyond basic classification

## Decision Framework

### Choose Option 1 (Keep VARCHAR) if:
- [x] Categories are just simple classifiers
- [x] Only 4-5 stable categories expected
- [x] No complex business rules per category
- [x] Performance is critical

### Choose Option 2 (Normalize) if:
- [ ] Need business rules per category
- [ ] Want hierarchical categorization
- [ ] Need UI customization (colors, icons)
- [ ] Planning category-based workflows
- [ ] Categories will expand significantly

## Recommendation

**Keep the current VARCHAR approach** for now because:

1. **YAGNI Principle**: You Aren't Gonna Need It (yet)
2. **Simplicity**: 4 static categories don't justify a table
3. **Performance**: Avoids unnecessary JOINs
4. **Future-Proof**: Can always normalize later if needed

### Compromise Solution:
```sql
-- Create an ENUM type for better validation (PostgreSQL specific)
CREATE TYPE contract_category AS ENUM ('goods', 'services', 'works', 'mixed');

-- Then use it in the table
ALTER TABLE contract_types 
ALTER COLUMN category TYPE contract_category 
USING category::contract_category;
```

## Migration Path

If you decide to normalize later:
1. The migration script is ready: `002_add_contract_categories_table_OPTIONAL.sql`
2. All relationships are preserved
3. Can be done with zero downtime
4. Rollback instructions included

## Current Statistics

| Category | Contract Types | Contracts | Total Value |
|----------|---------------|-----------|-------------|
| goods | 3 types | 72,081 | €4.9B |
| services | 3 types | 56,636 | €4.1B |
| works | 3 types | 9,003 | €3.6B |
| mixed | 4 types | 94 | €35.5M |

With only 4 categories handling €12.6B in contracts, the current structure is sufficient.
