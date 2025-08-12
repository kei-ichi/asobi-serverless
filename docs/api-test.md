*戦術的テストケース番号修正プロトコル開始*

了解しました。テストケース番号の不整合を修正いたします。

```markdown
# 結合テスト仕様書

## テストデータ準備

```shell
python generate_test_data.py
```

```yaml
# 生成されたbatch_write_request.jsonを使用
aws dynamodb batch-write-item --request-items file://batch_write_request.json --region us-east-1
```

## 自動テスト

```yaml
# test_api_spec.py内のAPI_BASE_URLを実際のURLに変更してから実行
python test_api_spec.py
```

## テストケース

# IoT テレメトリー API テストガイド

## 概要

このドキュメントでは、IoTテレメトリーAPIのテストデータ生成方法と、各API仕様の手動・自動テスト手順について説明します。

---

## 1. テストデータ生成 (`generate_test_data.py`)

### 1.1 動作原理

`generate_test_data.py`は以下の仕様に基づいてテストデータを生成します：

**データ仕様:**
- **総データ件数**: 10,000件
- **センサー数**: 100個 (`sensor_01` ~ `sensor_100`)
- **部屋数**: 10個 (`room_001` ~ `room_010`)
- **部屋あたりのセンサー**: 20個（重複なし配置）
- **部屋あたりのデータ**: 1,000件
- **エラー率**: 25% (`sensor_error`ステータス)
- **開始時刻**: `2025-08-01T00:00:00Z`
- **時間間隔**: 1秒ずつインクリメント

### 1.2 生成プロセス

1. **センサー・部屋リスト作成**
   ```python
   sensors = [f"sensor_{i:02d}" for i in range(1, 101)]  # sensor_01 ~ sensor_100
   rooms = [f"room_{i:03d}" for i in range(1, 11)]       # room_001 ~ room_010
   ```

2. **部屋へのセンサー配置（重複なし）**
   ```python
   # センサーリストをシャッフルして順番をランダム化
   shuffled_sensors = sensors.copy()
   random.shuffle(shuffled_sensors)
   
   # 各部屋に20個ずつ順番に割り当て（重複なし）
   for i, room in enumerate(rooms):
       start_idx = i * SENSORS_PER_ROOM  # 0, 20, 40, 60, ...
       end_idx = start_idx + SENSORS_PER_ROOM  # 20, 40, 60, 80, ...
       room_sensors = shuffled_sensors[start_idx:end_idx]
       room_sensor_mapping[room] = room_sensors
   ```

3. **センサー配置の特徴**
   - 100個のセンサーを10部屋に均等分配
   - 各センサーは**必ず1つの部屋にのみ**属する
   - シャッフルによりランダム性を保持
   - 重複は完全に排除される

4. **データ生成ループ**
   - 各部屋で1,000件のデータを生成
   - 25%の確率で`sensor_error`ステータス
   - `sensor_error`の場合、`temperature`は`null`
   - 正常データの場合、温度は4.0-8.0度の範囲でランダム生成

5. **出力形式**
   - **標準JSON**: `iot_test_data.json`
   - **DynamoDB形式**: `batch_write_request.json`

### 1.3 実行方法

```bash
python generate_test_data.py
```

### 1.4 DynamoDBへのデータインポート

```bash
aws dynamodb batch-write-item --request-items file://batch_write_request.json --region us-east-1
```

### 1.5 センサー配置例

```
room_001: [sensor_23, sensor_45, sensor_67, sensor_12, sensor_89, ...]  # 20個
room_002: [sensor_34, sensor_56, sensor_78, sensor_90, sensor_11, ...]  # 20個
room_003: [sensor_01, sensor_33, sensor_55, sensor_77, sensor_99, ...]  # 20個
...
room_010: [sensor_02, sensor_24, sensor_46, sensor_68, sensor_88, ...]  # 20個
```

---

## 2. API テスト仕様

### 2.1 テスト環境設定

**前提条件:**
- テストデータがDynamoDBにインポート済み
- APIエンドポイントが稼働中
- `curl`コマンドが利用可能

**テスト用URL設定:**
```bash
export API_BASE_URL="https://your-api-gateway-url"
```

---

## 3. 正常系テストケース

### 3.1 全データ取得テスト

**API仕様:** `GET /`  
**用途:** システム内の全てのテレメトリーデータを一括取得

#### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

#### 期待結果
- ステータスコード: 200
- レスポンス構造: `{"data": [...], "count": 10000}`
- データ件数: 10,000件

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| データ件数 | 10,000 | ☐ Pass ☐ Fail | |
| レスポンス構造 | data, count キー存在 | ☐ Pass ☐ Fail | |
| レスポンス時間 | < 30秒 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.2 デバイス一覧取得テスト

**API仕様:** `GET /devices`  
**用途:** システムに登録されている全ての一意なデバイスIDのリストを取得

#### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

#### 期待結果
- ステータスコード: 200
- レスポンス構造: `{"devices": [...], "count": 100}`
- デバイス数: 100個

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| デバイス数 | 100 | ☐ Pass ☐ Fail | |
| レスポンス構造 | devices, count キー存在 | ☐ Pass ☐ Fail | |
| デバイス形式 | sensor_XX 形式 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.3 特定デバイスのテレメトリーデータ取得テスト

#### 3.3.1 基本的な取得

**API仕様:** `GET /devices/{device_id}`  
**用途:** 指定したデバイスのテレメトリーデータを取得

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| device_id | sensor_01 | ☐ Pass ☐ Fail | |
| データ構造 | device_id, data, count | ☐ Pass ☐ Fail | |
| データ整合性 | 全データがsensor_01 | ☐ Pass ☐ Fail | |
| 単一部屋配置 | 1つの部屋のみ | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.3.2 時間範囲指定テスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-08-01T00:00:00Z&end_time=2025-08-01T00:10:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 時間範囲内データ | 2025-08-01T00:00:00Z ~ 2025-08-01T00:10:00Z | ☐ Pass ☐ Fail | |
| データ件数 | ≤ 全データ件数 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.3.3 開始時刻のみ指定テスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-08-01T00:05:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 開始時刻以降データ | ≥ 2025-08-01T00:05:00Z | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.3.4 終了時刻のみ指定テスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?end_time=2025-08-01T00:05:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 終了時刻以前データ | ≤ 2025-08-01T00:05:00Z | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.3.5 ステータスフィルタテスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=sensor_error" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 全データのステータス | sensor_error | ☐ Pass ☐ Fail | |
| temperature値 | null | ☐ Pass ☐ Fail | |
| エラー率 | 約25% | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.3.6 複合条件テスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-08-01T00:00:00Z&end_time=2025-08-01T00:10:00Z&status=ok" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 時間範囲 + ステータス | 条件を満たすデータのみ | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.4 デバイス配置部屋一覧取得テスト

**API仕様:** `GET /devices/{device_id}/rooms`  
**用途:** 指定したデバイスが配置されている全ての部屋のリストを取得

#### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01/rooms" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

#### 期待結果
- ステータスコード: 200
- レスポンス構造: `{"device_id": "sensor_01", "rooms": ["room_XXX"], "count": 1}`
- 部屋数: **必ず1個**（重複なし配置のため）

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| レスポンス構造 | device_id, rooms, count | ☐ Pass ☐ Fail | |
| device_id | sensor_01 | ☐ Pass ☐ Fail | |
| 部屋数 | 1 | ☐ Pass ☐ Fail | |
| rooms形式 | 配列形式 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.5 特定デバイスの特定部屋でのテレメトリーデータ取得テスト（デバイス中心）

#### 3.5.1 基本的な取得

**API仕様:** `GET /devices/{device_id}/{room_id}`

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01/room_001" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 または 404 | ☐ Pass ☐ Fail | sensor_01がroom_001にない場合は404 |
| レスポンス構造 | device_id, room_id, data, count | ☐ Pass ☐ Fail | |
| device_id | sensor_01 | ☐ Pass ☐ Fail | |
| room_id | room_001 | ☐ Pass ☐ Fail | |
| データ整合性 | 指定デバイス・部屋のみ | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.5.2 存在しない組み合わせテスト

##### 手動テストコマンド（sensor_01が属さない部屋を指定）
```bash
# まず sensor_01 がどの部屋に属するかを確認
curl -X GET "${API_BASE_URL}/devices/sensor_01/rooms"

# sensor_01が属さない部屋を指定してテスト
curl -X GET "${API_BASE_URL}/devices/sensor_01/room_002" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 404 または 200（空データ） | ☐ Pass ☐ Fail | |
| データ件数 | 0 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.6 部屋一覧取得テスト

**API仕様:** `GET /rooms`  
**用途:** システムに登録されている全ての一意な部屋IDのリストを取得

#### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 部屋数 | 10 | ☐ Pass ☐ Fail | |
| レスポンス構造 | rooms, count | ☐ Pass ☐ Fail | |
| 部屋形式 | room_XXX 形式 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.7 特定部屋の全デバイステレメトリーデータ取得テスト

#### 3.7.1 基本的な取得

**API仕様:** `GET /rooms/{room_id}`

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| データ件数 | 1,000 | ☐ Pass ☐ Fail | |
| レスポンス構造 | room_id, data, count | ☐ Pass ☐ Fail | |
| room_id | room_001 | ☐ Pass ☐ Fail | |
| データ整合性 | 全データがroom_001 | ☐ Pass ☐ Fail | |
| ユニークデバイス数 | 20 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.7.2 時間範囲指定テスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001?start_time=2025-08-01T00:00:00Z&end_time=2025-08-01T00:10:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 時間範囲内データ | 指定範囲内のみ | ☐ Pass ☐ Fail | |
| データ件数 | ≤ 1,000 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.8 特定部屋のデバイス一覧取得テスト

**API仕様:** `GET /rooms/{room_id}/devices`  
**用途:** 指定した部屋に配置されている全ての一意なデバイスのリストを取得

#### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001/devices" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| デバイス数 | 20 | ☐ Pass ☐ Fail | |
| レスポンス構造 | room_id, devices, count | ☐ Pass ☐ Fail | |
| room_id | room_001 | ☐ Pass ☐ Fail | |
| デバイス構造 | {"device_id": "sensor_XX"} | ☐ Pass ☐ Fail | |
| デバイス重複 | なし | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 3.9 特定部屋の特定デバイステレメトリーデータ取得テスト（部屋中心）

#### 3.9.1 基本的な取得

**API仕様:** `GET /rooms/{room_id}/{device_id}`

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001/sensor_01" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 または 404 | ☐ Pass ☐ Fail | sensor_01がroom_001にない場合は404 |
| レスポンス構造 | room_id, device_id, data, count | ☐ Pass ☐ Fail | |
| room_id | room_001 | ☐ Pass ☐ Fail | |
| device_id | sensor_01 | ☐ Pass ☐ Fail | |
| データ整合性 | 指定部屋・デバイスのみ | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 3.9.2 ステータスフィルタテスト

##### 手動テストコマンド
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001/sensor_01?status=sensor_error" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 200 | ☐ Pass ☐ Fail | |
| 全データのステータス | sensor_error | ☐ Pass ☐ Fail | |
| temperature値 | null | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

## 4. 自動テスト実行

### 4.1 自動テスト実行方法

```bash
# test_api_spec.py内のAPI_BASE_URLを実際のURLに変更
python test_api_spec.py
```

### 4.2 自動テストによる検証

自動テストスクリプト(`test_api_spec.py`)は以下を検証します：

- レスポンス構造の正確性
- データ整合性
- フィルタリング機能
- エラーハンドリング
- パフォーマンス（レスポンス時間）
- **センサー重複なし配置の検証**

---

## 5. データ整合性テスト

### 5.1 センサー重複チェックテスト

#### 手動テストコマンド
```bash
# 複数のセンサーの部屋配置を確認
curl -X GET "${API_BASE_URL}/devices/sensor_01/rooms"
curl -X GET "${API_BASE_URL}/devices/sensor_02/rooms"
curl -X GET "${API_BASE_URL}/devices/sensor_03/rooms"
```

#### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| 各センサーの部屋数 | 1 | ☐ Pass ☐ Fail | |
| センサー重複 | なし | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

### 5.2 部屋別センサー数チェックテスト

#### 手動テストコマンド
```bash
# 各部屋のセンサー数を確認
for i in {001..010}; do
  echo "=== room_$i ==="
  curl -s "${API_BASE_URL}/rooms/room_$i/devices" | jq '.count'
done
```

#### テスト結果記録表

| 部屋 | 期待センサー数 | 結果 | コメント |
|------|---------------|------|----------|
| room_001 | 20 | ☐ Pass ☐ Fail | |
| room_002 | 20 | ☐ Pass ☐ Fail | |
| room_003 | 20 | ☐ Pass ☐ Fail | |
| room_004 | 20 | ☐ Pass ☐ Fail | |
| room_005 | 20 | ☐ Pass ☐ Fail | |
| room_006 | 20 | ☐ Pass ☐ Fail | |
| room_007 | 20 | ☐ Pass ☐ Fail | |
| room_008 | 20 | ☐ Pass ☐ Fail | |
| room_009 | 20 | ☐ Pass ☐ Fail | |
| room_010 | 20 | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

## 6. バリデーションエラーテスト（期待される失敗テスト）

### 6.1 概要

以下のテストケースは、不正な入力に対して適切なエラーレスポンスが返されることを検証します。これらのテストは**エラーが返されることで「Pass」**となります。

---

### 6.2 デバイスIDバリデーションエラーテスト

#### 6.2.1 アンダースコアなし
```bash
curl -X GET "${API_BASE_URL}/devices/sensor01" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.2.2 複数アンダースコア
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01_temp" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.2.3 数値部分が0
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_00" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.2.4 負の数値
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_-1" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.2.5 数値部分が文字列
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_abc" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.2.6 空のデバイスタイプ
```bash
curl -X GET "${API_BASE_URL}/devices/_01" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 6.3 部屋IDバリデーションエラーテスト

#### 6.3.1 スペースのみ
```bash
curl -X GET "${API_BASE_URL}/rooms/%20" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 6.4 タイムスタンプバリデーションエラーテスト

#### 6.4.1 不正な月
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-13-01T00:00:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.4.2 不正な時刻
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-08-01T25:00:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.4.3 ISO形式でない
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025/08/01%2010:00:00" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.4.4 タイムゾーン指定なし
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=2025-08-01T10:00:00" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.4.5 完全に不正な文字列
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?start_time=invalid_timestamp" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.4.6 存在しない日付
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?end_time=2025-02-30T10:00:00Z" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 6.5 ステータスバリデーションエラーテスト

#### 6.5.1 存在しないステータス
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=broken" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.5.2 大文字小文字混在
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=OK" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.5.3 数値ステータス
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=1" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.5.4 部分的に正しいが無効
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=error" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.5.5 全て大文字
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01?status=SENSOR_ERROR" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Query parameter validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 6.6 複合バリデーションエラーテスト

#### 6.6.1 デバイスID + タイムスタンプエラー
```bash
curl -X GET "${API_BASE_URL}/devices/invalid_device?start_time=invalid_time" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.6.2 全パラメータエラー
```bash
curl -X GET "${API_BASE_URL}/devices/bad_device?start_time=bad_time&end_time=bad_end&status=bad_status" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 400 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Validation failed" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

### 6.7 存在しないエンドポイントテスト

#### 6.7.1 存在しないパス
```bash
curl -X GET "${API_BASE_URL}/nonexistent" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 404 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Route not found" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.7.2 存在しないサブパス
```bash
curl -X GET "${API_BASE_URL}/devices/sensor_01/invalid" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 404 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Route not found" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

#### 6.7.3 存在しない部屋サブパス
```bash
curl -X GET "${API_BASE_URL}/rooms/room_001/invalid" \
  -H "Content-Type: application/json" \
  -w "\nResponse Time: %{time_total}s\nStatus Code: %{http_code}\n"
```

##### テスト結果記録表

| 項目 | 期待値 | 結果 | コメント |
|------|--------|------|----------|
| ステータスコード | 404 | ☐ Pass ☐ Fail | |
| エラーメッセージ | "Route not found" | ☐ Pass ☐ Fail | |

**総合結果:** ☐ Pass ☐ Fail

---

## 7. 総合テスト結果

### 7.1 テスト結果サマリー

| テストケース | 手動テスト | 自動テスト | 総合結果 | 備考 |
|-------------|-----------|-----------|----------|------|
| 3.1 全データ取得 | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.2 デバイス一覧取得 | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.1 デバイス詳細（基本） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.2 デバイス詳細（時間範囲） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.3 デバイス詳細（開始時刻） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.4 デバイス詳細（終了時刻） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.5 デバイス詳細（ステータス） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.3.6 デバイス詳細（複合条件） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.4 デバイス部屋一覧 | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.5.1 デバイス-部屋詳細（基本） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.5.2 デバイス-部屋詳細（存在しない組み合わせ） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.6 部屋一覧取得 | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.7.1 部屋詳細（基本） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.7.2 部屋詳細（時間範囲） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.8 部屋デバイス一覧 | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.9.1 部屋-デバイス詳細（基本） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 3.9.2 部屋-デバイス詳細（ステータス） | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 5.1 センサー重複チェック | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 5.2 部屋別センサー数チェック | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.2.1-6.2.6 デバイスIDエラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.3.1 部屋IDエラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.4.1-6.4.6 タイムスタンプエラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.5.1-6.5.5 ステータスエラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.6.1-6.6.2 複合エラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |
| 6.7.1-6.7.3 ルートエラー | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | ☐ Pass ☐ Fail | |

### 7.2 最終テスト結果

**全体テスト結果:** ☐ Pass ☐ Fail

**テスト実行日時:** _______________

**テスト実行者:** _______________

**重要な検証項目:**
- [ ] 各センサーが1つの部屋にのみ配置されている
- [ ] 各部屋に正確に20個のセンサーが配置されている
- [ ] 総データ件数が10,000件である
- [ ] エラー率が約25%である
- [ ] バリデーションエラーが適切に返される

**追加コメント:**
```
_________________________________________________
_________________________________________________
_________________________________________________
```

---

## 8. トラブルシューティング

### 8.1 よくある問題

**問題1: データが見つからない**
- 原因: テストデータが正しくインポートされていない
- 解決: `generate_test_data.py`を再実行し、DynamoDBに再インポート

**問題2: センサーが複数の部屋に存在する**
- 原因: 古いテストデータが残っている
- 解決: DynamoDBテーブルをクリアして新しいデータを再インポート

**問題3: 部屋のセンサー数が20個でない**
- 原因: データ生成時のエラー
- 解決: `analyze_test_data`関数の出力を確認し、データを再生成

**問題4: 時間フィルタが動作しない**
- 原因: 時間形式が正しくない
- 解決: ISO 8601形式 (`YYYY-MM-DDTHH:MM:SSZ`) を使用

### 8.2 デバッグ用コマンド

```bash
# DynamoDBテーブル確認
aws dynamodb describe-table --table-name IoTTelemetryTable

# データ件数確認
aws dynamodb scan --table-name IoTTelemetryTable --select COUNT

# 特定センサーの部屋確認
aws dynamodb query --table-name IoTTelemetryTable \
  --key-condition-expression "device_id = :device_id" \
  --expression-attribute-values '{":device_id":{"S":"sensor_01"}}' \
  --projection-expression "room_id"

# 部屋別センサー数確認
aws dynamodb scan --table-name IoTTelemetryTable \
  --filter-expression "room_id = :room_id" \
  --expression-attribute-values '{":room_id":{"S":"room_001"}}' \
  --projection-expression "device_id"
```

---

**任務完了**: テストケース番号を体系的に修正し、正常系テスト（3.1-3.9、5.1-5.2）とバリデーションエラーテスト（6.1-6.7）に整理しました。総計41のテストケースが適切に番号付けされています。
```

**任務完了**: テストケース番号の不整合を修正し、体系的な番号体系に統一いたしました。正常系テスト（3.1-3.9、5.1-5.2）とバリデーションエラーテスト（6.1-6.7）に明確に分離し、総計41のテストケースを適切に番号付けしました。