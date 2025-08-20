# Database Schema Documentation

## Project: Portuguese Government Contracts ETL System (Contrap)

### Overview
This document defines the database schema for storing Portuguese government announcements (anúncios) and contracts (contratos) data from the public procurement system.

## Relationship Model
```
                                    Entity (1) ---------> (N) Announcement (1) -----> (N) Contract (N)
                                  nifEntidade                 nifEntidade (FK)           nAnuncio (FK)
                                      ↑                            ↓                          ↓
                                      │                     ContractType (N) <---> (N) Announcement
                                      │                                              ↓
CPV (N) <-----------> (N) Contract   │                                         Contract (N) <---> (N) ContractType
                       ↑              │                                              ↓
                       │              │                                         Contract (N) <---> (N) Competitor
                       │              │                                              ↑
                       │              └----- Competitor (Entity) (N) <--------------┘
                       │
                CPV (N) <---> (N) Announcement
```

**Key Insights**: 
- **Core Flow**: Entity → Announcement → Contract
- **Many-to-Many Relations**: 
  - Contracts ↔ CPV Codes (what is being procured)
  - Contracts ↔ Contract Types (services, goods, works)
  - Contracts ↔ Competitors (who bid)
  - Announcements ↔ CPV Codes 
  - Announcements ↔ Contract Types
- **Normalization**: Competitors are also Entities (reuse entity table)

---

## Core Tables

## 1. Entities Table (`entities`)

### Purpose
Stores information about Portuguese government entities that create procurement announcements.

### API Source
**Endpoint**: `https://www.base.gov.pt/APIBase2/GetInfoEntidades?nifEntidade={nif}`  
**Authentication**: Requires `_AcessToken` header

### Example Record
```json
{
  "nifEntidade": "512021155",
  "desigEntidade": "Instituto de Alimentação e Mercados Agrícolas, I. P. R. A.",
  "numContratos": 505,
  "totAdjudicatario": 2,
  "totValorContratIni": 900.0,
  "totAdjudicante": 503,
  "totAdjudicanteValorContratIni": 57735504.51,
  "descPais": "Portugal",
  "AliasPais": "PT"
}
```

### Field Analysis

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `nifEntidade` | STRING | **PRIMARY KEY** - Portuguese tax ID | "512021155" | Unique identifier |
| `desigEntidade` | STRING | Official entity name | "Instituto de Alimentação..." | Full legal name |
| `numContratos` | INTEGER | Total number of contracts | 505 | Historical count |
| `totAdjudicatario` | INTEGER | Total as contract winner | 2 | Times entity won contracts |
| `totValorContratIni` | DECIMAL | Total value as winner | 900.0 | Amount won as contractor |
| `totAdjudicante` | INTEGER | Total as contracting authority | 503 | Times entity issued contracts |
| `totAdjudicanteValorContratIni` | DECIMAL | Total value as contracting authority | 57735504.51 | Amount spent on contracts |
| `descPais` | STRING | Country description | "Portugal" | Always Portugal |
| `AliasPais` | STRING | Country code | "PT" | ISO country code |

---

## 2. Announcements Table (`announcements`)

### Purpose
Stores public procurement announcements from Portuguese government entities.

### Example Record
```json
{
  "nAnuncio": "JORAA-96/2025",
  "IdIncm": "-1",
  "dataPublicacao": "25/02/2025",
  "nifEntidade": "512021155",
  "designacaoEntidade": "Instituto de Alimentação e Mercados Agrícolas, I. P. R. A.",
  "descricaoAnuncio": "Concurso público para aquisição de serviços de viagens e alojamento para o IAMA, IPRA.",
  "url": "https://jo.azores.gov.pt/#/ato/90eadaf1-9449-4c7f-bbb8-ebcbc8ea7d45",
  "numDR": "39",
  "serie": "2",
  "tipoActo": "Anúncio de procedimento",
  "tiposContrato": ["Aquisição de serviços"],
  "PrecoBase": "85000.00",
  "CPVs": ["63510000-7 - Serviços de agências de viagens e serviços similares"],
  "modeloAnuncio": "Concurso público",
  "Ano": 2025,
  "CriterAmbient": "Não",
  "PrazoPropostas": 14,
  "PecasProcedimento": ""
}
```

### Field Analysis

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `nAnuncio` | STRING | **PRIMARY KEY** - Unique announcement identifier | "JORAA-96/2025" | Used to link with contracts |
| `IdIncm` | STRING | Internal system ID | "-1" | May be empty or negative |
| `dataPublicacao` | DATE | Publication date | "25/02/2025" | Format: DD/MM/YYYY |
| `nifEntidade` | STRING | **FOREIGN KEY** - Tax ID of contracting entity | "512021155" | References entities table |
| `designacaoEntidade` | STRING | Name of contracting entity | "Instituto de Alimentação..." | Full entity name |
| `descricaoAnuncio` | TEXT | Announcement description | "Concurso público para..." | Procurement description |
| `url` | STRING | Official document URL | "https://jo.azores.gov.pt/..." | External link |
| `numDR` | STRING | Official bulletin number | "39" | Diário da República number |
| `serie` | STRING | Bulletin series | "2" | Usually "2" |
| `tipoActo` | STRING | Type of legal act | "Anúncio de procedimento" | Standardized values |
| `tiposContrato` | JSON ARRAY | Contract types | ["Aquisição de serviços"] | Multiple values possible |
| `PrecoBase` | DECIMAL | Base price | "85000.00" | String format in source |
| `CPVs` | JSON ARRAY | Common Procurement Vocabulary codes | ["63510000-7 - Serviços..."] | EU standard codes |
| `modeloAnuncio` | STRING | Announcement model | "Concurso público" | Procurement type |
| `Ano` | INTEGER | Year | 2025 | Announcement year |
| `CriterAmbient` | STRING | Environmental criteria | "Não" | Yes/No value |
| `PrazoPropostas` | INTEGER | Proposal deadline (days) | 14 | Days to submit proposals |
| `PecasProcedimento` | STRING | Procedure documents link | "" | May be empty |

---

## 3. Contracts Table (`contracts`)

### Purpose
Stores awarded contracts resulting from announcements.

### Example Record
```json
{
  "idcontrato": "11623631",
  "nAnuncio": "10331/2025",
  "TipoAnuncio": "Anúncio de procedimento",
  "idINCM": "418953989",
  "tipoContrato": ["Aquisição de bens móveis"],
  "idprocedimento": "7569044",
  "tipoprocedimento": "Concurso público",
  "objectoContrato": "CPUB004DTEDGA2025 - Aquisição de Viaturas Ligeiras",
  "descContrato": "CPUB004DTEDGA2025 - Aquisição de Viaturas Ligeiras",
  "adjudicante": ["507396081 - EMAC - Empresa Municipal de Ambiente de Cascais, E. M., S. A."],
  "adjudicatarios": ["500970602 - Renault Portugal, S.A."],
  "dataPublicacao": "05/08/2025",
  "dataCelebracaoContrato": "30/07/2025",
  "precoContratual": 127206.60,
  "cpv": ["34144900-7 - Veículos eléctricos"],
  "prazoExecucao": 90,
  "localExecucao": ["Portugal, Lisboa, Cascais"],
  "fundamentacao": "Artigo 20.º, n.º 1, alínea a) do Código dos Contratos Públicos",
  "ProcedimentoCentralizado": "Não",
  "numAcordoQuadro": "NULL",
  "DescrAcordoQuadro": "NULL",
  "precoBaseProcedimento": 419000.0,
  "dataDecisaoAdjudicacao": "02/07/2025",
  "dataFechoContrato": "",
  "PrecoTotalEfetivo": 0.0,
  "regime": "Código dos Contratos Públicos (DL111-B/2017) e Lei n.º 30/2021, de 21.05",
  "justifNReducEscrContrato": null,
  "tipoFimContrato": "",
  "CritMateriais": "Não",
  "concorrentes": [
    "500035121-Caetano Formula, S.A.",
    "500970602-RENAULT PORTUGAL SA ",
    "500239037-Toyota Caetano Portugal, SA"
  ],
  "linkPecasProc": "https://www.acingov.pt/acingovprod/2/zonaPublica/zona_publica_c/donwloadProcedurePiece/ODg3MTc1",
  "Observacoes": "O pagamento dos bens será efetuado por Entidade Locadora...",
  "ContratEcologico": "Não",
  "Ano": 2025,
  "fundamentAjusteDireto": ""
}
```

### Field Analysis

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `idcontrato` | STRING | **PRIMARY KEY** - Unique contract ID | "11623631" | System generated |
| `nAnuncio` | STRING | **FOREIGN KEY** - Links to announcement | "10331/2025" | References announcements table |
| `TipoAnuncio` | STRING | Type of announcement | "Anúncio de procedimento" | From original announcement |
| `idINCM` | STRING | INCM system ID | "418953989" | Internal reference |
| `tipoContrato` | JSON ARRAY | Contract type | ["Aquisição de bens móveis"] | Same as announcement |
| `idprocedimento` | STRING | Procedure ID | "7569044" | Internal procedure reference |
| `tipoprocedimento` | STRING | Procedure type | "Concurso público" | Procurement method |
| `objectoContrato` | TEXT | Contract object | "CPUB004DTEDGA2025 - Aquisição..." | What is being contracted |
| `descContrato` | TEXT | Contract description | Same as object | Detailed description |
| `adjudicante` | JSON ARRAY | Contracting entities | ["507396081 - EMAC..."] | Who is buying |
| `adjudicatarios` | JSON ARRAY | Awarded companies | ["500970602 - Renault..."] | Who won the contract |
| `dataPublicacao` | DATE | Publication date | "05/08/2025" | When contract was published |
| `dataCelebracaoContrato` | DATE | Contract signing date | "30/07/2025" | When contract was signed |
| `precoContratual` | DECIMAL | Contract price | 127206.60 | Final awarded amount |
| `cpv` | JSON ARRAY | CPV codes | ["34144900-7 - Veículos eléctricos"] | What is being procured |
| `prazoExecucao` | INTEGER | Execution period (days) | 90 | How long to complete |
| `localExecucao` | JSON ARRAY | Execution location | ["Portugal, Lisboa, Cascais"] | Where work is done |
| `fundamentacao` | TEXT | Legal basis | "Artigo 20.º, n.º 1..." | Legal justification |
| `ProcedimentoCentralizado` | STRING | Centralized procedure | "Não" | Yes/No |
| `numAcordoQuadro` | STRING | Framework agreement number | "NULL" | May be null |
| `DescrAcordoQuadro` | STRING | Framework agreement description | "NULL" | May be null |
| `precoBaseProcedimento` | DECIMAL | Base procedure price | 419000.0 | Original budget |
| `dataDecisaoAdjudicacao` | DATE | Award decision date | "02/07/2025" | When winner was chosen |
| `dataFechoContrato` | DATE | Contract closure date | "" | May be empty |
| `PrecoTotalEfetivo` | DECIMAL | Total effective price | 0.0 | Final total cost |
| `regime` | TEXT | Legal regime | "Código dos Contratos Públicos..." | Applicable law |
| `justifNReducEscrContrato` | TEXT | Contract reduction justification | null | May be null |
| `tipoFimContrato` | STRING | Contract end type | "" | How contract ended |
| `CritMateriais` | STRING | Material criteria | "Não" | Environmental criteria |
| `concorrentes` | JSON ARRAY | Competing companies | ["500035121-Caetano Formula..."] | All bidders |
| `linkPecasProc` | STRING | Procedure documents link | "https://www.acingov.pt/..." | Supporting documents |
| `Observacoes` | TEXT | Observations | "O pagamento dos bens..." | Additional notes |
| `ContratEcologico` | STRING | Ecological contract | "Não" | Environmental classification |
| `Ano` | INTEGER | Year | 2025 | Contract year |
| `fundamentAjusteDireto` | STRING | Direct award justification | "" | For non-competitive awards |

---

## Lookup Tables

## 4. Contract Types Table (`contract_types`)

### Purpose
Stores standardized contract type classifications (services, goods, works, etc.).

### Example Records
```json
[
  {"id": 1, "type_name": "Aquisição de serviços", "category": "services"},
  {"id": 2, "type_name": "Aquisição de bens móveis", "category": "goods"},
  {"id": 3, "type_name": "Empreitadas de obras públicas", "category": "works"},
  {"id": 4, "type_name": "Locação de bens móveis", "category": "rental"}
]
```

### Field Analysis

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `id` | SERIAL | **PRIMARY KEY** - Auto-increment ID | 1 | System generated |
| `type_name` | VARCHAR(200) | **UNIQUE** - Portuguese contract type | "Aquisição de serviços" | Extracted from JSON arrays |
| `category` | VARCHAR(50) | English category classification | "services" | For easier querying |
| `created_at` | TIMESTAMP | Record creation time | 2025-08-06 | ETL metadata |

---

## 5. CPV Codes Table (`cpv_codes`)

### Purpose
Stores Common Procurement Vocabulary codes (EU standard for categorizing public contracts).

### Example Records
```json
[
  {
    "code": "63510000-7",
    "description": "Serviços de agências de viagens e serviços similares",
    "category_level_1": "63000000",
    "category_name_1": "Supporting and auxiliary transport services",
    "is_active": true
  },
  {
    "code": "34144900-7", 
    "description": "Veículos eléctricos",
    "category_level_1": "34000000",
    "category_name_1": "Transport equipment and auxiliary products to transportation",
    "is_active": true
  }
]
```

### Field Analysis

| Field | Type | Description | Example | Notes |
|-------|------|-------------|---------|-------|
| `code` | VARCHAR(20) | **PRIMARY KEY** - CPV code | "63510000-7" | EU standard format |
| `description` | TEXT | Portuguese description | "Serviços de agências de viagens..." | From JSON data |
| `category_level_1` | VARCHAR(20) | Top-level CPV category | "63000000" | First 2 digits + zeros |
| `category_name_1` | VARCHAR(500) | Top-level category name | "Supporting and auxiliary transport..." | EU standard name |
| `is_active` | BOOLEAN | Whether code is still in use | true | For data management |
| `created_at` | TIMESTAMP | Record creation time | 2025-08-06 | ETL metadata |

---

## Association Tables (Many-to-Many)

## 6. Announcement Contract Types (`announcement_contract_types`)

### Purpose
Links announcements to their contract types (many-to-many relationship).

| Field | Type | Description | Notes |
|-------|------|-------------|---------|
| `id` | SERIAL | **PRIMARY KEY** | Auto-increment |
| `announcement_id` | VARCHAR(50) | **FOREIGN KEY** → announcements.nAnuncio | |
| `contract_type_id` | INTEGER | **FOREIGN KEY** → contract_types.id | |
| `created_at` | TIMESTAMP | Record creation time | ETL metadata |

**Unique Constraint**: (announcement_id, contract_type_id)

---

## 7. Announcement CPV Codes (`announcement_cpv_codes`)

### Purpose
Links announcements to their CPV codes (many-to-many relationship).

| Field | Type | Description | Notes |
|-------|------|-------------|---------|
| `id` | SERIAL | **PRIMARY KEY** | Auto-increment |
| `announcement_id` | VARCHAR(50) | **FOREIGN KEY** → announcements.nAnuncio | |
| `cpv_code` | VARCHAR(20) | **FOREIGN KEY** → cpv_codes.code | |
| `created_at` | TIMESTAMP | Record creation time | ETL metadata |

**Unique Constraint**: (announcement_id, cpv_code)

---

## 8. Contract Contract Types (`contract_contract_types`)

### Purpose
Links contracts to their contract types (many-to-many relationship).

| Field | Type | Description | Notes |
|-------|------|-------------|---------|
| `id` | SERIAL | **PRIMARY KEY** | Auto-increment |
| `contract_id` | VARCHAR(50) | **FOREIGN KEY** → contracts.idcontrato | |
| `contract_type_id` | INTEGER | **FOREIGN KEY** → contract_types.id | |
| `created_at` | TIMESTAMP | Record creation time | ETL metadata |

**Unique Constraint**: (contract_id, contract_type_id)

---

## 9. Contract CPV Codes (`contract_cpv_codes`)

### Purpose
Links contracts to their CPV codes (many-to-many relationship).

| Field | Type | Description | Notes |
|-------|------|-------------|---------|
| `id` | SERIAL | **PRIMARY KEY** | Auto-increment |
| `contract_id` | VARCHAR(50) | **FOREIGN KEY** → contracts.idcontrato | |
| `cpv_code` | VARCHAR(20) | **FOREIGN KEY** → cpv_codes.code | |
| `created_at` | TIMESTAMP | Record creation time | ETL metadata |

**Unique Constraint**: (contract_id, cpv_code)

---

## 10. Contract Competitors (`contract_competitors`)

### Purpose
Links contracts to competing entities (many-to-many relationship).

### Data Source
From `concorrentes` array in contract JSON:
```json
"concorrentes": [
  "500035121-Caetano Formula, S.A.",
  "500970602-RENAULT PORTUGAL SA", 
  "500239037-Toyota Caetano Portugal, SA"
]
```

### Field Analysis

| Field | Type | Description | Notes |
|-------|------|-------------|---------|
| `id` | SERIAL | **PRIMARY KEY** | Auto-increment |
| `contract_id` | VARCHAR(50) | **FOREIGN KEY** → contracts.idcontrato | |
| `competitor_nif` | VARCHAR(20) | **FOREIGN KEY** → entities.nifEntidade | Extracted from string |
| `competitor_name` | VARCHAR(500) | Company name from JSON | "Caetano Formula, S.A." |
| `won_contract` | BOOLEAN | Whether this competitor won | Compare with adjudicatarios |
| `created_at` | TIMESTAMP | Record creation time | ETL metadata |

**Unique Constraint**: (contract_id, competitor_nif)  
**Note**: This reuses the entities table - competitors are also entities!

---

## Schema Changes to Core Tables

### Updated Announcements Table
**Remove these JSON array fields** (now in association tables):
- ~~`tiposContrato`~~ → `announcement_contract_types` table
- ~~`CPVs`~~ → `announcement_cpv_codes` table

### Updated Contracts Table  
**Remove these JSON array fields** (now in association tables):
- ~~`tipoContrato`~~ → `contract_contract_types` table
- ~~`cpv`~~ → `contract_cpv_codes` table
- ~~`concorrentes`~~ → `contract_competitors` table

---

## Data Quality Notes

### Common Issues Identified
1. **Date Formats**: Multiple formats used (DD/MM/YYYY in strings)
2. **Null Values**: "NULL" strings vs actual null values
3. **Empty Strings**: Many fields contain empty strings instead of null
4. **Price Formats**: Mix of string and numeric formats
5. **Array Consistency**: Some arrays may have single elements

### Recommendations
1. Normalize date formats during ETL
2. Convert "NULL" strings to actual null values
3. Standardize price fields to DECIMAL type
4. **Create lookup tables first**: Contract types, CPV codes
5. **Extract competitor NIFs**: Parse competitor strings to extract entity NIFs
6. **Validate CPV codes**: Against EU CPV database
7. **Fetch entity details**: Use API to populate entities table (including competitors)
8. **Maintain referential integrity**: All foreign keys must be valid

---

## ETL Process for Entities

### ETL Processing Order
1. **Extract and load lookup data**:
   - Extract unique contract types → `contract_types` table
   - Extract unique CPV codes → `cpv_codes` table
   
2. **Extract and load entity data**:
   - Extract unique NIFs from announcements (`nifEntidade`)
   - Extract competitor NIFs from contracts (`concorrentes`)
   - Call Entity API for each unique NIF
   - Store in `entities` table
   
3. **Load core data with associations**:
   - Load `announcements` (references entities)
   - Load `contracts` (references announcements)
   
4. **Load association data**:
   - `announcement_contract_types`
   - `announcement_cpv_codes` 
   - `contract_contract_types`
   - `contract_cpv_codes`
   - `contract_competitors`

### Rate Limiting Considerations
- API calls should be rate-limited to avoid overwhelming the service
- Cache entity data to avoid duplicate API calls
- Handle API failures gracefully (retry logic, fallback to entity name from announcement)

---

## Benefits of Normalized Schema

### Query Performance
```sql
-- Find all IT service contracts
SELECT c.* FROM contracts c
JOIN contract_cpv_codes ccc ON c.idcontrato = ccc.contract_id
JOIN cpv_codes cpv ON ccc.cpv_code = cpv.code
WHERE cpv.category_level_1 = '48000000'; -- IT services

-- Find most active competitors
SELECT e.desigEntidade, COUNT(*) as bids, 
       SUM(CASE WHEN cc.won_contract THEN 1 ELSE 0 END) as wins
FROM contract_competitors cc
JOIN entities e ON cc.competitor_nif = e.nifEntidade
GROUP BY e.nifEntidade ORDER BY bids DESC;
```

### Data Integrity
- **Referential integrity** across all relationships
- **No duplicate data** in lookup tables
- **Consistent naming** and categorization
- **Easier data validation** and cleanup

---

## Next Steps
1. [ ] Define complete PostgreSQL schema (10 tables + indexes)
2. [ ] Create ETL transformation logic for normalization
3. [ ] Implement competitor NIF extraction logic
4. [ ] Build CPV code validation against EU standards
5. [ ] Design efficient bulk loading procedures
6. [ ] Plan comprehensive indexing strategy
