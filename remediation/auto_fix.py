#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
from datetime import datetime
from typing import List

class RemediationEngine:
    """Applies security fixes based on failed checks"""

    def __init__(self, logger=None, backup_dir="./backups", interactive=True):
        self.logger = logger
        self.backup_dir = backup_dir
        self.interactive = interactive
        self.applied_fixes = []
        self.failed_fixes = []

    def apply_fixes(self, failed_results, rules_map: dict) -> dict:
        """Apply fixes for failed checks"""
        if self.logger:
            self.logger.info(f"Starting remediation for {len(failed_results)} failed checks...")

        os.makedirs(self.backup_dir, exist_ok=True)

        for result in failed_results:
            rule = rules_map.get(result.rule_id)

            if not rule:
                if self.logger:
                    self.logger.warning(f"Rule {result.rule_id} not found, skipping fix")
                continue

            if not rule.fix or not rule.fix.get("command"):
                if self.logger:
                    self.logger.warning(f"No fix available for {result.rule_id}")
                continue

            if self.interactive:
                print(f"\n{'='*60}")
                print(f"Rule: {result.rule_id} - {result.title}")
                print(f"Status: FAILED")
                print(f"Fix: {rule.fix.get('description', 'No description')}")
                print(f"Command: {rule.fix.get('command')}")
                print(f"{'='*60}")
                response = input("Apply this fix? [y/N]: ").strip().lower()

                if response not in ['y', 'yes']:
                    if self.logger:
                        self.logger.info(f"Skipped fix for {result.rule_id}")
                    continue

            success = self._apply_single_fix(result, rule)

            if success:
                self.applied_fixes.append({
                    'rule_id': result.rule_id,
                    'title': result.title,
                    'timestamp': datetime.now()
                })
            else:
                self.failed_fixes.append({
                    'rule_id': result.rule_id,
                    'title': result.title,
                    'timestamp': datetime.now()
                })

        summary = {
            'total_attempted': len(failed_results),
            'successful': len(self.applied_fixes),
            'failed': len(self.failed_fixes),
            'applied_fixes': self.applied_fixes,
            'failed_fixes': self.failed_fixes
        }

        if self.logger:
            self.logger.success(f"Remediation completed: {summary['successful']}/{summary['total_attempted']} fixes applied")

        return summary

    def _apply_single_fix(self, result, rule) -> bool:
        """Apply a single fix"""
        try:
            fix_command = rule.fix.get("command")

            if not fix_command:
                return False

            if rule.check.get("file"):
                file_path = rule.check.get("file")
                if os.path.exists(file_path):
                    self._create_backup(file_path)

            if self.logger:
                self.logger.info(f"Applying fix for {result.rule_id}...")

            result_exec = subprocess.run(
                fix_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result_exec.returncode == 0:
                if self.logger:
                    self.logger.success(f"Fix applied successfully for {result.rule_id}")
                return True
            else:
                if self.logger:
                    self.logger.error(f"Fix failed for {result.rule_id}: {result_exec.stderr}")
                return False

        except subprocess.TimeoutExpired:
            if self.logger:
                self.logger.error(f"Fix timeout for {result.rule_id}")
            return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error applying fix for {result.rule_id}: {e}")
            return False

    def _create_backup(self, file_path: str):
        """Create backup of a file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{os.path.basename(file_path)}.backup.{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            shutil.copy2(file_path, backup_path)

            if self.logger:
                self.logger.info(f"Backup created: {backup_path}")

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to create backup for {file_path}: {e}")

    def generate_remediation_log(self, output_file: str):
        """Generate a log file of all remediation actions"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("AUDITY REMEDIATION LOG\n")
                f.write("="*80 + "\n\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Total Fixes Attempted: {len(self.applied_fixes) + len(self.failed_fixes)}\n")
                f.write(f"Successful: {len(self.applied_fixes)}\n")
                f.write(f"Failed: {len(self.failed_fixes)}\n\n")

                if self.applied_fixes:
                    f.write("="*80 + "\n")
                    f.write("SUCCESSFULLY APPLIED FIXES\n")
                    f.write("="*80 + "\n\n")
                    for fix in self.applied_fixes:
                        f.write(f"[{fix['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] ")
                        f.write(f"{fix['rule_id']}: {fix['title']}\n")

                if self.failed_fixes:
                    f.write("\n" + "="*80 + "\n")
                    f.write("FAILED FIXES\n")
                    f.write("="*80 + "\n\n")
                    for fix in self.failed_fixes:
                        f.write(f"[{fix['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] ")
                        f.write(f"{fix['rule_id']}: {fix['title']}\n")

            if self.logger:
                self.logger.success(f"Remediation log saved: {output_file}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to write remediation log: {e}")
