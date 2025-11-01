"""
Step Functions Local テストフレームワーク使用例
基本的な使用方法とサンプルコード
"""

import json
import logging
from datetime import datetime

# テストフレームワークのインポート
from stepfunctions_local_client import StepFunctionsLocalClient
from workflow_execution_test import WorkflowExecutionTester, create_sample_test_scenarios
from input_output_validator import InputOutputValidator, AssertionHelper
from test_runner import StepFunctionsTestRunner, load_config

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_client_usage():
    """
    基本的なクライアント使用例
    """
    print("=== 基本的なクライアント使用例 ===")
    
    # Step Functions Localクライアントの初期化
    client = StepFunctionsLocalClient(
        local_endpoint="http://localhost:8083",
        region_name="us-east-1"
    )
    
    # 接続テスト
    if client.test_connection():
        print("✓ Step Functions Localに正常に接続しました")
    else:
        print("✗ Step Functions Localへの接続に失敗しました")
        return
    
    # サンプル入力データ
    input_data = {
        "requestId": "example-001",
        "inputData": {
            "value": "example_test_value",
            "metadata": {
                "source": "example_usage",
                "timestamp": datetime.now().isoformat()
            }
        }
    }
    
    # ワークフロー実行（実際のステートマシンARNが必要）
    state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:example-workflow"
    
    print(f"入力データ: {json.dumps(input_data, indent=2, ensure_ascii=False)}")
    
    # 注意: 実際の実行には有効なステートマシンARNが必要
    print("注意: 実際の実行には有効なステートマシンARNが必要です")


def example_validation_usage():
    """
    検証機能の使用例
    """
    print("\n=== 検証機能の使用例 ===")
    
    validator = InputOutputValidator()
    
    # サンプル入力データの検証
    sample_input = {
        "requestId": "validation-test-001",
        "inputData": {
            "value": "validation_test_value",
            "metadata": {
                "source": "validation_example"
            }
        }
    }
    
    print("入力データの検証:")
    input_validation = validator.validate_workflow_input(sample_input)
    
    if input_validation.is_valid:
        print("✓ 入力データの検証に成功しました")
    else:
        print(f"✗ 入力データの検証に失敗しました: {input_validation.errors}")
    
    # サンプルState1出力データの検証
    sample_state1_output = {
        "requestId": "validation-test-001",
        "state1Output": {
            "processedValue": "State1_processed_validation_test_value",
            "originalInput": "validation_test_value",
            "processingDetails": {
                "transformationType": "prefix_addition",
                "processingTime": datetime.now().isoformat()
            }
        },
        "stateMetadata": {
            "state": "State1",
            "executionTime": datetime.now().isoformat(),
            "functionName": "example_function"
        }
    }
    
    print("\nState1出力データの検証:")
    state1_validation = validator.validate_state1_output(sample_state1_output)
    
    if state1_validation.is_valid:
        print("✓ State1出力データの検証に成功しました")
    else:
        print(f"✗ State1出力データの検証に失敗しました: {state1_validation.errors}")
    
    # アサーション機能の例
    print("\nアサーション機能の例:")
    try:
        AssertionHelper.assert_field_equals(
            sample_state1_output, 
            "stateMetadata.state", 
            "State1", 
            "State1メタデータ検証"
        )
        print("✓ アサーション成功: stateMetadata.state == 'State1'")
        
        AssertionHelper.assert_field_contains(
            sample_state1_output,
            "state1Output.processedValue",
            "State1_processed_",
            "State1処理値検証"
        )
        print("✓ アサーション成功: processedValueに'State1_processed_'が含まれています")
        
    except AssertionError as e:
        print(f"✗ アサーション失敗: {str(e)}")


def example_test_runner_usage():
    """
    テストランナーの使用例
    """
    print("\n=== テストランナーの使用例 ===")
    
    # 設定の作成
    config = {
        "stepfunctions_local_endpoint": "http://localhost:8083",
        "region_name": "us-east-1",
        "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:example-workflow",
        "test_scenarios": [
            {
                "name": "example_test_scenario",
                "input_data": {
                    "requestId": "runner-test-001",
                    "inputData": {
                        "value": "runner_test_value",
                        "metadata": {
                            "source": "test_runner_example",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                },
                "timeout_seconds": 300
            }
        ]
    }
    
    print("テスト設定:")
    print(json.dumps(config, indent=2, ensure_ascii=False, default=str))
    
    # テストランナーの初期化
    runner = StepFunctionsTestRunner(config)
    
    print("\n注意: 実際のテスト実行には以下が必要です:")
    print("1. Step Functions Localが起動していること")
    print("2. 有効なステートマシンがデプロイされていること")
    print("3. Lambda関数が正常に動作すること")
    
    # 実際のテスト実行例（コメントアウト）
    # result = runner.run_all_tests()
    # print(f"テスト結果: {result['overall_status']}")


def example_sample_scenarios():
    """
    サンプルシナリオの表示
    """
    print("\n=== サンプルテストシナリオ ===")
    
    scenarios = create_sample_test_scenarios()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nシナリオ {i}: {scenario['name']}")
        print(f"入力データ: {json.dumps(scenario['input_data'], indent=2, ensure_ascii=False)}")
        print(f"タイムアウト: {scenario['timeout_seconds']}秒")


def main():
    """
    使用例のメイン実行関数
    """
    print("Step Functions Local テストフレームワーク使用例")
    print("=" * 50)
    
    try:
        # 各使用例の実行
        example_basic_client_usage()
        example_validation_usage()
        example_test_runner_usage()
        example_sample_scenarios()
        
        print("\n" + "=" * 50)
        print("使用例の実行が完了しました")
        print("\n実際のテスト実行方法:")
        print("1. Step Functions Localを起動: java -jar StepFunctionsLocal.jar --lambda-endpoint http://localhost:3001")
        print("2. SAMアプリケーションをローカルデプロイ: sam local start-lambda")
        print("3. テスト実行: python test_runner.py --config test_config.json")
        
    except Exception as e:
        logger.error(f"使用例の実行中にエラーが発生しました: {str(e)}")


if __name__ == "__main__":
    main()