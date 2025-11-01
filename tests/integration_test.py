"""
完全なワークフロー統合テスト実装
全コンポーネントを統合したエンドツーエンドテストとGitHub Actions環境での実行確認・デバッグ機能
"""

import json
import time
import logging
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import traceback

from stepfunctions_local_client import StepFunctionsLocalClient, WorkflowExecutionMonitor
from workflow_execution_test import WorkflowExecutionTester, WorkflowDataFlowTracer, create_sample_test_scenarios
from input_output_validator import InputOutputValidator, DataFlowValidator, AssertionHelper
from test_runner import StepFunctionsTestRunner, load_config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('integration_test.log')
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestEnvironment:
    """統合テスト環境の設定と状態"""
    stepfunctions_endpoint: str
    sam_api_endpoint: str
    state_machine_arn: Optional[str]
    environment_ready: bool = False
    services_status: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.services_status is None:
            self.services_status = {
                'stepfunctions_local': False,
                'sam_local_api': False,
                'state_machine_created': False
            }


@dataclass
class IntegrationTestResult:
    """統合テスト結果"""
    test_suite_name: str
    environment: IntegrationTestEnvironment
    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int
    execution_time_seconds: float
    detailed_results: List[Dict[str, Any]]
    environment_diagnostics: Dict[str, Any]
    github_actions_compatible: bool
    errors: List[str]
    warnings: List[str]
    
    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_scenarios == 0:
            return 0.0
        return (self.successful_scenarios / self.total_scenarios) * 100
    
    @property
    def overall_success(self) -> bool:
        """全体的な成功判定"""
        return (self.failed_scenarios == 0 and 
                len(self.errors) == 0 and 
                self.environment.environment_ready)


class IntegrationTestOrchestrator:
    """
    統合テストオーケストレーター
    全コンポーネントの統合テストを管理・実行
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        統合テストオーケストレーターの初期化
        
        Args:
            config: テスト設定
        """
        self.config = config
        self.environment = IntegrationTestEnvironment(
            stepfunctions_endpoint=config.get('stepfunctions_local_endpoint', 'http://localhost:8083'),
            sam_api_endpoint=config.get('sam_api_endpoint', 'http://localhost:3001'),
            state_machine_arn=config.get('state_machine_arn')
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def run_complete_integration_test(self) -> IntegrationTestResult:
        """
        完全な統合テストの実行
        
        Returns:
            IntegrationTestResult: 統合テスト結果
        """
        start_time = time.time()
        
        # 結果オブジェクトの初期化
        result = IntegrationTestResult(
            test_suite_name="Complete Workflow Integration Test",
            environment=self.environment,
            total_scenarios=0,
            successful_scenarios=0,
            failed_scenarios=0,
            execution_time_seconds=0.0,
            detailed_results=[],
            environment_diagnostics={},
            github_actions_compatible=False,
            errors=[],
            warnings=[]
        )
        
        try:
            self.logger.info("🚀 Starting complete integration test suite...")
            
            # 1. 環境診断とセットアップ検証
            self.logger.info("📋 Phase 1: Environment diagnostics and setup verification")
            env_diagnostics = self._perform_environment_diagnostics()
            result.environment_diagnostics = env_diagnostics
            
            if not env_diagnostics.get('environment_ready', False):
                result.errors.append("Environment is not ready for testing")
                return result
            
            # 2. サービス接続性テスト
            self.logger.info("🔗 Phase 2: Service connectivity testing")
            connectivity_result = self._test_service_connectivity()
            
            if not connectivity_result['all_services_available']:
                result.errors.extend(connectivity_result['errors'])
                result.warnings.extend(connectivity_result['warnings'])
                return result
            
            # 3. ワークフロー実行テスト
            self.logger.info("⚙️ Phase 3: Workflow execution testing")
            workflow_results = self._execute_workflow_test_scenarios()
            
            result.total_scenarios = len(workflow_results)
            result.successful_scenarios = sum(1 for r in workflow_results if r.get('success', False))
            result.failed_scenarios = result.total_scenarios - result.successful_scenarios
            result.detailed_results = workflow_results
            
            # エラーと警告の集約
            for wr in workflow_results:
                result.errors.extend(wr.get('errors', []))
                result.warnings.extend(wr.get('warnings', []))
            
            # 4. データフロー整合性検証
            self.logger.info("🔍 Phase 4: Data flow integrity verification")
            dataflow_verification = self._verify_data_flow_integrity(workflow_results)
            
            if not dataflow_verification['integrity_verified']:
                result.errors.extend(dataflow_verification['errors'])
                result.warnings.extend(dataflow_verification['warnings'])
            
            # 5. GitHub Actions互換性チェック
            self.logger.info("🐙 Phase 5: GitHub Actions compatibility check")
            github_compatibility = self._check_github_actions_compatibility()
            result.github_actions_compatible = github_compatibility['compatible']
            
            if not github_compatibility['compatible']:
                result.warnings.extend(github_compatibility['issues'])
            
            # 6. パフォーマンス分析
            self.logger.info("📊 Phase 6: Performance analysis")
            performance_analysis = self._analyze_performance_metrics(workflow_results)
            result.environment_diagnostics['performance'] = performance_analysis
            
        except Exception as e:
            self.logger.error(f"Critical error during integration test: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            result.errors.append(f"Critical integration test error: {str(e)}")
        
        finally:
            result.execution_time_seconds = time.time() - start_time
            
            # 最終結果のログ出力
            self._log_final_results(result)
        
        return result
    
    def _perform_environment_diagnostics(self) -> Dict[str, Any]:
        """環境診断の実行"""
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'environment_ready': False,
            'system_info': {},
            'service_endpoints': {},
            'configuration_status': {},
            'issues': []
        }
        
        try:
            # システム情報の収集
            diagnostics['system_info'] = {
                'python_version': sys.version,
                'platform': sys.platform,
                'working_directory': os.getcwd(),
                'environment_variables': {
                    'STEPFUNCTIONS_ENDPOINT': os.getenv('STEPFUNCTIONS_ENDPOINT'),
                    'STATE_MACHINE_ARN': os.getenv('STATE_MACHINE_ARN'),
                    'CI': os.getenv('CI', 'false'),
                    'GITHUB_ACTIONS': os.getenv('GITHUB_ACTIONS', 'false')
                }
            }
            
            # サービスエンドポイントの確認
            diagnostics['service_endpoints'] = {
                'stepfunctions_local': self.environment.stepfunctions_endpoint,
                'sam_local_api': self.environment.sam_api_endpoint,
                'configured_state_machine_arn': self.environment.state_machine_arn
            }
            
            # 設定状態の確認
            required_config = ['stepfunctions_local_endpoint', 'state_machine_arn']
            config_status = {}
            
            for key in required_config:
                config_status[key] = {
                    'present': key in self.config,
                    'value': self.config.get(key, 'NOT_SET')
                }
                
                if not self.config.get(key):
                    diagnostics['issues'].append(f"Required configuration '{key}' is missing or empty")
            
            diagnostics['configuration_status'] = config_status
            
            # 環境準備状況の判定
            diagnostics['environment_ready'] = len(diagnostics['issues']) == 0
            
        except Exception as e:
            diagnostics['issues'].append(f"Environment diagnostics error: {str(e)}")
        
        return diagnostics
    
    def _test_service_connectivity(self) -> Dict[str, Any]:
        """サービス接続性のテスト"""
        connectivity_result = {
            'all_services_available': False,
            'service_status': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Step Functions Local接続テスト
            self.logger.info("Testing Step Functions Local connectivity...")
            client = StepFunctionsLocalClient(
                local_endpoint=self.environment.stepfunctions_endpoint
            )
            
            stepfunctions_available = client.test_connection()
            connectivity_result['service_status']['stepfunctions_local'] = stepfunctions_available
            
            if not stepfunctions_available:
                connectivity_result['errors'].append(
                    f"Step Functions Local not available at {self.environment.stepfunctions_endpoint}"
                )
            else:
                self.logger.info("✓ Step Functions Local connection successful")
            
            # SAM Local API接続テスト（オプション）
            try:
                import requests
                sam_response = requests.get(f"{self.environment.sam_api_endpoint}/", timeout=5)
                sam_available = sam_response.status_code in [200, 404]  # 404も正常（エンドポイントが存在しない場合）
            except Exception:
                sam_available = False
            
            connectivity_result['service_status']['sam_local_api'] = sam_available
            
            if not sam_available:
                connectivity_result['warnings'].append(
                    f"SAM Local API may not be available at {self.environment.sam_api_endpoint}"
                )
            else:
                self.logger.info("✓ SAM Local API connection successful")
            
            # ステートマシン存在確認
            if stepfunctions_available and self.environment.state_machine_arn:
                try:
                    # ステートマシンの存在確認（ダミー実行ARNではなく、ステートマシンの詳細取得で確認）
                    client.client.describe_state_machine(stateMachineArn=self.environment.state_machine_arn)
                    state_machine_available = True
                    self.logger.info("✓ State machine exists and is accessible")
                except Exception as e:
                    # ステートマシンが存在しない場合は警告として扱う
                    state_machine_available = False
                    connectivity_result['warnings'].append(f"State machine may not exist: {str(e)}")
                
                connectivity_result['service_status']['state_machine'] = state_machine_available
            
            # 全体的な可用性判定
            connectivity_result['all_services_available'] = (
                stepfunctions_available and 
                len(connectivity_result['errors']) == 0
            )
            
        except Exception as e:
            connectivity_result['errors'].append(f"Service connectivity test error: {str(e)}")
        
        return connectivity_result
    
    def _execute_workflow_test_scenarios(self) -> List[Dict[str, Any]]:
        """ワークフローテストシナリオの実行"""
        workflow_results = []
        
        try:
            # テストランナーの初期化
            runner = StepFunctionsTestRunner(self.config)
            
            # テストシナリオの取得
            test_scenarios = self.config.get('test_scenarios')
            if not test_scenarios:
                self.logger.info("Using default test scenarios")
                test_scenarios = create_sample_test_scenarios()
            
            self.logger.info(f"Executing {len(test_scenarios)} test scenarios...")
            
            # 各シナリオの実行
            for i, scenario in enumerate(test_scenarios, 1):
                scenario_name = scenario.get('name', f'scenario_{i}')
                self.logger.info(f"Executing scenario {i}/{len(test_scenarios)}: {scenario_name}")
                
                scenario_result = {
                    'scenario_name': scenario_name,
                    'scenario_index': i,
                    'success': False,
                    'execution_time': 0.0,
                    'errors': [],
                    'warnings': [],
                    'details': {}
                }
                
                try:
                    start_time = time.time()
                    
                    # 単一テストの実行
                    test_result = runner.run_single_test(
                        scenario_name, 
                        scenario.get('input_data', {})
                    )
                    
                    scenario_result['execution_time'] = time.time() - start_time
                    scenario_result['details'] = test_result
                    
                    # 成功判定
                    if test_result.get('status') == 'COMPLETED':
                        test_data = test_result.get('test_result', {})
                        scenario_result['success'] = test_data.get('success', False)
                        
                        if not scenario_result['success']:
                            scenario_result['errors'].extend(test_data.get('errors', []))
                            scenario_result['warnings'].extend(test_data.get('warnings', []))
                    else:
                        scenario_result['errors'].append(f"Test execution failed: {test_result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    scenario_result['errors'].append(f"Scenario execution error: {str(e)}")
                    self.logger.error(f"Error in scenario {scenario_name}: {str(e)}")
                
                workflow_results.append(scenario_result)
                
                # シナリオ間の間隔
                if i < len(test_scenarios):
                    time.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Workflow test scenarios execution error: {str(e)}")
            workflow_results.append({
                'scenario_name': 'execution_error',
                'success': False,
                'errors': [f"Test scenarios execution error: {str(e)}"],
                'warnings': [],
                'details': {}
            })
        
        return workflow_results
    
    def _verify_data_flow_integrity(self, workflow_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """データフロー整合性の検証"""
        verification_result = {
            'integrity_verified': False,
            'verified_scenarios': 0,
            'total_scenarios': len(workflow_results),
            'data_flow_issues': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            dataflow_validator = DataFlowValidator()
            successful_results = [r for r in workflow_results if r.get('success', False)]
            
            for result in successful_results:
                scenario_name = result.get('scenario_name', 'unknown')
                
                try:
                    # 詳細なデータフロー検証は成功したテストのみ実行
                    test_details = result.get('details', {}).get('test_result', {})
                    final_output = test_details.get('final_output')
                    
                    if final_output:
                        # 基本的な出力構造の確認
                        validator = InputOutputValidator()
                        validation_result = validator.validate_state3_output(final_output)
                        
                        if validation_result.is_valid:
                            verification_result['verified_scenarios'] += 1
                        else:
                            verification_result['data_flow_issues'].append({
                                'scenario': scenario_name,
                                'issues': validation_result.errors
                            })
                    
                except Exception as e:
                    verification_result['warnings'].append(
                        f"Data flow verification failed for scenario {scenario_name}: {str(e)}"
                    )
            
            # 整合性判定
            verification_result['integrity_verified'] = (
                verification_result['verified_scenarios'] > 0 and
                len(verification_result['data_flow_issues']) == 0
            )
            
        except Exception as e:
            verification_result['errors'].append(f"Data flow integrity verification error: {str(e)}")
        
        return verification_result
    
    def _check_github_actions_compatibility(self) -> Dict[str, Any]:
        """GitHub Actions互換性のチェック"""
        compatibility_result = {
            'compatible': False,
            'ci_environment_detected': False,
            'required_tools_available': {},
            'issues': []
        }
        
        try:
            # CI環境の検出
            ci_detected = os.getenv('CI', '').lower() == 'true'
            github_actions_detected = os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
            
            compatibility_result['ci_environment_detected'] = ci_detected or github_actions_detected
            
            # 必要なツールの確認
            required_tools = ['python', 'java']
            tools_status = {}
            
            for tool in required_tools:
                try:
                    import subprocess
                    result = subprocess.run([tool, '--version'], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=10)
                    tools_status[tool] = result.returncode == 0
                except Exception:
                    tools_status[tool] = False
            
            compatibility_result['required_tools_available'] = tools_status
            
            # 互換性の問題チェック
            if not all(tools_status.values()):
                missing_tools = [tool for tool, available in tools_status.items() if not available]
                compatibility_result['issues'].append(f"Missing required tools: {missing_tools}")
            
            # 環境変数の確認
            required_env_vars = ['STEPFUNCTIONS_ENDPOINT', 'STATE_MACHINE_ARN']
            missing_env_vars = []
            
            for env_var in required_env_vars:
                if not os.getenv(env_var):
                    missing_env_vars.append(env_var)
            
            if missing_env_vars:
                compatibility_result['issues'].append(f"Missing environment variables: {missing_env_vars}")
            
            # 全体的な互換性判定
            compatibility_result['compatible'] = (
                all(tools_status.values()) and 
                len(missing_env_vars) == 0
            )
            
        except Exception as e:
            compatibility_result['issues'].append(f"GitHub Actions compatibility check error: {str(e)}")
        
        return compatibility_result
    
    def _analyze_performance_metrics(self, workflow_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """パフォーマンス分析"""
        performance_analysis = {
            'total_execution_time': 0.0,
            'average_scenario_time': 0.0,
            'fastest_scenario': None,
            'slowest_scenario': None,
            'performance_summary': {}
        }
        
        try:
            execution_times = []
            scenario_times = {}
            
            for result in workflow_results:
                scenario_name = result.get('scenario_name', 'unknown')
                execution_time = result.get('execution_time', 0.0)
                
                execution_times.append(execution_time)
                scenario_times[scenario_name] = execution_time
            
            if execution_times:
                performance_analysis['total_execution_time'] = sum(execution_times)
                performance_analysis['average_scenario_time'] = sum(execution_times) / len(execution_times)
                
                fastest_time = min(execution_times)
                slowest_time = max(execution_times)
                
                performance_analysis['fastest_scenario'] = {
                    'name': next(name for name, time in scenario_times.items() if time == fastest_time),
                    'time': fastest_time
                }
                
                performance_analysis['slowest_scenario'] = {
                    'name': next(name for name, time in scenario_times.items() if time == slowest_time),
                    'time': slowest_time
                }
                
                performance_analysis['performance_summary'] = {
                    'total_scenarios': len(execution_times),
                    'total_time_seconds': performance_analysis['total_execution_time'],
                    'average_time_seconds': performance_analysis['average_scenario_time'],
                    'time_range_seconds': slowest_time - fastest_time
                }
        
        except Exception as e:
            performance_analysis['error'] = f"Performance analysis error: {str(e)}"
        
        return performance_analysis
    
    def _log_final_results(self, result: IntegrationTestResult):
        """最終結果のログ出力"""
        self.logger.info("=" * 60)
        self.logger.info("🏁 INTEGRATION TEST RESULTS SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Test Suite: {result.test_suite_name}")
        self.logger.info(f"Total Scenarios: {result.total_scenarios}")
        self.logger.info(f"Successful: {result.successful_scenarios}")
        self.logger.info(f"Failed: {result.failed_scenarios}")
        self.logger.info(f"Success Rate: {result.success_rate:.1f}%")
        self.logger.info(f"Execution Time: {result.execution_time_seconds:.2f} seconds")
        self.logger.info(f"Overall Success: {'✅ PASS' if result.overall_success else '❌ FAIL'}")
        self.logger.info(f"GitHub Actions Compatible: {'✅ YES' if result.github_actions_compatible else '⚠️ ISSUES'}")
        
        if result.errors:
            self.logger.error("❌ ERRORS:")
            for error in result.errors:
                self.logger.error(f"  - {error}")
        
        if result.warnings:
            self.logger.warning("⚠️ WARNINGS:")
            for warning in result.warnings:
                self.logger.warning(f"  - {warning}")
        
        self.logger.info("=" * 60)
    
    def generate_integration_report(self, result: IntegrationTestResult) -> Dict[str, Any]:
        """統合テストレポートの生成"""
        report = {
            'integration_test_report': {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'test_suite': result.test_suite_name,
                    'execution_time_seconds': result.execution_time_seconds,
                    'github_actions_compatible': result.github_actions_compatible
                },
                'summary': {
                    'total_scenarios': result.total_scenarios,
                    'successful_scenarios': result.successful_scenarios,
                    'failed_scenarios': result.failed_scenarios,
                    'success_rate_percent': result.success_rate,
                    'overall_success': result.overall_success
                },
                'environment': asdict(result.environment),
                'diagnostics': result.environment_diagnostics,
                'detailed_results': result.detailed_results,
                'issues': {
                    'errors': result.errors,
                    'warnings': result.warnings
                }
            }
        }
        
        return report


def run_integration_test_from_config(config_file: Optional[str] = None) -> IntegrationTestResult:
    """
    設定ファイルから統合テストを実行
    
    Args:
        config_file: 設定ファイルパス
        
    Returns:
        IntegrationTestResult: 統合テスト結果
    """
    try:
        # 設定の読み込み
        config = load_config(config_file)
        
        # 環境変数からの設定上書き
        if os.getenv('STEPFUNCTIONS_ENDPOINT'):
            config['stepfunctions_local_endpoint'] = os.getenv('STEPFUNCTIONS_ENDPOINT')
        
        if os.getenv('STATE_MACHINE_ARN'):
            config['state_machine_arn'] = os.getenv('STATE_MACHINE_ARN')
        
        # 統合テストの実行
        orchestrator = IntegrationTestOrchestrator(config)
        result = orchestrator.run_complete_integration_test()
        
        return result
        
    except Exception as e:
        logger.error(f"Integration test execution failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # エラー時のダミー結果
        return IntegrationTestResult(
            test_suite_name="Integration Test (Failed)",
            environment=IntegrationTestEnvironment(
                stepfunctions_endpoint="unknown",
                sam_api_endpoint="unknown",
                state_machine_arn=None
            ),
            total_scenarios=0,
            successful_scenarios=0,
            failed_scenarios=0,
            execution_time_seconds=0.0,
            detailed_results=[],
            environment_diagnostics={},
            github_actions_compatible=False,
            errors=[f"Integration test setup failed: {str(e)}"],
            warnings=[]
        )


def main():
    """統合テストのメイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Step Functions Integration Test')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--output', '-o', help='Output report file path', default='integration_test_report.json')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # ログレベルの設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logger.info("🚀 Starting Step Functions Integration Test Suite")
        
        # 統合テストの実行
        result = run_integration_test_from_config(args.config)
        
        # レポートの生成と保存
        orchestrator = IntegrationTestOrchestrator({})
        report = orchestrator.generate_integration_report(result)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📊 Integration test report saved to {args.output}")
        
        # 終了コードの設定
        if result.overall_success:
            logger.info("🎉 Integration test completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Integration test failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Integration test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()