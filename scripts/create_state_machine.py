#!/usr/bin/env python3
"""
Step Functions ステートマシン作成スクリプト
GitHub Actions環境でStep Functions Localにステートマシンを作成
"""

import boto3
import json
import sys
import os
import time
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_state_machine():
    """ステートマシンの作成"""
    try:
        logger.info("Creating Step Functions state machine...")
        
        # ステートマシン定義の読み込み
        definition_file = 'workflow/state_machine.json'
        if not os.path.exists(definition_file):
            logger.error(f"State machine definition file not found: {definition_file}")
            return False
        
        with open(definition_file, 'r', encoding='utf-8') as f:
            definition_template = f.read()
        
        logger.info(f"Loaded state machine definition from {definition_file}")
        
        # ローカルテスト用のLambda ARNに置換
        # Step Functions Localでは実際のARN形式を使用する必要がある
        # SAM buildで生成される関数名に合わせる
        stack_name = os.getenv('SAM_STACK_NAME', 'stepfunctions-local-testing')
        environment = os.getenv('ENVIRONMENT', 'local')
        
        account_id = os.getenv('LOCAL_AWS_ACCOUNT_ID', '123456789012')

        local_function_arns = {
            'ProcessState1FunctionArn': f'arn:aws:lambda:us-east-1:{account_id}:function:{stack_name}-ProcessState1-{environment}',
            'ProcessState2FunctionArn': f'arn:aws:lambda:us-east-1:{account_id}:function:{stack_name}-ProcessState2-{environment}',
            'ProcessState3FunctionArn': f'arn:aws:lambda:us-east-1:{account_id}:function:{stack_name}-ProcessState3-{environment}'
        }
        
        # プレースホルダーを実際のARNに置換
        definition = definition_template
        for placeholder, arn in local_function_arns.items():
            old_placeholder = f"${{{placeholder}}}"
            definition = definition.replace(old_placeholder, arn)
            logger.info(f"Replaced {old_placeholder} with {arn}")
        
        logger.info("Substituted Lambda function ARNs for local testing")
        
        # 置換後の定義をログ出力（デバッグ用）
        logger.info("Final state machine definition created with local Lambda ARNs")
        
        # Step Functions Localクライアントの作成
        stepfunctions_endpoint = os.getenv('STEPFUNCTIONS_ENDPOINT', 'http://localhost:8083')
        
        client = boto3.client(
            'stepfunctions',
            endpoint_url=stepfunctions_endpoint,
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # 接続テスト
        logger.info(f"Testing connection to Step Functions Local at {stepfunctions_endpoint}")
        try:
            client.list_state_machines()
            logger.info("✓ Successfully connected to Step Functions Local")
        except Exception as e:
            logger.error(f"Failed to connect to Step Functions Local: {e}")
            return False
        
        # ステートマシンの作成
        state_machine_name = 'stepfunctions-local-testing-Workflow'
        role_arn = f'arn:aws:iam::{account_id}:role/DummyRole'
        
        logger.info(f"Creating state machine: {state_machine_name}")
        
        response = client.create_state_machine(
            name=state_machine_name,
            definition=definition,
            roleArn=role_arn
        )
        
        state_machine_arn = response['stateMachineArn']
        logger.info(f"✓ State machine created successfully: {state_machine_arn}")
        
        # ARNをファイルに保存
        arn_file = 'state_machine_arn.txt'
        with open(arn_file, 'w', encoding='utf-8') as f:
            f.write(state_machine_arn)
        
        logger.info(f"State machine ARN saved to {arn_file}")
        
        # 作成されたステートマシンの確認
        logger.info("Verifying created state machine...")
        try:
            describe_response = client.describe_state_machine(stateMachineArn=state_machine_arn)
            logger.info(f"✓ State machine verification successful")
            logger.info(f"  Name: {describe_response['name']}")
            logger.info(f"  Status: {describe_response['status']}")
            logger.info(f"  Creation Date: {describe_response['creationDate']}")
        except Exception as e:
            logger.warning(f"State machine verification failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating state machine: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def wait_for_stepfunctions_local(endpoint: str, max_attempts: int = 30, delay: int = 2):
    """Step Functions Localの起動を待機"""
    logger.info(f"Waiting for Step Functions Local at {endpoint}...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            client = boto3.client(
                'stepfunctions',
                endpoint_url=endpoint,
                region_name='us-east-1',
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
            
            client.list_state_machines()
            logger.info(f"✓ Step Functions Local is ready (attempt {attempt})")
            return True
            
        except Exception as e:
            if attempt < max_attempts:
                logger.info(f"Attempt {attempt}/{max_attempts}: Step Functions Local not ready yet, waiting {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"Step Functions Local failed to start after {max_attempts} attempts")
                logger.error(f"Last error: {e}")
                return False
    
    return False


def main():
    """メイン実行関数"""
    logger.info("🚀 Starting Step Functions state machine creation")
    
    try:
        # Step Functions Localの起動待機
        stepfunctions_endpoint = os.getenv('STEPFUNCTIONS_ENDPOINT', 'http://localhost:8083')
        
        if not wait_for_stepfunctions_local(stepfunctions_endpoint):
            logger.error("❌ Step Functions Local is not available")
            sys.exit(1)
        
        # ステートマシンの作成
        if create_state_machine():
            logger.info("🎉 State machine creation completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ State machine creation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ State machine creation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()