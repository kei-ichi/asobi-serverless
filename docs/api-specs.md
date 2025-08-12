# API仕様書

本プロジェクトのAPIは、IoTデバイス（冷蔵庫、センサーなど）から収集された温度データや動作状況を取得するためのサービスです。

提供機能:

- 各デバイスの温度データ取得
- 部屋ごとのデバイス状況確認
- 時間範囲指定によるデータ絞り込み
- デバイス故障状況の確認

APIの詳細仕様については２部に分かれて記載します：

1. OpenAPI仕様の形式
2. ドキュメント形式

必要に応じて対象となる仕様形式を参照してください。

## 2. 詳細仕様 - OpenAPI形式

以下はOpenAPI規格に従って、本プロジェクトのAPI仕様を記載します。

＊注意：サーバーのURLは仮書きになります。この詳細仕様を利用する際は実際のAPIエンドポイントを置き換えて利用してください。

```yaml
openapi: 3.0.3
info:
  title: IoTデータークAPI
  description: |
    IoTデバイスのテレメトリーデータを管理するためのRESTful API
    
    このAPIは以下の機能を提供します：
    - デバイス別テレメトリーデータの取得
    - 部屋別テレメトリーデータの取得
    - デバイスと部屋の関連情報の取得
    - 時間範囲とステータスによるフィルタリング
    
    **データ構造:**
    - device_id: デバイス識別子 (例: fridge_01, sensor_42)
    - room_id: 部屋識別子 (例: room_101, room_102)
    - timestamp: ISO 8601形式のタイムスタンプ
    - temperature: 温度データ (数値またはnull)
    - device_status: デバイス状態 (ok, sensor_error, offline, maintenance)
  version: 1.0.0

servers:
  - url: https://aaabbbccc.execute-api.ap-northeast-1.amazonaws.com/prod
    description: 本番環境
  - url: https://aaabbbccc.execute-api.ap-northeast-1.amazonaws.com/dev
    description: 開発環境

tags:
  - name: root
    description: ルートエンドポイント
  - name: devices
    description: デバイス関連操作
  - name: rooms
    description: 部屋関連操作

paths:
  /:
    get:
      tags:
        - root
      summary: 全テレメトリーデータ取得
      description: |
        システム内の全てのテレメトリーデータを取得します。
        
        **注意:** 大量のデータが存在する場合、レスポンス時間が長くなる可能性があります。
      operationId: getAllTelemetryData
      responses:
        '200':
          description: 全テレメトリーデータの取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TelemetryData'
                  count:
                    type: integer
                    description: 取得したデータの件数
                    example: 150
              example:
                data:
                  - device_id: "fridge_01"
                    room_id: "room_101"
                    timestamp: "2024-12-01T10:00:00Z"
                    temperature: 5.5
                    device_status: "ok"
                  - device_id: "fridge_02"
                    room_id: "room_101"
                    timestamp: "2024-12-01T10:00:00Z"
                    temperature: 5.6
                    device_status: "ok"
                count: 2
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices:
    get:
      tags:
        - devices
      summary: デバイス一覧取得
      description: システム内の全ての一意なデバイスIDのリストを取得します。
      operationId: getDevicesList
      responses:
        '200':
          description: デバイス一覧の取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  devices:
                    type: array
                    items:
                      type: string
                    description: デバイスIDのリスト
                    example: ["fridge_01", "fridge_02", "sensor_15"]
                  count:
                    type: integer
                    description: デバイス数
                    example: 3
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices/{device_id}:
    get:
      tags:
        - devices
      summary: 特定デバイスのテレメトリーデータ取得
      description: |
        指定されたデバイスのテレメトリーデータを取得します。
        
        オプションのクエリパラメータでフィルタリングが可能です：
        - 時間範囲による絞り込み
        - デバイス状態による絞り込み
      operationId: getDeviceDetail
      parameters:
        - $ref: '#/components/parameters/DeviceId'
        - $ref: '#/components/parameters/StartTime'
        - $ref: '#/components/parameters/EndTime'
        - $ref: '#/components/parameters/Status'
      responses:
        '200':
          description: デバイステレメトリーデータの取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  device_id:
                    type: string
                    example: "fridge_01"
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TelemetryData'
                  count:
                    type: integer
                    example: 5
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices/{device_id}/rooms:
    get:
      tags:
        - devices
      summary: デバイスが配置された部屋一覧取得
      description: |
        指定されたデバイスが配置されたことがある全ての部屋のリストを取得します。
        
        デバイスの配置履歴を確認する際に有用です。
      operationId: getDeviceRooms
      parameters:
        - $ref: '#/components/parameters/DeviceId'
      responses:
        '200':
          description: デバイス配置部屋一覧の取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  device_id:
                    type: string
                    example: "fridge_01"
                  rooms:
                    type: array
                    items:
                      type: string
                    description: 部屋IDのリスト
                    example: ["room_101", "room_102"]
                  count:
                    type: integer
                    description: 部屋数
                    example: 2
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices/{device_id}/{room_id}:
    get:
      tags:
        - devices
      summary: 特定デバイスの特定部屋でのテレメトリーデータ取得（デバイス中心）
      description: |
        指定されたデバイスの、指定された部屋でのテレメトリーデータを取得します。
        
        このエンドポイントはデバイス中心のアプローチを使用し、
        デバイスのパーティションキーを使用して最適化されたクエリを実行します。
        
        **注意:** `/rooms/{room_id}/{device_id}` と同じデータを返しますが、
        異なるクエリ戦略を使用します。
      operationId: getDeviceRoomDetail
      parameters:
        - $ref: '#/components/parameters/DeviceId'
        - $ref: '#/components/parameters/RoomId'
        - $ref: '#/components/parameters/StartTime'
        - $ref: '#/components/parameters/EndTime'
        - $ref: '#/components/parameters/Status'
      responses:
        '200':
          description: デバイス-部屋テレメトリーデータの取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  device_id:
                    type: string
                    example: "fridge_01"
                  room_id:
                    type: string
                    example: "room_101"
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TelemetryData'
                  count:
                    type: integer
                    example: 3
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /rooms:
    get:
      tags:
        - rooms
      summary: 部屋一覧取得
      description: システム内の全ての一意な部屋IDのリストを取得します。
      operationId: getRoomsList
      responses:
        '200':
          description: 部屋一覧の取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  rooms:
                    type: array
                    items:
                      type: string
                    description: 部屋IDのリスト
                    example: ["room_101", "room_102", "room_201"]
                  count:
                    type: integer
                    description: 部屋数
                    example: 3
        '500':
          $ref: '#/components/responses/InternalServerError'

  /rooms/{room_id}:
    get:
      tags:
        - rooms
      summary: 特定部屋の全デバイステレメトリーデータ取得
      description: |
        指定された部屋内の全てのデバイスのテレメトリーデータを取得します。
        
        Global Secondary Index (GSI) を使用して効率的な部屋ベースのクエリを実行します。
      operationId: getRoomDetail
      parameters:
        - $ref: '#/components/parameters/RoomId'
        - $ref: '#/components/parameters/StartTime'
        - $ref: '#/components/parameters/EndTime'
      responses:
        '200':
          description: 部屋テレメトリーデータの取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  room_id:
                    type: string
                    example: "room_101"
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TelemetryData'
                  count:
                    type: integer
                    example: 10
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /rooms/{room_id}/devices:
    get:
      tags:
        - rooms
      summary: 特定部屋のデバイス一覧取得
      description: |
        指定された部屋に配置されている全ての一意なデバイスのリストを取得します。
        
        部屋のデバイスインベントリを確認する際に有用です。
      operationId: getRoomDevices
      parameters:
        - $ref: '#/components/parameters/RoomId'
      responses:
        '200':
          description: 部屋デバイス一覧の取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  room_id:
                    type: string
                    example: "room_101"
                  devices:
                    type: array
                    items:
                      type: object
                      properties:
                        device_id:
                          type: string
                          example: "fridge_01"
                    description: デバイス情報のリスト
                  count:
                    type: integer
                    description: デバイス数
                    example: 2
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /rooms/{room_id}/{device_id}:
    get:
      tags:
        - rooms
      summary: 特定部屋の特定デバイステレメトリーデータ取得（部屋中心）
      description: |
        指定された部屋の、指定されたデバイスのテレメトリーデータを取得します。
        
        このエンドポイントは部屋中心のアプローチを使用し、
        Global Secondary Index (GSI) を使用して部屋ベースのクエリを実行します。
        
        **注意:** `/devices/{device_id}/{room_id}` と同じデータを返しますが、
        異なるクエリ戦略を使用します。
      operationId: getRoomDeviceDetail
      parameters:
        - $ref: '#/components/parameters/RoomId'
        - $ref: '#/components/parameters/DeviceId'
        - $ref: '#/components/parameters/StartTime'
        - $ref: '#/components/parameters/EndTime'
        - $ref: '#/components/parameters/Status'
      responses:
        '200':
          description: 部屋-デバイステレメトリーデータの取得に成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  room_id:
                    type: string
                    example: "room_101"
                  device_id:
                    type: string
                    example: "fridge_01"
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TelemetryData'
                  count:
                    type: integer
                    example: 3
        '400':
          $ref: '#/components/responses/ValidationError'
        '500':
          $ref: '#/components/responses/InternalServerError'

components:
  parameters:
    DeviceId:
      name: device_id
      in: path
      required: true
      description: |
        デバイス識別子
        
        形式: {デバイスタイプ}_{番号}
        - デバイスタイプ: 英数字の文字列
        - 番号: 1以上の正の整数
      schema:
        type: string
        pattern: '^[a-zA-Z0-9]+_[1-9][0-9]*$'
        example: "fridge_01"
      examples:
        fridge:
          value: "fridge_01"
          description: 冷蔵庫デバイス
        sensor:
          value: "sensor_42"
          description: センサーデバイス
        thermostat:
          value: "thermostat_5"
          description: サーモスタットデバイス

    RoomId:
      name: room_id
      in: path
      required: true
      description: |
        部屋識別子
        
        空でない文字列である必要があります。
      schema:
        type: string
        minLength: 1
        example: "room_101"
      examples:
        room101:
          value: "room_101"
          description: 101号室
        room102:
          value: "room_102"
          description: 102号室

    StartTime:
      name: start_time
      in: query
      required: false
      description: |
        開始時刻（ISO 8601形式）
        
        この時刻以降のデータを取得します。
        end_timeと組み合わせて時間範囲を指定できます。
      schema:
        type: string
        format: date-time
        example: "2024-12-01T10:00:00Z"
      examples:
        morning:
          value: "2024-12-01T09:00:00Z"
          description: 朝9時から
        afternoon:
          value: "2024-12-01T13:00:00Z"
          description: 午後1時から

    EndTime:
      name: end_time
      in: query
      required: false
      description: |
        終了時刻（ISO 8601形式）
        
        この時刻以前のデータを取得します。
        start_timeと組み合わせて時間範囲を指定できます。
      schema:
        type: string
        format: date-time
        example: "2024-12-01T10:05:00Z"
      examples:
        morning_end:
          value: "2024-12-01T12:00:00Z"
          description: 正午まで
        afternoon_end:
          value: "2024-12-01T17:00:00Z"
          description: 午後5時まで

    Status:
      name: status
      in: query
      required: false
      description: |
        デバイス状態によるフィルタリング
        
        指定された状態のデータのみを取得します。
      schema:
        type: string
        enum: [ok, sensor_error, offline, maintenance]
        example: "ok"
      examples:
        ok:
          value: "ok"
          description: 正常状態
        sensor_error:
          value: "sensor_error"
          description: センサーエラー状態
        offline:
          value: "offline"
          description: オフライン状態
        maintenance:
          value: "maintenance"
          description: メンテナンス状態

  schemas:
    TelemetryData:
      type: object
      description: IoTデバイスのテレメトリーデータ
      required:
        - device_id
        - room_id
        - timestamp
        - device_status
      properties:
        device_id:
          type: string
          description: デバイス識別子
          example: "fridge_01"
        room_id:
          type: string
          description: 部屋識別子
          example: "room_101"
        timestamp:
          type: string
          format: date-time
          description: データ取得時刻（ISO 8601形式）
          example: "2024-12-01T10:00:00Z"
        temperature:
          type: number
          nullable: true
          description: |
            温度データ（摂氏）
            
            センサーエラー時はnullになる場合があります。
          example: 5.5
        device_status:
          type: string
          enum: [ok, sensor_error, offline, maintenance]
          description: |
            デバイスの状態
            
            - ok: 正常動作
            - sensor_error: センサーエラー
            - offline: オフライン
            - maintenance: メンテナンス中
          example: "ok"

    ErrorResponse:
      type: object
      description: エラーレスポンス
      required:
        - error
      properties:
        error:
          type: string
          description: エラーメッセージ
          example: "Validation failed"
        details:
          type: array
          items:
            type: string
          description: 詳細なエラー情報（オプション）
          example: ["Invalid device_id: invalid_format"]

  responses:
    ValidationError:
      description: バリデーションエラー
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            device_id_validation:
              summary: デバイスID形式エラー
              value:
                error: "Validation failed"
                details: ["Invalid device_id: invalid_format"]
            timestamp_validation:
              summary: タイムスタンプ形式エラー
              value:
                error: "Query parameter validation failed"
                details: ["Invalid start_time: 2024-13-01T10:00:00Z"]

    InternalServerError:
      description: 内部サーバーエラー
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            error: "Failed to retrieve data: Database connection failed"

  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API認証キー

security:
  - ApiKeyAuth: []

externalDocs:
  description: IoTシステム技術文書
  url: https://docs.iot-system.com

```


## 3. 詳細仕様 - ドキュメント形式

以下はドキュメント形式で、本プロジェクトのAPI仕様を記載します。

### 3.1 全データ取得

**URL:** `GET /`  
**用途:** システム内の全てのテレメトリーデータを一括取得

**対応クエリパラメータ:** なし

**使用例:**
```bash
curl -X GET "https://your-api-gateway-url/"
```

**サンプルレスポンス:**
```json
{
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.6,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 3
}
```

### 3.2 デバイス一覧取得

**URL:** `GET /devices`  
**用途:** システムに登録されている全ての一意なデバイスIDのリストを取得

**対応クエリパラメータ:** なし

**使用例:**
```bash
curl -X GET "https://your-api-gateway-url/devices"
```

**サンプルレスポンス:**
```json
{
  "devices": ["fridge_01", "fridge_02", "sensor_15", "thermostat_3"],
  "count": 4
}
```

### 3.3 特定デバイスのテレメトリーデータ取得

**URL:** `GET /devices/{device_id}`  
**用途:** 指定したデバイスのテレメトリーデータを取得

**対応クエリパラメータ:**
- `start_time` (オプション): 開始時刻（ISO 8601形式）
- `end_time` (オプション): 終了時刻（ISO 8601形式）
- `status` (オプション): デバイス状態フィルタ

**使用例1: 基本的な取得**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01"
```

**サンプルレスポンス1:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例2: 時間範囲指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:05:00Z"
```

**サンプルレスポンス2:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 3
}
```

**使用例3: 開始時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01?start_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス3:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例4: 終了時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01?end_time=2024-12-01T10:01:00Z"
```

**サンプルレスポンス4:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例5: ステータスフィルタ**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01?status=sensor_error"
```

**サンプルレスポンス5:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 2
}
```

**使用例6: 複合条件（時間範囲 + ステータス）**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:05:00Z&status=ok"
```

**サンプルレスポンス6:**
```json
{
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```



### 3.4 デバイス配置部屋一覧取得

**URL:** `GET /devices/{device_id}/rooms`  
**用途:** 指定したデバイスが配置されている全ての部屋のリストを取得

**対応クエリパラメータ:** なし

**使用例:**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/rooms"
```

**サンプルレスポンス:**
```json
{
  "device_id": "fridge_01",
  "rooms": ["room_101", "room_102"],
  "count": 2
}
```



### 3.5 特定デバイスの特定部屋でのテレメトリーデータ取得（デバイス中心）

**URL:** `GET /devices/{device_id}/{room_id}`  
**用途:** 指定したデバイスの、指定した部屋でのテレメトリーデータを取得（デバイス中心のクエリ戦略）

**対応クエリパラメータ:**
- `start_time` (オプション): 開始時刻（ISO 8601形式）
- `end_time` (オプション): 終了時刻（ISO 8601形式）
- `status` (オプション): デバイス状態フィルタ

**使用例1: 基本的な取得**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101"
```

**サンプルレスポンス1:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例2: 時間範囲指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス2:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 2
}
```

**使用例3: 開始時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101?start_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス3:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例4: 終了時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101?end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス4:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 3
}
```

**使用例5: ステータスフィルタ**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101?status=ok"
```

**サンプルレスポンス5:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 3
}
```

**使用例6: 複合条件（時間範囲 + ステータス）**
```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_101?start_time=2024-12-01T10:01:00Z&end_time=2024-12-01T10:04:00Z&status=ok"
```

**サンプルレスポンス6:**
```json
{
  "device_id": "fridge_01",
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```



### 3.6 部屋一覧取得

**URL:** `GET /rooms`  
**用途:** システムに登録されている全ての一意な部屋IDのリストを取得

**対応クエリパラメータ:** なし

**使用例:**
```bash
curl -X GET "https://your-api-gateway-url/rooms"
```

**サンプルレスポンス:**
```json
{
  "rooms": ["room_101", "room_102", "room_201", "room_202"],
  "count": 4
}
```



### 3.7 特定部屋の全デバイステレメトリーデータ取得

**URL:** `GET /rooms/{room_id}`  
**用途:** 指定した部屋内の全てのデバイスのテレメトリーデータを取得

**対応クエリパラメータ:**
- `start_time` (オプション): 開始時刻（ISO 8601形式）
- `end_time` (オプション): 終了時刻（ISO 8601形式）

**使用例1: 基本的な取得**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101"
```

**サンプルレスポンス1:**
```json
{
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.6,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 3
}
```

**使用例2: 時間範囲指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス2:**
```json
{
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.6,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.8,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": 6.0,
      "device_status": "ok"
    }
  ],
  "count": 6
}
```

**使用例3: 開始時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101?start_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス3:**
```json
{
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": 6.1,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 6.2,
      "device_status": "ok"
    }
  ],
  "count": 4
}
```

**使用例4: 終了時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101?end_time=2024-12-01T10:01:00Z"
```

**サンプルレスポンス4:**
```json
{
  "room_id": "room_101",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.6,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_02",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.8,
      "device_status": "ok"
    }
  ],
  "count": 4
}
```



### 3.8 特定部屋のデバイス一覧取得

**URL:** `GET /rooms/{room_id}/devices`  
**用途:** 指定した部屋に配置されている全ての一意なデバイスのリストを取得

**対応クエリパラメータ:** なし

**使用例:**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/devices"
```

**サンプルレスポンス:**
```json
{
  "room_id": "room_101",
  "devices": [
    {"device_id": "fridge_01"},
    {"device_id": "fridge_02"}
  ],
  "count": 2
}
```



### 3.9 特定部屋の特定デバイステレメトリーデータ取得（部屋中心）

**URL:** `GET /rooms/{room_id}/{device_id}`  
**用途:** 指定した部屋の、指定したデバイスのテレメトリーデータを取得（部屋中心のクエリ戦略）

**対応クエリパラメータ:**
- `start_time` (オプション): 開始時刻（ISO 8601形式）
- `end_time` (オプション): 終了時刻（ISO 8601形式）
- `status` (オプション): デバイス状態フィルタ

**使用例1: 基本的な取得**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01"
```

**サンプルレスポンス1:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例2: 時間範囲指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01?start_time=2024-12-01T10:01:00Z&end_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス2:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 3
}
```

**使用例3: 開始時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01?start_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス3:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

**使用例4: 終了時刻のみ指定**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01?end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス4:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 3
}
```

**使用例5: ステータスフィルタ**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01?status=sensor_error"
```

**サンプルレスポンス5:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    }
  ],
  "count": 2
}
```

**使用例6: 複合条件（時間範囲 + ステータス）**
```bash
curl -X GET "https://your-api-gateway-url/rooms/room_101/fridge_01?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:04:00Z&status=ok"
```

**サンプルレスポンス6:**
```json
{
  "room_id": "room_101",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_101",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```


## 4. 実際の使用方法

### 3.1 curlコマンドの使い方

1. **コマンドプロンプト（Windows）またはターミナル（Mac/Linux）を開く**

2. **上記のcurlコマンドをコピーして貼り付け**

3. **`https://your-api-gateway-url` の部分を実際のAPIのURLに変更**
   - 例: `https://abc123def.execute-api.us-east-1.amazonaws.com/prod`

4. **Enterキーを押して実行**

### 実際の例

```bash
# 実際のURLを使用した例
curl -X GET "https://abc123def.execute-api.us-east-1.amazonaws.com/prod/devices/fridge_01"
```

## 5. データ形式説明

### デバイス状態の種類
- `ok`: 正常動作中
- `sensor_error`: センサー故障
- `offline`: 通信不能
- `maintenance`: メンテナンス中

### 時間形式
ISO 8601形式: `YYYY-MM-DDTHH:MM:SSZ`

例: `2024-12-01T10:00:00Z` = 2024年12月1日 午前10時（UTC）


## エラーレスポンス

### 400 バリデーションエラー
```json
{
  "error": "Validation failed",
  "details": ["Invalid device_id: invalid_format"]
}
```

### 500 内部サーバーエラー
```json
{
  "error": "Failed to retrieve data: Database connection failed"
}
```