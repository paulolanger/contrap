"""
Data Validator Module
Responsible for validating and cleaning data from the Portuguese Government Procurement API.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validate and clean data from the API.
    """
    
    # Valid contract types based on Portuguese procurement law
    VALID_CONTRACT_TYPES = {
        "Aquisição de Bens Móveis",
        "Aquisição de Serviços", 
        "Empreitadas de Obras Públicas",
        "Concessão de Obras Públicas",
        "Concessão de Serviços Públicos",
        "Locação de Bens Móveis",
        "Contrato de Sociedade",
        "Outros"
    }
    
    # Valid procedure types
    VALID_PROCEDURE_TYPES = {
        "Concurso público",
        "Concurso público urgente",
        "Concurso limitado por prévia qualificação",
        "Procedimento de negociação",
        "Diálogo concorrencial",
        "Parceria para a inovação",
        "Concurso de conceção",
        "Concurso de ideias",
        "Ajuste direto",
        "Ajuste direto simplificado",
        "Consulta prévia",
        "Acordo quadro",
        "Sistema de aquisição dinâmico",
        "Hasta pública",
        "Outros"
    }
    
    @staticmethod
    def validate_nif(nif: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Portuguese NIF format with full checksum validation.
        
        Args:
            nif: NIF string to validate
        
        Returns:
            Tuple of (is_valid, cleaned_nif)
        """
        if not nif or nif in ["NULL", "null", "N/A", "0"]:
            return False, None
        
        # Remove any non-digit characters
        nif_clean = re.sub(r'\D', '', str(nif).strip())
        
        # Portuguese NIF should be 9 digits
        if len(nif_clean) != 9:
            return False, None
        
        # First digit must be 1, 2, 3, 5, 6, 7, 8 or 9
        if nif_clean[0] not in '12356789':
            return False, None
        
        # Calculate check digit
        try:
            check_sum = 0
            for i in range(8):
                check_sum += int(nif_clean[i]) * (9 - i)
            
            check_digit = 11 - (check_sum % 11)
            if check_digit >= 10:
                check_digit = 0
            
            if int(nif_clean[8]) == check_digit:
                return True, nif_clean
            else:
                return False, None
                
        except (ValueError, IndexError):
            return False, None
    
    @staticmethod
    def normalize_date(date_str: str) -> Optional[datetime]:
        """
        Convert various date formats to datetime object.
        
        Args:
            date_str: Date string to normalize
        
        Returns:
            datetime object or None if invalid
        """
        if not date_str or date_str in ["NULL", "null", "N/A", ""]:
            return None
        
        # List of date formats to try
        date_formats = [
            "%d/%m/%Y",           # DD/MM/YYYY
            "%Y-%m-%d",           # YYYY-MM-DD
            "%d-%m-%Y",           # DD-MM-YYYY
            "%Y/%m/%d",           # YYYY/MM/DD
            "%d.%m.%Y",           # DD.MM.YYYY
            "%Y-%m-%dT%H:%M:%S",  # ISO format with time
            "%Y-%m-%d %H:%M:%S"   # DateTime format
        ]
        
        date_str = str(date_str).strip()
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @staticmethod
    def normalize_amount(amount_str: str) -> Optional[Decimal]:
        """
        Normalize monetary amounts to Decimal.
        
        Args:
            amount_str: Amount string to normalize
        
        Returns:
            Decimal amount or None if invalid
        """
        if not amount_str or amount_str in ["NULL", "null", "N/A", ""]:
            return None
        
        try:
            # Remove currency symbols and spaces
            amount_clean = re.sub(r'[€$£\s]', '', str(amount_str))
            
            # Handle European number format (comma as decimal separator)
            if ',' in amount_clean and '.' in amount_clean:
                # Assume format is 1.234.567,89
                amount_clean = amount_clean.replace('.', '').replace(',', '.')
            elif ',' in amount_clean:
                # Could be 1234,56 or 1,234,567
                if amount_clean.count(',') == 1 and len(amount_clean.split(',')[1]) <= 2:
                    # Likely European format with decimal
                    amount_clean = amount_clean.replace(',', '.')
                else:
                    # Likely thousands separator
                    amount_clean = amount_clean.replace(',', '')
            
            return Decimal(amount_clean)
            
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Could not parse amount: {amount_str} - {e}")
            return None
    
    @staticmethod
    def clean_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace 'NULL' strings and empty values with None.
        
        Args:
            data: Dictionary to clean
        
        Returns:
            Cleaned dictionary
        """
        cleaned = {}
        
        for key, value in data.items():
            if value in ["NULL", "null", "N/A"]:
                cleaned[key] = None
            elif isinstance(value, str):
                stripped = value.strip()
                cleaned[key] = None if stripped == "" else stripped
            elif isinstance(value, list):
                # Clean list items
                cleaned_list = []
                for item in value:
                    if item not in ["NULL", "null", "N/A", ""]:
                        if isinstance(item, str):
                            stripped_item = item.strip()
                            if stripped_item:
                                cleaned_list.append(stripped_item)
                        else:
                            cleaned_list.append(item)
                cleaned[key] = cleaned_list if cleaned_list else None
            elif isinstance(value, dict):
                # Recursively clean nested dictionaries
                cleaned[key] = DataValidator.clean_null_values(value)
            else:
                cleaned[key] = value
        
        return cleaned
    
    @staticmethod
    def extract_cpv_codes(cpv_list: List[str]) -> List[Dict[str, str]]:
        """
        Extract and validate CPV codes and descriptions.
        
        Args:
            cpv_list: List of CPV strings
        
        Returns:
            List of dictionaries with code and description
        """
        cpv_data = []
        
        if not cpv_list:
            return cpv_data
        
        for cpv_str in cpv_list:
            if not cpv_str or cpv_str in ["NULL", "null", "N/A"]:
                continue
            
            cpv_str = str(cpv_str).strip()
            
            # Format variations:
            # "12345678-9 - Description"
            # "12345678 Description"
            # "12345678-9"
            
            # Try to extract code and description
            match = re.match(r'(\d{8}(?:-\d)?)\s*[-–]?\s*(.*)$', cpv_str)
            if match:
                code = match.group(1)
                description = match.group(2).strip()
                
                # Validate CPV code format
                if len(code.replace('-', '')) >= 8:
                    cpv_entry = {'code': code}
                    if description:
                        cpv_entry['description'] = description
                    cpv_data.append(cpv_entry)
            else:
                # Try to extract just the code
                code_match = re.search(r'\d{8}(?:-\d)?', cpv_str)
                if code_match:
                    cpv_data.append({'code': code_match.group()})
        
        return cpv_data
    
    @staticmethod
    def parse_competitors(competitors_list: List[str]) -> List[Dict[str, Any]]:
        """
        Parse competitor NIFs and names.
        
        Args:
            competitors_list: List of competitor strings
        
        Returns:
            List of parsed competitor dictionaries
        """
        parsed = []
        
        if not competitors_list:
            return parsed
        
        for competitor_str in competitors_list:
            if not competitor_str or competitor_str in ["NULL", "null", "N/A"]:
                continue
            
            competitor_str = str(competitor_str).strip()
            
            # Format variations:
            # "123456789-Company Name"
            # "123456789 - Company Name"
            # "Company Name (123456789)"
            
            competitor_data = {}
            
            # Try format: NIF-Name or NIF - Name
            if '-' in competitor_str:
                parts = competitor_str.split('-', 1)
                potential_nif = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else ""
                
                is_valid, clean_nif = DataValidator.validate_nif(potential_nif)
                if is_valid:
                    competitor_data['nif'] = clean_nif
                    if name:
                        competitor_data['name'] = name
                else:
                    # NIF might be after the dash
                    if len(parts) > 1:
                        is_valid, clean_nif = DataValidator.validate_nif(parts[1].strip())
                        if is_valid:
                            competitor_data['nif'] = clean_nif
                            competitor_data['name'] = parts[0].strip()
                        else:
                            # Just store the whole string as name
                            competitor_data['name'] = competitor_str
            
            # Try format: Name (NIF)
            elif '(' in competitor_str and ')' in competitor_str:
                match = re.match(r'(.+)\s*\((\d+)\)', competitor_str)
                if match:
                    name = match.group(1).strip()
                    potential_nif = match.group(2)
                    
                    is_valid, clean_nif = DataValidator.validate_nif(potential_nif)
                    if is_valid:
                        competitor_data['nif'] = clean_nif
                    competitor_data['name'] = name
                else:
                    competitor_data['name'] = competitor_str
            
            # Try to find NIF pattern in the string
            else:
                nif_match = re.search(r'\b\d{9}\b', competitor_str)
                if nif_match:
                    potential_nif = nif_match.group()
                    is_valid, clean_nif = DataValidator.validate_nif(potential_nif)
                    if is_valid:
                        competitor_data['nif'] = clean_nif
                        # Remove NIF from name
                        name = competitor_str.replace(potential_nif, '').strip(' -,')
                        if name:
                            competitor_data['name'] = name
                else:
                    # No NIF found, just store as name
                    competitor_data['name'] = competitor_str
            
            if competitor_data:
                parsed.append(competitor_data)
        
        return parsed
    
    @staticmethod
    def normalize_contract_type(contract_type: str) -> Optional[str]:
        """
        Normalize contract type to standard values.
        
        Args:
            contract_type: Contract type string
        
        Returns:
            Normalized contract type or None
        """
        if not contract_type or contract_type in ["NULL", "null", "N/A"]:
            return None
        
        contract_type = str(contract_type).strip()
        
        # Direct match
        if contract_type in DataValidator.VALID_CONTRACT_TYPES:
            return contract_type
        
        # Case-insensitive match
        contract_type_lower = contract_type.lower()
        for valid_type in DataValidator.VALID_CONTRACT_TYPES:
            if valid_type.lower() == contract_type_lower:
                return valid_type
        
        # Partial matching for common variations
        type_mapping = {
            "bens": "Aquisição de Bens Móveis",
            "serviços": "Aquisição de Serviços",
            "serviço": "Aquisição de Serviços",
            "empreitada": "Empreitadas de Obras Públicas",
            "obras": "Empreitadas de Obras Públicas",
            "concessão": "Concessão de Serviços Públicos",
            "locação": "Locação de Bens Móveis",
            "aluguer": "Locação de Bens Móveis"
        }
        
        for keyword, mapped_type in type_mapping.items():
            if keyword in contract_type_lower:
                return mapped_type
        
        logger.warning(f"Unknown contract type: {contract_type}")
        return "Outros"
    
    @staticmethod
    def validate_announcement(announcement: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an announcement record.
        
        Args:
            announcement: Announcement dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Clean null values first
        announcement = DataValidator.clean_null_values(announcement)
        
        # Required fields
        required_fields = ['idAnuncio', 'nifEntidade', 'dataPublicacao']
        for field in required_fields:
            if not announcement.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate NIF
        if announcement.get('nifEntidade'):
            is_valid, _ = DataValidator.validate_nif(announcement['nifEntidade'])
            if not is_valid:
                errors.append(f"Invalid NIF: {announcement['nifEntidade']}")
        
        # Validate dates
        date_fields = ['dataPublicacao', 'dataFimProposta', 'dataAberturaPropostas']
        for field in date_fields:
            if announcement.get(field):
                date_val = DataValidator.normalize_date(announcement[field])
                if not date_val:
                    errors.append(f"Invalid date format in {field}: {announcement[field]}")
        
        # Validate amount if present
        if announcement.get('precoBase'):
            amount = DataValidator.normalize_amount(announcement['precoBase'])
            if amount and amount < 0:
                errors.append(f"Negative price base: {announcement['precoBase']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_contract(contract: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a contract record.
        
        Args:
            contract: Contract dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Clean null values first
        contract = DataValidator.clean_null_values(contract)
        
        # Required fields
        required_fields = ['idContrato', 'nifEntidade', 'dataPublicacao']
        for field in required_fields:
            if not contract.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate NIFs
        nif_fields = ['nifEntidade', 'nifAdjudicatario']
        for field in nif_fields:
            if contract.get(field):
                is_valid, _ = DataValidator.validate_nif(contract[field])
                if not is_valid:
                    errors.append(f"Invalid NIF in {field}: {contract[field]}")
        
        # Validate dates
        date_fields = ['dataPublicacao', 'dataCelebracaoContrato', 'dataInicioExecucao', 'dataFimExecucao']
        for field in date_fields:
            if contract.get(field):
                date_val = DataValidator.normalize_date(contract[field])
                if not date_val:
                    errors.append(f"Invalid date format in {field}: {contract[field]}")
        
        # Validate amounts
        amount_fields = ['precoContratual', 'valorAdjudicacao']
        for field in amount_fields:
            if contract.get(field):
                amount = DataValidator.normalize_amount(contract[field])
                if amount and amount < 0:
                    errors.append(f"Negative amount in {field}: {contract[field]}")
        
        # Validate contract type
        if contract.get('tipoContrato'):
            normalized_type = DataValidator.normalize_contract_type(contract['tipoContrato'])
            if not normalized_type:
                errors.append(f"Invalid contract type: {contract['tipoContrato']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_entity(entity: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an entity record.
        
        Args:
            entity: Entity dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Clean null values first
        entity = DataValidator.clean_null_values(entity)
        
        # Required fields
        if not entity.get('nif'):
            errors.append("Missing required field: nif")
        else:
            is_valid, _ = DataValidator.validate_nif(entity['nif'])
            if not is_valid:
                errors.append(f"Invalid NIF: {entity['nif']}")
        
        if not entity.get('designacao'):
            errors.append("Missing required field: designacao (name)")
        
        return len(errors) == 0, errors


def validate_batch(records: List[Dict[str, Any]], record_type: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Validate a batch of records.
    
    Args:
        records: List of records to validate
        record_type: Type of records (announcement, contract, entity)
    
    Returns:
        Tuple of (valid_records, invalid_records_with_errors)
    """
    validator = DataValidator()
    valid_records = []
    invalid_records = []
    
    validation_methods = {
        'announcement': validator.validate_announcement,
        'contract': validator.validate_contract,
        'entity': validator.validate_entity
    }
    
    validate_func = validation_methods.get(record_type)
    if not validate_func:
        raise ValueError(f"Unknown record type: {record_type}")
    
    for record in records:
        is_valid, errors = validate_func(record)
        if is_valid:
            # Clean the record before adding to valid list
            clean_record = validator.clean_null_values(record)
            valid_records.append(clean_record)
        else:
            invalid_records.append({
                'record': record,
                'errors': errors
            })
    
    return valid_records, invalid_records


if __name__ == "__main__":
    # Test examples
    validator = DataValidator()
    
    # Test NIF validation
    test_nifs = ["123456789", "500000000", "999999999", "12345678", "NULL", "ABC123456"]
    print("NIF Validation Tests:")
    for nif in test_nifs:
        is_valid, clean = validator.validate_nif(nif)
        print(f"  {nif}: Valid={is_valid}, Clean={clean}")
    
    # Test date normalization
    print("\nDate Normalization Tests:")
    test_dates = ["01/01/2024", "2024-01-01", "01-01-2024", "NULL", "invalid"]
    for date_str in test_dates:
        normalized = validator.normalize_date(date_str)
        print(f"  {date_str}: {normalized}")
    
    # Test amount normalization
    print("\nAmount Normalization Tests:")
    test_amounts = ["1000", "1,000.50", "1.000,50", "€1000", "NULL", "invalid"]
    for amount in test_amounts:
        normalized = validator.normalize_amount(amount)
        print(f"  {amount}: {normalized}")
    
    # Test CPV extraction
    print("\nCPV Extraction Tests:")
    test_cpvs = [
        ["12345678-9 - Test Description"],
        ["12345678 Test"],
        ["NULL"],
        []
    ]
    for cpv_list in test_cpvs:
        extracted = validator.extract_cpv_codes(cpv_list)
        print(f"  {cpv_list}: {extracted}")
