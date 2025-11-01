"""
ワークフロー実行テスト実装
完全なワークフロー実行をテストするメイン関数と実行履歴の取得・データフロー追跡機能
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from stepfunctions_local_client import StepFunctionsLocalClient, WorkflowExecutionMonitor
from input_output_validator import InputOutputValidator, DataFlowValidator, AssertionHelper, ValidationResult

# ログ設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class WorkflowTestResult:
    """ワークフロー実行テスト結果"""
    test_name: str
    success: bool
    execution_arn: Optional[str]
    execution_status: Optional[str]
    input_data: Dict[str, Any]
    final_output: Optional[Dict[str, Any]]
    execution_time_seconds: float
    validation_results: List[ValidationResult]
    errors: List[str]
    warnings: List[str]
    execution_history: Optional[List[Dict[str, Any]]]
    data_flow_trace: Optional[List[Dict[str, Any]]]


class WorkflowExecutionTester:
    """
    ワークフロー実行テストクラス
    完全なワークフロー実行とデータフロー検証を行う
    """
    
    def __init__(self, 
                 stepfunctions_client: StepFunctionsLocalClient,
                 state_machine_arn: str):
        """
        テスタークラスの初期化
        
        Args:
            stepfunctions_client: Step Functions Localクライアント
            state_machine_arn: テスト対象のステートマシンARN
        """
        self.client = stepfunctions_client
        self.state_machine_arn = state_machine_arn
        self.monitor = WorkflowExecutionMonitor(stepfunctions_client)
        self.input_validator = InputOutputValidator()
        self.dataflow_validator = DataFlowValidator()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def run_complete_workflow_test(self, 
                                 test_name: str,
                                 input_data: Dict[str, Any],
                                 timeout_seconds: int = 300) -> WorkflowTestResult:
        """
        完全なワークフロー実行テストを実行
        
        Args:
            test_name: テスト名
            input_data: 入力データ
            timeout_seconds: タイムアウト時間
            
        Returns:
            WorkflowTestResult: テスト結果
        """
        start_time = time.time()
        test_result = WorkflowTestResult(
            test_name=test_name,
            success=False,
            execution_arn=None,
            execution_status=None,
            input_data=input_data,
            final_output=None,
            execution_time_seconds=0.0,
            validation_results=[],
            errors=[],
            warnings=[],
            execution_history=None,
            data_flow_trace=None
        )
        
        try:
            self.logger.info(f"Starting workflow test: {test_name}")
            
            # 1. 入力データの事前検証
            input_validation = self.input_validator.validate_workflow_input(input_data)
            test_result.validation_results.append(input_validation)
            
            if not input_validation.is_valid:
                test_result.errors.extend(input_validation.errors)
                test_result.warnings.extend(input_validation.warnings)
                return test_result
            
            # 2. ワークフロー実行の開始
            execution_arn = self.client.start_execution(
                state_machine_arn=self.state_machine_arn,
                input_data=input_data,
                execution_name=f"{test_name}_{int(time.time())}"
            )
            
            if not execution_arn:
                test_result.errors.append("Failed to start workflow execution")
                return test_result
            
            test_result.execution_arn = execution_arn
            self.logger.info(f"Workflow execution started: {execution_arn}")
            
            # 3. 実行完了まで監視
            monitoring_result = self.monitor.monitor_execution_with_details(execution_arn)
            
            if monitoring_result.get('errors'):
                test_result.errors.extend(monitoring_result['errors'])
            
            # 4. 実行結果の取得
            final_status = monitoring_result.get('finalStatus')
            if final_status:
                test_result.execution_status = final_status['status']
                test_result.final_output = final_status.get('output')
            
            test_result.execution_history = monitoring_result.get('events')
            test_result.data_flow_trace = monitoring_result.get('dataFlow')
            
            # 5. 実行成功の場合のみ詳細検証を実行
            if test_result.execution_status == 'SUCCEEDED' and test_result.final_output:
                validation_results = self._perform_detailed_validation(
                    input_data, 
                    test_result.final_output,
                    monitoring_result.get('stateOutputs', {})
                )
                test_result.validation_results.extend(validation_results)
                
                # 全ての検証がパスした場合のみ成功とする
                test_result.success = all(vr.is_valid for vr in validation_results)
                
                # エラーと警告を集約
                for vr in validation_results:
                    test_result.errors.extend(vr.errors)
                    test_result.warnings.extend(vr.warnings)
            
            elif test_result.execution_status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
                test_result.errors.append(f"Workflow execution failed with status: {test_result.execution_status}")
            
        except Exception as e:
            self.logger.error(f"Error during workflow test execution: {str(e)}")
            test_result.errors.append(f"Test execution error: {str(e)}")
        
        finally:
            test_result.execution_time_seconds = time.time() - start_time
            
            self.logger.info(f"Workflow test completed: {test_name}")
            self.logger.info(f"Test result: {'SUCCESS' if test_result.success else 'FAILED'}")
            self.logger.info(f"Execution time: {test_result.execution_time_seconds:.2f} seconds")
            
            if test_result.errors:
                self.logger.error(f"Test errors: {test_result.errors}")
        
        return test_result
    
    def _perform_detailed_validation(self, 
                                   input_data: Dict[str, Any],
                                   final_output: Dict[str, Any],
                                   state_outputs: Dict[str, Any]) -> List[ValidationResult]:
        """
        詳細な検証を実行
        
        Args:
            input_data: 入力データ
            final_output: 最終出力データ
            state_outputs: 各ステートの出力データ
            
        Returns:
            List[ValidationResult]: 検証結果のリスト
        """
        validation_results = []
        
        try:
            # State3（最終）出力の検証
            state3_validation = self.input_validator.validate_state3_output(final_output)
            validation_results.append(state3_validation)
            
            # 各ステートの出力が取得できている場合の個別検証
            if 'State1' in state_outputs:
                state1_validation = self.input_validator.validate_state1_output(state_outputs['State1'])
                validation_results.append(state1_validation)
            
            if 'State2' in state_outputs:
                state2_validation = self.input_validator.validate_state2_output(state_outputs['State2'])
                validation_results.append(state2_validation)
            
            # データフロー連続性の検証
            if all(state in state_outputs for state in ['State1', 'State2']):
                dataflow_validation = self.dataflow_validator.validate_data_flow_continuity(
                    input_data,
                    state_outputs['State1'],
                    state_outputs['State2'],
                    final_output
                )
                validation_results.append(dataflow_validation)
            
        except Exception as e:
            error_validation = ValidationResult(
                is_valid=False,
                errors=[f"Validation execution error: {str(e)}"],
                warnings=[]
            )
            validation_results.append(error_validation)
        
        return validation_results
    
    def run_multiple_test_scenarios(self, test_scenarios: List[Dict[str, Any]]) -> List[WorkflowTestResult]:
        """
        複数のテストシナリオを実行
        
        Args:
            test_scenarios: テストシナリオのリスト
            
        Returns:
            List[WorkflowTestResult]: 全テスト結果
        """
        all_results = []
        
        for i, scenario in enumerate(test_scenarios):
            test_name = scenario.get('name', f'test_scenario_{i+1}')
            input_data = scenario.get('input_data', {})
            timeout = scenario.get('timeout_seconds', 300)
            
            self.logger.info(f"Running test scenario {i+1}/{len(test_scenarios)}: {test_name}")
            
            result = self.run_complete_workflow_test(test_name, input_data, timeout)
            all_results.append(result)
            
            # テスト間の間隔を設ける
            if i < len(test_scenarios) - 1:
                time.sleep(2)
        
        return all_results
    
    def generate_test_report(self, test_results: List[WorkflowTestResult]) -> Dict[str, Any]:
        """
        テスト結果レポートの生成
        
        Args:
            test_results: テスト結果のリスト
            
        Returns:
            Dict: テストレポート
        """
        total_tests = len(test_results)
        successful_tests = sum(1 for result in test_results if result.success)
        failed_tests = total_tests - successful_tests
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_execution_time': sum(result.execution_time_seconds for result in test_results)
            },
            'test_details': [],
            'overall_status': 'PASSED' if failed_tests == 0 else 'FAILED',
            'generated_at': datetime.now().isoformat()
        }
        
        for result in test_results:
            test_detail = {
                'test_name': result.test_name,
                'status': 'PASSED' if result.success else 'FAILED',
                'execution_status': result.execution_status,
                'execution_time_seconds': result.execution_time_seconds,
                'validation_count': len(result.validation_results),
                'error_count': len(result.errors),
                'warning_count': len(result.warnings),
                'errors': result.errors,
                'warnings': result.warnings
            }
            report['test_details'].append(test_detail)
        
        return report


class WorkflowDataFlowTracer:
    """
    ワークフローデータフロー追跡クラス
    実行履歴からデータの流れを詳細に追跡・分析
    """
    
    def __init__(self):
        """データフロー追跡クラスの初期化"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def trace_data_flow(self, execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        実行履歴からデータフローを追跡
        
        Args:
            execution_history: Step Functions実行履歴
            
        Returns:
            Dict: データフロー追跡結果
        """
        flow_trace = {
            'workflow_start': None,
            'workflow_end': None,
            'state_transitions': [],
            'data_transformations': [],
            'execution_timeline': [],
            'error_events': []
        }
        
        try:
            for event in execution_history:
                event_type = event.get('type')
                timestamp = event.get('timestamp')
                
                # ワークフロー開始・終了の記録
                if event_type == 'ExecutionStarted':
                    flow_trace['workflow_start'] = {
                        'timestamp': timestamp.isoformat() if timestamp else None,
                        'input': event.get('executionStartedEventDetails', {}).get('input')
                    }
                
                elif event_type in ['ExecutionSucceeded', 'ExecutionFailed', 'ExecutionAborted']:
                    flow_trace['workflow_end'] = {
                        'timestamp': timestamp.isoformat() if timestamp else None,
                        'status': event_type.replace('Execution', '').upper(),
                        'output': event.get('executionSucceededEventDetails', {}).get('output') if event_type == 'ExecutionSucceeded' else None
                    }
                
                # ステート遷移の記録
                elif event_type in ['TaskStateEntered', 'TaskStateExited']:
                    self._record_state_transition(event, flow_trace)
                
                # エラーイベントの記録
                elif 'Failed' in event_type or 'TimedOut' in event_type:
                    self._record_error_event(event, flow_trace)
                
                # 実行タイムラインの記録
                flow_trace['execution_timeline'].append({
                    'timestamp': timestamp.isoformat() if timestamp else None,
                    'event_type': event_type,
                    'event_id': event.get('id')
                })
            
            # データ変換の分析
            flow_trace['data_transformations'] = self._analyze_data_transformations(flow_trace['state_transitions'])
            
        except Exception as e:
            self.logger.error(f"Error during data flow tracing: {str(e)}")
            flow_trace['errors'] = [str(e)]
        
        return flow_trace
    
    def _record_state_transition(self, event: Dict[str, Any], flow_trace: Dict[str, Any]):
        """ステート遷移の記録"""
        event_type = event.get('type')
        timestamp = event.get('timestamp')
        
        if event_type == 'TaskStateEntered':
            details = event.get('stateEnteredEventDetails', {})
            transition = {
                'state_name': details.get('name'),
                'entered_at': timestamp.isoformat() if timestamp else None,
                'input_data': details.get('input'),
                'exited_at': None,
                'output_data': None
            }
            flow_trace['state_transitions'].append(transition)
        
        elif event_type == 'TaskStateExited':
            details = event.get('stateExitedEventDetails', {})
            state_name = details.get('name')
            
            # 対応するエントリーイベントを見つけて更新
            for transition in reversed(flow_trace['state_transitions']):
                if transition['state_name'] == state_name and transition['exited_at'] is None:
                    transition['exited_at'] = timestamp.isoformat() if timestamp else None
                    transition['output_data'] = details.get('output')
                    break
    
    def _record_error_event(self, event: Dict[str, Any], flow_trace: Dict[str, Any]):
        """エラーイベントの記録"""
        error_event = {
            'timestamp': event.get('timestamp').isoformat() if event.get('timestamp') else None,
            'event_type': event.get('type'),
            'error_details': event
        }
        flow_trace['error_events'].append(error_event)
    
    def _analyze_data_transformations(self, state_transitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """データ変換の分析"""
        transformations = []
        
        for i, transition in enumerate(state_transitions):
            if transition['input_data'] and transition['output_data']:
                try:
                    input_data = json.loads(transition['input_data']) if isinstance(transition['input_data'], str) else transition['input_data']
                    output_data = json.loads(transition['output_data']) if isinstance(transition['output_data'], str) else transition['output_data']
                    
                    transformation = {
                        'state_name': transition['state_name'],
                        'transformation_index': i + 1,
                        'input_size': len(str(input_data)),
                        'output_size': len(str(output_data)),
                        'data_growth': len(str(output_data)) - len(str(input_data)),
                        'processing_time': self._calculate_processing_time(transition),
                        'key_changes': self._identify_key_changes(input_data, output_data)
                    }
                    transformations.append(transformation)
                
                except Exception as e:
                    self.logger.warning(f"Failed to analyze transformation for {transition['state_name']}: {str(e)}")
        
        return transformations
    
    def _calculate_processing_time(self, transition: Dict[str, Any]) -> Optional[float]:
        """処理時間の計算"""
        try:
            if transition['entered_at'] and transition['exited_at']:
                entered = datetime.fromisoformat(transition['entered_at'].replace('Z', '+00:00'))
                exited = datetime.fromisoformat(transition['exited_at'].replace('Z', '+00:00'))
                return (exited - entered).total_seconds()
        except Exception:
            pass
        return None
    
    def _identify_key_changes(self, input_data: Any, output_data: Any) -> List[str]:
        """主要な変更点の特定"""
        changes = []
        
        try:
            if isinstance(input_data, dict) and isinstance(output_data, dict):
                # 新しく追加されたキーを特定
                input_keys = set(input_data.keys()) if input_data else set()
                output_keys = set(output_data.keys()) if output_data else set()
                
                new_keys = output_keys - input_keys
                if new_keys:
                    changes.append(f"Added keys: {list(new_keys)}")
                
                removed_keys = input_keys - output_keys
                if removed_keys:
                    changes.append(f"Removed keys: {list(removed_keys)}")
        
        except Exception:
            changes.append("Unable to analyze key changes")
        
        return changes


def create_sample_test_scenarios() -> List[Dict[str, Any]]:
    """
    サンプルテストシナリオの作成
    
    Returns:
        List[Dict]: テストシナリオのリスト
    """
    scenarios = [
        {
            'name': 'basic_workflow_test',
            'input_data': {
                'requestId': 'test-request-001',
                'inputData': {
                    'value': 'test_value_basic',
                    'metadata': {
                        'source': 'automated_test',
                        'timestamp': datetime.now().isoformat()
                    }
                }
            },
            'timeout_seconds': 300
        },
        {
            'name': 'complex_data_workflow_test',
            'input_data': {
                'requestId': 'test-request-002',
                'inputData': {
                    'value': 'complex_test_data_with_special_chars_!@#$%',
                    'metadata': {
                        'source': 'complex_test',
                        'timestamp': datetime.now().isoformat(),
                        'additional_info': {
                            'test_type': 'complex_scenario',
                            'expected_transformations': 3
                        }
                    }
                }
            },
            'timeout_seconds': 300
        },
        {
            'name': 'minimal_data_workflow_test',
            'input_data': {
                'requestId': 'test-request-003',
                'inputData': {
                    'value': 'min'
                }
            },
            'timeout_seconds': 300
        }
    ]
    
    return scenarios