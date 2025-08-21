"""
Field Mappings Module
Maps Portuguese API field names to English database columns.

The BASE.GOV API returns data with Portuguese field names and varying formats.
This module centralizes all field mappings to ensure consistency.
"""

# Announcement field mappings
ANNOUNCEMENT_FIELD_MAP = {
    # API field -> Database field
    'nAnuncio': 'external_id',          # Announcement number (e.g., "1/2024")
    'IdIncm': 'api_internal_id',        # Internal API ID
    'dataPublicacao': 'publication_date',
    'nifEntidade': 'entity_nif',
    'designacaoEntidade': 'entity_name',
    'descricaoAnuncio': 'description',  # or 'title' depending on content
    'objetoContrato': 'title',          # Contract object/subject
    'url': 'url',
    'numDR': 'dr_number',               # Diário da República number
    'serie': 'dr_series',                # Diário da República series
    'tipoActo': 'act_type',              # Type of act
    'tiposContrato': 'contract_types',  # Note: plural, it's an array
    'tipoContrato': 'contract_type',    # Sometimes singular
    'PrecoBase': 'base_price',          # Base price
    'precoBase': 'base_price',          # Sometimes lowercase
    'CPVs': 'cpv_codes',                 # CPV codes array
    'cpvs': 'cpv_codes',                 # Sometimes lowercase
    'modeloAnuncio': 'procedure_type',  # Announcement model/procedure
    'tipoProcedimento': 'procedure_type',
    'Ano': 'year',
    'CriterAmbient': 'environmental_criteria',
    'PrazoPropostas': 'proposal_deadline_days',
    'dataFimProposta': 'submission_deadline',
    'dataAberturaPropostas': 'opening_date',
    'PecasProcedimento': 'procedure_documents',
    'referencia': 'reference',
    'localExecucao': 'location',
    'codigoNuts': 'nuts_code',
    'prazoExecucao': 'duration_months',
    'acordoQuadro': 'is_framework',
    'sistemaAquisicaoDinamico': 'is_dynamic_purchasing',
    'permitePropostasEletronicas': 'allows_electronic_submission',
    'obrigaPropostasEletronicas': 'requires_electronic_submission',
    'estado': 'status'
}

# Contract field mappings
CONTRACT_FIELD_MAP = {
    # API field -> Database field
    'idContrato': 'external_id',
    'id_contrato': 'external_id',
    'nContrato': 'external_id',         # Contract number
    'idAnuncio': 'announcement_id',
    'nAnuncio': 'announcement_reference',
    'n_anuncio': 'announcement_reference',
    'tipo_anuncio': 'announcement_type',
    'id_incm': 'api_internal_id',
    'id_procedimento': 'procedure_id',
    'tipo_procedimento': 'procedure_type',
    'tipoProcedimento': 'procedure_type',
    'objecto_contrato': 'title',
    'objetoContrato': 'title',
    'desc_contrato': 'description',
    'descricao': 'description',
    'nifEntidade': 'entity_nif',
    'nif_entidade': 'entity_nif',
    'adjudicante_nif': 'entity_nif',
    'designacaoEntidade': 'entity_name',
    'nifAdjudicatario': 'supplier_nif',
    'nif_adjudicatario': 'supplier_nif',
    'designacaoAdjudicatario': 'supplier_name',
    'data_publicacao': 'publication_date',
    'dataPublicacao': 'publication_date',
    'data_celebracao': 'signature_date',
    'dataCelebracaoContrato': 'signature_date',
    'dataInicioExecucao': 'start_date',
    'data_inicio_execucao': 'start_date',
    'dataFimExecucao': 'end_date',
    'data_fim_execucao': 'end_date',
    'preco_contratual': 'contract_value',
    'precoContratual': 'contract_value',
    'valorAdjudicacao': 'contract_value',
    'valor_adjudicacao': 'contract_value',
    'prazo_execucao': 'duration_months',
    'prazoExecucao': 'duration_months',
    'local_execucao': 'location',
    'localExecucao': 'location',
    'fundamentacao': 'justification',
    'procedimento_centralizado': 'is_centralized',
    'num_acordo_quadro': 'framework_agreement_number',
    'acordoQuadro': 'is_framework',
    'tipoContrato': 'contract_type',
    'tipo_contrato': 'contract_type',
    'tiposContrato': 'contract_types',
    'cpvs': 'cpv_codes',
    'CPVs': 'cpv_codes',
    'observacoes': 'observations',
    'url': 'url',
    'estado': 'status',
    'codigoNuts': 'nuts_code',
    'codigo_nuts': 'nuts_code'
}

# Entity field mappings
ENTITY_FIELD_MAP = {
    'nif': 'nif',
    'designacao': 'name',
    'nome': 'name',
    'morada': 'address',
    'endereco': 'address',
    'codigoPostal': 'postal_code',
    'codigo_postal': 'postal_code',
    'localidade': 'city',
    'cidade': 'city',
    'pais': 'country',
    'email': 'email',
    'telefone': 'phone',
    'website': 'website',
    'site': 'website',
    'tipoEntidade': 'entity_type',
    'tipo_entidade': 'entity_type'
}

def normalize_field_names(data: dict, field_map: dict) -> dict:
    """
    Normalize field names from API format to database format.
    
    Args:
        data: Dictionary with API field names
        field_map: Mapping from API fields to database fields
    
    Returns:
        Dictionary with normalized field names
    """
    normalized = {}
    
    for api_field, value in data.items():
        # Check if we have a mapping for this field
        db_field = field_map.get(api_field)
        
        if db_field:
            normalized[db_field] = value
        else:
            # Keep the original field if no mapping exists
            # This helps with debugging and ensures we don't lose data
            normalized[api_field] = value
    
    return normalized

def get_required_fields(record_type: str) -> list:
    """
    Get required fields for a record type.
    
    Args:
        record_type: Type of record (announcement, contract, entity)
    
    Returns:
        List of required API field names
    """
    if record_type == 'announcement':
        # These are the API field names that must be present
        return ['nAnuncio', 'nifEntidade', 'dataPublicacao']
    elif record_type == 'contract':
        return ['idContrato', 'nifEntidade', 'dataPublicacao']
    elif record_type == 'entity':
        return ['nif', 'designacao']
    else:
        return []

def extract_announcement_id(announcement_data: dict) -> str:
    """
    Extract the announcement ID from various possible field names.
    
    Args:
        announcement_data: Announcement data from API
    
    Returns:
        Announcement ID or None
    """
    # Try different field names
    for field in ['nAnuncio', 'idAnuncio', 'id_anuncio', 'numeroAnuncio']:
        if field in announcement_data:
            return str(announcement_data[field])
    
    # If we have IdIncm, use it as fallback
    if 'IdIncm' in announcement_data:
        return f"incm_{announcement_data['IdIncm']}"
    
    return None

def extract_contract_id(contract_data: dict) -> str:
    """
    Extract the contract ID from various possible field names.
    
    Args:
        contract_data: Contract data from API
    
    Returns:
        Contract ID or None
    """
    # Try different field names (including lowercase)
    for field in ['idContrato', 'idcontrato', 'id_contrato', 'nContrato', 'numeroContrato']:
        if field in contract_data:
            return str(contract_data[field])
    
    # If we have idINCM, use it as fallback  
    if 'idINCM' in contract_data:
        return f"incm_{contract_data['idINCM']}"
    
    return None

def extract_entity_nif(entity_data: dict) -> str:
    """
    Extract the entity NIF from various possible field names.
    
    Args:
        entity_data: Entity data
    
    Returns:
        Entity NIF or None
    """
    # Try different field names
    for field in ['nif', 'nifEntidade', 'nif_entidade', 'NIF']:
        if field in entity_data:
            return str(entity_data[field])
    
    return None

def extract_entity_name(entity_data: dict) -> str:
    """
    Extract the entity name from various possible field names.
    
    Args:
        entity_data: Entity data
    
    Returns:
        Entity name or None
    """
    # Try different field names
    for field in ['designacao', 'designacaoEntidade', 'nome', 'name']:
        if field in entity_data:
            return str(entity_data[field])
    
    return None

def extract_contract_entity_nif(contract_data: dict) -> str:
    """
    Extract the contracting entity NIF from contract data.
    
    The API returns the entity in format: "NIF - Name" in the adjudicante field.
    
    Args:
        contract_data: Contract data from API
    
    Returns:
        Entity NIF or None
    """
    # Try direct NIF field first
    nif = extract_entity_nif(contract_data)
    if nif:
        return nif
    
    # Try to extract from adjudicante field (format: "NIF - Name")
    if 'adjudicante' in contract_data:
        adjudicante = contract_data['adjudicante']
        if isinstance(adjudicante, list) and len(adjudicante) > 0:
            # Take first adjudicante
            adj_str = adjudicante[0]
            if ' - ' in adj_str:
                # Extract NIF part (before the dash)
                nif_part = adj_str.split(' - ')[0].strip()
                # Validate it looks like a NIF (9 digits)
                if nif_part.isdigit() and len(nif_part) == 9:
                    return nif_part
    
    return None

def extract_contract_supplier_nif(contract_data: dict) -> str:
    """
    Extract the supplier/adjudicatario NIF from contract data.
    
    The API returns the supplier in format: "NIF - Name" in the adjudicatarios field.
    
    Args:
        contract_data: Contract data from API
    
    Returns:
        Supplier NIF or None
    """
    # Try direct field first
    if 'nifAdjudicatario' in contract_data:
        return str(contract_data['nifAdjudicatario'])
    
    # Try to extract from adjudicatarios field (format: "NIF - Name")
    if 'adjudicatarios' in contract_data:
        adjudicatarios = contract_data['adjudicatarios']
        if isinstance(adjudicatarios, list) and len(adjudicatarios) > 0:
            # Take first adjudicatario
            adj_str = adjudicatarios[0]
            if ' - ' in adj_str:
                # Extract NIF part (before the dash)
                nif_part = adj_str.split(' - ')[0].strip()
                # Validate it looks like a NIF (9 digits)
                if nif_part.isdigit() and len(nif_part) == 9:
                    return nif_part
    
    return None
