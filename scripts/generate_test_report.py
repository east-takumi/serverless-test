#!/usr/bin/env python3
"""
包括的テストレポート生成スクリプト
pytest結果と統合テスト結果を組み合わせた包括的なレポートを生成
"""

import json
import xml.etree.ElementTree as ET
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_pytest_results(xml_file: str) -> Optional[Dict[str, Any]]:
    """pytest結果XMLファイルの解析"""
    try:
        if not os.path.exists(xml_file):
            logger.warning(f"pytest results file not found: {xml_file}")
            return None
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        total_tests = int(root.get('tests', 0))
        failures = int(root.get('failures', 0))
        errors = int(root.get('errors', 0))
        skipped = int(root.get('skipped', 0))
        passed = total_tests - failures - errors - skipped
        
        pytest_results = {
            'summary': {
                'total': total_tests,
                'passed': passed,
                'failed': failures + errors,
                'skipped': skipped,
                'success_rate': f'{(passed/total_tests*100):.1f}%' if total_tests > 0 else '0%'
            },
            'test_cases': []
        }
        
        # 個別テストケースの詳細
        for testcase in root.findall('.//testcase'):
            test_name = testcase.get('name')
            class_name = testcase.get('classname')
            time_taken = float(testcase.get('time', 0))
            
            test_detail = {
                'name': test_name,
                'class': class_name,
                'duration_seconds': time_taken,
                'status': 'passed'
            }
            
            # 失敗・エラーの確認
            failure = testcase.find('failure')
            error = testcase.find('error')
            
            if failure is not None:
                test_detail['status'] = 'failed'
                test_detail['message'] = failure.get('message', '')
                test_detail['details'] = failure.text or ''
            elif error is not None:
                test_detail['status'] = 'error'
                test_detail['message'] = error.get('message', '')
                test_detail['details'] = error.text or ''
            
            pytest_results['test_cases'].append(test_detail)
        
        logger.info(f"✓ Parsed pytest results: {total_tests} tests, {passed} passed, {failures + errors} failed")
        return pytest_results
        
    except Exception as e:
        logger.error(f"Error parsing pytest results: {e}")
        return None


def parse_integration_test_results(json_file: str) -> Optional[Dict[str, Any]]:
    """統合テスト結果JSONファイルの解析"""
    try:
        if not os.path.exists(json_file):
            logger.warning(f"Integration test results file not found: {json_file}")
            return None
        
        with open(json_file, 'r', encoding='utf-8') as f:
            integration_data = json.load(f)
        
        # 統合テスト結果の抽出
        integration_report = integration_data.get('integration_test_report', {})
        
        logger.info("✓ Parsed integration test results")
        return integration_report
        
    except Exception as e:
        logger.error(f"Error parsing integration test results: {e}")
        return None


def collect_log_files() -> List[Dict[str, Any]]:
    """ログファイルの収集"""
    log_files = []
    
    # 収集対象のログファイル
    log_patterns = [
        'workflow_test.log',
        'integration_test.log',
        '*.log'
    ]
    
    try:
        import glob
        
        for pattern in log_patterns:
            for log_file in glob.glob(pattern):
                if os.path.exists(log_file):
                    try:
                        file_size = os.path.getsize(log_file)
                        modified_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                        
                        log_info = {
                            'filename': log_file,
                            'size_bytes': file_size,
                            'modified_at': modified_time.isoformat(),
                            'available': True
                        }
                        
                        # ログファイルの最後の数行を取得（エラー確認用）
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                log_info['last_lines'] = lines[-10:] if len(lines) > 10 else lines
                        except Exception:
                            log_info['last_lines'] = []
                        
                        log_files.append(log_info)
                        
                    except Exception as e:
                        logger.warning(f"Error reading log file {log_file}: {e}")
        
        logger.info(f"✓ Collected {len(log_files)} log files")
        
    except Exception as e:
        logger.error(f"Error collecting log files: {e}")
    
    return log_files


def detect_ci_environment() -> Dict[str, Any]:
    """CI環境の検出"""
    ci_info = {
        'is_ci': False,
        'platform': 'unknown',
        'environment_variables': {},
        'github_actions': False
    }
    
    try:
        # CI環境の検出
        ci_info['is_ci'] = os.getenv('CI', '').lower() == 'true'
        ci_info['github_actions'] = os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
        
        if ci_info['github_actions']:
            ci_info['platform'] = 'github_actions'
        elif ci_info['is_ci']:
            ci_info['platform'] = 'ci_generic'
        else:
            ci_info['platform'] = 'local'
        
        # 関連する環境変数の収集
        relevant_env_vars = [
            'CI', 'GITHUB_ACTIONS', 'GITHUB_WORKFLOW', 'GITHUB_RUN_ID',
            'GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_REF',
            'STEPFUNCTIONS_ENDPOINT', 'STATE_MACHINE_ARN'
        ]
        
        for var in relevant_env_vars:
            value = os.getenv(var)
            if value:
                ci_info['environment_variables'][var] = value
        
        logger.info(f"✓ Detected CI environment: {ci_info['platform']}")
        
    except Exception as e:
        logger.error(f"Error detecting CI environment: {e}")
    
    return ci_info


def generate_comprehensive_report() -> Dict[str, Any]:
    """包括的テストレポートの生成"""
    logger.info("🔄 Generating comprehensive test report...")
    
    # 各種データの収集
    pytest_results = parse_pytest_results('test-results.xml')
    integration_results = parse_integration_test_results('integration_test_report.json')
    log_files = collect_log_files()
    ci_environment = detect_ci_environment()
    
    # 包括的レポートの構築
    comprehensive_report = {
        'report_metadata': {
            'generated_at': datetime.now().isoformat(),
            'generator': 'generate_test_report.py',
            'version': '1.0.0'
        },
        'ci_environment': ci_environment,
        'test_results': {
            'pytest': pytest_results,
            'integration': integration_results
        },
        'log_files': log_files,
        'summary': {
            'overall_success': False,
            'total_test_suites': 0,
            'successful_test_suites': 0,
            'issues_found': []
        }
    }
    
    # 全体的な成功判定
    issues = []
    successful_suites = 0
    total_suites = 0
    
    # pytest結果の評価
    if pytest_results:
        total_suites += 1
        if pytest_results['summary']['failed'] == 0:
            successful_suites += 1
        else:
            issues.append(f"pytest: {pytest_results['summary']['failed']} tests failed")
    
    # 統合テスト結果の評価
    if integration_results:
        total_suites += 1
        summary = integration_results.get('summary', {})
        if summary.get('overall_success', False):
            successful_suites += 1
        else:
            failed_scenarios = summary.get('failed_scenarios', 0)
            if failed_scenarios > 0:
                issues.append(f"Integration tests: {failed_scenarios} scenarios failed")
    
    # サマリーの更新
    comprehensive_report['summary'].update({
        'overall_success': len(issues) == 0 and total_suites > 0,
        'total_test_suites': total_suites,
        'successful_test_suites': successful_suites,
        'issues_found': issues
    })
    
    logger.info(f"✓ Comprehensive report generated: {successful_suites}/{total_suites} test suites passed")
    
    return comprehensive_report


def save_report(report: Dict[str, Any], output_file: str):
    """レポートの保存"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✓ Comprehensive report saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        raise


def print_summary(report: Dict[str, Any]):
    """サマリーの表示"""
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST REPORT SUMMARY")
    print("=" * 60)
    
    summary = report['summary']
    ci_env = report['ci_environment']
    
    print(f"Environment: {ci_env['platform']}")
    print(f"Generated at: {report['report_metadata']['generated_at']}")
    print(f"Total Test Suites: {summary['total_test_suites']}")
    print(f"Successful Test Suites: {summary['successful_test_suites']}")
    print(f"Overall Success: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")
    
    if summary['issues_found']:
        print("\n❌ Issues Found:")
        for issue in summary['issues_found']:
            print(f"  - {issue}")
    
    # pytest詳細
    pytest_results = report['test_results']['pytest']
    if pytest_results:
        print(f"\n🧪 pytest Results:")
        pytest_summary = pytest_results['summary']
        print(f"  Total: {pytest_summary['total']}")
        print(f"  Passed: {pytest_summary['passed']}")
        print(f"  Failed: {pytest_summary['failed']}")
        print(f"  Success Rate: {pytest_summary['success_rate']}")
    
    # 統合テスト詳細
    integration_results = report['test_results']['integration']
    if integration_results:
        print(f"\n🔗 Integration Test Results:")
        integration_summary = integration_results.get('summary', {})
        print(f"  Total Scenarios: {integration_summary.get('total_scenarios', 0)}")
        print(f"  Successful: {integration_summary.get('successful_scenarios', 0)}")
        print(f"  Failed: {integration_summary.get('failed_scenarios', 0)}")
        print(f"  Success Rate: {integration_summary.get('success_rate_percent', 0):.1f}%")
    
    print("=" * 60)


def main():
    """メイン実行関数"""
    logger.info("🚀 Starting comprehensive test report generation")
    
    try:
        # 包括的レポートの生成
        report = generate_comprehensive_report()
        
        # レポートの保存
        output_file = 'comprehensive_test_report.json'
        save_report(report, output_file)
        
        # サマリーの表示
        print_summary(report)
        
        # 終了コードの決定
        if report['summary']['overall_success']:
            logger.info("🎉 All tests passed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Error generating comprehensive test report: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()