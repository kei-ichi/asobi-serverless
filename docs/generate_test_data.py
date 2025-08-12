import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ============================================================================
# 設定変数 - 実行前にこれらの値を変更してください
# ============================================================================

# DynamoDBテーブル名設定
DYNAMODB_TABLE_NAME = "IoTTelemetryTable"

# データ生成設定
NUM_SENSORS = 100
NUM_ROOMS = 10
SENSORS_PER_ROOM = 20
DATA_POINTS_PER_ROOM = 1000
ERROR_RATE = 0.25  # 25%

# 出力ファイル名設定
OUTPUT_FILES = {
    "dynamodb_format": "iot_test_data_dynamodb.json",
    "normal_format": "iot_test_data_normal.json",
    "batch_write_format": "batch_write_request.json"
}

# データ生成開始時刻
START_TIME = datetime(2025, 8, 1, 0, 0, 0)


# ============================================================================
# データ生成関数
# ============================================================================


def convert_dynamodb_to_normal_format(dynamodb_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    DynamoDB形式のデータを通常のJSON形式に変換
    """
    normal_data = []

    for item in dynamodb_data:
        normal_item = {}

        for key, value in item.items():
            if isinstance(value, dict):
                if "S" in value:  # String type
                    normal_item[key] = value["S"]
                elif "N" in value:  # Number type
                    normal_item[key] = float(value["N"])
                elif "NULL" in value and value["NULL"]:  # Null type
                    normal_item[key] = None
                else:
                    normal_item[key] = value
            else:
                normal_item[key] = value

        normal_data.append(normal_item)

    return normal_data


def generate_test_data() -> List[Dict[str, Any]]:
    """
    API仕様に基づくテストデータ生成

    仕様:
    - 設定可能なデータ件数
    - 設定可能なセンサー数・部屋数
    - 各部屋にセンサーを重複なしで配置
    - 設定可能なエラー率
    - sensor_errorの場合、temperatureはnull
    - 設定可能な開始時刻
    - 1秒間隔でインクリメント
    """
    print("データ生成設定を初期化中...")
    print(f"設定値:")
    print(f"  - センサー数: {NUM_SENSORS}")
    print(f"  - 部屋数: {NUM_ROOMS}")
    print(f"  - 部屋あたりセンサー数: {SENSORS_PER_ROOM}")
    print(f"  - 部屋あたりデータポイント数: {DATA_POINTS_PER_ROOM}")
    print(f"  - エラー率: {ERROR_RATE * 100}%")
    print(f"  - 開始時刻: {START_TIME}")
    print(f"  - DynamoDBテーブル名: {DYNAMODB_TABLE_NAME}")

    # センサーとルームのリスト生成（API仕様に合わせた命名）
    sensors = [f"sensor_{i:02d}" for i in range(1, NUM_SENSORS + 1)]
    rooms = [f"room_{i:03d}" for i in range(1, NUM_ROOMS + 1)]

    print(f"生成されたセンサー数: {len(sensors)}, 部屋数: {len(rooms)}")

    # 各部屋にセンサーを重複なしで配置
    print("センサーを部屋に配置中...")
    room_sensor_mapping = {}

    # センサーリストをシャッフルして順番をランダム化
    shuffled_sensors = sensors.copy()
    random.shuffle(shuffled_sensors)

    # 各部屋に指定数ずつ順番に割り当て
    for i, room in enumerate(rooms):
        start_idx = i * SENSORS_PER_ROOM
        end_idx = start_idx + SENSORS_PER_ROOM
        room_sensors = shuffled_sensors[start_idx:end_idx]
        room_sensor_mapping[room] = room_sensors
        print(f"  {room}: {len(room_sensors)}個のセンサーを配置")

    # テストデータ生成
    print("テストデータ生成中...")
    test_data = []
    current_timestamp = START_TIME
    total_generated = 0

    for room_idx, room in enumerate(rooms):
        print(f"  部屋 {room} ({room_idx + 1}/{len(rooms)}) のデータ生成中...")
        room_sensors = room_sensor_mapping[room]
        room_data_count = 0

        # 各部屋で指定数のデータポイント生成
        cycles = DATA_POINTS_PER_ROOM // SENSORS_PER_ROOM

        for cycle in range(cycles):
            if cycle % 10 == 0:  # 進捗表示
                print(f"    サイクル {cycle + 1}/{cycles} 完了")

            for sensor in room_sensors:
                if room_data_count >= DATA_POINTS_PER_ROOM:
                    break

                # エラー率に基づいてステータス決定
                is_error = random.random() < ERROR_RATE

                if is_error:
                    # sensor_errorの場合（temperatureはnull）
                    data_point = {
                        "device_id": {"S": sensor},
                        "room_id": {"S": room},
                        "timestamp": {"S": current_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")},
                        "temperature": {"NULL": True},
                        "device_status": {"S": "sensor_error"}
                    }
                else:
                    # 正常データの場合
                    temperature = round(random.uniform(4.0, 8.0), 1)
                    data_point = {
                        "device_id": {"S": sensor},
                        "room_id": {"S": room},
                        "timestamp": {"S": current_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")},
                        "temperature": {"N": str(temperature)},
                        "device_status": {"S": "ok"}
                    }

                test_data.append(data_point)
                current_timestamp += timedelta(seconds=1)
                room_data_count += 1
                total_generated += 1

        print(f"    {room}: {room_data_count}件のデータを生成完了")

    print(f"データ生成完了: 総計 {total_generated} 件")
    return test_data


def save_test_data_to_file(data: List[Dict[str, Any]], filename: str = None):
    """DynamoDB形式のテストデータをファイルに保存"""
    if filename is None:
        filename = OUTPUT_FILES["dynamodb_format"]

    print(f"DynamoDB形式データを {filename} に保存中...")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"DynamoDB形式テストデータを {filename} に保存しました。データ件数: {len(data)}")


def save_normal_format_data(data: List[Dict[str, Any]], filename: str = None):
    """通常のJSON形式でテストデータを保存"""
    if filename is None:
        filename = OUTPUT_FILES["normal_format"]

    print(f"通常形式データを {filename} に保存中...")
    normal_data = convert_dynamodb_to_normal_format(data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(normal_data, f, indent=2, ensure_ascii=False)
    print(f"通常形式テストデータを {filename} に保存しました。データ件数: {len(normal_data)}")

    return normal_data


def generate_batch_write_format(data: List[Dict[str, Any]], table_name: str = None) -> Dict[str, Any]:
    """DynamoDB batch-write-item形式に変換"""
    if table_name is None:
        table_name = DYNAMODB_TABLE_NAME

    print(f"DynamoDB batch-write形式に変換中... (テーブル名: {table_name})")
    batch_items = []

    for item in data:
        batch_item = {
            "PutRequest": {
                "Item": item
            }
        }
        batch_items.append(batch_item)

    print(f"batch-write形式変換完了: {len(batch_items)} アイテム")
    return {table_name: batch_items}


def save_batch_write_format(data: List[Dict[str, Any]], table_name: str = None, filename: str = None):
    """DynamoDB batch-write形式でファイルに保存"""
    if table_name is None:
        table_name = DYNAMODB_TABLE_NAME
    if filename is None:
        filename = OUTPUT_FILES["batch_write_format"]

    print(f"batch-write形式を {filename} に保存中... (テーブル名: {table_name})")
    batch_format = generate_batch_write_format(data, table_name)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(batch_format, f, indent=2, ensure_ascii=False)
    print(f"DynamoDB batch-write形式を {filename} に保存しました。")


def analyze_test_data(data: List[Dict[str, Any]]):
    """テストデータの統計情報を表示"""
    print("テストデータ分析中...")
    total_items = len(data)

    # デバイス別統計
    devices = set()
    rooms = set()
    error_count = 0
    ok_count = 0

    print("  基本統計を計算中...")
    for item in data:
        devices.add(item["device_id"]["S"])
        rooms.add(item["room_id"]["S"])

        if item["device_status"]["S"] == "sensor_error":
            error_count += 1
        else:
            ok_count += 1

    print("=== テストデータ統計 ===")
    print(f"総データ件数: {total_items}")
    print(f"ユニークデバイス数: {len(devices)}")
    print(f"ユニーク部屋数: {len(rooms)}")
    print(f"正常データ: {ok_count} ({ok_count / total_items * 100:.1f}%)")
    print(f"エラーデータ: {error_count} ({error_count / total_items * 100:.1f}%)")

    # 部屋別統計
    print("  部屋別統計を計算中...")
    room_stats = {}
    for item in data:
        room = item["room_id"]["S"]
        if room not in room_stats:
            room_stats[room] = {"total": 0, "error": 0, "devices": set()}

        room_stats[room]["total"] += 1
        room_stats[room]["devices"].add(item["device_id"]["S"])

        if item["device_status"]["S"] == "sensor_error":
            room_stats[room]["error"] += 1

    print("\n=== 部屋別統計 ===")
    for room, stats in sorted(room_stats.items()):
        error_rate = stats["error"] / stats["total"] * 100
        print(f"{room}: {stats['total']}件, {len(stats['devices'])}デバイス, エラー率{error_rate:.1f}%")

    # センサー重複チェック
    print("  センサー配置を検証中...")
    device_room_mapping = {}
    for item in data:
        device = item["device_id"]["S"]
        room = item["room_id"]["S"]

        if device not in device_room_mapping:
            device_room_mapping[device] = set()
        device_room_mapping[device].add(room)

    # 重複センサーの確認
    duplicated_sensors = []
    for device, rooms_set in device_room_mapping.items():
        if len(rooms_set) > 1:
            duplicated_sensors.append((device, list(rooms_set)))

    print("\n=== センサー配置検証 ===")
    if duplicated_sensors:
        print("WARNING: 重複センサーが検出されました:")
        for device, rooms_list in duplicated_sensors:
            print(f"  {device}: {rooms_list}")
    else:
        print("SUCCESS: 全センサーが単一の部屋にのみ配置されています")

    # 部屋別センサー配置の表示
    print("\n=== 部屋別センサー配置 ===")
    room_device_mapping = {}
    for device, rooms_set in device_room_mapping.items():
        room = list(rooms_set)[0]  # 各センサーは1つの部屋にのみ属する
        if room not in room_device_mapping:
            room_device_mapping[room] = []
        room_device_mapping[room].append(device)

    for room in sorted(room_device_mapping.keys()):
        sensors_in_room = sorted(room_device_mapping[room])
        print(f"{room}: {sensors_in_room}")


def compare_data_formats(dynamodb_data: List[Dict[str, Any]], normal_data: List[Dict[str, Any]]):
    """DynamoDB形式と通常形式のデータを比較"""
    print("\n=== データ形式比較 ===")

    if len(dynamodb_data) != len(normal_data):
        print(f"WARNING: データ件数が異なります: DynamoDB={len(dynamodb_data)}, Normal={len(normal_data)}")
        return

    print(f"SUCCESS: データ件数一致: {len(dynamodb_data)} 件")

    # サンプルデータの比較
    if dynamodb_data and normal_data:
        print("\n--- サンプルデータ比較 ---")
        print("DynamoDB形式:")
        print(json.dumps(dynamodb_data[0], indent=2, ensure_ascii=False))
        print("\n通常形式:")
        print(json.dumps(normal_data[0], indent=2, ensure_ascii=False))

        # データ整合性チェック
        sample_dynamo = dynamodb_data[0]
        sample_normal = normal_data[0]

        integrity_check = True

        # device_id チェック
        if sample_dynamo["device_id"]["S"] != sample_normal["device_id"]:
            print("WARNING: device_id が一致しません")
            integrity_check = False

        # room_id チェック
        if sample_dynamo["room_id"]["S"] != sample_normal["room_id"]:
            print("WARNING: room_id が一致しません")
            integrity_check = False

        # timestamp チェック
        if sample_dynamo["timestamp"]["S"] != sample_normal["timestamp"]:
            print("WARNING: timestamp が一致しません")
            integrity_check = False

        # temperature チェック
        if "NULL" in sample_dynamo["temperature"]:
            if sample_normal["temperature"] is not None:
                print("WARNING: temperature (null) が一致しません")
                integrity_check = False
        else:
            if float(sample_dynamo["temperature"]["N"]) != sample_normal["temperature"]:
                print("WARNING: temperature (数値) が一致しません")
                integrity_check = False

        # device_status チェック
        if sample_dynamo["device_status"]["S"] != sample_normal["device_status"]:
            print("WARNING: device_status が一致しません")
            integrity_check = False

        if integrity_check:
            print("SUCCESS: データ整合性チェック: 正常")
        else:
            print("ERROR: データ整合性チェック: 問題あり")


def print_configuration():
    """現在の設定を表示"""
    print("=== 現在の設定 ===")
    print(f"DynamoDBテーブル名: {DYNAMODB_TABLE_NAME}")
    print(f"センサー数: {NUM_SENSORS}")
    print(f"部屋数: {NUM_ROOMS}")
    print(f"部屋あたりセンサー数: {SENSORS_PER_ROOM}")
    print(f"部屋あたりデータポイント数: {DATA_POINTS_PER_ROOM}")
    print(f"総データポイント数: {NUM_ROOMS * DATA_POINTS_PER_ROOM}")
    print(f"エラー率: {ERROR_RATE * 100}%")
    print(f"開始時刻: {START_TIME}")
    print(f"出力ファイル:")
    for file_type, filename in OUTPUT_FILES.items():
        print(f"  - {file_type}: {filename}")


if __name__ == "__main__":
    print("IoTテレメトリーテストデータ生成開始...")
    print("=" * 50)

    # 設定表示
    print_configuration()
    print("=" * 50)

    try:
        # テストデータ生成
        test_data = generate_test_data()
        print(f"SUCCESS: テストデータ生成完了: {len(test_data)} 件")

        # 統計情報表示
        print("\n" + "=" * 50)
        analyze_test_data(test_data)

        # ファイル保存
        print("\n" + "=" * 50)
        print("ファイル保存開始...")

        # DynamoDB形式で保存
        save_test_data_to_file(test_data)

        # 通常形式で保存
        normal_data = save_normal_format_data(test_data)

        # batch-write形式で保存
        save_batch_write_format(test_data)

        # データ形式比較
        compare_data_formats(test_data, normal_data)

        print("\n" + "=" * 50)
        print("SUCCESS: テストデータ生成完了!")
        print("\n生成されたファイル:")
        print(f"  - {OUTPUT_FILES['dynamodb_format']} (DynamoDB形式)")
        print(f"  - {OUTPUT_FILES['normal_format']} (通常JSON形式)")
        print(f"  - {OUTPUT_FILES['batch_write_format']} (DynamoDB batch-write形式)")

        print(f"\nDynamoDBへのインポートコマンド:")
        print(
            f"aws dynamodb batch-write-item --request-items file://{OUTPUT_FILES['batch_write_format']} --region us-east-1")

    except Exception as e:
        print(f"ERROR: エラーが発生しました: {str(e)}")
        import traceback

        traceback.print_exc()
