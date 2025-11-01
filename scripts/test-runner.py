#!/usr/bin/env python3
"""
Test runner script for Step Functions Local testing
Provides detailed test execution and reporting capabilities
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

class TestRunner:
    def __init__(self, config_path="scripts/test-config.json"):
        """Initialize test runner with configuration"""
        self.config = self._load_config(config_path)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0
            }
        }
    
    def _load_config(self, config_path):
        """Load test configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            sys.exit(1)
    
    def setup_environment(self):
        """Set up environment variables for testing"""
        os.environ['STEPFUNCTIONS_ENDPOINT'] = self.config['stepfunctions']['endpoint']
        os.environ['AWS_DEFAULT_REGION'] = self.config['stepfunctions']['region']
        os.environ['AWS_ACCESS_KEY_ID'] = self.config['aws']['access_key_id']
        os.environ['AWS_SECRET_ACCESS_KEY'] = self.config['aws']['secret_access_key']
        
        # Set state machine ARN if available
        if os.path.exists('state_machine_arn.txt'):
            with open('state_machine_arn.txt', 'r') as f:
                os.environ['STATE_MACHINE_ARN'] = f.read().strip()
    
    def run_tests(self, test_path="tests/", verbose=True):
        """Run the test suite"""
        print("🧪 Running Step Functions workflow tests...")
        
        # Setup environment
        self.setup_environment()
        
        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            test_path,
            '--tb=short',
            '--junit-xml=test-results.xml'
        ]
        
        if verbose:
            cmd.append('-v')
        
        # Run tests
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            execution_time = time.time() - start_time
            
            # Parse results
            self._parse_test_results(result, execution_time)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ Tests timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return False
    
    def _parse_test_results(self, result, execution_time):
        """Parse test results from pytest output"""
        self.results['execution_time'] = f"{execution_time:.2f}s"
        self.results['stdout'] = result.stdout
        self.results['stderr'] = result.stderr
        self.results['return_code'] = result.returncode
        
        # Try to parse XML results if available
        if os.path.exists('test-results.xml'):
            self._parse_xml_results()
        
        # Parse from stdout as fallback
        lines = result.stdout.split('\n')
        for line in lines:
            if '=====' in line and 'passed' in line:
                # Extract summary from pytest output
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if 'passed' in line:
                            self.results['summary']['passed'] = int(part)
                        elif 'failed' in line:
                            self.results['summary']['failed'] = int(part)
                        elif 'error' in line:
                            self.results['summary']['errors'] = int(part)
    
    def _parse_xml_results(self):
        """Parse XML test results"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse('test-results.xml')
            root = tree.getroot()
            
            self.results['summary']['total'] = int(root.get('tests', 0))
            self.results['summary']['failed'] = int(root.get('failures', 0))
            self.results['summary']['errors'] = int(root.get('errors', 0))
            self.results['summary']['passed'] = (
                self.results['summary']['total'] - 
                self.results['summary']['failed'] - 
                self.results['summary']['errors']
            )
            
        except Exception as e:
            print(f"⚠️  Could not parse XML results: {e}")
    
    def generate_report(self, output_file="test-report.json"):
        """Generate detailed test report"""
        # Calculate success rate
        total = self.results['summary']['total']
        passed = self.results['summary']['passed']
        
        if total > 0:
            success_rate = (passed / total) * 100
            self.results['summary']['success_rate'] = f"{success_rate:.1f}%"
        else:
            self.results['summary']['success_rate'] = "0%"
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📊 Test report saved to: {output_file}")
    
    def print_summary(self):
        """Print test summary to console"""
        summary = self.results['summary']
        
        print("\n" + "="*50)
        print("📋 TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"💥 Errors: {summary['errors']}")
        print(f"📈 Success Rate: {summary.get('success_rate', 'N/A')}")
        
        if 'execution_time' in self.results:
            print(f"⏱️  Execution Time: {self.results['execution_time']}")
        
        print("="*50)
        
        # Print status
        if summary['failed'] + summary['errors'] == 0:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("💔 SOME TESTS FAILED!")
            return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Step Functions Local Test Runner')
    parser.add_argument('--config', default='scripts/test-config.json',
                       help='Path to test configuration file')
    parser.add_argument('--test-path', default='tests/',
                       help='Path to test directory')
    parser.add_argument('--output', default='test-report.json',
                       help='Output file for test report')
    parser.add_argument('--quiet', action='store_true',
                       help='Run tests in quiet mode')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner(args.config)
    
    # Run tests
    success = runner.run_tests(args.test_path, verbose=not args.quiet)
    
    # Generate report
    runner.generate_report(args.output)
    
    # Print summary
    all_passed = runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()