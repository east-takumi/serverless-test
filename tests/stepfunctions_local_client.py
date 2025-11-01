"""
Step Functions Local クライアント実装
Step Functions Localに接続するBoto3クライアントとワークフロー実行・監視機能
"""

import boto3
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

# ログ設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StepFunctionsLocalClient:
    """
    Step Functions Localクライアント
    ローカル環境でのStep Functions操作を提供
    """
    
    def __init__(self, 
                 local_endpoint: str = "http://localhost:8083",
                 region_name: str = "us-east-1",
                 aws_access_key_id: str = "testing",
                 aws_secret_access_key: str = "testing"):
        """
        クライアントの初期化
        
        Args:
            local_endpoint: Step Functions Localのエンドポイント
            region_name: AWSリージョン名（ローカルテスト用）
            aws_access_key_id: ダミーのアクセスキー
            aws_secret_access_key: ダミーのシークレットキー
        """
        self.local_endpoint = local_endpoint
        self.region_name = region_name
        
        try:
            # Step Functions Localクライアントの作成
            self.client = boto3.client(
                'stepfunctions',
                endpoint_url=local_endpoint,
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            
            logger.info(f"Step Functions Local client initialized with endpoint: {local_endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Step Functions Local client: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        Step Functions Localへの接続テスト
        
        Returns:
            bool: 接続成功の場合True
        """
        try:
            # ステートマシンのリストを取得して接続をテスト
            response = self.client.list_state_machines()
            logger.info("Successfully connected to Step Functions Local")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Step Functions Local: {str(e)}")
            return False
    
    def create_state_machine(self, 
                           name: str, 
                           definition: Dict[str, Any], 
                           role_arn: str) -> Optional[str]:
        """
        ステートマシンの作成
        
        Args:
            name: ステートマシン名
            definition: ステートマシン定義
            role_arn: 実行ロールARN
            
        Returns:
            Optional[str]: 作成されたステートマシンのARN
        """
        try:
            response = self.client.create_state_machine(
                name=name,
                definition=json.dumps(definition),
                roleArn=role_arn
            )
            
            state_machine_arn = response['stateMachineArn']
            logger.info(f"State machine created successfully: {state_machine_arn}")
            return state_machine_arn
            
        except ClientError as e:
            logger.error(f"Failed to create state machine: {str(e)}")
            return None
    
    def start_execution(self, 
                       state_machine_arn: str, 
                       input_data: Dict[str, Any],
                       execution_name: Optional[str] = None) -> Optional[str]:
        """
        ワークフロー実行の開始
        
        Args:
            state_machine_arn: ステートマシンARN
            input_data: 実行入力データ
            execution_name: 実行名（オプション）
            
        Returns:
            Optional[str]: 実行ARN
        """
        try:
            # 実行名が指定されていない場合は自動生成
            if execution_name is None:
                execution_name = f"test_execution_{int(time.time())}"
            
            response = self.client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"Execution started successfully: {execution_arn}")
            return execution_arn
            
        except ClientError as e:
            logger.error(f"Failed to start execution: {str(e)}")
            return None
    
    def get_execution_status(self, execution_arn: str) -> Optional[Dict[str, Any]]:
        """
        実行ステータスの取得
        
        Args:
            execution_arn: 実行ARN
            
        Returns:
            Optional[Dict]: 実行ステータス情報
        """
        try:
            response = self.client.describe_execution(executionArn=execution_arn)
            
            status_info = {
                'status': response['status'],
                'startDate': response.get('startDate'),
                'stopDate': response.get('stopDate'),
                'input': json.loads(response.get('input', '{}')),
                'output': json.loads(response.get('output', '{}')) if response.get('output') else None,
                'executionArn': execution_arn
            }
            
            return status_info
            
        except ClientError as e:
            logger.error(f"Failed to get execution status: {str(e)}")
            return None
    
    def wait_for_execution_completion(self, 
                                    execution_arn: str, 
                                    timeout_seconds: int = 300,
                                    poll_interval: int = 2) -> Optional[Dict[str, Any]]:
        """
        実行完了まで待機
        
        Args:
            execution_arn: 実行ARN
            timeout_seconds: タイムアウト時間（秒）
            poll_interval: ポーリング間隔（秒）
            
        Returns:
            Optional[Dict]: 最終実行ステータス
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            status_info = self.get_execution_status(execution_arn)
            
            if status_info is None:
                logger.error("Failed to get execution status during wait")
                return None
            
            status = status_info['status']
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                logger.info(f"Execution completed with status: {status}")
                return status_info
            
            logger.debug(f"Execution status: {status}, waiting...")
            time.sleep(poll_interval)
        
        logger.warning(f"Execution did not complete within {timeout_seconds} seconds")
        return self.get_execution_status(execution_arn)
    
    def get_execution_history(self, execution_arn: str) -> Optional[List[Dict[str, Any]]]:
        """
        実行履歴の取得
        
        Args:
            execution_arn: 実行ARN
            
        Returns:
            Optional[List[Dict]]: 実行履歴イベントのリスト
        """
        try:
            response = self.client.get_execution_history(executionArn=execution_arn)
            events = response.get('events', [])
            
            # イベントを時系列順にソート
            sorted_events = sorted(events, key=lambda x: x.get('timestamp', datetime.min))
            
            logger.info(f"Retrieved {len(sorted_events)} execution history events")
            return sorted_events
            
        except ClientError as e:
            logger.error(f"Failed to get execution history: {str(e)}")
            return None
    
    def stop_execution(self, execution_arn: str, error: str = "Manual stop", cause: str = "Test stopped") -> bool:
        """
        実行の停止
        
        Args:
            execution_arn: 実行ARN
            error: エラーメッセージ
            cause: 停止理由
            
        Returns:
            bool: 停止成功の場合True
        """
        try:
            self.client.stop_execution(
                executionArn=execution_arn,
                error=error,
                cause=cause
            )
            
            logger.info(f"Execution stopped successfully: {execution_arn}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to stop execution: {str(e)}")
            return False
    
    def list_executions(self, state_machine_arn: str, status_filter: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        実行リストの取得
        
        Args:
            state_machine_arn: ステートマシンARN
            status_filter: ステータスフィルター（RUNNING, SUCCEEDED, FAILED等）
            
        Returns:
            Optional[List[Dict]]: 実行リスト
        """
        try:
            params = {'stateMachineArn': state_machine_arn}
            if status_filter:
                params['statusFilter'] = status_filter
            
            response = self.client.list_executions(**params)
            executions = response.get('executions', [])
            
            logger.info(f"Retrieved {len(executions)} executions")
            return executions
            
        except ClientError as e:
            logger.error(f"Failed to list executions: {str(e)}")
            return None


class WorkflowExecutionMonitor:
    """
    ワークフロー実行監視クラス
    実行の詳細な監視とデータフロー追跡機能を提供
    """
    
    def __init__(self, client: StepFunctionsLocalClient):
        """
        監視クラスの初期化
        
        Args:
            client: Step Functions Localクライアント
        """
        self.client = client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def monitor_execution_with_details(self, execution_arn: str) -> Dict[str, Any]:
        """
        詳細な実行監視
        
        Args:
            execution_arn: 実行ARN
            
        Returns:
            Dict: 詳細な監視結果
        """
        monitoring_result = {
            'executionArn': execution_arn,
            'startTime': datetime.now().isoformat(),
            'events': [],
            'stateOutputs': {},
            'dataFlow': [],
            'errors': []
        }
        
        try:
            # 実行完了まで待機
            final_status = self.client.wait_for_execution_completion(execution_arn)
            
            if final_status is None:
                monitoring_result['errors'].append("Failed to get final execution status")
                return monitoring_result
            
            monitoring_result['finalStatus'] = final_status
            
            # 実行履歴の取得と解析
            history = self.client.get_execution_history(execution_arn)
            
            if history:
                monitoring_result['events'] = history
                monitoring_result['stateOutputs'] = self._extract_state_outputs(history)
                monitoring_result['dataFlow'] = self._trace_data_flow(history)
            
            monitoring_result['endTime'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error during execution monitoring: {str(e)}")
            monitoring_result['errors'].append(str(e))
        
        return monitoring_result
    
    def _extract_state_outputs(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        実行履歴からステート出力を抽出
        
        Args:
            history: 実行履歴イベント
            
        Returns:
            Dict: ステート別出力データ
        """
        state_outputs = {}
        
        for event in history:
            event_type = event.get('type')
            
            if event_type == 'TaskStateExited':
                state_name = event.get('stateExitedEventDetails', {}).get('name')
                output = event.get('stateExitedEventDetails', {}).get('output')
                
                if state_name and output:
                    try:
                        state_outputs[state_name] = json.loads(output)
                    except json.JSONDecodeError:
                        state_outputs[state_name] = output
        
        return state_outputs
    
    def _trace_data_flow(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        データフローの追跡
        
        Args:
            history: 実行履歴イベント
            
        Returns:
            List[Dict]: データフロー情報
        """
        data_flow = []
        
        for event in history:
            event_type = event.get('type')
            timestamp = event.get('timestamp')
            
            if event_type in ['TaskStateEntered', 'TaskStateExited']:
                flow_entry = {
                    'timestamp': timestamp.isoformat() if timestamp else None,
                    'eventType': event_type,
                    'stateName': None,
                    'data': None
                }
                
                if event_type == 'TaskStateEntered':
                    details = event.get('stateEnteredEventDetails', {})
                    flow_entry['stateName'] = details.get('name')
                    flow_entry['data'] = details.get('input')
                
                elif event_type == 'TaskStateExited':
                    details = event.get('stateExitedEventDetails', {})
                    flow_entry['stateName'] = details.get('name')
                    flow_entry['data'] = details.get('output')
                
                data_flow.append(flow_entry)
        
        return data_flow