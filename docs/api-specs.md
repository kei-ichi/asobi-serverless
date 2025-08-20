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
    - room_id: 部屋識別子 (例: room_001, room_002)
    - timestamp: ISO 8601形式のタイムスタンプ (UTC必須)
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
        DynamoDBの全テーブルスキャンを実行するため、本番環境では使用を控えることを推奨します。
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
                    room_id: "room_001"
                    timestamp: "2024-12-01T10:00:00Z"
                    temperature: 5.5
                    device_status: "ok"
                  - device_id: "sensor_42"
                    room_id: "room_001"
                    timestamp: "2024-12-01T10:00:00Z"
                    temperature: 22.3
                    device_status: "ok"
                count: 2
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices:
    get:
      tags:
        - devices
      summary: デバイス一覧取得
      description: |
        システム内の全ての一意なデバイスIDのリストを取得します。
        
        DynamoDBのプロジェクションクエリを使用して効率的にデバイスIDのみを取得します。
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
                    description: デバイスIDのリスト（ソート済み）
                    example: ["fridge_01", "fridge_02", "sensor_15", "thermostat_5"]
                  count:
                    type: integer
                    description: デバイス数
                    example: 4
        '500':
          $ref: '#/components/responses/InternalServerError'

  /devices/{device_id}:
    get:
      tags:
        - devices
      summary: 特定デバイスのテレメトリーデータ取得
      description: |
        指定されたデバイスのテレメトリーデータを取得します。
        
        DynamoDBのパーティションキー（device_id）を使用した効率的なクエリを実行します。
        
        **フィルタリングオプション:**
        - 時間範囲による絞り込み（ソートキーでの効率的フィルタ）
        - デバイス状態による絞り込み（FilterExpression使用）
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
        
        DynamoDBのプロジェクションクエリでroom_idのみを取得し、重複を除去してソートします。
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
                    description: 部屋IDのリスト（ソート済み、重複なし）
                    example: ["room_001", "room_002"]
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
        
        **クエリ戦略:** デバイス中心のアプローチ
        - DynamoDBのパーティションキー（device_id）でクエリ
        - room_idをFilterExpressionで絞り込み
        - 単一デバイスの複数部屋配置履歴分析に最適
        
        **注意:** `/rooms/{room_id}/{device_id}` と同じデータを返しますが、
        異なるクエリ戦略を使用するため、パフォーマンス特性が異なります。
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
                    example: "room_001"
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
      description: |
        システム内の全ての一意な部屋IDのリストを取得します。
        
        DynamoDBのプロジェクションクエリを使用して効率的にroom_idのみを取得します。
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
                    description: 部屋IDのリスト（ソート済み）
                    example: ["room_001", "room_002", "room_003"]
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
        
        **クエリ戦略:** Global Secondary Index (GSI) を使用
        - GSI: room_id-timestamp-index
        - 部屋ベースの効率的なクエリを実行
        - 時間範囲フィルタはGSIのソートキーで最適化
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
                    example: "room_001"
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
        
        **クエリ戦略:**
        - GSIでroom_idクエリ
        - device_idのみプロジェクション
        - 重複除去とソート処理
        
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
                    example: "room_001"
                  devices:
                    type: array
                    items:
                      type: object
                      properties:
                        device_id:
                          type: string
                          example: "fridge_01"
                    description: デバイス情報のリスト（ソート済み、重複なし）
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
        
        **クエリ戦略:** 部屋中心のアプローチ
        - Global Secondary Index (GSI) でroom_idクエリ
        - device_idをFilterExpressionで絞り込み
        - 部屋内デバイス分析に最適
        
        **注意:** `/devices/{device_id}/{room_id}` と同じデータを返しますが、
        異なるクエリ戦略を使用するため、パフォーマンス特性が異なります。
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
                    example: "room_001"
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
        
        **厳密な形式要件:**
        - パターン: {デバイスタイプ}_{番号}
        - デバイスタイプ: 英数字の文字列（1文字以上）
        - 番号: 1以上の正の整数
        - アンダースコア区切り文字は1つのみ
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
        
        **厳密な形式要件:**
        - パターン: room_{3桁数字}
        - プレフィックス: "room"
        - 数字部分: 001-999の3桁形式
        - アンダースコア区切り文字は1つのみ
      schema:
        type: string
        pattern: '^room_[0-9]{3}$'
        example: "room_001"
      examples:
        room001:
          value: "room_001"
          description: 001号室
        room002:
          value: "room_002"
          description: 002号室
        room100:
          value: "room_100"
          description: 100号室

    StartTime:
      name: start_time
      in: query
      required: false
      description: |
        開始時刻（ISO 8601形式、UTC必須）
        
        **厳密な形式要件:**
        - 形式: YYYY-MM-DDTHH:MM:SSZ
        - UTC指定（Z）が必須
        - この時刻以降のデータを取得
        - end_timeと組み合わせて時間範囲を指定可能
        - DynamoDBのソートキーで効率的にフィルタ
      schema:
        type: string
        format: date-time
        pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
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
        終了時刻（ISO 8601形式、UTC必須）
        
        **厳密な形式要件:**
        - 形式: YYYY-MM-DDTHH:MM:SSZ
        - UTC指定（Z）が必須
        - この時刻以前のデータを取得
        - start_timeと組み合わせて時間範囲を指定可能
        - DynamoDBのソートキーで効率的にフィルタ
      schema:
        type: string
        format: date-time
        pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
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
        
        **厳密な値制限:**
        - 小文字のみ許可
        - 指定された状態のデータのみを取得
        - DynamoDBのFilterExpressionで適用
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
          description: センサーエラー状態（temperature=null）
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
          pattern: '^[a-zA-Z0-9]+_[1-9][0-9]*$'
          example: "fridge_01"
        room_id:
          type: string
          description: 部屋識別子
          pattern: '^room_[0-9]{3}$'
          example: "room_001"
        timestamp:
          type: string
          format: date-time
          description: データ取得時刻（ISO 8601形式、UTC必須）
          pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
          example: "2024-12-01T10:00:00Z"
        temperature:
          type: number
          nullable: true
          description: |
            温度データ（摂氏）
            
            **重要な制約:**
            - sensor_errorステータス時は必ずnull
            - 正常時は数値（DynamoDB Decimalから変換）
          example: 5.5
        device_status:
          type: string
          enum: [ok, sensor_error, offline, maintenance]
          description: |
            デバイスの状態（小文字のみ）
            
            **状態定義:**
            - ok: 正常動作
            - sensor_error: センサーエラー（temperature=null）
            - offline: オフライン
            - maintenance: メンテナンス中
          example: "ok"

    ErrorResponse:
      type: object
      description: 標準エラーレスポンス
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
      description: バリデーションエラー（400）
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
            room_id_validation:
              summary: 部屋ID形式エラー
              value:
                error: "Validation failed"
                details: ["Invalid room_id: must be room_XXX format with 3 digits"]
            timestamp_validation:
              summary: タイムスタンプ形式エラー
              value:
                error: "Query parameter validation failed"
                details: ["Invalid start_time: 2024-13-01T10:00:00Z"]
            status_validation:
              summary: ステータス値エラー
              value:
                error: "Query parameter validation failed"
                details: ["Invalid status: INVALID_STATUS"]

    InternalServerError:
      description: 内部サーバーエラー（500）
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            database_error:
              summary: データベースエラー
              value:
                error: "Failed to retrieve data: Database connection failed"
            query_error:
              summary: クエリエラー
              value:
                error: "Device query failed: Invalid key condition"

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

**重要な注意事項:**

- DynamoDBの全テーブルスキャンを実行するため、大量データ環境では高コスト
- 本番環境では使用を控えることを推奨
- レスポンス時間が長くなる可能性があります

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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 22.3,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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

**最適化ポイント:**

- DynamoDBのプロジェクションクエリを使用してdevice_idのみを効率的に取得
- 重複除去とソート処理を実行
- 通信量を最小化

**対応クエリパラメータ:** なし

**使用例:**

```bash
curl -X GET "https://your-api-gateway-url/devices"
```

**サンプルレスポンス:**

```json
{
  "devices": ["fridge_01", "fridge_02", "sensor_15", "thermostat_5"],
  "count": 4
}
```

### 3.3 特定デバイスのテレメトリーデータ取得

**URL:** `GET /devices/{device_id}`  
**用途:** 指定したデバイスのテレメトリーデータを取得

**クエリ戦略:**

- DynamoDBのパーティションキー（device_id）を使用した効率的なクエリ
- 時間範囲フィルタはソートキー（timestamp）で最適化
- ステータスフィルタはFilterExpressionで適用

**デバイスID形式要件:**

- パターン: `{デバイスタイプ}_{番号}`
- デバイスタイプ: 英数字の文字列（1文字以上）
- 番号: 1以上の正の整数
- 例: `fridge_01`, `sensor_42`, `thermostat_5`

**対応クエリパラメータ:**

- `start_time` (オプション): 開始時刻（ISO 8601形式、UTC必須）
- `end_time` (オプション): 終了時刻（ISO 8601形式、UTC必須）
- `status` (オプション): デバイス状態フィルタ（ok, sensor_error, offline, maintenance）

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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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

**最適化ポイント:**

- DynamoDBのプロジェクションクエリでroom_idのみを取得
- 重複除去とソート処理を実行
- デバイスの配置履歴分析に有用

**対応クエリパラメータ:** なし

**使用例:**

```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/rooms"
```

**サンプルレスポンス:**

```json
{
  "device_id": "fridge_01",
  "rooms": ["room_001", "room_002"],
  "count": 2
}
```

### 3.5 特定デバイスの特定部屋でのテレメトリーデータ取得（デバイス中心）

**URL:** `GET /devices/{device_id}/{room_id}`  
**用途:** 指定したデバイスの、指定した部屋でのテレメトリーデータを取得（デバイス中心のクエリ戦略）

**クエリ戦略:**

- DynamoDBのパーティションキー（device_id）でクエリ
- room_idをFilterExpressionで絞り込み
- 単一デバイスの複数部屋配置履歴分析に最適
- `/rooms/{room_id}/{device_id}`と同じデータを返すが、異なるクエリ戦略

**部屋ID形式要件:**

- パターン: `room_{3桁数字}`
- プレフィックス: "room"
- 数字部分: 001-999の3桁形式
- 例: `room_001`, `room_002`, `room_100`

**対応クエリパラメータ:**

- `start_time` (オプション): 開始時刻（ISO 8601形式、UTC必須）
- `end_time` (オプション): 終了時刻（ISO 8601形式、UTC必須）
- `status` (オプション): デバイス状態フィルタ

**使用例1: 基本的な取得**

```bash
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001"
```

**サンプルレスポンス1:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス2:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001?start_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス3:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001?end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス4:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001?status=ok"
```

**サンプルレスポンス5:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/devices/fridge_01/room_001?start_time=2024-12-01T10:01:00Z&end_time=2024-12-01T10:04:00Z&status=ok"
```

**サンプルレスポンス6:**

```json
{
  "device_id": "fridge_01",
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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

**最適化ポイント:**

- DynamoDBのプロジェクションクエリを使用してroom_idのみを効率的に取得
- 重複除去とソート処理を実行
- 通信量を最小化

**対応クエリパラメータ:** なし

**使用例:**

```bash
curl -X GET "https://your-api-gateway-url/rooms"
```

**サンプルレスポンス:**

```json
{
  "rooms": ["room_001", "room_002", "room_003"],
  "count": 3
}
```

### 3.7 特定部屋の全デバイステレメトリーデータ取得

**URL:** `GET /rooms/{room_id}`  
**用途:** 指定した部屋内の全てのデバイスのテレメトリーデータを取得

**クエリ戦略:**

- Global Secondary Index (GSI) を使用: `room_id-timestamp-index`
- 部屋ベースの効率的なクエリを実行
- 時間範囲フィルタはGSIのソートキー（timestamp）で最適化

**対応クエリパラメータ:**

- `start_time` (オプション): 開始時刻（ISO 8601形式、UTC必須）
- `end_time` (オプション): 終了時刻（ISO 8601形式、UTC必須）

**使用例1: 基本的な取得**

```bash
curl -X GET "https://your-api-gateway-url/rooms/room_001"
```

**サンプルレスポンス1:**

```json
{
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 22.3,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス2:**

```json
{
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 22.3,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 22.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": 22.7,
      "device_status": "ok"
    }
  ],
  "count": 6
}
```

**使用例3: 開始時刻のみ指定**

```bash
curl -X GET "https://your-api-gateway-url/rooms/room_001?start_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス3:**

```json
{
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": 22.9,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 5.9,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:04:00Z",
      "temperature": 23.1,
      "device_status": "ok"
    }
  ],
  "count": 4
}
```

**使用例4: 終了時刻のみ指定**

```bash
curl -X GET "https://your-api-gateway-url/rooms/room_001?end_time=2024-12-01T10:01:00Z"
```

**サンプルレスポンス4:**

```json
{
  "room_id": "room_001",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 22.3,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "sensor_42",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 22.5,
      "device_status": "ok"
    }
  ],
  "count": 4
}
```

### 3.8 特定部屋のデバイス一覧取得

**URL:** `GET /rooms/{room_id}/devices`  
**用途:** 指定した部屋に配置されている全ての一意なデバイスのリストを取得

**クエリ戦略:**

- GSIでroom_idクエリ
- device_idのみプロジェクション
- 重複除去とソート処理
- 部屋のデバイスインベントリ確認に有用

**対応クエリパラメータ:** なし

**使用例:**

```bash
curl -X GET "https://your-api-gateway-url/rooms/room_001/devices"
```

**サンプルレスポンス:**

```json
{
  "room_id": "room_001",
  "devices": [
    {"device_id": "fridge_01"},
    {"device_id": "sensor_42"}
  ],
  "count": 2
}
```

### 3.9 特定部屋の特定デバイステレメトリーデータ取得（部屋中心）

**URL:** `GET /rooms/{room_id}/{device_id}`  
**用途:** 指定した部屋の、指定したデバイスのテレメトリーデータを取得（部屋中心のクエリ戦略）

**クエリ戦略:**

- Global Secondary Index (GSI) でroom_idクエリ
- device_idをFilterExpressionで絞り込み
- 部屋内デバイス分析に最適
- `/devices/{device_id}/{room_id}`と同じデータを返すが、異なるクエリ戦略

**対応クエリパラメータ:**

- `start_time` (オプション): 開始時刻（ISO 8601形式、UTC必須）
- `end_time` (オプション): 終了時刻（ISO 8601形式、UTC必須）
- `status` (オプション): デバイス状態フィルタ

**使用例1: 基本的な取得**

```bash
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01"
```

**サンプルレスポンス1:**

```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01?start_time=2024-12-01T10:01:00Z&end_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス2:**

```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01?start_time=2024-12-01T10:03:00Z"
```

**サンプルレスポンス3:**

```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:03:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01?end_time=2024-12-01T10:02:00Z"
```

**サンプルレスポンス4:**

```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01?status=sensor_error"
```

**サンプルレスポンス5:**

```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:02:00Z",
      "temperature": null,
      "device_status": "sensor_error"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
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
curl -X GET "https://your-api-gateway-url/rooms/room_001/fridge_01?start_time=2024-12-01T10:00:00Z&end_time=2024-12-01T10:04:00Z&status=ok"
```

**サンプルレスポンス6:**
```json
{
  "room_id": "room_001",
  "device_id": "fridge_01",
  "data": [
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:00:00Z",
      "temperature": 5.5,
      "device_status": "ok"
    },
    {
      "device_id": "fridge_01",
      "room_id": "room_001",
      "timestamp": "2024-12-01T10:01:00Z",
      "temperature": 5.7,
      "device_status": "ok"
    }
  ],
  "count": 2
}
```

## 4. 実際の使用方法

### 4.1 curlコマンドの使い方

1. **コマンドプロンプト（Windows）またはターミナル（Mac/Linux）を開く**

2. **上記のcurlコマンドをコピーして貼り付け**

3. **`https://your-api-gateway-url` の部分を実際のAPIのURLに変更**
   - 例: `https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod`

4. **Enterキーを押して実行**

### 4.2 実際の例

```bash
# 実際のURLを使用した例
curl -X GET "https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod/devices/fridge_01"
```

## 5. データ形式説明

### 5.1 デバイスID形式

- **パターン:** `{デバイスタイプ}_{番号}`
- **デバイスタイプ:** 英数字の文字列（1文字以上）
- **番号:** 1以上の正の整数
- **例:** `fridge_01`, `sensor_42`, `thermostat_5`

### 5.2 部屋ID形式

- **パターン:** `room_{3桁数字}`
- **プレフィックス:** "room"
- **数字部分:** 001-999の3桁形式
- **例:** `room_001`, `room_002`, `room_100`

### 5.3 デバイス状態の種類

- `ok`: 正常動作中
- `sensor_error`: センサー故障（**重要:** temperature値は必ずnull）
- `offline`: 通信不能
- `maintenance`: メンテナンス中

### 5.4 時間形式

**厳密なISO 8601形式（UTC必須）:** `YYYY-MM-DDTHH:MM:SSZ`

**例:** `2024-12-01T10:00:00Z` = 2024年12月1日 午前10時（UTC）

**重要な注意事項:**

- UTC指定（Z）が必須
- 他のタイムゾーン表記は受け付けません
- 形式が正確でない場合はバリデーションエラーになります

### 5.5 温度データ

- **正常時:** 数値（DynamoDB Decimalから変換）
- **sensor_errorステータス時:** 必ずnull
- **単位:** 摂氏

## 6. エラーレスポンス

### 6.1 400 バリデーションエラー

**デバイスID形式エラー:**

```json
{
  "error": "Validation failed",
  "details": ["Invalid device_id: invalid_format"]
}
```

**部屋ID形式エラー:**

```json
{
  "error": "Validation failed",
  "details": ["Invalid room_id: must be room_XXX format with 3 digits"]
}
```

**タイムスタンプ形式エラー:**

```json
{
  "error": "Query parameter validation failed",
  "details": ["Invalid start_time: 2024-13-01T10:00:00Z"]
}
```

**ステータス値エラー:**

```json
{
  "error": "Query parameter validation failed",
  "details": ["Invalid status: INVALID_STATUS"]
}
```

### 6.2 500 内部サーバーエラー

**データベースエラー:**

```json
{
  "error": "Failed to retrieve data: Database connection failed"
}
```

**クエリエラー:**

```json
{
  "error": "Device query failed: Invalid key condition"
}
```

## 7. パフォーマンス最適化情報

### 7.1 クエリ戦略の選択

**デバイス中心のアクセスパターン:**

- `/devices/{device_id}/*` エンドポイントを使用
- パーティションキーでの効率的なクエリ

**部屋中心のアクセスパターン:**

- `/rooms/{room_id}/*` エンドポイントを使用
- GSI（Global Secondary Index）での最適化されたクエリ

### 7.2 フィルタリングの効率性

**効率的なフィルタ:**

- 時間範囲フィルタ（start_time, end_time）: ソートキーで最適化
- 単一デバイス/部屋の絞り込み: パーティションキーで最適化

**非効率的なフィルタ:**

- ステータスフィルタ: FilterExpressionで後処理（必要に応じて使用）

### 7.3 大量データ処理の注意事項

**避けるべき操作:**

- `GET /` エンドポイントの頻繁な使用（全テーブルスキャン）
- 広範囲な時間範囲での大量データ取得

**推奨される操作:**

- 特定のデバイス/部屋に絞った取得
- 適切な時間範囲での絞り込み
- 必要に応じたステータスフィルタの活用
