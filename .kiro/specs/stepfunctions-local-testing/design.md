# 設計書

## 概要

Step Functions Localを使用したサーバレスアプリケーションのテスト自動化システムの設計です。3つのLambda関数を順次実行するStep Functionsワークフローを、GitHub Actions環境でローカルテストする仕組みを提供します。

## アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions環境                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                テスト実行環境                            │ │
│  │  ┌─────────────────┐  ┌─────────────────────────────────┐ │ │
│  │  │ Step Functions  │  │        Lambda Runtime           │ │ │
│  │  │     Local       │  │  ┌─────┐ ┌─────┐ ┌─────────┐   │ │ │
│  │  │                 │  │  │State│ │State│ │ State   │   │ │ │
│  │  │  ┌───────────┐  │  │  │  1  │ │  2  │ │    3    │   │ │ │
│  │  │  │ワークフロー│  │  │  │     │ │     │ │         │   │ │ │
│  │  │  │   定義     │  │  │  └─────┘ └─────┘ └─────────┘   │ │ │
│  │  │  └───────────┘  │  └─────────────────────────────────┘ │ │
│  │  └─────────────────┘                                      │ │
│  │                                                            │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              テストスイート                          │   │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │ │
│  │  │  │ワークフロー │ │入出力検証   │ │エラーハンド │   │   │ │
│  │  │  │実行テスト   │ │テスト       │ │リングテスト │   │   │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘   │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### コンポーネント構成

#### 1. サーバレスアプリケーション層
- **SAMテンプレート**: インフラストラクチャ定義
- **Step Functionsワークフロー**: 3つのLambdaステートの順次実行
- **Lambda関数**: 各ステートで実行される処理ロジック

#### 2. テスト実行層
- **Step Functions Local**: ローカルStep Functionsエミュレータ
- **Lambda Runtime**: ローカルLambda実行環境
- **テストランナー**: テスト実行とレポート生成

#### 3. CI/CD層
- **GitHub Actions**: テスト自動化パイプライン
- **環境セットアップ**: 依存関係とツールのインストール
- **テスト結果レポート**: 成功/失敗の詳細報告

## コンポーネントとインターフェース

### Step Functionsワークフロー

```json
{
  "Comment": "3つのLambda関数を順次実行するワークフロー",
  "StartAt": "State1",
  "States": {
    "State1": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:ProcessState1",
      "Next": "State2"
    },
    "State2": {
      "Type": "Task", 
      "Resource": "arn:aws:lambda:region:account:function:ProcessState2",
      "Next": "State3"
    },
    "State3": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:ProcessState3",
      "End": true
    }
  }
}
```

### Lambda関数インターフェース

各Lambda関数は以下の共通インターフェースを実装：

```python
def lambda_handler(event, context):
    """
    入力: event (前のステートからの出力または初期入力)
    出力: 次のステートへの入力となるデータ
    """
    # 入力データの処理
    processed_data = process_input(event)
    
    # ステート固有の処理
    result = execute_state_logic(processed_data)
    
    # 次のステートへの出力
    return {
        'statusCode': 200,
        'body': result,
        'metadata': {
            'state': 'StateX',
            'timestamp': datetime.now().isoformat()
        }
    }
```

### テストフレームワークインターフェース

```python
class StepFunctionsTestFramework:
    def __init__(self, local_endpoint, state_machine_arn):
        self.client = boto3.client('stepfunctions', endpoint_url=local_endpoint)
        self.state_machine_arn = state_machine_arn
    
    def execute_workflow(self, input_data):
        """ワークフローを実行し、結果を返す"""
        
    def validate_state_output(self, execution_arn, state_name, expected_data):
        """特定のステートの出力を検証"""
        
    def get_execution_history(self, execution_arn):
        """実行履歴を取得してデータフローを追跡"""
```

## データモデル

### ワークフロー入力データ

```json
{
  "requestId": "uuid",
  "inputData": {
    "value": "初期値",
    "metadata": {
      "source": "test",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  }
}
```

### ステート間データフロー

```json
{
  "state1Output": {
    "processedValue": "State1で処理された値",
    "originalInput": "初期値",
    "stateMetadata": {
      "state": "State1",
      "processingTime": 100
    }
  },
  "state2Output": {
    "processedValue": "State2で処理された値", 
    "previousStates": ["State1"],
    "stateMetadata": {
      "state": "State2",
      "processingTime": 150
    }
  },
  "finalOutput": {
    "processedValue": "最終処理値",
    "allStatesData": ["State1結果", "State2結果", "State3結果"],
    "executionSummary": {
      "totalStates": 3,
      "totalProcessingTime": 400,
      "success": true
    }
  }
}
```

## エラーハンドリング

### エラー分類と対応

1. **Lambda関数エラー**
   - 実行時例外: try-catch でキャッチし、エラー詳細を出力
   - タイムアウト: 適切なタイムアウト設定とリトライ機能

2. **Step Functionsエラー**
   - ステート遷移エラー: 実行履歴から詳細を取得
   - 定義エラー: ワークフロー定義の検証

3. **テスト環境エラー**
   - Step Functions Local接続エラー: 再試行とフォールバック
   - 環境セットアップエラー: 詳細なログ出力

### エラーレポート形式

```json
{
  "error": {
    "type": "LambdaExecutionError",
    "state": "State2", 
    "message": "処理中にエラーが発生しました",
    "details": {
      "exception": "ValueError: 無効な入力データ",
      "input": "エラー時の入力データ",
      "stackTrace": "詳細なスタックトレース"
    },
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## テスト戦略

### テストレベル

1. **ユニットテスト**
   - 各Lambda関数の個別テスト
   - 入力データの検証
   - 出力データの形式確認

2. **統合テスト**
   - Step Functions Localを使用したワークフロー全体テスト
   - ステート間データフローの検証
   - エラーハンドリングの確認

3. **エンドツーエンドテスト**
   - 実際のワークフロー実行シナリオ
   - 複数の入力パターンでのテスト
   - パフォーマンス測定

### テストケース設計

```python
class WorkflowTestCases:
    def test_successful_workflow_execution(self):
        """正常なワークフロー実行のテスト"""
        
    def test_state_data_flow(self):
        """ステート間データフローのテスト"""
        
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        
    def test_input_validation(self):
        """入力データ検証のテスト"""
        
    def test_output_format(self):
        """出力データ形式のテスト"""
```

### GitHub Actions統合

```yaml
name: Step Functions Local Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
      - name: Setup Python
      - name: Install dependencies
      - name: Start Step Functions Local
      - name: Deploy SAM application locally
      - name: Run workflow tests
      - name: Generate test report
```

## パフォーマンス考慮事項

### 実行時間最適化
- Step Functions Localの起動時間短縮
- Lambda関数のコールドスタート対策
- テスト並列実行の検討

### リソース使用量
- GitHub Actions環境のメモリ制限考慮
- 同時実行数の制限設定
- ログ出力量の最適化

## セキュリティ考慮事項

### テスト環境セキュリティ
- 実際のAWS認証情報の使用回避
- テストデータの機密情報除去
- ローカル環境での実行に限定

### データ保護
- テスト実行時のデータ暗号化
- ログ出力での機密情報マスキング
- 一時ファイルの適切な削除