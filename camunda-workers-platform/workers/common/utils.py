"""
Common utilities for Camunda workers
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException


def safe_json_parse(data: str, default: Dict = None) -> Dict[str, Any]:
    """Safely parse JSON string"""
    try:
        return json.loads(data) if data else (default or {})
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse JSON: {e}")
        return default or {}


def safe_json_dump(data: Any) -> str:
    """Safely convert data to JSON string"""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError) as e:
        logging.warning(f"Failed to serialize to JSON: {e}")
        return "{}"


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> tuple[bool, list]:
    """
    Validate that all required fields are present in data
    
    Returns:
        tuple: (is_valid, missing_fields)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields


def make_http_request(
    method: str, 
    url: str, 
    data: Dict = None, 
    headers: Dict = None, 
    timeout: int = 30,
    auth: tuple = None
) -> tuple[bool, Dict]:
    """
    Make HTTP request with error handling
    
    Returns:
        tuple: (success, response_data)
    """
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=timeout,
            auth=auth
        )
        response.raise_for_status()
        
        try:
            return True, response.json()
        except json.JSONDecodeError:
            return True, {"message": response.text}
            
    except RequestException as e:
        logging.error(f"HTTP request failed: {e}")
        return False, {"error": str(e)}


def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message with context"""
    error_msg = f"{error.__class__.__name__}: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    return error_msg


def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def validate_file_type(filename: str, allowed_types: list) -> bool:
    """Validate file type based on extension"""
    if not filename:
        return False
    
    file_extension = filename.lower().split('.')[-1]
    return file_extension in [t.lower() for t in allowed_types]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    return sanitized


class TaskResult:
    """Helper class for task results"""
    
    @staticmethod
    def success(data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create success result"""
        result = {
            "status": "success",
            "timestamp": get_timestamp()
        }
        if data:
            result.update(data)
        return result
    
    @staticmethod
    def error(message: str, details: str = None, code: str = None) -> Dict[str, Any]:
        """Create error result"""
        result = {
            "status": "error",
            "error_message": message,
            "timestamp": get_timestamp()
        }
        if details:
            result["error_details"] = details
        if code:
            result["error_code"] = code
        return result
    
    @staticmethod
    def validation_error(missing_fields: list) -> Dict[str, Any]:
        """Create validation error result"""
        return TaskResult.error(
            message="Validation failed",
            details=f"Missing required fields: {', '.join(missing_fields)}",
            code="VALIDATION_ERROR"
        )


def log_task_start(logger: logging.Logger, task_id: str, topic: str, variables: Dict = None):
    """Log task start with context"""
    var_keys = None
    # var_keys = list(variables.keys()) if variables else []
    logger.info(f"Starting task {task_id} for topic '{topic}' with variables: {var_keys}")


def log_task_complete(logger: logging.Logger, task_id: str, topic: str, result: Dict = None):
    """Log task completion"""
    logger.info(f"Completed task {task_id} for topic '{topic}' - Status: {result.get('status', 'unknown')}")


def log_task_error(logger: logging.Logger, task_id: str, topic: str, error: Exception):
    """Log task error"""
    logger.error(f"Task {task_id} for topic '{topic}' failed: {format_error_message(error)}")


# Data transformation utilities
def transform_document_data(document: Dict[str, Any]) -> Dict[str, Any]:
    """Transform document data for processing"""
    return {
        "id": document.get("id"),
        "title": document.get("title", "").strip(),
        "content": document.get("content", "").strip(),
        "author": document.get("author", "").strip(),
        "created_at": document.get("created_at") or get_timestamp(),
        "file_type": document.get("file_type", "").lower(),
        "file_size": document.get("file_size", 0)
    }