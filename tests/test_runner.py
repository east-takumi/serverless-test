"""
メインテストランナー
Step Functions Localを使用したワークフロー実行テストの統合実行
"""

import json
import sys
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from stepfunctions_local_client import StepFunctionsLocalClient
    from workflow_execution_test import (
        WorkflowExecutionTester,
        WorkflowDataFlowTracer,
        create_sample_test_scenarios,
    )
    from input_output_validator import InputOutputValidator
except ImportError:  # pragma: no cover - fallback for package imports
    from .stepfunctions_local_client import StepFunctionsLocalClient
    from .workflow_execution_test import (
        WorkflowExecutionTester,
        WorkflowDataFlowTracer,
        create_sample_test_scenarios,
    )
    from .input_output_validator import InputOutputValidator

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('workflow_test.log')
    ]
)

logger = logging.getLogger(__name__)


class StepFunctionsTestRunner:
    """
    Step Functions テスト実行統合クラス
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        テストランナーの初期化
        
        Args:
            config: テスト設定
        """
        self.config = config
        self.client = None
        self.tester = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def setup(self) -> bool:
        """
        テスト環境のセットアップ
        
        Returns:
            bool: セットアップ成功の場合True
        """
        try:
            # Step Functions Localクライアントの初期化
            self.client = StepFunctionsLocalClient(
                local_endpoint=self.config.get('stepfunctions_local_endpoint', 'http://localhost:8083'),
                region_name=self.config.get('region_name', 'us-east-1')
            )
            
            # 接続テスト
            if not self.client.test_connection():
                self.logger.error("Failed to connect to Step Functions Local")
                return False
            
            # ワークフロー実行テスターの初期化
            state_machine_arn = self.config.get('state_machine_arn')
            if not state_machine_arn:
                self.logger.error("state_machine_arn is required in configuration")
                return False
            
            self.tester = WorkflowExecutionTester(self.client, state_machine_arn)
            
            self.logger.info("Test environment setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        全テストの実行
        
        Returns:
            Dict: テスト結果レポート
        """
        if not self.setup():
            return {
                'status': 'SETUP_FAILED',
                'error': 'Failed to setup test environment',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # テストシナリオの取得
            test_scenarios = self.config.get('test_scenarios')
            if not test_scenarios:
                self.logger.info("No custom test scenarios provided, using default scenarios")
                test_scenarios = create_sample_test_scenarios()
            
            self.logger.info(f"Running {len(test_scenarios)} test scenarios")
            
            # テスト実行
            test_results = self.tester.run_multiple_test_scenarios(test_scenarios)
            
            # レポート生成
            report = self.tester.generate_test_report(test_results)
            
            # 詳細なデータフロー分析（成功したテストのみ）
            successful_results = [r for r in test_results if r.success and r.execution_history]
            if successful_results:
                report['data_flow_analysis'] = self._analyze_data_flows(successful_results)
            
            # 設定情報の追加
            report['test_configuration'] = {
                'stepfunctions_endpoint': self.config.get('stepfunctions_local_endpoint'),
                'state_machine_arn': self.config.get('state_machine_arn'),
                'test_scenarios_count': len(test_scenarios)
            }
            
            self.logger.info(f"All tests completed. Overall status: {report['overall_status']}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error during test execution: {str(e)}")
            return {
                'status': 'EXECUTION_FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_data_flows(self, successful_results: List) -> Dict[str, Any]:
        """
        成功したテストのデータフロー分析
        
        Args:
            successful_results: 成功したテスト結果のリスト
            
        Returns:
            Dict: データフロー分析結果
        """
        tracer = WorkflowDataFlowTracer()
        analysis_results = []
        
        for result in successful_results:
            if result.execution_history:
                flow_trace = tracer.trace_data_flow(result.execution_history)
                analysis_results.append({
                    'test_name': result.test_name,
                    'flow_trace': flow_trace
                })
        
        return {
            'analyzed_executions': len(analysis_results),
            'flow_analyses': analysis_results
        }
    
    def run_single_test(self, test_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一テストの実行
        
        Args:
            test_name: テスト名
            input_data: 入力データ
            
        Returns:
            Dict: テスト結果
        """
        if not self.setup():
            return {
                'status': 'SETUP_FAILED',
                'error': 'Failed to setup test environment'
            }
        
        try:
            result = self.tester.run_complete_workflow_test(test_name, input_data)
            
            return {
                'status': 'COMPLETED',
                'test_result': {
                    'test_name': result.test_name,
                    'success': result.success,
                    'execution_status': result.execution_status,
                    'execution_time_seconds': result.execution_time_seconds,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'final_output': result.final_output
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error during single test execution: {str(e)}")
            return {
                'status': 'EXECUTION_FAILED',
                'error': str(e)
            }


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    設定ファイルの読み込み
    
    Args:
        config_file: 設定ファイルパス
        
    Returns:
        Dict: 設定データ
    """
    default_config = {
        'stepfunctions_local_endpoint': 'http://localhost:8083',
        'region_name': 'us-east-1',
        'state_machine_arn': 'arn:aws:states:us-east-1:123456789012:stateMachine:WorkflowStateMachine',
        'test_scenarios': None
    }
    
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
                logger.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {str(e)}")
            logger.info("Using default configuration")
    
    return default_config


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Step Functions Local Workflow Test Runner')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--output', '-o', help='Output report file path', default='test_report.json')
    parser.add_argument('--single-test', help='Run single test with specified name')
    parser.add_argument('--input-data', help='Input data for single test (JSON string)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # ログレベルの設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 設定の読み込み
    config = load_config(args.config)
    
    # テストランナーの初期化
    runner = StepFunctionsTestRunner(config)
    
    try:
        if args.single_test:
            # 単一テストの実行
            input_data = {}
            if args.input_data:
                try:
                    input_data = json.loads(args.input_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in input data: {str(e)}")
                    sys.exit(1)
            
            result = runner.run_single_test(args.single_test, input_data)
            
        else:
            # 全テストの実行
            result = runner.run_all_tests()
        
        # 結果の出力
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Test report saved to {args.output}")
        
        # 終了コードの設定
        if result.get('overall_status') == 'FAILED' or result.get('status') in ['SETUP_FAILED', 'EXECUTION_FAILED']:
            logger.error("Tests failed")
            sys.exit(1)
        else:
            logger.info("All tests passed")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()