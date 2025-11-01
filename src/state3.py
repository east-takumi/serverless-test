"""
State3 Lambda Function
State2からの出力を受け取り、最終処理を行うLambda関数
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_state2_output(event: Dict[str, Any]) -> bool:
    """
    State2からの出力データの検証
    
    Args:
        event: State2からの出力イベント
        
    Returns:
        bool: 検証結果
    """
    required_fields = ['requestId', 'state1Output', 'state2Output', 'stateMetadata']
    
    for field in required_fields:
        if field not in event:
            logger.error(f"Required field '{field}' is missing from State2 output")
            return False
    
    # State2出力の詳細検証
    state2_output = event['state2Output']
    required_state2_fields = ['processedValue', 'previousStateData']
    
    for field in required_state2_fields:
        if field not in state2_output:
            logger.error(f"Required field '{field}' is missing from state2Output")
            return False
    
    # メタデータの検証
    if event['stateMetadata'].get('state') != 'State2':
        logger.error("Invalid state metadata - expected State2")
        return False
    
    return True


def aggregate_all_states_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    全ステートのデータを集約
    
    Args:
        event: State2からの出力イベント
        
    Returns:
        Dict: 集約されたデータ
    """
    # 各ステートからのデータを抽出
    state1_data = event['state1Output']
    state2_data = event['state2Output']
    
    # 処理チェーンの構築
    processing_chain = [
        {
            'state': 'State1',
            'processedValue': state1_data['processedValue'],
            'originalInput': state1_data['originalInput'],
            'processingTime': state1_data.get('processingDetails', {}).get('processingTime')
        },
        {
            'state': 'State2', 
            'processedValue': state2_data['processedValue'],
            'enhancementData': state2_data.get('enhancementData', {}),
            'processingTime': state2_data.get('processingDetails', {}).get('processingTime')
        }
    ]
    
    # 最終処理値の生成
    final_processed_value = f"State3_final_{state2_data['processedValue']}"
    
    return {
        'finalProcessedValue': final_processed_value,
        'processingChain': processing_chain,
        'aggregatedMetadata': {
            'totalStates': 3,
            'originalInput': state1_data['originalInput'],
            'finalTransformation': 'complete_workflow_processing'
        }
    }


def generate_execution_summary(event: Dict[str, Any], processing_start_time: str) -> Dict[str, Any]:
    """
    実行サマリーの生成
    
    Args:
        event: 入力イベント
        processing_start_time: 処理開始時刻
        
    Returns:
        Dict: 実行サマリー
    """
    processing_end_time = datetime.now().isoformat()
    
    # データサイズの計算
    total_data_size = len(json.dumps(event))
    
    # 各ステートの処理時間を抽出（可能な場合）
    state_timings = []
    
    if 'state1Output' in event and 'processingDetails' in event['state1Output']:
        state_timings.append({
            'state': 'State1',
            'processingTime': event['state1Output']['processingDetails'].get('processingTime')
        })
    
    if 'state2Output' in event and 'processingDetails' in event['state2Output']:
        state_timings.append({
            'state': 'State2', 
            'processingTime': event['state2Output']['processingDetails'].get('processingTime')
        })
    
    state_timings.append({
        'state': 'State3',
        'processingTime': processing_end_time
    })
    
    return {
        'totalStates': 3,
        'executionStatus': 'SUCCESS',
        'processingStartTime': processing_start_time,
        'processingEndTime': processing_end_time,
        'totalDataSize': total_data_size,
        'stateTimings': state_timings,
        'dataFlowValidation': 'PASSED'
    }


def lambda_handler(event, context):
    """
    State3 Lambda関数のメインハンドラー
    
    Args:
        event: State2からの出力イベント
        context: Lambda実行コンテキスト
        
    Returns:
        Dict: 最終出力データ
    """
    processing_start_time = datetime.now().isoformat()
    
    try:
        logger.info(f"State3 Lambda function started with event data size: {len(json.dumps(event))} characters")
        
        # State2出力の検証
        if not validate_state2_output(event):
            raise ValueError("State2 output validation failed")
        
        # 全ステートのデータを集約
        aggregated_data = aggregate_all_states_data(event)
        
        # 実行サマリーの生成
        execution_summary = generate_execution_summary(event, processing_start_time)
        
        # 最終出力の構築
        final_output = {
            'requestId': event['requestId'],
            'executionSummary': execution_summary,
            'allStatesData': {
                'state1Output': event['state1Output'],
                'state2Output': event['state2Output'],
                'state3Output': aggregated_data
            },
            'finalResult': {
                'success': True,
                'finalValue': aggregated_data['finalProcessedValue'],
                'processingChain': aggregated_data['processingChain'],
                'workflowMetadata': {
                    'completedStates': ['State1', 'State2', 'State3'],
                    'totalProcessingTime': execution_summary['processingEndTime'],
                    'dataIntegrity': 'VERIFIED'
                }
            },
            'stateMetadata': {
                'state': 'State3',
                'executionTime': datetime.now().isoformat(),
                'functionName': context.function_name if context else 'local_test',
                'requestId': context.aws_request_id if context else 'test_request_id',
                'previousStates': ['State1', 'State2'],
                'isWorkflowComplete': True
            }
        }
        
        logger.info(f"State3 processing completed successfully")
        logger.info(f"Final output generated with {len(final_output['allStatesData'])} state outputs")
        logger.info(f"Workflow execution summary: {execution_summary['executionStatus']}")
        
        return final_output
        
    except Exception as e:
        logger.error(f"Error in State3 Lambda function: {str(e)}")
        
        # エラー情報を含む出力
        error_output = {
            'error': {
                'type': 'State3ExecutionError',
                'message': str(e),
                'timestamp': datetime.now().isoformat(),
                'input': event,
                'previousStates': ['State1', 'State2'],
                'workflowStatus': 'FAILED'
            }
        }
        
        # Step Functionsでエラーハンドリングできるよう例外を再発生
        raise Exception(json.dumps(error_output))