import json
import boto3
import os
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import reduce, partial
from datetime import datetime
import re
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB resource with environment variable for flexible deployment
TABLE_NAME = os.environ.get('DYNAMODB_TABLE')
if not TABLE_NAME:
    raise ValueError("DYNAMODB_TABLE environment variable is required")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# GSI name constant - matches DynamoDB secondary index configuration
GSI_NAME = "room_id-timestamp-index"


# ============================================================================
# PURE VALIDATION FUNCTIONS - No side effects, deterministic output
# ============================================================================

def validate_device_id(device_id: str) -> bool:
    """
    Validate device_id format: device_type_number where number > 0
    Examples: fridge_01, sensor_42, thermostat_5
    """
    # Check basic type and underscore count
    if not isinstance(device_id, str) or device_id.count('_') != 1:
        return False

    # Split into device type and numeric ID
    device_type, device_num = device_id.split('_')

    try:
        # Validate numeric part is positive integer
        num = int(device_num)
        return isinstance(device_type, str) and len(device_type) > 0 and num > 0
    except ValueError:
        return False


def validate_room_id(room_id: str) -> bool:
    """Validate room_id is non-empty string"""
    return isinstance(room_id, str) and len(room_id.strip()) > 0


def validate_timestamp(timestamp: str) -> bool:
    """Validate ISO timestamp format (e.g., 2024-12-01T10:00:00Z)"""
    if not isinstance(timestamp, str):
        return False
    try:
        # Parse ISO format with timezone handling
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def validate_status(status: str) -> bool:
    """Validate device status against allowed values"""
    valid_statuses = {'ok', 'sensor_error', 'offline', 'maintenance'}
    return isinstance(status, str) and status.lower() in valid_statuses


# ============================================================================
# PARAMETER EXTRACTION FUNCTIONS - Pure functions for event parsing
# ============================================================================

def extract_query_params(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract query parameters from API Gateway event, return empty dict if none"""
    return event.get('queryStringParameters') or {}


def extract_path_params(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract path parameters from API Gateway event, return empty dict if none"""
    return event.get('pathParameters') or {}


# ============================================================================
# VALIDATION PIPELINE - Functional composition for parameter validation
# ============================================================================

def validate_params(params: Dict[str, Any], validators: Dict[str, callable]) -> Tuple[bool, List[str]]:
    """
    Validate parameters using provided validator functions
    Returns: (is_valid: bool, errors: List[str])
    """
    errors = []

    # Apply each validator to corresponding parameter
    for param, value in params.items():
        if param in validators and value is not None:
            if not validators[param](value):
                errors.append(f"Invalid {param}: {value}")

    return len(errors) == 0, errors


# ============================================================================
# DYNAMODB QUERY FUNCTIONS - Database interaction layer
# ============================================================================

def query_all_devices() -> List[Dict]:
    """
    Scan entire table to retrieve all device records
    WARNING: Expensive operation for large tables
    """
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Database query failed: {str(e)}")


def query_device_by_id(device_id: str, start_time: Optional[str] = None,
                       end_time: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """
    Query specific device using partition key with optional filters
    Uses primary table index for optimal performance
    """
    try:
        # Build key condition for device_id (partition key)
        key_condition = Key('device_id').eq(device_id)

        # Add timestamp range filtering using sort key
        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        # Prepare query parameters
        query_params = {'KeyConditionExpression': key_condition}

        # Add status filter as FilterExpression (applied after key condition)
        if status:
            query_params['FilterExpression'] = Attr('device_status').eq(status)

        response = table.query(**query_params)
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Device query failed: {str(e)}")


def query_room_by_id(room_id: str, start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> List[Dict]:
    """
    Query room data using Global Secondary Index
    Efficient for room-based queries across all devices
    """
    try:
        # Build key condition for room_id (GSI partition key)
        key_condition = Key('room_id').eq(room_id)

        # Add timestamp filtering using GSI sort key
        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        # Query using GSI
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=key_condition
        )
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Room query failed: {str(e)}")


def query_room_device_specific(room_id: str, device_id: str, start_time: Optional[str] = None,
                               end_time: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """
    Query specific device in specific room with optional filters
    Uses GSI for room filtering, then applies device filter
    """
    try:
        # Start with room-based query using GSI
        key_condition = Key('room_id').eq(room_id)

        # Add timestamp filtering
        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        # Prepare query parameters
        query_params = {
            'IndexName': GSI_NAME,
            'KeyConditionExpression': key_condition
        }

        # Build filter expression for device_id and optional status
        filter_expressions = [Attr('device_id').eq(device_id)]
        if status:
            filter_expressions.append(Attr('device_status').eq(status))

        # Combine filter expressions with AND logic
        if len(filter_expressions) == 1:
            query_params['FilterExpression'] = filter_expressions[0]
        else:
            query_params['FilterExpression'] = filter_expressions[0] & filter_expressions[1]

        response = table.query(**query_params)
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Room-device query failed: {str(e)}")


def get_unique_rooms() -> List[str]:
    """
    Scan table to get all unique room IDs
    Uses projection to minimize data transfer
    """
    try:
        response = table.scan(
            ProjectionExpression='room_id'  # Only fetch room_id attribute
        )
        # Use set to eliminate duplicates, then sort for consistent output
        rooms = set(item['room_id'] for item in response.get('Items', []))
        return sorted(list(rooms))
    except Exception as e:
        raise Exception(f"Room scan failed: {str(e)}")


def get_unique_devices() -> List[str]:
    """
    Scan table to get all unique device IDs
    Uses projection to minimize data transfer
    """
    try:
        response = table.scan(
            ProjectionExpression='device_id'  # Only fetch device_id attribute
        )
        # Use set to eliminate duplicates, then sort for consistent output
        devices = set(item['device_id'] for item in response.get('Items', []))
        return sorted(list(devices))
    except Exception as e:
        raise Exception(f"Device scan failed: {str(e)}")


def get_devices_in_room(room_id: str) -> List[Dict]:
    """
    Get all unique devices present in a specific room
    Uses GSI with projection to optimize query performance
    """
    try:
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('room_id').eq(room_id),
            ProjectionExpression='device_id'  # Only fetch device_id
        )
        # Extract unique device IDs and format as objects
        devices = set(item['device_id'] for item in response.get('Items', []))
        return [{'device_id': device} for device in sorted(devices)]
    except Exception as e:
        raise Exception(f"Room devices query failed: {str(e)}")


# ============================================================================
# RESPONSE FORMATTING FUNCTIONS - Pure functions for data transformation
# ============================================================================

def decimal_to_float(obj):
    """
    Recursively convert DynamoDB Decimal objects to float for JSON serialization
    DynamoDB returns numbers as Decimal type which isn't JSON serializable
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def create_response(status_code: int, body: Any, headers: Optional[Dict] = None) -> Dict:
    """
    Create standardized API Gateway response with CORS headers
    Ensures consistent response format across all endpoints
    """
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',  # Enable CORS for web clients
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

    # Merge custom headers if provided
    if headers:
        default_headers.update(headers)

    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(decimal_to_float(body))  # Convert Decimals and serialize
    }


def create_error_response(status_code: int, message: str, errors: Optional[List] = None) -> Dict:
    """
    Create standardized error response with optional detailed error list
    Provides consistent error format for client error handling
    """
    error_body = {'error': message}
    if errors:
        error_body['details'] = errors

    return create_response(status_code, error_body)


# ============================================================================
# ROUTE HANDLERS - Individual endpoint logic
# ============================================================================

def handle_root(event: Dict) -> Dict:
    """
    Handle GET / - return all telemetry data from table
    WARNING: This can be expensive for large datasets
    """
    try:
        data = query_all_devices()
        return create_response(200, {'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve data: {str(e)}")


def handle_devices_list(event: Dict) -> Dict:
    """
    Handle GET /devices - return list of all unique device IDs
    Useful for discovering available devices in the system
    """
    try:
        devices = get_unique_devices()
        return create_response(200, {'devices': devices, 'count': len(devices)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve devices: {str(e)}")


def handle_device_detail(event: Dict) -> Dict:
    """
    Handle GET /devices/{device_id} - return specific device telemetry data
    Supports optional query parameters for filtering
    """
    # Extract parameters from API Gateway event
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    device_id = path_params.get('device_id')

    # Validate required path parameter
    validators = {'device_id': validate_device_id}
    is_valid, errors = validate_params({'device_id': device_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    # Extract optional query parameters
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    status = query_params.get('status')

    # Validate optional query parameters
    optional_validators = {
        'start_time': validate_timestamp,
        'end_time': validate_timestamp,
        'status': validate_status
    }

    optional_params = {k: v for k, v in query_params.items() if v is not None}
    is_valid, errors = validate_params(optional_params, optional_validators)

    if not is_valid:
        return create_error_response(400, "Query parameter validation failed", errors)

    try:
        # Execute database query with filters
        data = query_device_by_id(device_id, start_time, end_time, status)
        return create_response(200, {'device_id': device_id, 'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve device data: {str(e)}")


def handle_rooms_list(event: Dict) -> Dict:
    """
    Handle GET /rooms - return list of all unique room IDs
    Useful for discovering available rooms in the system
    """
    try:
        rooms = get_unique_rooms()
        return create_response(200, {'rooms': rooms, 'count': len(rooms)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve rooms: {str(e)}")


def handle_room_detail(event: Dict) -> Dict:
    """
    Handle GET /rooms/{room_id} - return all telemetry data for devices in specific room
    Uses GSI for efficient room-based queries
    """
    # Extract parameters from API Gateway event
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    room_id = path_params.get('room_id')

    # Validate required path parameter
    validators = {'room_id': validate_room_id}
    is_valid, errors = validate_params({'room_id': room_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    # Extract optional query parameters
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')

    # Validate optional query parameters
    optional_validators = {
        'start_time': validate_timestamp,
        'end_time': validate_timestamp
    }

    optional_params = {k: v for k, v in query_params.items() if v is not None}
    is_valid, errors = validate_params(optional_params, optional_validators)

    if not is_valid:
        return create_error_response(400, "Query parameter validation failed", errors)

    try:
        # Execute GSI query for room data
        data = query_room_by_id(room_id, start_time, end_time)
        return create_response(200, {'room_id': room_id, 'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve room data: {str(e)}")


def handle_room_devices(event: Dict) -> Dict:
    """
    Handle GET /rooms/{room_id}/devices - return list of unique devices in specific room
    Provides device inventory for a room
    """
    path_params = extract_path_params(event)
    room_id = path_params.get('room_id')

    # Validate required path parameter
    validators = {'room_id': validate_room_id}
    is_valid, errors = validate_params({'room_id': room_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    try:
        # Get unique devices in the specified room
        devices = get_devices_in_room(room_id)
        return create_response(200, {'room_id': room_id, 'devices': devices, 'count': len(devices)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve room devices: {str(e)}")


def handle_room_device_detail(event: Dict) -> Dict:
    """
    Handle GET /rooms/{room_id}/{device_id} - return specific device data in specific room
    Combines room and device filtering for precise queries
    """
    # Extract parameters from API Gateway event
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    room_id = path_params.get('room_id')
    device_id = path_params.get('device_id')

    # Validate required path parameters
    validators = {
        'room_id': validate_room_id,
        'device_id': validate_device_id
    }
    is_valid, errors = validate_params({'room_id': room_id, 'device_id': device_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    # Extract optional query parameters
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    status = query_params.get('status')

    # Validate optional query parameters
    optional_validators = {
        'start_time': validate_timestamp,
        'end_time': validate_timestamp,
        'status': validate_status
    }

    optional_params = {k: v for k, v in query_params.items() if v is not None}
    is_valid, errors = validate_params(optional_params, optional_validators)

    if not is_valid:
        return create_error_response(400, "Query parameter validation failed", errors)

    try:
        # Execute room-device specific query
        data = query_room_device_specific(room_id, device_id, start_time, end_time, status)
        return create_response(200, {
            'room_id': room_id,
            'device_id': device_id,
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve room-device data: {str(e)}")


# ============================================================================
# ROUTING CONFIGURATION - Maps HTTP method + resource path to handlers
# ============================================================================

ROUTE_HANDLERS = {
    ('GET', '/'): handle_root,
    ('GET', '/devices'): handle_devices_list,
    ('GET', '/devices/{device_id}'): handle_device_detail,
    ('GET', '/rooms'): handle_rooms_list,
    ('GET', '/rooms/{room_id}'): handle_room_detail,
    ('GET', '/rooms/{room_id}/devices'): handle_room_devices,
    ('GET', '/rooms/{room_id}/{device_id}'): handle_room_device_detail,  # New endpoint
}


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main Lambda handler with functional routing
    Processes API Gateway events and routes to appropriate handlers
    """
    try:
        # Extract HTTP method and resource path from API Gateway event
        http_method = event.get('httpMethod', 'GET')
        resource_path = event.get('resource', '/')

        # Route resolution using tuple key lookup
        route_key = (http_method, resource_path)
        handler = ROUTE_HANDLERS.get(route_key)

        # Handle unknown routes
        if not handler:
            return create_error_response(404, f"Route not found: {http_method} {resource_path}")

        # Execute appropriate handler function
        return handler(event)

    except Exception as e:
        # Catch-all error handler for unexpected failures
        return create_error_response(500, f"Internal server error: {str(e)}")
