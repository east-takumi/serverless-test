# Step Functions Local テストフレームワーク

AWS Step Functions Localを使用したサーバレスワークフローの自動テストフレームワークです。

## 概要

このテストフレームワークは、Step Functions Localを使用してAWS Step Functionsワークフローをローカル環境でテストするための包括的なソリューションを提供します。実際のAWS環境にデプロイすることなく、ワークフロー全体の動作検証、データフロー追跡、入出力検証を行うことができます。

## 主要機能

### 1. Step Functions Localクライアント (`stepfunctions_local_client.py`)
- Step Functions Localへの接続とワークフロー実行
- 実行ステータスの監視と履歴取得
- エラーハンドリングとリトライ機能

### 2. 入出力検証 (`input_output_validator.py`)
- 各ステートの入出力データ形式検証
- 期待値との比較とアサーション機能
- データフロー連続性の検証

### 3. ワークフロー実行テスト (`workflow_execution_test.py`)
- 完全なワークフロー実行テスト
- 実行履歴の詳細分析
- データフロー追跡とレポート生成

### 4. 統合テストランナー (`test_runner.py`)
- 複数テストシナリオの自動実行
- 設定ファイルベースのテスト管理
- 詳細なテストレポート生成

## ファイル構成

```
tests/
├── stepfunctions_local_client.py    # Step Functions Localクライアント
├── input_output_validator.py        # 入出力検証機能
├── workflow_execution_test.py       # ワークフロー実行テスト
├── test_runner.py                   # メインテストランナー
├── test_config.json                 # テスト設定ファイル
├── example_usage.py                 # 使用例とサンプルコード
├── test_framework_init.py           # フレームワーク初期化
└── README.md                        # このファイル
```

## セットアップ

### 前提条件

1. **Step Functions Local**
   ```bash
   # Step Functions Localのダウンロードと起動
   java -jar StepFunctionsLocal.jar --lambda-endpoint http://localhost:3001
   ```

2. **SAM CLI**
   ```bash
   # Lambda関数のローカル実行
   sam local start-lambda
   ```

3. **Python依存関係**
   ```bash
   pip install boto3
   ```

### 設定ファイル

`test_config.json`でテスト設定を管理：

```json
{
  "stepfunctions_local_endpoint": "http://localhost:8083",
  "region_name": "us-east-1", 
  "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:your-workflow",
  "test_scenarios": [
    {
      "name": "basic_test",
      "input_data": {
        "requestId": "test-001",
        "inputData": {
          "value": "test_value"
        }
      },
      "timeout_seconds": 300
    }
  ]
}
```

## 使用方法

### 基本的な使用方法

```python
from stepfunctions_local_client import StepFunctionsLocalClient
from workflow_execution_test import WorkflowExecutionTester

# クライアントの初期化
client = StepFunctionsLocalClient("http://localhost:8083")

# テスターの初期化
tester = WorkflowExecutionTester(client, "your-state-machine-arn")

# テスト実行
input_data = {
    "requestId": "test-001",
    "inputData": {"value": "test"}
}

result = tester.run_complete_workflow_test("basic_test", input_data)
print(f"テスト結果: {'成功' if result.success else '失敗'}")
```

### コマンドライン実行

```bash
# 全テストの実行
python test_runner.py --config test_config.json --output report.json

# 単一テストの実行
python test_runner.py --single-test "basic_test" --input-data '{"requestId":"test-001","inputData":{"value":"test"}}'

# 詳細ログ付き実行
python test_runner.py --config test_config.json --verbose
```

### 検証機能の使用

```python
from input_output_validator import InputOutputValidator, AssertionHelper

validator = InputOutputValidator()

# 入力データの検証
validation_result = validator.validate_workflow_input(input_data)
AssertionHelper.assert_validation_passed(validation_result, "入力データ検証")

# 出力データの検証
state1_validation = validator.validate_state1_output(state1_output)
AssertionHelper.assert_field_equals(state1_output, "stateMetadata.state", "State1")
```

## テストシナリオ

フレームワークは以下のテストシナリオをサポートします：

1. **基本ワークフローテスト**: 標準的な入力データでの正常実行
2. **複雑データテスト**: 特殊文字や複雑な構造を持つデータでのテスト
3. **最小データテスト**: 必須フィールドのみでのテスト
4. **Unicode データテスト**: 日本語や絵文字を含むデータでのテスト

## 検証項目

### 入力データ検証
- 必須フィールドの存在確認
- データ型の検証
- 構造の妥当性確認

### 各ステート出力検証
- **State1**: 初期データ処理と変換の確認
- **State2**: 中間処理とデータ保持の確認  
- **State3**: 最終集約と完全性の確認

### データフロー検証
- requestIDの連続性
- 元データの保持確認
- データ変換の正確性
- ステート間の連続性

## エラーハンドリング

フレームワークは以下のエラーを適切に処理します：

- Step Functions Local接続エラー
- Lambda関数実行エラー
- データ検証エラー
- タイムアウトエラー
- ネットワークエラー

## ログ出力

詳細なログ出力により、テスト実行の追跡とデバッグが可能です：

```
2024-01-01 12:00:00 - INFO - ワークフローテスト開始: basic_test
2024-01-01 12:00:01 - INFO - 実行開始: arn:aws:states:...
2024-01-01 12:00:05 - INFO - State1 完了
2024-01-01 12:00:08 - INFO - State2 完了  
2024-01-01 12:00:10 - INFO - State3 完了
2024-01-01 12:00:10 - INFO - テスト成功: basic_test
```

## レポート生成

テスト実行後、詳細なJSONレポートが生成されます：

```json
{
  "summary": {
    "total_tests": 4,
    "successful_tests": 4,
    "failed_tests": 0,
    "success_rate": 100.0,
    "total_execution_time": 45.67
  },
  "test_details": [...],
  "data_flow_analysis": {...},
  "overall_status": "PASSED"
}
```

## トラブルシューティング

### よくある問題

1. **Step Functions Local接続エラー**
   - Step Functions Localが起動していることを確認
   - エンドポイントURLが正しいことを確認

2. **Lambda関数実行エラー**
   - SAM CLIでLambda関数が起動していることを確認
   - 関数のログを確認してエラー詳細を調査

3. **タイムアウトエラー**
   - timeout_secondsの値を増加
   - Lambda関数の処理時間を確認

### デバッグ方法

```bash
# 詳細ログでの実行
python test_runner.py --config test_config.json --verbose

# 単一テストでの問題切り分け
python test_runner.py --single-test "problem_test" --verbose
```

## 拡張方法

### カスタム検証の追加

```python
class CustomValidator(InputOutputValidator):
    def validate_custom_field(self, data):
        # カスタム検証ロジック
        pass
```

### 新しいテストシナリオの追加

```python
def create_custom_scenarios():
    return [
        {
            "name": "custom_scenario",
            "input_data": {...},
            "timeout_seconds": 300
        }
    ]
```

## 貢献

このテストフレームワークの改善や新機能の追加については、以下のガイドラインに従ってください：

1. 既存のコード構造を維持
2. 適切なログ出力を追加
3. エラーハンドリングを実装
4. ドキュメントを更新

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。