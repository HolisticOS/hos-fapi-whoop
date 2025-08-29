"""
UUID utilities for WHOOP API
Handles UUID validation and conversion
"""

import uuid
import re
from typing import Union, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def is_valid_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format
    
    Args:
        uuid_string: String to validate as UUID
        
    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError, AttributeError):
        return False

def normalize_whoop_id(whoop_id: Union[str, int]) -> Dict[str, Any]:
    """
    Normalize WHOOP ID to support both v1 and v2 formats
    
    Args:
        whoop_id: Either integer (v1) or UUID string (v2)
        
    Returns:
        Dict with normalized ID information
        
    Raises:
        ValueError: If ID format is invalid
    """
    if isinstance(whoop_id, int):
        # v1 integer ID
        return {
            "uuid": None,
            "v1_id": whoop_id,
            "version": "v1",
            "is_uuid": False
        }
    elif isinstance(whoop_id, str):
        if is_valid_uuid(whoop_id):
            # v2 UUID
            return {
                "uuid": whoop_id,
                "v1_id": None,
                "version": "v2", 
                "is_uuid": True
            }
        else:
            # Try to parse as integer string
            try:
                v1_id = int(whoop_id)
                return {
                    "uuid": None,
                    "v1_id": v1_id,
                    "version": "v1",
                    "is_uuid": False
                }
            except ValueError:
                raise ValueError(f"Invalid WHOOP ID format: {whoop_id}")
    else:
        raise ValueError(f"Invalid WHOOP ID type: {type(whoop_id)}")

def convert_v1_response_to_v2(v1_data: dict) -> dict:
    """
    Convert v1 response format to v2-compatible format
    This is for migration period compatibility when dealing with legacy data
    
    Provides compatibility between integer IDs and UUID identifiers.
    The activityV1Id field ensures legacy systems compatibility.
    
    Args:
        v1_data: Original v1 API response
        
    Returns:
        Dict formatted for v2 compatibility
    """
    v2_data = v1_data.copy()
    
    if "id" in v1_data and isinstance(v1_data["id"], int):
        # Convert v1 integer ID to v2 format with backward compatibility
        v2_data["activityV1Id"] = v1_data["id"]  # Preserve original v1 ID
        v2_data["id"] = str(uuid.uuid4())  # Generate UUID for compatibility
        logger.info(f"Converted v1 ID {v1_data['id']} to UUID {v2_data['id']} with backward compatibility")
    
    return v2_data

def extract_uuid_from_url(url: str) -> Optional[str]:
    """
    Extract UUID from WHOOP API v2 URLs
    
    Args:
        url: API URL that may contain UUID
        
    Returns:
        Extracted UUID if found, None otherwise
    """
    # UUID pattern in URLs
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    match = re.search(uuid_pattern, url, re.IGNORECASE)
    
    if match:
        extracted_uuid = match.group(0)
        if is_valid_uuid(extracted_uuid):
            return extracted_uuid
    
    return None

def generate_deterministic_uuid(seed_data: str) -> str:
    """
    Generate deterministic UUID from seed data
    Useful for creating consistent UUIDs during migration
    
    Args:
        seed_data: String data to use as seed
        
    Returns:
        UUID string generated from seed
    """
    # Use UUID5 with a namespace for deterministic generation
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
    return str(uuid.uuid5(namespace, seed_data))

def validate_whoop_resource_id(resource_id: Union[str, int], resource_type: str) -> Dict[str, Any]:
    """
    Validate WHOOP resource ID based on type and API version
    
    Args:
        resource_id: ID to validate
        resource_type: Type of resource (sleep, workout, recovery, etc.)
        
    Returns:
        Dict with validation results and normalized ID info
    """
    try:
        normalized = normalize_whoop_id(resource_id)
        
        # Additional validation based on resource type
        validation_result = {
            "is_valid": True,
            "resource_type": resource_type,
            "normalized_id": normalized,
            "validation_notes": []
        }
        
        # Resource-specific validation
        if resource_type in ["sleep", "workout"]:
            if normalized["version"] == "v1":
                validation_result["validation_notes"].append(
                    "v1 ID detected - ensure migration to v2 UUID"
                )
            elif normalized["version"] == "v2":
                validation_result["validation_notes"].append(
                    "v2 UUID format - ready for v2 API"
                )
        elif resource_type == "recovery":
            # Recovery uses cycle IDs which remain consistent in v2
            validation_result["validation_notes"].append(
                "Recovery resource - uses cycle ID (consistent across versions)"
            )
        
        return validation_result
        
    except ValueError as e:
        return {
            "is_valid": False,
            "error": str(e),
            "resource_type": resource_type,
            "normalized_id": None,
            "validation_notes": [f"Invalid ID format: {e}"]
        }

def create_migration_mapping(v1_id: int, v2_uuid: str) -> Dict[str, Any]:
    """
    Create mapping record for v1 to v2 ID migration
    
    Args:
        v1_id: Original v1 integer ID
        v2_uuid: New v2 UUID identifier
        
    Returns:
        Migration mapping record
    """
    if not is_valid_uuid(v2_uuid):
        raise ValueError(f"Invalid v2 UUID: {v2_uuid}")
    
    if not isinstance(v1_id, int) or v1_id <= 0:
        raise ValueError(f"Invalid v1 ID: {v1_id}")
    
    return {
        "v1_id": v1_id,
        "v2_uuid": v2_uuid,
        "created_at": uuid.uuid1().time,  # Timestamp from UUID1
        "mapping_type": "migration",
        "is_active": True
    }

# Validation constants
UUID_REGEX_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

WHOOP_V2_RESOURCES_WITH_UUIDS = {
    "sleep", 
    "workout"
}

WHOOP_V2_RESOURCES_WITHOUT_UUIDS = {
    "recovery",
    "cycle", 
    "user_profile",
    "body_measurement"
}

def is_uuid_required_for_resource(resource_type: str) -> bool:
    """
    Check if resource type requires UUID identifiers in v2
    
    Args:
        resource_type: Type of WHOOP resource
        
    Returns:
        True if resource requires UUID in v2, False otherwise
    """
    return resource_type.lower() in WHOOP_V2_RESOURCES_WITH_UUIDS

# Export commonly used functions
__all__ = [
    "is_valid_uuid",
    "normalize_whoop_id", 
    "convert_v1_response_to_v2",
    "extract_uuid_from_url",
    "generate_deterministic_uuid",
    "validate_whoop_resource_id",
    "create_migration_mapping",
    "is_uuid_required_for_resource",
    "UUID_REGEX_PATTERN",
    "WHOOP_V2_RESOURCES_WITH_UUIDS",
    "WHOOP_V2_RESOURCES_WITHOUT_UUIDS"
]