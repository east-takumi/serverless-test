"""
統合ワークフローテスト
pytestフレームワークを使用した統合テストの実装
"""

import pytest
import os
import json
import time
from typing import Dict, Any

try:
    from integration_test import (
        run_integration_test_from_config,
        IntegrationTestOrchestrator,
    )
    from test_runner import load_config
except ImportError:  # pragma: no cover - fallback for package imports
    from .integration_test import (
        run_integration_test_from_config,
        IntegrationTestOrchestrator,
    )
    from .test_runner import load_config


class TestIntegrationWorkflow:
    """統合ワークフローテストクラス"""
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """テスト設定のフィクスチャ"""
        config_file = os.path.join(os.path.dirname(__file__), 'test_config.json')
        config = load_config(config_file)
        
        # 環境変数からの設定上書き
        if os.getenv('STEPFUNCTIONS_ENDPOINT'):
            config['stepfunctions_local_endpoint'] = os.getenv('STEPFUNCTIONS_ENDPOINT')
        
        if os.getenv('STATE_MACHINE_ARN'):
            config['state_machine_arn'] = os.getenv('STATE_MACHINE_ARN')
        
        return config
    
    @pytest.fixture(scope="class")
    def integration_orchestrator(self, test_config):
        """統合テストオーケストレーターのフィクスチャ"""
        return IntegrationTestOrchestrator(test_config)

    @pytest.fixture(scope="class")
    def service_connectivity(self, integration_orchestrator):
        """テスト環境でのサービス接続情報"""
        return integration_orchestrator._test_service_connectivity() or {}
    
    def test_environment_diagnostics(self, integration_orchestrator, service_connectivity):
        """環境診断テスト"""
        diagnostics = integration_orchestrator._perform_environment_diagnostics()
        
        assert diagnostics is not None, "Environment diagnostics should not be None"
        assert 'environment_ready' in diagnostics, "Diagnostics should include environment_ready status"
        assert 'system_info' in diagnostics, "Diagnostics should include system info"
        assert 'service_endpoints' in diagnostics, "Diagnostics should include service endpoints"
        
        # 重要な設定の確認
        if not diagnostics['environment_ready']:
            pytest.skip(
                f"Environment not ready for integration tests: {diagnostics.get('issues', [])}"
            )

        assert diagnostics['environment_ready'], f"Environment should be ready. Issues: {diagnostics.get('issues', [])}"

    def test_service_connectivity(self, integration_orchestrator, service_connectivity):
        """サービス接続性テスト"""
        connectivity = integration_orchestrator._test_service_connectivity()
        
        assert connectivity is not None, "Connectivity test should not be None"
        assert 'all_services_available' in connectivity, "Should include service availability status"
        assert 'service_status' in connectivity, "Should include individual service status"
        
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                f"Step Functions Local not available: {service_connectivity.get('errors', [])}"
            )

        # Step Functions Localの接続確認
        assert connectivity['all_services_available'], f"Services should be available. Errors: {connectivity.get('errors', [])}"
        assert connectivity['service_status'].get('stepfunctions_local', False), "Step Functions Local should be available"

    def test_basic_workflow_execution(self, test_config, service_connectivity):
        """基本的なワークフロー実行テスト"""
        # 基本的なテストシナリオの実行
        basic_scenario = {
            'name': 'pytest_basic_test',
            'input_data': {
                'requestId': 'pytest-test-001',
                'inputData': {
                    'value': 'pytest_test_value',
                    'metadata': {
                        'source': 'pytest_integration_test',
                        'timestamp': '2024-01-01T00:00:00Z'
                    }
                }
            },
            'timeout_seconds': 300
        }
        
        # テスト設定にシナリオを追加
        test_config_with_scenario = test_config.copy()
        test_config_with_scenario['test_scenarios'] = [basic_scenario]
        
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                f"Skipping workflow execution tests because Step Functions Local is unavailable: {service_connectivity.get('errors', [])}"
            )

        # 統合テストの実行
        orchestrator = IntegrationTestOrchestrator(test_config_with_scenario)
        result = orchestrator.run_complete_integration_test()
        
        # 結果の検証
        assert result is not None, "Integration test result should not be None"
        assert result.total_scenarios > 0, "Should have executed at least one scenario"
        assert result.successful_scenarios > 0, f"Should have successful scenarios. Errors: {result.errors}"
        assert result.overall_success, f"Integration test should succeed. Errors: {result.errors}"
    
    def test_multiple_scenarios_execution(self, test_config, service_connectivity):
        """複数シナリオ実行テスト"""
        # 複数のテストシナリオ
        scenarios = [
            {
                'name': 'pytest_scenario_1',
                'input_data': {
                    'requestId': 'pytest-multi-001',
                    'inputData': {
                        'value': 'scenario_1_value',
                        'metadata': {'source': 'pytest_multi_test'}
                    }
                }
            },
            {
                'name': 'pytest_scenario_2',
                'input_data': {
                    'requestId': 'pytest-multi-002',
                    'inputData': {
                        'value': 'scenario_2_value',
                        'metadata': {'source': 'pytest_multi_test'}
                    }
                }
            }
        ]
        
        test_config_with_scenarios = test_config.copy()
        test_config_with_scenarios['test_scenarios'] = scenarios
        
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                "Skipping multiple scenario execution tests because Step Functions Local is unavailable"
            )

        # 統合テストの実行
        orchestrator = IntegrationTestOrchestrator(test_config_with_scenarios)
        result = orchestrator.run_complete_integration_test()
        
        # 結果の検証
        assert result.total_scenarios == len(scenarios), f"Should execute {len(scenarios)} scenarios"
        assert result.successful_scenarios >= 1, "Should have at least one successful scenario"
        assert result.execution_time_seconds > 0, "Should have measurable execution time"
    
    def test_data_flow_integrity(self, test_config, service_connectivity):
        """データフロー整合性テスト"""
        # データフロー検証用のシナリオ
        dataflow_scenario = {
            'name': 'pytest_dataflow_test',
            'input_data': {
                'requestId': 'pytest-dataflow-001',
                'inputData': {
                    'value': 'dataflow_test_value',
                    'metadata': {
                        'source': 'pytest_dataflow_test',
                        'timestamp': '2024-01-01T00:00:00Z'
                    }
                }
            }
        }
        
        test_config_with_scenario = test_config.copy()
        test_config_with_scenario['test_scenarios'] = [dataflow_scenario]
        
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                "Skipping data flow integrity tests because Step Functions Local is unavailable"
            )

        orchestrator = IntegrationTestOrchestrator(test_config_with_scenario)
        result = orchestrator.run_complete_integration_test()
        
        # データフロー整合性の確認
        assert result.overall_success, "Dataflow test should succeed"
        
        # 詳細結果からデータフローの確認
        if result.detailed_results:
            first_result = result.detailed_results[0]
            assert first_result.get('success', False), "First scenario should succeed"
            
            # 最終出力の存在確認
            test_details = first_result.get('details', {}).get('test_result', {})
            final_output = test_details.get('final_output')
            assert final_output is not None, "Should have final output"
    
    def test_github_actions_compatibility(self, integration_orchestrator):
        """GitHub Actions互換性テスト"""
        compatibility = integration_orchestrator._check_github_actions_compatibility()
        
        assert compatibility is not None, "Compatibility check should not be None"
        assert 'compatible' in compatibility, "Should include compatibility status"
        assert 'required_tools_available' in compatibility, "Should check required tools"
        
        # 必要なツールの確認
        tools = compatibility['required_tools_available']
        assert tools.get('python', False), "Python should be available"

        # JavaはGitHub Actions環境では未インストールの場合があるため、利用可能な場合のみ検証
        if 'java' in tools:
            assert tools.get('java', False), "Java should be available"
    
    def test_performance_analysis(self, test_config, service_connectivity):
        """パフォーマンス分析テスト"""
        # パフォーマンス測定用のシナリオ
        performance_scenario = {
            'name': 'pytest_performance_test',
            'input_data': {
                'requestId': 'pytest-perf-001',
                'inputData': {
                    'value': 'performance_test_value'
                }
            }
        }
        
        test_config_with_scenario = test_config.copy()
        test_config_with_scenario['test_scenarios'] = [performance_scenario]
        
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                "Skipping performance analysis because Step Functions Local is unavailable"
            )

        orchestrator = IntegrationTestOrchestrator(test_config_with_scenario)
        result = orchestrator.run_complete_integration_test()
        
        # パフォーマンス分析の確認
        performance_data = result.environment_diagnostics.get('performance', {})
        assert performance_data is not None, "Should have performance data"
        
        if result.successful_scenarios > 0:
            assert performance_data.get('total_execution_time', 0) > 0, "Should have measurable execution time"
            assert performance_data.get('average_scenario_time', 0) > 0, "Should have average scenario time"
    
    def test_error_handling(self, test_config):
        """エラーハンドリングテスト"""
        # 無効なデータでのテスト（エラーハンドリング確認）
        invalid_scenario = {
            'name': 'pytest_error_handling_test',
            'input_data': {
                # requestIdを意図的に省略してエラーを発生させる
                'inputData': {
                    'value': 'error_test_value'
                }
            }
        }
        
        test_config_with_scenario = test_config.copy()
        test_config_with_scenario['test_scenarios'] = [invalid_scenario]
        
        orchestrator = IntegrationTestOrchestrator(test_config_with_scenario)
        result = orchestrator.run_complete_integration_test()
        
        # エラーハンドリングの確認
        assert result is not None, "Should return result even with errors"
        # エラーが適切に捕捉されていることを確認
        assert len(result.errors) > 0 or result.failed_scenarios > 0, "Should detect validation errors"
    
    @pytest.mark.slow
    def test_complete_integration_suite(self, test_config, service_connectivity):
        """完全な統合テストスイート（時間がかかるテスト）"""
        # デフォルトのテストシナリオを使用
        if not service_connectivity.get('all_services_available', False):
            pytest.skip(
                "Skipping complete integration suite because Step Functions Local is unavailable"
            )

        result = run_integration_test_from_config()
        
        # 包括的な結果検証
        assert result is not None, "Integration test should return result"
        assert result.total_scenarios > 0, "Should execute test scenarios"
        
        # 成功率の確認（少なくとも50%は成功すべき）
        success_rate = result.success_rate
        assert success_rate >= 50.0, f"Success rate should be at least 50%, got {success_rate}%"
        
        # 実行時間の妥当性確認
        assert result.execution_time_seconds > 0, "Should have measurable execution time"
        assert result.execution_time_seconds < 600, "Should complete within 10 minutes"


@pytest.mark.integration
class TestWorkflowComponents:
    """ワークフローコンポーネントテスト"""
    
    def test_stepfunctions_client_initialization(self):
        """Step Functions クライアント初期化テスト"""
        try:
            from stepfunctions_local_client import StepFunctionsLocalClient
        except ImportError:  # pragma: no cover - fallback for package imports
            from .stepfunctions_local_client import StepFunctionsLocalClient
        
        endpoint = os.getenv('STEPFUNCTIONS_ENDPOINT', 'http://localhost:8083')
        client = StepFunctionsLocalClient(local_endpoint=endpoint)
        
        assert client is not None, "Client should be initialized"
        assert client.local_endpoint == endpoint, "Endpoint should be set correctly"
    
    def test_input_output_validator(self):
        """入出力バリデーターテスト"""
        try:
            from input_output_validator import InputOutputValidator
        except ImportError:  # pragma: no cover - fallback for package imports
            from .input_output_validator import InputOutputValidator
        
        validator = InputOutputValidator()
        
        # 有効な入力データのテスト
        valid_input = {
            'requestId': 'test-001',
            'inputData': {
                'value': 'test_value',
                'metadata': {'source': 'test'}
            }
        }
        
        result = validator.validate_workflow_input(valid_input)
        assert result.is_valid, f"Valid input should pass validation. Errors: {result.errors}"
        
        # 無効な入力データのテスト
        invalid_input = {
            'inputData': {
                'value': 'test_value'
            }
            # requestId が欠落
        }
        
        result = validator.validate_workflow_input(invalid_input)
        assert not result.is_valid, "Invalid input should fail validation"
        assert len(result.errors) > 0, "Should have validation errors"
    
    def test_workflow_execution_tester_initialization(self):
        """ワークフロー実行テスター初期化テスト"""
        try:
            from workflow_execution_test import WorkflowExecutionTester
            from stepfunctions_local_client import StepFunctionsLocalClient
        except ImportError:  # pragma: no cover - fallback for package imports
            from .workflow_execution_test import WorkflowExecutionTester
            from .stepfunctions_local_client import StepFunctionsLocalClient
        
        endpoint = os.getenv('STEPFUNCTIONS_ENDPOINT', 'http://localhost:8083')
        state_machine_arn = os.getenv('STATE_MACHINE_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:test')
        
        client = StepFunctionsLocalClient(local_endpoint=endpoint)
        tester = WorkflowExecutionTester(client, state_machine_arn)
        
        assert tester is not None, "Tester should be initialized"
        assert tester.state_machine_arn == state_machine_arn, "State machine ARN should be set correctly"


if __name__ == '__main__':
    # 直接実行時のテスト
    pytest.main([__file__, '-v'])