"""
State2 Lambda Function
State1からの出力を受け取り、中間処理を行うLambda関数
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_state1_output(event: Dict[str, Any]) -> bool:
    """
    State1からの出力データの検証
    
    Args:
        event: State1からの出力イベント
        
    Returns:
        bool: 検証結果
    """
    required_fields = ['requestId', 'state1Output', 'stateMetadata']
    
    for field in required_fields:
        if field not in event:
            logger.error(f"Required field '{field}' is missing from State1 output")
            return False
    
    # State1出力の詳細検証
    state1_output = event['state1Output']
    required_state1_fields = ['processedValue', 'originalInput']
    
    for field in required_state1_fields:
        if field not in state1_output:
            logger.error(f"Required field '{field}' is missing from state1Output")
            return False
    
    # メタデータの検証
    if event['stateMetadata'].get('state') != 'State1':
        logger.error("Invalid state metadata - expected State1")
        return False
    
    return True


def process_state1_data(state1_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    State1からのデータを処理
    
    Args:
        state1_output: State1からの出力データ
        
    Returns:
        Dict: 処理済みデータ
    """
    # State1のデータを基に中間処理を実行
    processed_value = f"State2_enhanced_{state1_output['processedValue']}"
    
    # 追加の処理ロジック
    enhancement_data = {
        'enhancementType': 'data_enrichment',
        'additionalInfo': f"enriched_at_{datetime.now().strftime('%H%M%S')}",
        'processingChain': ['State1', 'State2']
    }
    
    return {
        'processedValue': processed_value,
        'previousStateData': state1_output,
        'enhancementData': enhancement_data,
        'processingDetails': {
            'transformationType': 'enhancement_and_enrichment',
            'processingTime': datetime.now().isoformat(),
            'dataSize': len(str(state1_output))
        }
    }


def lambda_handler(event, context):
    """
    State2 Lambda関数のメインハンドラー
    
    Args:
        event: State1からの出力イベント
        context: Lambda実行コンテキスト
        
    Returns:
        Dict: State3への出力データ
    """
    try:
        logger.info(f"State2 Lambda function started with event: {json.dumps(event)}")
        
        # State1出力の検証
        if not validate_state1_output(event):
            raise ValueError("State1 output validation failed")
        
        # State1データの処理
        processed_data = process_state1_data(event['state1Output'])
        
        # 前のステートデータを保持しながら新しい処理結果を追加
        output = {
            'requestId': event['requestId'],
            'state1Output': event['state1Output'],  # 前のステートデータを保持
            'state2Output': processed_data,
            'stateMetadata': {
                'state': 'State2',
                'executionTime': datetime.now().isoformat(),
                'functionName': context.function_name if context else 'local_test',
                'requestId': context.aws_request_id if context else 'test_request_id',
                'previousStates': ['State1']
            },
            'dataFlow': {
                'inputSource': 'State1',
                'outputDestination': 'State3',
                'dataTransformation': 'enhancement_and_enrichment'
            }
        }
        
        logger.info(f"State2 processing completed successfully")
        logger.info(f"Output data size: {len(json.dumps(output))} characters")
        
        return output
        
    except Exception as e:
        logger.error(f"Error in State2 Lambda function: {str(e)}")
        
        # エラー情報を含む出力
        error_output = {
            'error': {
                'type': 'State2ExecutionError',
                'message': str(e),
                'timestamp': datetime.now().isoformat(),
                'input': event,
                'previousState': 'State1'
            }
        }
        
        # Step Functionsでエラーハンドリングできるよう例外を再発生
        raise Exception(json.dumps(error_output))