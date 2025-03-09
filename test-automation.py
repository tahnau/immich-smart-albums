#!/usr/bin/env python3
"""CLI Test Automation: Execute commands and compare outputs to previous runs"""

import argparse
import difflib
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

class CLITester:
    def __init__(self, test_file=None, history_dir="test_history", report_file=None, update_baseline=False):
        self.test_cases = []
        self.history_dir = history_dir
        self.report_file = report_file
        self.update_baseline = update_baseline
        self.results = {"passed": 0, "failed": 0, "tests": []}

        if not os.path.exists(history_dir): os.makedirs(history_dir)
        if test_file and os.path.exists(test_file): self.load_test_cases(test_file)

    def load_test_cases(self, file_path):
        with open(file_path, 'r') as f:
            self.test_cases.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    def add_test_case(self, command): self.test_cases.append(command)
    def add_test_cases(self, commands): self.test_cases.extend(commands)

    def execute_command(self, command):
        try:
            # Using shell=True to properly handle shell operators like pipes
            process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=60)
            return process.stdout + process.stderr, process.returncode
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 60 seconds", 1
        except Exception as e:
            return f"ERROR: Failed to execute command: {e}", 1

    def get_history_file(self, command):
        import hashlib
        # Create MD5 hash of the command
        hash_obj = hashlib.md5(command.encode())
        hash_name = hash_obj.hexdigest()
        return os.path.join(self.history_dir, f"{hash_name}.json")

    def load_history(self, history_file):
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f: return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: History file {history_file} is corrupted. Starting fresh.")
        return []

    def save_history(self, history_file, history):
        with open(history_file, 'w') as f: json.dump(history, f, indent=2)

    def compare_outputs(self, current, previous, historical):
        if previous is None: return True, "No previous runs to compare with.", False
        if current == previous: return True, "Output matches previous run.", False

        diff = difflib.unified_diff(previous.splitlines(), current.splitlines(),
                                   lineterm='', fromfile='previous', tofile='current')
        suspicious = historical is not None and previous == historical and current != previous
        # Convert diff iterator to list to count lines
        diff_list = list(diff)
        return False, diff_list, suspicious

    def run_tests(self):
        print(f"Running {len(self.test_cases)} test cases...")

        for i, command in enumerate(self.test_cases, 1):
            print(f"[{i}/{len(self.test_cases)}] Command: {command}")
            output, return_code = self.execute_command(command)
            test_result = {
                "command": command, "timestamp": datetime.now().isoformat(),
                "output": output, "return_code": return_code, "status": "PASSED"
            }

            history_file = self.get_history_file(command)
            history = self.load_history(history_file)

            if self.update_baseline:
                history = [test_result]
                self.save_history(history_file, history)
                print(f"  Status: BASELINE | Return code: {return_code} | History: {os.path.basename(history_file)}")
                test_result["status"] = "BASELINE"
                self.results["tests"].append(test_result)
                continue

            previous_output = history[-1]["output"] if history else None
            historical_output = history[-2]["output"] if len(history) > 1 else None

            is_match, diff_output, suspicious = self.compare_outputs(output, previous_output, historical_output)

            if not is_match:
                test_result["status"], test_result["diff"], test_result["suspicious"] = "FAILED", '\n'.join(diff_output), suspicious
                self.results["failed"] += 1
                print(f"  Status: FAILED | Return code: {return_code} | History: {os.path.basename(history_file)}")
                if suspicious: print("  WARNING: Current output differs from two identical previous runs!")
                # Show only first 10 lines of diff
                print("\n  Diff (first 10 lines):")
                for line_num, line in enumerate(diff_output[:10]):
                    print(f"    {line}")
                if len(diff_output) > 10:
                    print(f"    ... ({len(diff_output) - 10} more lines)")
            else:
                self.results["passed"] += 1
                print(f"  Status: PASSED | Return code: {return_code} | History: {os.path.basename(history_file)}")

            history.append(test_result)
            self.save_history(history_file, history)
            self.results["tests"].append(test_result)

    def generate_report(self):
        report = [
            "=" * 80,
            f"CLI Test Report - {datetime.now().isoformat()}",
            "=" * 80,
            f"Total Tests: {len(self.results['tests'])}",
            f"Passed: {self.results['passed']}",
            f"Failed: {self.results['failed']}",
            "=" * 80
        ]

        for test in self.results["tests"]:
            report.extend([
                f"\nCommand: {test['command']}",
                f"Status: {test['status']}",
                f"Return Code: {test['return_code']}"
            ])

            if test["status"] == "FAILED":
                # Limit diff to 10 lines in the report
                diff_lines = test["diff"].splitlines()
                limited_diff = '\n'.join(diff_lines[:10])
                if len(diff_lines) > 10:
                    limited_diff += f"\n... ({len(diff_lines) - 10} more lines)"

                report.extend(["\nDiff:", limited_diff])
                if test.get("suspicious", False):
                    report.append("\nWARNING: Output differs from two identical previous runs!")

            report.append("-" * 80)

        return "\n".join(report)

    def save_report(self, report):
        if self.report_file:
            with open(self.report_file, 'w') as f: f.write(report)
            print(f"Report saved to {self.report_file}")

def main():
    parser = argparse.ArgumentParser(description='Automated CLI Testing Tool')
    parser.add_argument('-f', '--file', help='File containing test cases (one per line)')
    parser.add_argument('-c', '--commands', nargs='+', help='Test commands to run')
    parser.add_argument('-d', '--history-dir', default='test_history', help='Directory to store test history')
    parser.add_argument('-r', '--report', help='File to save the test report')
    parser.add_argument('-u', '--update-baseline', action='store_true', help='Update baseline for all tests')

    args = parser.parse_args()

    if not args.file and not args.commands:
        parser.error("Either --file or --commands must be provided")

    tester = CLITester(test_file=args.file, history_dir=args.history_dir,
                      report_file=args.report, update_baseline=args.update_baseline)

    if args.commands: tester.add_test_cases(args.commands)

    tester.run_tests()
    report = tester.generate_report()
    print(report)
    tester.save_report(report)

if __name__ == "__main__":
    main()
