import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime


class IoTAPISpecTester:
    """IoT テレメトリー API 仕様準拠テストクラス（バリデーションテスト含む）"""

    def __init__(self, base_url: str):
        """
        Args:
            base_url: APIのベースURL (例: https://abc123.execute-api.us-east-1.amazonaws.com/prod)
        """
        self.base_url = base_url.rstrip('/')
        self.test_results = []

        # テストデータから期待される値 - センサー数を200に変更
        self.expected_devices = [f"sensor_{i:02d}" for i in range(1, 201)]  # sensor_01 ~ sensor_200
        self.expected_rooms = [f"room_{i:03d}" for i in range(1, 11)]  # room_001 ~ room_010
        self.total_expected_items = 10000
        self.items_per_room = 1000
        self.devices_per_room = 20

    def make_request(self, endpoint: str, params: Optional[Dict] = None, expect_error: bool = False) -> Dict[str, Any]:
        """APIリクエストを実行"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)

            # エラーが期待される場合は、ステータスコードに関係なく成功とする
            if expect_error:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json() if response.content else {},
                    "response_time": response.elapsed.total_seconds()
                }

            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json(),
                "response_time": response.elapsed.total_seconds()
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                "response_data": getattr(e.response, 'json', lambda: {})() if hasattr(e,
                                                                                      'response') and e.response else {}
            }

    def validate_response_structure(self, data: Dict, expected_keys: List[str]) -> bool:
        """レスポンス構造の検証"""
        return all(key in data for key in expected_keys)

    def validate_telemetry_data_structure(self, items: List[Dict]) -> bool:
        """テレメトリーデータ構造の検証"""
        required_keys = ["device_id", "room_id", "timestamp", "device_status"]

        for item in items:
            if not all(key in item for key in required_keys):
                return False

            # temperatureはnullまたは数値
            if "temperature" in item:
                temp = item["temperature"]
                if temp is not None and not isinstance(temp, (int, float)):
                    return False

        return True

    def validate_error_response(self, data: Dict, expected_status: int, expected_error_message: str = None) -> List[
        str]:
        """
        エラーレスポンスの検証 - 大文字小文字を無視して比較
        """
        errors = []

        # エラーキーの存在チェック
        if "error" not in data:
            errors.append("Missing 'error' key in error response")
        elif expected_error_message:
            # 大文字小文字を無視してエラーメッセージを比較
            actual_error = data["error"].lower()
            expected_error = expected_error_message.lower()

            if expected_error not in actual_error:
                errors.append(f"Expected error message containing '{expected_error_message}', got '{data['error']}'")

        return errors

    # ============================================================================
    # テストケース：全データ取得
    # ============================================================================
    def test_root_endpoint(self) -> Dict[str, Any]:
        """3.1 全データ取得のテスト"""
        print("Testing 3.1: GET /")
        result = self.make_request("/")

        test_result = {
            "test_id": "3.1",
            "endpoint": "GET /",
            "description": "全データ取得",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["data", "count"]):
            test_result["errors"].append("Missing required keys: data, count")

        # データ件数チェック
        actual_count = data.get("count", 0)
        if actual_count != self.total_expected_items:
            test_result["errors"].append(f"Expected {self.total_expected_items} items, got {actual_count}")

        # データ構造チェック
        items = data.get("data", [])
        if not self.validate_telemetry_data_structure(items):
            test_result["errors"].append("Invalid telemetry data structure")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：デバイス一覧取得
    # ============================================================================
    def test_devices_list(self) -> Dict[str, Any]:
        """3.2 デバイス一覧取得のテスト"""
        print("Testing 3.2: GET /devices")
        result = self.make_request("/devices")

        test_result = {
            "test_id": "3.2",
            "endpoint": "GET /devices",
            "description": "デバイス一覧取得",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["devices", "count"]):
            test_result["errors"].append("Missing required keys: devices, count")

        # デバイス数チェック
        devices = data.get("devices", [])
        actual_count = len(devices)
        expected_count = len(self.expected_devices)

        if actual_count != expected_count:
            test_result["errors"].append(f"Expected {expected_count} devices, got {actual_count}")

        # countフィールドの整合性チェック
        if data.get("count") != actual_count:
            test_result["errors"].append(f"Count field mismatch: count={data.get('count')}, actual={actual_count}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（基本）
    # ============================================================================
    def test_device_detail_basic(self) -> Dict[str, Any]:
        """3.3.1 特定デバイスのテレメトリーデータ取得（基本）"""
        device_id = "sensor_01"
        print(f"Testing 3.3.1: GET /devices/{device_id}")
        result = self.make_request(f"/devices/{device_id}")

        test_result = {
            "test_id": "3.3.1",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（基本）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # ステータスコード 200 チェック（既に result["success"] で確認済み）

        # レスポンス構造チェック (device_id, data, count)
        if not self.validate_response_structure(data, ["device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, data, count")

        # device_id チェック
        if data.get("device_id") != device_id:
            test_result["errors"].append(f"Expected device_id {device_id}, got {data.get('device_id')}")

        # データ構造チェック
        items = data.get("data", [])
        if not self.validate_telemetry_data_structure(items):
            test_result["errors"].append("Invalid telemetry data structure")

        # データ整合性チェック（全てのデータが指定デバイスのものか）
        for item in items:
            if item.get("device_id") != device_id:
                test_result["errors"].append(f"Found data for different device: {item.get('device_id')}")
                break

        # 単一部屋配置チェック
        room_result = self.make_request(f"/devices/{device_id}/rooms")
        if room_result["success"]:
            room_data = room_result["data"]
            rooms = room_data.get("rooms", [])

            if len(rooms) != 1:
                test_result["errors"].append(f"Device {device_id} found in {len(rooms)} rooms, expected exactly 1")
            else:
                # 単一部屋配置の詳細情報を記録
                test_result["assigned_room"] = rooms[0]
        else:
            test_result["errors"].append(f"Failed to verify room assignment for {device_id}: {room_result['error']}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（時間範囲指定）
    # ============================================================================
    def test_device_detail_time_range(self) -> Dict[str, Any]:
        """3.3.2 特定デバイスのテレメトリーデータ取得（時間範囲指定）"""
        device_id = "sensor_01"
        params = {
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T00:10:00Z"
        }

        print(f"Testing 3.3.2: GET /devices/{device_id} with time range")
        result = self.make_request(f"/devices/{device_id}", params)

        test_result = {
            "test_id": "3.3.2",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（時間範囲指定）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        # ステータスコード 200 チェック
        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # 基本構造チェック
        if not self.validate_response_structure(data, ["device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, data, count")

        # 時間範囲内データチェック
        items = data.get("data", [])
        start_time = datetime.fromisoformat(params["start_time"].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(params["end_time"].replace('Z', '+00:00'))

        for item in items:
            item_time = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
            if not (start_time <= item_time <= end_time):
                test_result["errors"].append(f"Data outside time range: {item['timestamp']}")
                break

        # データ件数チェック（≤ 全データ件数）
        total_sensors = len(self.expected_devices)
        expected_data_points_per_sensor = self.total_expected_items // total_sensors

        total_data_result = self.make_request(f"/devices/{device_id}")
        if total_data_result["success"]:
            total_count = total_data_result["data"].get("count", 0)
            filtered_count = data.get("count", 0)

            # 期待値との比較
            if total_count != expected_data_points_per_sensor:
                test_result["errors"].append(
                    f"Total count ({total_count}) does not match expected ({expected_data_points_per_sensor})")

            # データ件数 ≤ 全データ件数
            if filtered_count > total_count:
                test_result["errors"].append(
                    f"Filtered data count ({filtered_count}) exceeds total count ({total_count})")

            # データ整合性チェック
            actual_items_count = len(items)
            if actual_items_count != filtered_count:
                test_result["errors"].append(
                    f"Count mismatch: reported {filtered_count}, actual items {actual_items_count}")

            # 結果情報を記録
            test_result["total_data_count"] = total_count
            test_result["filtered_data_count"] = filtered_count
            test_result["expected_total"] = expected_data_points_per_sensor

        else:
            test_result["errors"].append(f"Failed to get total data count for comparison: {total_data_result['error']}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（開始時刻のみ指定）
    # ============================================================================
    def test_device_detail_start_time_only(self) -> Dict[str, Any]:
        """3.3.3 特定デバイスのテレメトリーデータ取得（開始時刻のみ指定）"""
        device_id = "sensor_01"
        params = {"start_time": "2025-08-01T00:05:00Z"}

        print(f"Testing 3.3.3: GET /devices/{device_id} with start_time only")
        result = self.make_request(f"/devices/{device_id}", params)

        test_result = {
            "test_id": "3.3.3",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（開始時刻のみ指定）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # 基本構造チェック
        if not self.validate_response_structure(data, ["device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, data, count")

        # 開始時刻以降のデータかチェック
        items = data.get("data", [])
        start_time = datetime.fromisoformat(params["start_time"].replace('Z', '+00:00'))

        for item in items:
            item_time = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
            if item_time < start_time:
                test_result["errors"].append(f"Data before start_time: {item['timestamp']}")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（終了時刻のみ指定）
    # ============================================================================
    def test_device_detail_end_time_only(self) -> Dict[str, Any]:
        """3.3.4 特定デバイスのテレメトリーデータ取得（終了時刻のみ指定）"""
        device_id = "sensor_01"
        params = {"end_time": "2025-08-01T00:05:00Z"}

        print(f"Testing 3.3.4: GET /devices/{device_id} with end_time only")
        result = self.make_request(f"/devices/{device_id}", params)

        test_result = {
            "test_id": "3.3.4",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（終了時刻のみ指定）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # 基本構造チェック
        if not self.validate_response_structure(data, ["device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, data, count")

        # 終了時刻以前のデータかチェック
        items = data.get("data", [])
        end_time = datetime.fromisoformat(params["end_time"].replace('Z', '+00:00'))

        for item in items:
            item_time = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
            if item_time > end_time:
                test_result["errors"].append(f"Data after end_time: {item['timestamp']}")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（ステータスフィルタ）
    # ============================================================================
    def test_device_detail_status_filter(self) -> Dict[str, Any]:
        """3.3.5 特定デバイスのテレメトリーデータ取得（ステータスフィルタ）"""
        device_id = "sensor_01"
        params = {"status": "sensor_error"}

        print(f"Testing 3.3.5: GET /devices/{device_id} with status filter")
        result = self.make_request(f"/devices/{device_id}", params)

        test_result = {
            "test_id": "3.3.5",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（ステータスフィルタ）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        # ステータスコード 200 チェック
        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # 基本構造チェック
        if not self.validate_response_structure(data, ["device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, data, count")

        items = data.get("data", [])

        # 全データのステータス = sensor_error チェック
        for item in items:
            if item.get("device_status") != "sensor_error":
                test_result["errors"].append(f"Found non-error status: {item.get('device_status')}")
                break

            # temperature値 = null チェック
            if item.get("temperature") is not None:
                test_result["errors"].append("sensor_error status should have null temperature")
                break

        # エラー率 ≈ 25% (±5%) チェック
        total_data_result = self.make_request(f"/devices/{device_id}")
        if total_data_result["success"]:
            total_count = total_data_result["data"].get("count", 0)
            error_count = data.get("count", 0)

            if total_count > 0:
                error_rate = (error_count / total_count) * 100
                expected_rate = 25.0
                tolerance = 5.0

                if not (expected_rate - tolerance <= error_rate <= expected_rate + tolerance):
                    test_result["errors"].append(
                        f"Error rate {error_rate:.1f}% is outside expected range {expected_rate - tolerance}%-{expected_rate + tolerance}%"
                    )

                # 結果情報を記録
                test_result["total_count"] = total_count
                test_result["error_count"] = error_count
                test_result["error_rate"] = f"{error_rate:.1f}%"
                test_result["expected_range"] = f"{expected_rate - tolerance}%-{expected_rate + tolerance}%"
            else:
                test_result["errors"].append("No total data found for error rate calculation")
        else:
            test_result["errors"].append(f"Failed to get total data count: {total_data_result['error']}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスのテレメトリーデータ取得（複合条件）
    # ============================================================================
    def test_device_detail_complex_conditions(self) -> Dict[str, Any]:
        """3.3.6 特定デバイスのテレメトリーデータ取得（複合条件）"""
        device_id = "sensor_01"
        params = {
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T00:10:00Z",
            "status": "ok"
        }

        print(f"Testing 3.3.6: GET /devices/{device_id} with complex conditions")
        result = self.make_request(f"/devices/{device_id}", params)

        test_result = {
            "test_id": "3.3.6",
            "endpoint": f"GET /devices/{device_id}",
            "description": "特定デバイスのテレメトリーデータ取得（複合条件）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]
        items = data.get("data", [])

        # 時間範囲とステータスの両方をチェック
        start_time = datetime.fromisoformat(params["start_time"].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(params["end_time"].replace('Z', '+00:00'))

        for item in items:
            # 時間範囲チェック
            item_time = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
            if not (start_time <= item_time <= end_time):
                test_result["errors"].append(f"Data outside time range: {item['timestamp']}")
                break

            # ステータスチェック
            if item.get("device_status") != "ok":
                test_result["errors"].append(f"Found non-ok status: {item.get('device_status')}")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：デバイス配置部屋一覧取得
    # ============================================================================
    def test_device_rooms(self) -> Dict[str, Any]:
        """3.4 デバイス配置部屋一覧取得"""
        device_id = "sensor_01"
        print(f"Testing 3.4: GET /devices/{device_id}/rooms")
        result = self.make_request(f"/devices/{device_id}/rooms")

        test_result = {
            "test_id": "3.4",
            "endpoint": f"GET /devices/{device_id}/rooms",
            "description": "デバイス配置部屋一覧取得",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["device_id", "rooms", "count"]):
            test_result["errors"].append("Missing required keys: device_id, rooms, count")

        # device_idチェック
        if data.get("device_id") != device_id:
            test_result["errors"].append(f"Expected device_id {device_id}, got {data.get('device_id')}")

        # roomsが配列かチェック
        rooms = data.get("rooms", [])
        if not isinstance(rooms, list):
            test_result["errors"].append("rooms should be an array")

        # 重複なし配置のため、部屋数は1であるべき
        if len(rooms) != 1:
            test_result["errors"].append(f"Expected 1 room (no duplicate placement), got {len(rooms)}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["room_count"] = len(rooms)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスの特定部屋でのテレメトリーデータ取得（基本）
    # ============================================================================
    def test_device_room_detail_basic(self) -> Dict[str, Any]:
        """3.5.1 特定デバイスの特定部屋でのテレメトリーデータ取得（基本）"""
        device_id = "sensor_01"
        room_id = "room_001"
        print(f"Testing 3.5.1: GET /devices/{device_id}/{room_id}")
        result = self.make_request(f"/devices/{device_id}/{room_id}")

        test_result = {
            "test_id": "3.5.1",
            "endpoint": f"GET /devices/{device_id}/{room_id}",
            "description": "特定デバイスの特定部屋でのテレメトリーデータ取得（基本）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["device_id", "room_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, room_id, data, count")

        # device_id, room_idチェック
        if data.get("device_id") != device_id:
            test_result["errors"].append(f"Expected device_id {device_id}, got {data.get('device_id')}")

        if data.get("room_id") != room_id:
            test_result["errors"].append(f"Expected room_id {room_id}, got {data.get('room_id')}")

        # 全てのデータが指定デバイス・部屋のものかチェック
        items = data.get("data", [])
        for item in items:
            if item.get("device_id") != device_id:
                test_result["errors"].append(f"Found data for different device: {item.get('device_id')}")
                break
            if item.get("room_id") != room_id:
                test_result["errors"].append(f"Found data for different room: {item.get('room_id')}")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定デバイスの特定部屋でのテレメトリーデータ取得（存在しない組み合わせ）
    # ============================================================================
    def test_device_room_detail_nonexistent(self) -> Dict[str, Any]:
        """3.5.2 特定デバイスの特定部屋でのテレメトリーデータ取得（存在しない組み合わせ）"""
        import random

        device_id = "sensor_01"

        test_result = {
            "test_id": "3.5.2",
            "endpoint": f"GET /devices/{device_id}/[nonexistent_room]",
            "description": "特定デバイスの特定部屋でのテレメトリーデータ取得（存在しない組み合わせ）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        # sensor_01が実際に配置されている部屋を取得
        print(f"Testing 3.5.2: First getting rooms for {device_id}")
        rooms_result = self.make_request(f"/devices/{device_id}/rooms")

        if not rooms_result["success"]:
            test_result["errors"].append(f"Failed to get device rooms: {rooms_result['error']}")
            self.test_results.append(test_result)
            return test_result

        # sensor_01が配置されている部屋を特定
        device_rooms_data = rooms_result["data"]
        assigned_rooms = device_rooms_data.get("rooms", [])

        if not assigned_rooms:
            test_result["errors"].append("No rooms found for sensor_01")
            self.test_results.append(test_result)
            return test_result

        # 配置されている部屋のIDを抽出
        assigned_room_ids = []
        for room in assigned_rooms:
            if isinstance(room, dict):
                assigned_room_ids.append(room.get("room_id"))
            elif isinstance(room, str):
                assigned_room_ids.append(room)

        print(f"sensor_01 is assigned to rooms: {assigned_room_ids}")

        # self.expected_roomsから未配置の部屋を選択
        available_rooms = [room_id for room_id in self.expected_rooms if room_id not in assigned_room_ids]

        if not available_rooms:
            test_result["errors"].append(
                f"All expected rooms {self.expected_rooms} are assigned to sensor_01 - cannot test nonexistent combination")
            self.test_results.append(test_result)
            return test_result

        # ランダムに未配置の部屋を選択
        nonexistent_room_id = random.choice(available_rooms)
        print(
            f"Testing with nonexistent room: {nonexistent_room_id} (selected from {len(available_rooms)} available rooms)")

        # 存在しない組み合わせでテスト実行
        test_result["endpoint"] = f"GET /devices/{device_id}/{nonexistent_room_id}"
        result = self.make_request(f"/devices/{device_id}/{nonexistent_room_id}")

        # ステータスコード 200 チェック
        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック（基本構造は維持されるべき）
        if not self.validate_response_structure(data, ["device_id", "room_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: device_id, room_id, data, count")

        # データ件数 = 0 チェック
        actual_count = data.get("count", 0)
        if actual_count != 0:
            test_result["errors"].append(f"Expected 0 items for nonexistent combination, got {actual_count}")

        # データ配列も空であることを確認
        items = data.get("data", [])
        if len(items) != 0:
            test_result["errors"].append(f"Expected empty data array, got {len(items)} items")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count
        test_result["tested_room"] = nonexistent_room_id
        test_result["assigned_rooms"] = assigned_room_ids
        test_result["available_rooms_count"] = len(available_rooms)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：部屋一覧取得
    # ============================================================================
    def test_rooms_list(self) -> Dict[str, Any]:
        """3.6 部屋一覧取得"""

        print("Testing 3.6: GET /rooms")
        result = self.make_request("/rooms")

        test_result = {
            "test_id": "3.6",
            "endpoint": "GET /rooms",
            "description": "部屋一覧取得",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["rooms", "count"]):
            test_result["errors"].append("Missing required keys: rooms, count")

        # 部屋数チェック
        rooms = data.get("rooms", [])
        actual_count = len(rooms)
        expected_count = len(self.expected_rooms)

        if actual_count != expected_count:
            test_result["errors"].append(f"Expected {expected_count} rooms, got {actual_count}")

        # 部屋形式チェック
        invalid_room_formats = []

        for room in rooms:
            room_id = room.get("room_id") if isinstance(room, dict) else room

            if not self._validate_room_id_format(room_id):
                invalid_room_formats.append(room_id)

        if invalid_room_formats:
            test_result["errors"].append(
                f"Invalid room format found: {invalid_room_formats}. Expected room_XXX format (XXX > 0)")

        # countフィールドとrooms配列の整合性チェック
        response_count = data.get("count", 0)
        if response_count != actual_count:
            test_result["errors"].append(
                f"Count mismatch: response count={response_count}, actual rooms={actual_count}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count
        test_result["expected_count"] = expected_count

        self.test_results.append(test_result)
        return test_result

    def _validate_room_id_format(self, room_id: str) -> bool:
        """部屋ID形式の検証: room_number（numberは0より大きい3桁の数字）"""
        if not isinstance(room_id, str) or room_id.count('_') != 1:
            return False

        room_prefix, room_num = room_id.split('_')

        try:
            if room_prefix != 'room':
                return False

            num = int(room_num)
            return num > 0 and len(room_num) == 3 and room_num.isdigit()
        except ValueError:
            return False

    # ============================================================================
    # テストケース：特定部屋の全デバイステレメトリーデータ取得（基本）
    # ============================================================================
    def test_room_detail_basic(self) -> Dict[str, Any]:
        """3.7.1 特定部屋の全デバイステレメトリーデータ取得（基本）"""
        room_id = "room_001"

        print(f"Testing 3.7.1: GET /rooms/{room_id}")
        result = self.make_request(f"/rooms/{room_id}")

        test_result = {
            "test_id": "3.7.1",
            "endpoint": f"GET /rooms/{room_id}",
            "description": "特定部屋の全デバイステレメトリーデータ取得（基本）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["room_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: room_id, data, count")

        # room_idチェック
        if data.get("room_id") != room_id:
            test_result["errors"].append(f"Expected room_id {room_id}, got {data.get('room_id')}")

        # データ件数チェック
        actual_count = data.get("count", 0)
        if actual_count != self.items_per_room:
            test_result["errors"].append(f"Expected {self.items_per_room} items for room, got {actual_count}")

        # 全てのデータが指定部屋のものかチェック
        items = data.get("data", [])
        for item in items:
            if item.get("room_id") != room_id:
                test_result["errors"].append(f"Found data for different room: {item.get('room_id')}")
                break

        # ユニークデバイス数チェック
        unique_devices = set()
        for item in items:
            device_id = item.get("device_id")
            if device_id:
                unique_devices.add(device_id)

        actual_unique_devices = len(unique_devices)
        if actual_unique_devices != self.devices_per_room:
            test_result["errors"].append(
                f"Expected {self.devices_per_room} unique devices, got {actual_unique_devices}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count
        test_result["actual_unique_devices"] = actual_unique_devices
        test_result["expected_count"] = self.items_per_room
        test_result["expected_unique_devices"] = self.devices_per_room

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定部屋の全デバイステレメトリーデータ取得（時間範囲指定）
    # ============================================================================
    def test_room_detail_time_range(self) -> Dict[str, Any]:
        """3.7.2 特定部屋の全デバイステレメトリーデータ取得（時間範囲指定）"""
        room_id = "room_001"
        params = {
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T00:10:00Z"
        }

        print(f"Testing 3.7.2: GET /rooms/{room_id} with time range")
        result = self.make_request(f"/rooms/{room_id}", params)

        test_result = {
            "test_id": "3.7.2",
            "endpoint": f"GET /rooms/{room_id}",
            "description": "特定部屋の全デバイステレメトリーデータ取得（時間範囲指定）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # 基本構造チェック
        if not self.validate_response_structure(data, ["room_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: room_id, data, count")

        # 時間範囲内のデータかチェック
        items = data.get("data", [])
        start_time = datetime.fromisoformat(params["start_time"].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(params["end_time"].replace('Z', '+00:00'))

        for item in items:
            item_time = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
            if not (start_time <= item_time <= end_time):
                test_result["errors"].append(f"Data outside time range: {item['timestamp']}")
                break

        # データ件数は1000件以下であるべき
        actual_count = data.get("count", 0)
        if actual_count > self.items_per_room:
            test_result["errors"].append(f"Data count exceeds room limit: {actual_count} > {self.items_per_room}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定部屋のデバイス一覧取得
    # ============================================================================
    def test_room_devices(self) -> Dict[str, Any]:
        """3.8 特定部屋のデバイス一覧取得"""
        room_id = "room_001"
        print(f"Testing 3.8: GET /rooms/{room_id}/devices")
        result = self.make_request(f"/rooms/{room_id}/devices")

        test_result = {
            "test_id": "3.8",
            "endpoint": f"GET /rooms/{room_id}/devices",
            "description": "特定部屋のデバイス一覧取得",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["room_id", "devices", "count"]):
            test_result["errors"].append("Missing required keys: room_id, devices, count")

        # room_idチェック
        if data.get("room_id") != room_id:
            test_result["errors"].append(f"Expected room_id {room_id}, got {data.get('room_id')}")

        # デバイス数チェック（各部屋20デバイス）
        devices = data.get("devices", [])
        actual_count = len(devices)
        if actual_count != self.devices_per_room:
            test_result["errors"].append(f"Expected {self.devices_per_room} devices for room, got {actual_count}")

        # デバイス構造チェック
        device_ids = []
        for device in devices:
            if not isinstance(device, dict) or "device_id" not in device:
                test_result["errors"].append("Invalid device structure")
                break
            device_ids.append(device["device_id"])

        # デバイス重複チェック
        unique_device_ids = set(device_ids)
        if len(unique_device_ids) != len(device_ids):
            duplicates = [device_id for device_id in device_ids if device_ids.count(device_id) > 1]
            test_result["errors"].append(f"Duplicate devices found: {list(set(duplicates))}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = actual_count
        test_result["unique_devices"] = len(unique_device_ids)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定部屋の特定デバイステレメトリーデータ取得（基本）
    # ============================================================================
    def test_room_device_detail_basic(self) -> Dict[str, Any]:
        """3.9.1 特定部屋の特定デバイステレメトリーデータ取得（基本）"""
        room_id = "room_001"
        device_id = "sensor_01"
        print(f"Testing 3.9.1: GET /rooms/{room_id}/{device_id}")
        result = self.make_request(f"/rooms/{room_id}/{device_id}")

        test_result = {
            "test_id": "3.9.1",
            "endpoint": f"GET /rooms/{room_id}/{device_id}",
            "description": "特定部屋の特定デバイステレメトリーデータ取得（基本）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]

        # レスポンス構造チェック
        if not self.validate_response_structure(data, ["room_id", "device_id", "data", "count"]):
            test_result["errors"].append("Missing required keys: room_id, device_id, data, count")

        # room_id, device_idチェック
        if data.get("room_id") != room_id:
            test_result["errors"].append(f"Expected room_id {room_id}, got {data.get('room_id')}")

        if data.get("device_id") != device_id:
            test_result["errors"].append(f"Expected device_id {device_id}, got {data.get('device_id')}")

        # 全てのデータが指定部屋・デバイスのものかチェック
        items = data.get("data", [])
        for item in items:
            if item.get("room_id") != room_id:
                test_result["errors"].append(f"Found data for different room: {item.get('room_id')}")
                break
            if item.get("device_id") != device_id:
                test_result["errors"].append(f"Found data for different device: {item.get('device_id')}")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：特定部屋の特定デバイステレメトリーデータ取得（ステータスフィルタ）
    # ============================================================================
    def test_room_device_detail_status_filter(self) -> Dict[str, Any]:
        """3.9.2 特定部屋の特定デバイステレメトリーデータ取得（ステータスフィルタ）"""
        room_id = "room_001"
        device_id = "sensor_01"
        params = {"status": "sensor_error"}

        print(f"Testing 3.9.2: GET /rooms/{room_id}/{device_id} with status filter")
        result = self.make_request(f"/rooms/{room_id}/{device_id}", params)

        test_result = {
            "test_id": "3.9.2",
            "endpoint": f"GET /rooms/{room_id}/{device_id}",
            "description": "特定部屋の特定デバイステレメトリーデータ取得（ステータスフィルタ）",
            "test_type": "positive",
            "success": False,
            "errors": [],
            "params": params
        }

        if not result["success"]:
            test_result["errors"].append(f"Request failed: {result['error']}")
            self.test_results.append(test_result)
            return test_result

        data = result["data"]
        items = data.get("data", [])

        # 全てのデータが指定ステータスかチェック
        for item in items:
            if item.get("device_status") != "sensor_error":
                test_result["errors"].append(f"Found non-error status: {item.get('device_status')}")
                break

            # sensor_errorの場合、temperatureはnullであるべき
            if item.get("temperature") is not None:
                test_result["errors"].append("sensor_error status should have null temperature")
                break

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["response_time"] = result["response_time"]
        test_result["actual_count"] = data.get("count", 0)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：センサー重複チェック
    # ============================================================================
    def test_sensor_duplicate_check(self) -> Dict[str, Any]:
        """5.1 センサー重複チェックテスト - シンプル版"""
        print("Testing 5.1: Sensor Duplicate Check")

        test_result = {
            "test_id": "5.1",
            "endpoint": "Multiple GET /devices/{device_id}/rooms",
            "description": "センサー重複チェック（各センサーが1つの部屋にのみ属することを確認）",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        # 複数のセンサーの部屋配置を確認（サンプルテスト）
        test_devices = ["sensor_01", "sensor_02", "sensor_03", "sensor_21", "sensor_41"]
        device_room_mapping = {}

        for device_id in test_devices:
            result = self.make_request(f"/devices/{device_id}/rooms")

            if not result["success"]:
                test_result["errors"].append(f"Failed to get rooms for {device_id}: {result['error']}")
                continue

            data = result["data"]
            rooms = data.get("rooms", [])
            device_room_mapping[device_id] = rooms

            # 各センサーは正確に1つの部屋にのみ属するべき
            if len(rooms) != 1:
                test_result["errors"].append(f"Device {device_id} found in {len(rooms)} rooms, expected exactly 1")

        # 部屋配置の詳細情報を追加（デバッグ用）
        room_to_devices = {}
        for device_id, rooms in device_room_mapping.items():
            if len(rooms) == 1:
                room_id = rooms[0]
                if room_id not in room_to_devices:
                    room_to_devices[room_id] = []
                room_to_devices[room_id].append(device_id)

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["device_count"] = len(test_devices)
        test_result["room_mapping"] = device_room_mapping
        test_result["room_to_devices_mapping"] = room_to_devices

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：部屋別センサー数チェック
    # ============================================================================
    def test_room_sensor_count_check(self) -> Dict[str, Any]:
        """5.2 部屋別センサー数チェックテスト"""
        print("Testing 5.2: Room Sensor Count Check")

        test_result = {
            "test_id": "5.2",
            "endpoint": "Multiple GET /rooms/{room_id}/devices",
            "description": "部屋別センサー数チェック",
            "test_type": "positive",
            "success": False,
            "errors": []
        }

        # 各部屋のセンサー数を確認
        room_sensor_counts = {}

        for room_id in self.expected_rooms:
            result = self.make_request(f"/rooms/{room_id}/devices")

            if not result["success"]:
                test_result["errors"].append(f"Failed to get devices for {room_id}: {result['error']}")
                continue

            data = result["data"]
            devices = data.get("devices", [])
            actual_count = len(devices)
            room_sensor_counts[room_id] = actual_count

            # 各部屋に20個のセンサーがあるべき
            if actual_count != self.devices_per_room:
                test_result["errors"].append(
                    f"Room {room_id} has {actual_count} devices, expected {self.devices_per_room}")

        test_result["success"] = len(test_result["errors"]) == 0
        test_result["room_counts"] = room_sensor_counts
        test_result["total_rooms_checked"] = len(self.expected_rooms)

        self.test_results.append(test_result)
        return test_result

    # ============================================================================
    # テストケース：デバイスIDバリデーションエラー
    # ============================================================================
    def test_invalid_device_id_formats(self) -> List[Dict[str, Any]]:
        """6.2 デバイスIDバリデーションエラーテスト"""
        print("Testing 6.2: Invalid Device ID Formats")

        invalid_device_ids = [
            ("sensor01", "アンダースコアなし"),
            ("sensor_01_temp", "複数アンダースコア"),
            ("sensor_00", "数値部分が0"),
            ("sensor_-1", "負の数値"),
            ("sensor_abc", "数値部分が文字列"),
            ("_01", "空のデバイスタイプ")
        ]

        test_results = []

        for invalid_id, description in invalid_device_ids:
            print(f"  Testing invalid device_id: {invalid_id} ({description})")
            result = self.make_request(f"/devices/{invalid_id}", expect_error=True)

            test_result = {
                "test_id": f"6.2.{len(test_results) + 1}",
                "endpoint": f"GET /devices/{invalid_id}",
                "description": f"デバイスIDバリデーションエラー: {description}",
                "test_type": "negative",
                "success": False,
                "errors": []
            }

            # 400エラーが返されることを期待
            if result["status_code"] != 400:
                test_result["errors"].append(f"Expected status 400, got {result['status_code']}")

            # エラーレスポンスの構造チェック（大文字小文字を無視）
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                validation_errors = self.validate_error_response(error_data, 400, "Validation failed")
                test_result["errors"].extend(validation_errors)
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テストケース：部屋IDバリデーションエラー
    # ============================================================================
    def test_invalid_room_id_formats(self) -> List[Dict[str, Any]]:
        """6.3 部屋IDバリデーションエラーテスト"""
        print("Testing 6.3: Invalid Room ID Formats")

        invalid_room_tests = [
            ("/rooms/%20", "スペースのみの部屋ID", "room_id with spaces only"),
            ("/rooms/_", "アンダースコアのみ", "room_id with underscore only"),
            ("/rooms/room01", "2桁の数値部分", "room_id with 2-digit number"),
            ("/rooms/room_0001", "4桁の数値部分", "room_id with 4-digit number"),
            ("/rooms/room_000", "数値部分が0", "room_id with zero number"),
            ("/rooms/room_-01", "負の数値", "room_id with negative number"),
            ("/rooms/room_abc", "数値部分が文字列", "room_id with non-numeric part"),
            ("/rooms/room__001", "複数のアンダースコア", "room_id with multiple underscores"),
            ("/rooms/room001", "アンダースコアなし", "room_id without underscore"),
            ("/rooms/office_001", "不正なプレフィックス", "room_id with wrong prefix"),
            ("/rooms/_001", "空のプレフィックス", "room_id with empty prefix"),
            ("/rooms/room_", "空の数値部分", "room_id with empty number part"),
            ("/rooms/room_01a", "数値部分に文字が混在", "room_id with mixed alphanumeric"),
            ("/rooms/room_1.0", "小数点を含む数値", "room_id with decimal number"),
            ("/rooms/ROOM_001", "大文字のプレフィックス", "room_id with uppercase prefix"),
            ("/rooms/room_+01", "正の符号付き数値", "room_id with positive sign"),
            ("/rooms/", "空の部屋ID", "empty room_id"),
            ("/rooms/room_00a", "先頭0で文字が混在", "room_id with leading zero and letter")
        ]

        test_results = []

        for endpoint, description, test_desc in invalid_room_tests:
            print(f"  Testing invalid room_id: {endpoint} ({description})")
            result = self.make_request(endpoint, expect_error=True)

            test_result = {
                "test_id": f"6.3.{len(test_results) + 1}",
                "endpoint": f"GET {endpoint}",
                "description": f"部屋IDバリデーションエラー: {description}",
                "test_type": "negative",
                "success": False,
                "errors": []
            }

            # 400または404エラーが返されることを期待
            if result["status_code"] not in [400, 404]:
                test_result["errors"].append(f"Expected status 400 or 404, got {result['status_code']}")

            # エラーレスポンスの構造チェック
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                if "error" not in error_data:
                    test_result["errors"].append("Missing 'error' key in error response")
                else:
                    # バリデーションエラーメッセージの確認（大文字小文字を無視）
                    error_message = error_data["error"].lower()
                    if "validation" not in error_message and "invalid" not in error_message:
                        # 一部のケースでは404が適切な場合もある
                        if result["status_code"] != 404:
                            test_result["errors"].append(
                                f"Expected validation error message, got: {error_data['error']}")
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テストケース：タイムスタンプバリデーションエラー
    # ============================================================================
    def test_invalid_timestamp_formats(self) -> List[Dict[str, Any]]:
        """6.4 タイムスタンプバリデーションエラーテスト"""
        print("Testing 6.4: Invalid Timestamp Formats")

        invalid_timestamps = [
            ("2025-13-01T00:00:00Z", "不正な月"),
            ("2025-08-01T25:00:00Z", "不正な時刻"),
            ("2025/08/01 10:00:00", "ISO形式でない"),
            ("2025-08-01T10:00:00", "タイムゾーン指定なし"),
            ("invalid_timestamp", "完全に不正な文字列"),
            ("2025-02-30T10:00:00Z", "存在しない日付")
        ]

        test_results = []
        device_id = "sensor_01"

        for invalid_timestamp, description in invalid_timestamps:
            print(f"  Testing invalid timestamp: {invalid_timestamp} ({description})")
            params = {"start_time": invalid_timestamp}
            result = self.make_request(f"/devices/{device_id}", params, expect_error=True)

            test_result = {
                "test_id": f"6.4.{len(test_results) + 1}",
                "endpoint": f"GET /devices/{device_id}",
                "description": f"タイムスタンプバリデーションエラー: {description}",
                "test_type": "negative",
                "success": False,
                "errors": [],
                "params": params
            }

            # 400エラーが返されることを期待
            if result["status_code"] != 400:
                test_result["errors"].append(f"Expected status 400, got {result['status_code']}")

            # エラーレスポンスの構造チェック（大文字小文字を無視）
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                validation_errors = self.validate_error_response(error_data, 400, "validation failed")
                test_result["errors"].extend(validation_errors)
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テストケース：ステータスバリデーションエラー
    # ============================================================================
    def test_invalid_status_values(self) -> List[Dict[str, Any]]:
        """6.5 ステータスバリデーションエラーテスト"""
        print("Testing 6.5: Invalid Status Values")

        invalid_statuses = [
            ("broken", "存在しないステータス"),
            ("OK", "大文字小文字混在"),
            ("1", "数値ステータス"),
            ("error", "部分的に正しいが無効"),
            ("SENSOR_ERROR", "全て大文字")
        ]

        test_results = []
        device_id = "sensor_01"

        for invalid_status, description in invalid_statuses:
            print(f"  Testing invalid status: {invalid_status} ({description})")
            params = {"status": invalid_status}
            result = self.make_request(f"/devices/{device_id}", params, expect_error=True)

            test_result = {
                "test_id": f"6.5.{len(test_results) + 1}",
                "endpoint": f"GET /devices/{device_id}",
                "description": f"ステータスバリデーションエラー: {description}",
                "test_type": "negative",
                "success": False,
                "errors": [],
                "params": params
            }

            # 400エラーが返されることを期待
            if result["status_code"] != 400:
                test_result["errors"].append(f"Expected status 400, got {result['status_code']}")

            # エラーレスポンスの構造チェック（大文字小文字を無視）
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                validation_errors = self.validate_error_response(error_data, 400, "validation failed")
                test_result["errors"].extend(validation_errors)
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テストケース：複合バリデーションエラー
    # ============================================================================
    def test_complex_validation_errors(self) -> List[Dict[str, Any]]:
        """6.6 複合バリデーションエラーテスト"""
        print("Testing 6.6: Complex Validation Errors")

        complex_error_tests = [
            ("invalid_device", {"start_time": "invalid_time"}, "デバイスID + タイムスタンプエラー"),
            ("bad_device", {"start_time": "bad_time", "end_time": "bad_end", "status": "bad_status"},
             "全パラメータエラー")
        ]

        test_results = []

        for device_id, params, description in complex_error_tests:
            print(f"  Testing complex validation: {device_id} with {params} ({description})")
            result = self.make_request(f"/devices/{device_id}", params, expect_error=True)

            test_result = {
                "test_id": f"6.6.{len(test_results) + 1}",
                "endpoint": f"GET /devices/{device_id}",
                "description": f"複合バリデーションエラー: {description}",
                "test_type": "negative",
                "success": False,
                "errors": [],
                "params": params
            }

            # 400エラーが返されることを期待
            if result["status_code"] != 400:
                test_result["errors"].append(f"Expected status 400, got {result['status_code']}")

            # エラーレスポンスの構造チェック（大文字小文字を無視）
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                validation_errors = self.validate_error_response(error_data, 400, "Validation failed")
                test_result["errors"].extend(validation_errors)
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テストケース：存在しないエンドポイント
    # ============================================================================
    def test_nonexistent_routes(self) -> List[Dict[str, Any]]:
        """6.7 存在しないエンドポイントテスト"""
        print("Testing 6.7: Non-existent Routes")

        invalid_routes = [
            ("/nonexistent", "存在しないパス"),
            ("/devices/sensor_01/room_001/invalid", "存在しないサブパス"),
            ("/rooms/room_001/sensor_01/invalid", "存在しない部屋サブパス")
        ]

        test_results = []

        for route, description in invalid_routes:
            print(f"  Testing non-existent route: {route} ({description})")
            result = self.make_request(route, expect_error=True)

            test_result = {
                "test_id": f"6.7.{len(test_results) + 1}",
                "endpoint": f"GET {route}",
                "description": f"存在しないエンドポイント: {description}",
                "test_type": "negative",
                "success": False,
                "errors": []
            }

            # 404エラーが返されることを期待
            if result["status_code"] != 404:
                test_result["errors"].append(f"Expected status 404, got {result['status_code']}")

            # エラーレスポンスの構造チェック
            if result.get("data") or result.get("response_data"):
                error_data = result.get("data") or result.get("response_data")
                validation_errors = self.validate_error_response(error_data, 403, "Missing Authentication Token")
                test_result["errors"].extend(validation_errors)
            else:
                test_result["errors"].append("No error response data received")

            test_result["success"] = len(test_result["errors"]) == 0
            test_result["response_time"] = result.get("response_time", 0)

            test_results.append(test_result)
            self.test_results.append(test_result)

        return test_results

    # ============================================================================
    # テスト実行制御
    # ============================================================================
    def run_all_tests(self) -> Dict[str, Any]:
        """全てのAPI仕様テスト（正常系 + バリデーションエラー系）を実行"""
        print("=== IoT API 包括的テスト開始 ===\n")
        start_time = time.time()

        # 正常系テスト実行
        print("--- 正常系テスト ---")
        self.test_root_endpoint()  # 3.1
        self.test_devices_list()  # 3.2
        self.test_device_detail_basic()  # 3.3.1
        self.test_device_detail_time_range()  # 3.3.2
        self.test_device_detail_start_time_only()  # 3.3.3
        self.test_device_detail_end_time_only()  # 3.3.4
        self.test_device_detail_status_filter()  # 3.3.5
        self.test_device_detail_complex_conditions()  # 3.3.6
        self.test_device_rooms()  # 3.4
        self.test_device_room_detail_basic()  # 3.5.1
        self.test_device_room_detail_nonexistent()  # 3.5.2
        self.test_rooms_list()  # 3.6
        self.test_room_detail_basic()  # 3.7.1
        self.test_room_detail_time_range()  # 3.7.2
        self.test_room_devices()  # 3.8
        self.test_room_device_detail_basic()  # 3.9.1
        self.test_room_device_detail_status_filter()  # 3.9.2

        # データ整合性テスト実行
        print("\n--- データ整合性テスト ---")
        self.test_sensor_duplicate_check()  # 5.1
        self.test_room_sensor_count_check()  # 5.2

        # バリデーションエラーテスト実行
        print("\n--- バリデーションエラーテスト ---")
        self.test_invalid_device_id_formats()  # 6.2
        self.test_invalid_room_id_formats()  # 6.3
        self.test_invalid_timestamp_formats()  # 6.4
        self.test_invalid_status_values()  # 6.5
        self.test_complex_validation_errors()  # 6.6
        self.test_nonexistent_routes()  # 6.7

        end_time = time.time()
        total_time = end_time - start_time

        # テスト結果サマリー
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests

        # テストタイプ別集計
        positive_tests = [r for r in self.test_results if r.get("test_type") == "positive"]
        negative_tests = [r for r in self.test_results if r.get("test_type") == "negative"]

        positive_success = sum(1 for r in positive_tests if r["success"])
        negative_success = sum(1 for r in negative_tests if r["success"])

        summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
            "positive_tests": {
                "total": len(positive_tests),
                "success": positive_success,
                "success_rate": (positive_success / len(positive_tests)) * 100 if positive_tests else 0
            },
            "negative_tests": {
                "total": len(negative_tests),
                "success": negative_success,
                "success_rate": (negative_success / len(negative_tests)) * 100 if negative_tests else 0
            },
            "total_time": total_time,
            "test_results": self.test_results
        }

        print(f"\n=== 包括的テスト結果サマリー ===")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {successful_tests}")
        print(f"失敗: {failed_tests}")
        print(f"全体成功率: {summary['success_rate']:.1f}%")
        print(
            f"正常系テスト: {positive_success}/{len(positive_tests)} ({summary['positive_tests']['success_rate']:.1f}%)")
        print(
            f"バリデーションテスト: {negative_success}/{len(negative_tests)} ({summary['negative_tests']['success_rate']:.1f}%)")
        print(f"実行時間: {total_time:.2f}秒")

        # 失敗したテストの詳細表示
        if failed_tests > 0:
            print(f"\n=== 失敗したテスト ===")
            for result in self.test_results:
                if not result["success"]:
                    test_type = result.get("test_type", "unknown")
                    print(f"- [{test_type}] {result['test_id']} {result['endpoint']}: {', '.join(result['errors'])}")

        return summary

    def save_test_results(self, filename: str = "comprehensive_api_test_results.json"):
        """テスト結果をファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        print(f"包括的テスト結果を {filename} に保存しました。")


# ============================================================================
# メイン実行部
# ============================================================================
if __name__ == "__main__":
    # APIのベースURLを設定（実際のURLに変更してください）
    API_BASE_URL = "https://your-api-gateway-url"

    # テスト実行
    tester = IoTAPISpecTester(API_BASE_URL)
    results = tester.run_all_tests()

    # 結果をファイルに保存
    tester.save_test_results()
