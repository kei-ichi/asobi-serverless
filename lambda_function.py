import json
import boto3
import os
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import reduce, partial
from datetime import datetime
import re
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# 環境変数からDynamoDBテーブル名を取得
TABLE_NAME = os.environ.get('DYNAMODB_TABLE')
if not TABLE_NAME:
    raise ValueError("DYNAMODB_TABLE environment variable is required")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# GSI名 - room_idをパーティションキー、timestampをソートキーとするインデックス
GSI_NAME = "room_id-timestamp-index"


# ============================================================================
# バリデーション関数
# ============================================================================

def validate_device_id(device_id: str) -> bool:
    """
    デバイスID形式の検証: device_type_number（numberは0より大きい）
    例: fridge_01, sensor_42, thermostat_5
    """
    if not isinstance(device_id, str) or device_id.count('_') != 1:
        return False

    device_type, device_num = device_id.split('_')

    try:
        num = int(device_num)
        return isinstance(device_type, str) and len(device_type) > 0 and num > 0
    except ValueError:
        return False


def validate_room_id(room_id: str) -> bool:
    """
    部屋ID形式の検証: room_number（numberは0より大きい3桁の数字）
    例: room_001, room_002, room_010, room_100
    """
    if not isinstance(room_id, str) or room_id.count('_') != 1:
        return False

    room_prefix, room_num = room_id.split('_')

    try:
        # プレフィックスが'room'であることを確認
        if room_prefix != 'room':
            return False

        # 数値部分が正の整数であることを検証
        num = int(room_num)

        # 数値が0より大きく、3桁の形式（001, 002など）であることを確認
        return num > 0 and len(room_num) == 3 and room_num.isdigit()
    except ValueError:
        return False


def validate_timestamp(timestamp: str) -> bool:
    """
    UTC形式タイムスタンプを検証: YYYY-MM-DDTHH:MM:SSZ（Z必須）
    テストデータ形式に合わせてUTCのみ許可
    """
    if not isinstance(timestamp, str):
        return False

    # UTC（Z）で終わることを必須とする
    if not timestamp.endswith('Z'):
        return False

    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def validate_status(status: str) -> bool:
    """
    厳密な小文字ステータス値のみを許可
    許可値: 'ok', 'sensor_error', 'offline', 'maintenance'
    """
    valid_statuses = {'ok', 'sensor_error', 'offline', 'maintenance'}
    return isinstance(status, str) and status in valid_statuses

# ============================================================================
# パラメータ抽出関数
# ============================================================================

def extract_query_params(event: Dict[str, Any]) -> Dict[str, str]:
    """API Gatewayイベントからクエリパラメータを抽出"""
    return event.get('queryStringParameters') or {}


def extract_path_params(event: Dict[str, Any]) -> Dict[str, str]:
    """API Gatewayイベントからパスパラメータを抽出"""
    return event.get('pathParameters') or {}


# ============================================================================
# バリデーションパイプライン
# ============================================================================

def validate_params(params: Dict[str, Any], validators: Dict[str, callable]) -> Tuple[bool, List[str]]:
    """
    複数パラメータを一括検証
    Returns: (検証成功フラグ, エラーメッセージリスト)
    """
    errors = []

    for param, value in params.items():
        if param in validators and value is not None:
            if not validators[param](value):
                errors.append(f"Invalid {param}: {value}")

    return len(errors) == 0, errors


# ============================================================================
# DynamoDBクエリ関数
# ============================================================================

def query_all_devices() -> List[Dict]:
    """
    テーブル全体をスキャン - 大きなテーブルでは高コスト
    """
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Database query failed: {str(e)}")


def query_device_by_id(device_id: str, start_time: Optional[str] = None,
                       end_time: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """
    device_id（パーティションキー）でクエリ、timestampとstatusでフィルタ
    """
    try:
        key_condition = Key('device_id').eq(device_id)

        # timestampはソートキーなのでKeyConditionExpressionで効率的にフィルタ
        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        query_params = {'KeyConditionExpression': key_condition}

        # statusはFilterExpressionで後からフィルタ（キー条件後に適用）
        if status:
            query_params['FilterExpression'] = Attr('device_status').eq(status)

        response = table.query(**query_params)
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Device query failed: {str(e)}")


def query_room_by_id(room_id: str, start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> List[Dict]:
    """
    GSIを使用してroom_idでクエリ - 部屋内の全デバイスデータを取得
    """
    try:
        key_condition = Key('room_id').eq(room_id)

        # GSIのソートキー（timestamp）でフィルタ
        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

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
    GSIでroom_idクエリ後、device_idとstatusでフィルタ
    """
    try:
        key_condition = Key('room_id').eq(room_id)

        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        query_params = {
            'IndexName': GSI_NAME,
            'KeyConditionExpression': key_condition
        }

        # device_idとstatusはFilterExpressionで適用
        filter_expressions = [Attr('device_id').eq(device_id)]
        if status:
            filter_expressions.append(Attr('device_status').eq(status))

        if len(filter_expressions) == 1:
            query_params['FilterExpression'] = filter_expressions[0]
        else:
            query_params['FilterExpression'] = filter_expressions[0] & filter_expressions[1]

        response = table.query(**query_params)
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Room-device query failed: {str(e)}")


def query_device_room_info(device_id: str) -> List[str]:
    """
    特定デバイスが配置されている全部屋IDを取得
    room_idのみプロジェクションして通信量を削減
    """
    try:
        response = table.query(
            KeyConditionExpression=Key('device_id').eq(device_id),
            ProjectionExpression='room_id'
        )
        # setで重複除去してからソート
        rooms = set(item['room_id'] for item in response.get('Items', []))
        return sorted(list(rooms))
    except Exception as e:
        raise Exception(f"Device room query failed: {str(e)}")


def query_device_in_specific_room(device_id: str, room_id: str, start_time: Optional[str] = None,
                                  end_time: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """
    device_id（パーティションキー）でクエリ後、room_idでフィルタ
    デバイス中心のクエリではGSIより効率的
    """
    try:
        key_condition = Key('device_id').eq(device_id)

        if start_time and end_time:
            key_condition = key_condition & Key('timestamp').between(start_time, end_time)
        elif start_time:
            key_condition = key_condition & Key('timestamp').gte(start_time)
        elif end_time:
            key_condition = key_condition & Key('timestamp').lte(end_time)

        query_params = {'KeyConditionExpression': key_condition}

        # room_idとstatusをFilterExpressionで適用
        filter_expressions = [Attr('room_id').eq(room_id)]
        if status:
            filter_expressions.append(Attr('device_status').eq(status))

        if len(filter_expressions) == 1:
            query_params['FilterExpression'] = filter_expressions[0]
        else:
            query_params['FilterExpression'] = filter_expressions[0] & filter_expressions[1]

        response = table.query(**query_params)
        return response.get('Items', [])
    except Exception as e:
        raise Exception(f"Device-room query failed: {str(e)}")


def get_unique_rooms() -> List[str]:
    """
    全ユニーク部屋IDを取得 - room_idのみプロジェクションして通信量削減
    """
    try:
        response = table.scan(
            ProjectionExpression='room_id'
        )
        rooms = set(item['room_id'] for item in response.get('Items', []))
        return sorted(list(rooms))
    except Exception as e:
        raise Exception(f"Room scan failed: {str(e)}")


def get_unique_devices() -> List[str]:
    """
    全ユニークデバイスIDを取得 - device_idのみプロジェクションして通信量削減
    """
    try:
        response = table.scan(
            ProjectionExpression='device_id'
        )
        devices = set(item['device_id'] for item in response.get('Items', []))
        return sorted(list(devices))
    except Exception as e:
        raise Exception(f"Device scan failed: {str(e)}")


def get_devices_in_room(room_id: str) -> List[Dict]:
    """
    特定部屋の全ユニークデバイスを取得
    GSIでroom_idクエリ、device_idのみプロジェクション
    """
    try:
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('room_id').eq(room_id),
            ProjectionExpression='device_id'
        )
        devices = set(item['device_id'] for item in response.get('Items', []))
        return [{'device_id': device} for device in sorted(devices)]
    except Exception as e:
        raise Exception(f"Room devices query failed: {str(e)}")


# ============================================================================
# レスポンス整形関数
# ============================================================================

def decimal_to_float(obj):
    """
    DynamoDB Decimalオブジェクトをfloatに再帰変換
    DynamoDBの数値はDecimal型でJSON直列化できないため
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
    API Gateway標準レスポンス形式を作成、CORSヘッダー付き
    """
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

    if headers:
        default_headers.update(headers)

    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(decimal_to_float(body))  # Decimal変換してJSON化
    }


def create_error_response(status_code: int, message: str, errors: Optional[List] = None) -> Dict:
    """
    標準エラーレスポンス作成、詳細エラーリスト付き
    """
    error_body = {'error': message}
    if errors:
        error_body['details'] = errors

    return create_response(status_code, error_body)


# ============================================================================
# ルートハンドラー
# ============================================================================

def handle_root(event: Dict) -> Dict:
    """GET / - 全テレメトリーデータ取得（大量データでは高コスト）"""
    try:
        data = query_all_devices()
        return create_response(200, {'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve data: {str(e)}")


def handle_devices_list(event: Dict) -> Dict:
    """GET /devices - 全ユニークデバイスIDリスト取得"""
    try:
        devices = get_unique_devices()
        return create_response(200, {'devices': devices, 'count': len(devices)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve devices: {str(e)}")


def handle_device_detail(event: Dict) -> Dict:
    """GET /devices/{device_id} - 特定デバイスのテレメトリーデータ取得"""
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    device_id = path_params.get('device_id')

    # パスパラメータ検証
    validators = {'device_id': validate_device_id}
    is_valid, errors = validate_params({'device_id': device_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    # クエリパラメータ抽出
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    status = query_params.get('status')

    # クエリパラメータ検証
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
        data = query_device_by_id(device_id, start_time, end_time, status)
        return create_response(200, {'device_id': device_id, 'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve device data: {str(e)}")


def handle_device_rooms(event: Dict) -> Dict:
    """GET /devices/{device_id}/rooms - デバイスが配置されている全部屋取得"""
    path_params = extract_path_params(event)
    device_id = path_params.get('device_id')

    validators = {'device_id': validate_device_id}
    is_valid, errors = validate_params({'device_id': device_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    try:
        rooms = query_device_room_info(device_id)
        return create_response(200, {
            'device_id': device_id,
            'rooms': rooms,
            'count': len(rooms)
        })
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve device rooms: {str(e)}")


def handle_device_room_detail(event: Dict) -> Dict:
    """GET /devices/{device_id}/{room_id} - 特定デバイスの特定部屋データ取得"""
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    device_id = path_params.get('device_id')
    room_id = path_params.get('room_id')

    validators = {
        'device_id': validate_device_id,
        'room_id': validate_room_id
    }
    is_valid, errors = validate_params({'device_id': device_id, 'room_id': room_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    status = query_params.get('status')

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
        # デバイスパーティションキー使用で効率的
        data = query_device_in_specific_room(device_id, room_id, start_time, end_time, status)
        return create_response(200, {
            'device_id': device_id,
            'room_id': room_id,
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve device-room data: {str(e)}")


def handle_rooms_list(event: Dict) -> Dict:
    """GET /rooms - 全ユニーク部屋IDリスト取得"""
    try:
        rooms = get_unique_rooms()
        return create_response(200, {'rooms': rooms, 'count': len(rooms)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve rooms: {str(e)}")


def handle_room_detail(event: Dict) -> Dict:
    """GET /rooms/{room_id} - 特定部屋の全デバイステレメトリーデータ取得"""
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    room_id = path_params.get('room_id')

    validators = {'room_id': validate_room_id}
    is_valid, errors = validate_params({'room_id': room_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')

    optional_validators = {
        'start_time': validate_timestamp,
        'end_time': validate_timestamp
    }

    optional_params = {k: v for k, v in query_params.items() if v is not None}
    is_valid, errors = validate_params(optional_params, optional_validators)

    if not is_valid:
        return create_error_response(400, "Query parameter validation failed", errors)

    try:
        # GSI使用で部屋ベースクエリ
        data = query_room_by_id(room_id, start_time, end_time)
        return create_response(200, {'room_id': room_id, 'data': data, 'count': len(data)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve room data: {str(e)}")


def handle_room_devices(event: Dict) -> Dict:
    """GET /rooms/{room_id}/devices - 特定部屋のユニークデバイスリスト取得"""
    path_params = extract_path_params(event)
    room_id = path_params.get('room_id')

    validators = {'room_id': validate_room_id}
    is_valid, errors = validate_params({'room_id': room_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    try:
        devices = get_devices_in_room(room_id)
        return create_response(200, {'room_id': room_id, 'devices': devices, 'count': len(devices)})
    except Exception as e:
        return create_error_response(500, f"Failed to retrieve room devices: {str(e)}")


def handle_room_device_detail(event: Dict) -> Dict:
    """GET /rooms/{room_id}/{device_id} - 特定部屋の特定デバイスデータ取得"""
    path_params = extract_path_params(event)
    query_params = extract_query_params(event)

    room_id = path_params.get('room_id')
    device_id = path_params.get('device_id')

    validators = {
        'room_id': validate_room_id,
        'device_id': validate_device_id
    }
    is_valid, errors = validate_params({'room_id': room_id, 'device_id': device_id}, validators)

    if not is_valid:
        return create_error_response(400, "Validation failed", errors)

    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    status = query_params.get('status')

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
        # GSI使用で部屋ベースクエリ
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
# ルーティング設定
# ============================================================================

ROUTE_HANDLERS = {
    ('GET', '/'): handle_root,
    ('GET', '/devices'): handle_devices_list,
    ('GET', '/devices/{device_id}'): handle_device_detail,
    ('GET', '/devices/{device_id}/rooms'): handle_device_rooms,
    ('GET', '/devices/{device_id}/{room_id}'): handle_device_room_detail,
    ('GET', '/rooms'): handle_rooms_list,
    ('GET', '/rooms/{room_id}'): handle_room_detail,
    ('GET', '/rooms/{room_id}/devices'): handle_room_devices,
    ('GET', '/rooms/{room_id}/{device_id}'): handle_room_device_detail,
}


def handler(event: Dict, context: Any) -> Dict:
    """
    メインLambdaハンドラー - API Gatewayイベントを適切なハンドラーにルーティング
    """
    try:
        http_method = event.get('httpMethod', 'GET')
        resource_path = event.get('resource', '/')

        # ルート解決
        route_key = (http_method, resource_path)
        route_handler = ROUTE_HANDLERS.get(route_key)

        if not route_handler:
            return create_error_response(404, f"Route not found: {http_method} {resource_path}")

        return route_handler(event)

    except Exception as e:
        return create_error_response(500, f"Internal server error: {str(e)}")
