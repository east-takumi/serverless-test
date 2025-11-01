"""
State1 Lambda Function
初期入力データを受け取り、処理してState2に渡すLambda関数
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_input(event: Dict[str, Any]) -> bool:
    """
    入力データの検証
    
    Args:
        event: Lambda関数への入力イベント
        
    Returns:
        bool: 検証結果
    """
    required_fields = ['requestId', 'inputData']
    
    for field in required_fields:
        if field not in event:
            logger.error(f"Required field '{field}' is missing from input")
            return False
    
    if not isinstance(event['inputData'], dict):
        logger.error("inputData must be a dictionary")
        return False
        
    if 'value' not in event['inputData']:
        logger.error("inputData must contain 'value' field")
        return False
    
    return True


def process_input_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    入力データの処理
    
    Args:
        input_data: 処理対象の入力データ
        
    Returns:
        Dict: 処理済みデータ
    """
    processed_value = f"State1_processed_{input_data['value']}"
    
    return {
        'processedValue': processed_value,
        'originalInput': input_data['value'],
        'inputMetadata': input_data.get('metadata', {}),
        'processingDetails': {
            'transformationType': 'prefix_addition',
            'processingTime': datetime.now().isoformat()
        }
    }


def lambda_handler(event, context):
    """
    State1 Lambda関数のメインハンドラー
    
    Args:
        event: Step Functionsからの入力イベント
        context: Lambda実行コンテキスト
        
    Returns:
        Dict: State2への出力データ
    """
    try:
        logger.info(f"State1 Lambda function started with event: {json.dumps(event)}")
        
        # 入力データの検証
        if not validate_input(event):
            raise ValueError("Input validation failed")
        
        # 入力データの処理
        processed_data = process_input_data(event['inputData'])
        
        # メタデータの追加
        output = {
            'requestId': event['requestId'],
            'state1Output': processed_data,
            'stateMetadata': {
                'state': 'State1',
                'executionTime': datetime.now().isoformat(),
                'functionName': context.function_name if context else 'local_test',
                'requestId': context.aws_request_id if context else 'test_request_id'
            }
        }
        
        logger.info(f"State1 processing completed successfully")
        logger.info(f"Output: {json.dumps(output)}")
        
        return output
        
    except Exception as e:
        logger.error(f"Error in State1 Lambda function: {str(e)}")
        
        # エラー情報を含む出力
        error_output = {
            'error': {
                'type': 'State1ExecutionError',
                'message': str(e),
                'timestamp': datetime.now().isoformat(),
                'input': event
            }
        }
        
        # Step Functionsでエラーハンドリングできるよう例外を再発生
        raise Exception(json.dumps(error_output))