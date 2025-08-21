# NULL Field Analysis Report

## Summary
Many fields in the database are 100% NULL because the API doesn't provide these fields, and the ETL pipeline is trying to map fields that don't exist.

## Announcements Table Analysis

### Fields with 100% NULL (21,774 records):
| Field | Expected API Field | Actual API Field | Status |
|-------|-------------------|------------------|--------|
| `nuts_code` | `codigoNuts` | **NOT PROVIDED** | ❌ API doesn't send |
| `procedure_type` | `tipoProcedimento` | `modeloAnuncio` | ⚠️ Wrong mapping |
| `submission_deadline` | `dataFimProposta` | **NOT PROVIDED** | ❌ API doesn't send |
| `opening_date` | `dataAberturaPropostas` | **NOT PROVIDED** | ❌ API doesn't send |
| `duration_months` | `prazoExecucao` | `PrazoPropostas` (in days) | ⚠️ Different field |
| `reference` | `referencia` | **NOT PROVIDED** | ❌ API doesn't send |
| `location` | `localExecucao` | **NOT PROVIDED** | ❌ API doesn't send |

### Available API Fields NOT Being Used:
- `IdIncm` - Internal API ID
- `numDR` - Diário da República number
- `serie` - DR series
- `tipoActo` - Type of act
- `modeloAnuncio` - Procedure model (should map to procedure_type)
- `CriterAmbient` - Environmental criteria
- `PrazoPropostas` - Proposal deadline in days
- `PecasProcedimento` - Procedure documents URL

## Contracts Table Analysis

### Fields with 100% NULL (137,784 records):
| Field | Expected API Field | Actual API Field | Status |
|-------|-------------------|------------------|--------|
| `observations` | `observacoes` | `Observacoes` (always empty) | ⚠️ Case mismatch |
| `url` | `url` | **NOT PROVIDED** | ❌ API doesn't send |
| `reference` | `referencia` | **NOT PROVIDED** | ❌ API doesn't send |
| `nuts_code` | `codigoNuts` | **NOT PROVIDED** | ❌ API doesn't send |
| `procedure_type` | `tipoProcedimento` | `tipoprocedimento` | ⚠️ Case mismatch |
| `start_date` | `dataInicioExecucao` | **NOT PROVIDED** | ❌ API doesn't send |
| `end_date` | `dataFimExecucao` | `dataFechoContrato` (empty) | ⚠️ Different field |

### Fields with 91% NULL:
| Field | Issue |
|-------|-------|
| `announcement_id` | Most contracts don't link back to announcements |

### Available Contract API Fields NOT Being Used:
- `idprocedimento` - Procedure ID
- `fundamentacao` - Legal foundation
- `ProcedimentoCentralizado` - Is centralized
- `regime` - Legal regime
- `CritMateriais` - Material criteria
- `concorrentes` - Competitors (usually null)
- `linkPecasProc` - Procedure documents link
- `ContratEcologico` - Ecological contract

## Root Causes

1. **API Field Names Changed**: The API evolved but mappings weren't updated
2. **Case Sensitivity**: API uses mixed case (`Observacoes` vs `observacoes`)
3. **Missing Fields**: Some fields simply aren't provided by the API
4. **Wrong Assumptions**: ETL expects fields that don't exist

## Recommendations

### Option 1: Fix Mappings (Quick Win)
Update the field mappings to match actual API responses:
- Map `modeloAnuncio` → `procedure_type`
- Map `PrazoPropostas` → calculate deadline from days
- Map `tipoprocedimento` → `procedure_type` (lowercase)
- Handle case variations

### Option 2: Schema Adjustment (Clean Solution)
Remove or make nullable the fields that API never provides:
- Remove `nuts_code` (never provided)
- Remove `reference` (never provided)
- Make `location` nullable (rarely provided)
- Add new fields for data that IS provided

### Option 3: Enhanced ETL (Best Solution)
1. Fix field mappings
2. Add derived fields (calculate submission_deadline from days)
3. Add new columns for useful API fields
4. Keep schema but document which fields are always NULL

## Immediate Actions Needed

1. **Fix case sensitivity in mappings**
2. **Map procedure_type correctly**
3. **Calculate submission_deadline from PrazoPropostas**
4. **Document which fields are expected to be NULL**
