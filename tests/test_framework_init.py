"""
Step Functions Local テストフレームワーク
初期化とユーティリティ関数
"""

import logging
import sys
from typing import Dict, Any

# テストフレームワークのバージョン
__version__ = "1.0.0"

# ログ設定のデフォルト
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL = logging.INFO


def setup_logging(level: int = DEFAULT_LOG_LEVEL, 
                 format_string: str = DEFAULT_LOG_FORMAT,
                 log_file: str = None) -> None:
    """
    テストフレームワーク用のログ設定
    
    Args:
        level: ログレベル
        format_string: ログフォーマット
        log_file: ログファイルパス（オプション）
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    )


def get_framework_info() -> Dict[str, Any]:
    """
    フレームワーク情報の取得
    
    Returns:
        Dict: フレームワーク情報
    """
    return {
        'name': 'Step Functions Local Test Framework',
        'version': __version__,
        'description': 'AWS Step Functions Local用の自動テストフレームワーク',
        'components': [
            'StepFunctionsLocalClient',
            'InputOutputValidator', 
            'WorkflowExecutionTester',
            'WorkflowDataFlowTracer',
            'StepFunctionsTestRunner'
        ]
    }


# フレームワークの主要クラスをインポート
try:
    from .stepfunctions_local_client import StepFunctionsLocalClient, WorkflowExecutionMonitor
    from .input_output_validator import InputOutputValidator, DataFlowValidator, AssertionHelper
    from .workflow_execution_test import WorkflowExecutionTester, WorkflowDataFlowTracer
    from .test_runner import StepFunctionsTestRunner
    
    __all__ = [
        'StepFunctionsLocalClient',
        'WorkflowExecutionMonitor', 
        'InputOutputValidator',
        'DataFlowValidator',
        'AssertionHelper',
        'WorkflowExecutionTester',
        'WorkflowDataFlowTracer',
        'StepFunctionsTestRunner',
        'setup_logging',
        'get_framework_info'
    ]
    
except ImportError as e:
    # 開発環境での相対インポートエラーを処理
    __all__ = [
        'setup_logging',
        'get_framework_info'
    ]