"""
入出力検証テスト実装
各ステートの入出力データを検証するテスト関数と期待値との比較・アサーション機能
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass

# ログ設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_data: Optional[Dict[str, Any]] = None


class InputOutputValidator:
    """
    入出力データ検証クラス
    各ステートの入出力データの形式と内容を検証
    """
    
    def __init__(self):
        """バリデーターの初期化"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_workflow_input(self, input_data: Dict[str, Any]) -> ValidationResult:
        """
        ワークフロー初期入力データの検証
        
        Args:
            input_data: 検証対象の入力データ
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        
        # 必須フィールドの検証
        required_fields = ['requestId', 'inputData']
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Required field '{field}' is missing")
        
        # requestIdの検証
        if 'requestId' in input_data:
            if not isinstance(input_data['requestId'], str) or not input_data['requestId'].strip():
                errors.append("requestId must be a non-empty string")
        
        # inputDataの検証
        if 'inputData' in input_data:
            if not isinstance(input_data['inputData'], dict):
                errors.append("inputData must be a dictionary")
            else:
                input_data_validation = self._validate_input_data_structure(input_data['inputData'])
                errors.extend(input_data_validation.errors)
                warnings.extend(input_data_validation.warnings)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"Workflow input validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            self.logger.error(f"Validation errors: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=input_data if is_valid else None
        )
    
    def validate_state1_output(self, output_data: Dict[str, Any]) -> ValidationResult:
        """
        State1出力データの検証
        
        Args:
            output_data: State1の出力データ
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        
        # 必須フィールドの検証
        required_fields = ['requestId', 'state1Output', 'stateMetadata']
        for field in required_fields:
            if field not in output_data:
                errors.append(f"Required field '{field}' is missing from State1 output")
        
        # state1Outputの詳細検証
        if 'state1Output' in output_data:
            state1_validation = self._validate_state1_output_structure(output_data['state1Output'])
            errors.extend(state1_validation.errors)
            warnings.extend(state1_validation.warnings)
        
        # stateMetadataの検証
        if 'stateMetadata' in output_data:
            metadata_validation = self._validate_state_metadata(output_data['stateMetadata'], 'State1')
            errors.extend(metadata_validation.errors)
            warnings.extend(metadata_validation.warnings)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"State1 output validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            self.logger.error(f"State1 validation errors: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=output_data if is_valid else None
        )
    
    def validate_state2_output(self, output_data: Dict[str, Any]) -> ValidationResult:
        """
        State2出力データの検証
        
        Args:
            output_data: State2の出力データ
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        
        # 必須フィールドの検証
        required_fields = ['requestId', 'state1Output', 'state2Output', 'stateMetadata', 'dataFlow']
        for field in required_fields:
            if field not in output_data:
                errors.append(f"Required field '{field}' is missing from State2 output")
        
        # state1Outputの保持確認
        if 'state1Output' in output_data:
            state1_validation = self._validate_state1_output_structure(output_data['state1Output'])
            if not state1_validation.is_valid:
                errors.append("State1 output data is not properly preserved in State2 output")
        
        # state2Outputの詳細検証
        if 'state2Output' in output_data:
            state2_validation = self._validate_state2_output_structure(output_data['state2Output'])
            errors.extend(state2_validation.errors)
            warnings.extend(state2_validation.warnings)
        
        # stateMetadataの検証
        if 'stateMetadata' in output_data:
            metadata_validation = self._validate_state_metadata(output_data['stateMetadata'], 'State2')
            errors.extend(metadata_validation.errors)
            warnings.extend(metadata_validation.warnings)
        
        # dataFlowの検証
        if 'dataFlow' in output_data:
            dataflow_validation = self._validate_dataflow_structure(output_data['dataFlow'])
            errors.extend(dataflow_validation.errors)
            warnings.extend(dataflow_validation.warnings)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"State2 output validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            self.logger.error(f"State2 validation errors: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=output_data if is_valid else None
        )
    
    def validate_state3_output(self, output_data: Dict[str, Any]) -> ValidationResult:
        """
        State3（最終）出力データの検証
        
        Args:
            output_data: State3の出力データ
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        
        # 必須フィールドの検証
        required_fields = ['requestId', 'executionSummary', 'allStatesData', 'finalResult', 'stateMetadata']
        for field in required_fields:
            if field not in output_data:
                errors.append(f"Required field '{field}' is missing from State3 output")
        
        # executionSummaryの検証
        if 'executionSummary' in output_data:
            summary_validation = self._validate_execution_summary(output_data['executionSummary'])
            errors.extend(summary_validation.errors)
            warnings.extend(summary_validation.warnings)
        
        # allStatesDataの検証
        if 'allStatesData' in output_data:
            all_states_validation = self._validate_all_states_data(output_data['allStatesData'])
            errors.extend(all_states_validation.errors)
            warnings.extend(all_states_validation.warnings)
        
        # finalResultの検証
        if 'finalResult' in output_data:
            final_result_validation = self._validate_final_result(output_data['finalResult'])
            errors.extend(final_result_validation.errors)
            warnings.extend(final_result_validation.warnings)
        
        # stateMetadataの検証
        if 'stateMetadata' in output_data:
            metadata_validation = self._validate_state_metadata(output_data['stateMetadata'], 'State3')
            errors.extend(metadata_validation.errors)
            warnings.extend(metadata_validation.warnings)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"State3 output validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            self.logger.error(f"State3 validation errors: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=output_data if is_valid else None
        )
    
    def _validate_input_data_structure(self, input_data: Dict[str, Any]) -> ValidationResult:
        """inputDataの構造検証"""
        errors = []
        warnings = []
        
        if 'value' not in input_data:
            errors.append("inputData must contain 'value' field")
        
        if 'metadata' in input_data and not isinstance(input_data['metadata'], dict):
            errors.append("metadata must be a dictionary")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_state1_output_structure(self, state1_output: Dict[str, Any]) -> ValidationResult:
        """State1出力構造の検証"""
        errors = []
        warnings = []
        
        required_fields = ['processedValue', 'originalInput']
        for field in required_fields:
            if field not in state1_output:
                errors.append(f"State1 output missing required field: {field}")
        
        # processedValueの検証
        if 'processedValue' in state1_output:
            if not isinstance(state1_output['processedValue'], str):
                errors.append("processedValue must be a string")
            elif not state1_output['processedValue'].startswith('State1_processed_'):
                warnings.append("processedValue does not follow expected naming pattern")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_state2_output_structure(self, state2_output: Dict[str, Any]) -> ValidationResult:
        """State2出力構造の検証"""
        errors = []
        warnings = []
        
        required_fields = ['processedValue', 'previousStateData', 'enhancementData']
        for field in required_fields:
            if field not in state2_output:
                errors.append(f"State2 output missing required field: {field}")
        
        # processedValueの検証
        if 'processedValue' in state2_output:
            if not isinstance(state2_output['processedValue'], str):
                errors.append("processedValue must be a string")
            elif not state2_output['processedValue'].startswith('State2_enhanced_'):
                warnings.append("processedValue does not follow expected naming pattern")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_state_metadata(self, metadata: Dict[str, Any], expected_state: str) -> ValidationResult:
        """ステートメタデータの検証"""
        errors = []
        warnings = []
        
        required_fields = ['state', 'executionTime']
        for field in required_fields:
            if field not in metadata:
                errors.append(f"State metadata missing required field: {field}")
        
        if 'state' in metadata and metadata['state'] != expected_state:
            errors.append(f"Expected state '{expected_state}', got '{metadata['state']}'")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_dataflow_structure(self, dataflow: Dict[str, Any]) -> ValidationResult:
        """データフロー構造の検証"""
        errors = []
        warnings = []
        
        required_fields = ['inputSource', 'outputDestination', 'dataTransformation']
        for field in required_fields:
            if field not in dataflow:
                errors.append(f"DataFlow missing required field: {field}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_execution_summary(self, summary: Dict[str, Any]) -> ValidationResult:
        """実行サマリーの検証"""
        errors = []
        warnings = []
        
        required_fields = ['totalStates', 'executionStatus']
        for field in required_fields:
            if field not in summary:
                errors.append(f"Execution summary missing required field: {field}")
        
        if 'totalStates' in summary and summary['totalStates'] != 3:
            errors.append(f"Expected 3 total states, got {summary['totalStates']}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_all_states_data(self, all_states: Dict[str, Any]) -> ValidationResult:
        """全ステートデータの検証"""
        errors = []
        warnings = []
        
        required_states = ['state1Output', 'state2Output', 'state3Output']
        for state in required_states:
            if state not in all_states:
                errors.append(f"All states data missing: {state}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_final_result(self, final_result: Dict[str, Any]) -> ValidationResult:
        """最終結果の検証"""
        errors = []
        warnings = []
        
        required_fields = ['success', 'finalValue', 'processingChain']
        for field in required_fields:
            if field not in final_result:
                errors.append(f"Final result missing required field: {field}")
        
        if 'success' in final_result and not isinstance(final_result['success'], bool):
            errors.append("success field must be boolean")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class DataFlowValidator:
    """
    データフロー検証クラス
    ステート間のデータフローと変換を検証
    """
    
    def __init__(self):
        """データフロー検証クラスの初期化"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_data_flow_continuity(self, 
                                    workflow_input: Dict[str, Any],
                                    state1_output: Dict[str, Any],
                                    state2_output: Dict[str, Any],
                                    state3_output: Dict[str, Any]) -> ValidationResult:
        """
        ワークフロー全体のデータフロー連続性を検証
        
        Args:
            workflow_input: ワークフロー初期入力
            state1_output: State1出力
            state2_output: State2出力
            state3_output: State3出力
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        
        # requestIdの連続性確認
        request_id = workflow_input.get('requestId')
        if not self._check_request_id_continuity(request_id, [state1_output, state2_output, state3_output]):
            errors.append("requestId is not consistent across all states")
        
        # 元の入力データの保持確認
        original_value = workflow_input.get('inputData', {}).get('value')
        if not self._check_original_data_preservation(original_value, state1_output, state2_output, state3_output):
            errors.append("Original input data is not properly preserved through the workflow")
        
        # データ変換の連続性確認
        transformation_validation = self._validate_data_transformations(
            workflow_input, state1_output, state2_output, state3_output
        )
        errors.extend(transformation_validation.errors)
        warnings.extend(transformation_validation.warnings)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"Data flow continuity validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            self.logger.error(f"Data flow validation errors: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def _check_request_id_continuity(self, original_request_id: str, state_outputs: List[Dict[str, Any]]) -> bool:
        """requestIDの連続性確認"""
        for output in state_outputs:
            if output.get('requestId') != original_request_id:
                return False
        return True
    
    def _check_original_data_preservation(self, 
                                        original_value: str, 
                                        state1_output: Dict[str, Any],
                                        state2_output: Dict[str, Any],
                                        state3_output: Dict[str, Any]) -> bool:
        """元データの保持確認"""
        # State1での保持確認
        if state1_output.get('state1Output', {}).get('originalInput') != original_value:
            return False
        
        # State2での保持確認（State1データ経由）
        state1_data_in_state2 = state2_output.get('state1Output', {})
        if state1_data_in_state2.get('originalInput') != original_value:
            return False
        
        # State3での保持確認（allStatesData経由）
        all_states_data = state3_output.get('allStatesData', {})
        state1_data_in_state3 = all_states_data.get('state1Output', {})
        if state1_data_in_state3.get('originalInput') != original_value:
            return False
        
        return True
    
    def _validate_data_transformations(self, 
                                     workflow_input: Dict[str, Any],
                                     state1_output: Dict[str, Any],
                                     state2_output: Dict[str, Any],
                                     state3_output: Dict[str, Any]) -> ValidationResult:
        """データ変換の検証"""
        errors = []
        warnings = []
        
        original_value = workflow_input.get('inputData', {}).get('value', '')
        
        # State1変換の確認
        state1_processed = state1_output.get('state1Output', {}).get('processedValue', '')
        expected_state1 = f"State1_processed_{original_value}"
        if state1_processed != expected_state1:
            errors.append(f"State1 transformation incorrect. Expected: {expected_state1}, Got: {state1_processed}")
        
        # State2変換の確認
        state2_processed = state2_output.get('state2Output', {}).get('processedValue', '')
        expected_state2 = f"State2_enhanced_{expected_state1}"
        if state2_processed != expected_state2:
            errors.append(f"State2 transformation incorrect. Expected: {expected_state2}, Got: {state2_processed}")
        
        # State3変換の確認
        final_value = state3_output.get('finalResult', {}).get('finalValue', '')
        expected_final = f"State3_final_{expected_state2}"
        if final_value != expected_final:
            errors.append(f"State3 transformation incorrect. Expected: {expected_final}, Got: {final_value}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class AssertionHelper:
    """
    アサーション機能を提供するヘルパークラス
    期待値との比較とテスト結果の判定
    """
    
    @staticmethod
    def assert_validation_passed(validation_result: ValidationResult, context: str = ""):
        """
        検証結果がパスしていることをアサート
        
        Args:
            validation_result: 検証結果
            context: コンテキスト情報
            
        Raises:
            AssertionError: 検証が失敗した場合
        """
        if not validation_result.is_valid:
            error_msg = f"Validation failed{' for ' + context if context else ''}: {validation_result.errors}"
            raise AssertionError(error_msg)
    
    @staticmethod
    def assert_field_equals(actual_data: Dict[str, Any], field_path: str, expected_value: Any, context: str = ""):
        """
        指定されたフィールドの値が期待値と等しいことをアサート
        
        Args:
            actual_data: 実際のデータ
            field_path: フィールドパス（例: "state1Output.processedValue"）
            expected_value: 期待値
            context: コンテキスト情報
            
        Raises:
            AssertionError: 値が期待値と異なる場合
        """
        actual_value = AssertionHelper._get_nested_value(actual_data, field_path)
        
        if actual_value != expected_value:
            error_msg = f"Field '{field_path}' assertion failed{' for ' + context if context else ''}: expected {expected_value}, got {actual_value}"
            raise AssertionError(error_msg)
    
    @staticmethod
    def assert_field_contains(actual_data: Dict[str, Any], field_path: str, expected_substring: str, context: str = ""):
        """
        指定されたフィールドの値が期待する部分文字列を含むことをアサート
        
        Args:
            actual_data: 実際のデータ
            field_path: フィールドパス
            expected_substring: 期待する部分文字列
            context: コンテキスト情報
            
        Raises:
            AssertionError: 部分文字列が含まれていない場合
        """
        actual_value = str(AssertionHelper._get_nested_value(actual_data, field_path))
        
        if expected_substring not in actual_value:
            error_msg = f"Field '{field_path}' does not contain '{expected_substring}'{' for ' + context if context else ''}: got '{actual_value}'"
            raise AssertionError(error_msg)
    
    @staticmethod
    def _get_nested_value(data: Dict[str, Any], field_path: str) -> Any:
        """
        ネストされたフィールドの値を取得
        
        Args:
            data: データ辞書
            field_path: フィールドパス（ドット区切り）
            
        Returns:
            Any: フィールドの値
        """
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current