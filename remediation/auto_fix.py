#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
from datetime import datetime

class RemediationEngine:
    """Engine to apply corrections for failed rules with safety checks"""

    def __init__(self, logger=None):
        self.logger = logger
        self.applied_fixes = []
        self.failed_fixes = []
        self.skipped_fixes = []

    def apply_fixes_for_failed_rules(self, failed_results, get_rule_by_id, interactive=True):
        """
        Apply fixes for failed rules with comprehensive safety filtering
        
        Args:
            failed_results: List of failed check results
            get_rule_by_id: Function to retrieve rule by ID
            interactive: If True, ask confirmation before each fix
        """
        for result in failed_results:
            rule = get_rule_by_id(result.rule_id)
            
            if rule is None:
                if self.logger:
                    self.logger.warning(f"Rule {result.rule_id} not found, skipping")
                continue

            # ═══════════════════════════════════════════════════════════
            # FILTER 1: Manual and CORRECTION rules
            # ═══════════════════════════════════════════════════════════
            if rule.fix.get("correction_manual", False):
                if self.logger:
                    self.logger.info(f"⏭️  Règle {rule.id} ignorée : correction manuelle requise (CORRECTION)")
                self.skipped_fixes.append({
                    'rule_id': rule.id,
                    'reason': 'Manual correction required (CORRECTION flag)'
                })
                continue
            
            if rule.fix.get("type") == "manual":
                if self.logger:
                    self.logger.info(f"⏭️  Règle {rule.id} ignorée : règle manuelle (YES)")
                self.skipped_fixes.append({
                    'rule_id': rule.id,
                    'reason': 'Manual rule (YES flag)'
                })
                continue

            # ═══════════════════════════════════════════════════════════
            # FILTER 2: Risky rules (firewall, critical paths, dangerous commands)
            # ═══════════════════════════════════════════════════════════
            correction = rule.fix.get("command", "")
            rule_id = rule.id
            file_path = rule.check.get("file", "")

            risky = False
            risky_reason = ""

            # Check 1: Debian filesystem/firewall rules
            if file_path and "debian" in file_path:
                if rule_id.startswith("1.1."):
                    risky = True
                    risky_reason = "Debian filesystem rule (1.1.*)"
                elif rule_id.startswith("4."):
                    risky = True
                    risky_reason = "Debian firewall rule (4.*)"
                elif "5.1.4" in rule_id:
                    risky = True
                    risky_reason = "SSH access configuration (5.1.4)"

                # Check 2: Corrections affecting critical system paths
                if "/usr/lib" in correction or "/usr/bin" or "/usr/sbin" in correction:
                    risky = True
                    risky_reason = "Modifies critical system paths (/usr/lib or /usr/bin)"

                # Check 3: Dangerous chmod -R outside /usr/local
                if "chmod -R" in correction and "/usr/local" not in correction:
                    risky = True
                    risky_reason = "Recursive chmod outside /usr/local"
                    
                if rule_id in ["5.4.2.7", "5.4.2.8"]:
                    risky = True
                    risky_reason = "Modifies user shells or locks accounts (5.4.2.7/5.4.2.8)"

            if risky:
                if self.logger:
                    self.logger.warning(f"⏭️  Règle {rule.id} ignorée : {risky_reason}")
                self.skipped_fixes.append({
                    'rule_id': rule.id,
                    'reason': risky_reason
                })
                continue

            # ═══════════════════════════════════════════════════════════
            # FILTER 3: Empty or invalid fix command
            # ═══════════════════════════════════════════════════════════
            fix_command = correction.strip()
            if not fix_command:
                if self.logger:
                    self.logger.warning(f"Pas de commande de correction définie pour la règle {rule.id}")
                self.skipped_fixes.append({
                    'rule_id': rule.id,
                    'reason': 'No fix command defined'
                })
                continue

            # ═══════════════════════════════════════════════════════════
            # INTERACTIVE MODE: Ask user confirmation
            # ═══════════════════════════════════════════════════════════
            if interactive:
                print("="*60)
                print(f"Rule: {rule.id} - {rule.title}")
                print(f"Status: {result.status.upper()}")
                print(f"Fix: {rule.fix.get('description', '')}")
                print(f"Command: {fix_command}")
                print("="*60)
                answer = input("Apply this fix? [y/N]: ")
                if not answer or answer[0].lower() != "y":
                    if self.logger:
                        self.logger.info(f"Correction ignorée pour {rule.id} (user declined)")
                    self.skipped_fixes.append({
                        'rule_id': rule.id,
                        'reason': 'User declined'
                    })
                    continue

            # ═══════════════════════════════════════════════════════════
            # BACKUP: Create backup if target file exists
            # ═══════════════════════════════════════════════════════════
            target_file = rule.check.get("file", "")
            if target_file and os.path.exists(target_file):
                backup_dir = "./backups/"
                os.makedirs(backup_dir, exist_ok=True)
                backup_name = f"{os.path.basename(target_file)}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_path = os.path.join(backup_dir, backup_name)
                
                try:
                    shutil.copy2(target_file, backup_path)
                    if self.logger:
                        self.logger.info(f"Backup created: {backup_path}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to create backup for {target_file}: {e}")
                    self.failed_fixes.append({
                        'rule_id': rule.id,
                        'error': f'Backup failed: {str(e)}'
                    })
                    continue

            # ═══════════════════════════════════════════════════════════
            # APPLY FIX: Execute correction command
            # ═══════════════════════════════════════════════════════════
            try:
                if self.logger:
                    self.logger.info(f"Applying fix for {rule.id}...")
                
                result_process = subprocess.run(
                    fix_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minutes timeout
                )
                
                if result_process.returncode == 0:
                    if self.logger:
                        self.logger.info(f"✓ Fix applied successfully for {rule.id}")
                    self.applied_fixes.append({
                        'rule_id': rule.id,
                        'command': fix_command,
                        'stdout': result_process.stdout,
                        'stderr': result_process.stderr
                    })
                else:
                    if self.logger:
                        self.logger.error(f"✗ Fix failed for {rule.id}. Exit code: {result_process.returncode}")
                        self.logger.error(f"   STDERR: {result_process.stderr}")
                    self.failed_fixes.append({
                        'rule_id': rule.id,
                        'error': f'Exit code {result_process.returncode}: {result_process.stderr}',
                        'command': fix_command
                    })
                    
            except subprocess.TimeoutExpired:
                if self.logger:
                    self.logger.error(f"Fix timeout for {rule.id}")
                self.failed_fixes.append({
                    'rule_id': rule.id,
                    'error': 'Command timeout (180s)',
                    'command': fix_command
                })
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Fix exception for {rule.id}: {e}")
                self.failed_fixes.append({
                    'rule_id': rule.id,
                    'error': str(e),
                    'command': fix_command
                })

    def generate_remediation_log(self, log_file):
        """Generate detailed remediation log file"""
        try:
            with open(log_file, 'w') as f:
                f.write("="*80 + "\n")
                f.write("AUDITY REMEDIATION LOG\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")

                # Applied fixes
                f.write(f"APPLIED FIXES: {len(self.applied_fixes)}\n")
                f.write("-"*80 + "\n")
                for fix in self.applied_fixes:
                    f.write(f"Rule ID: {fix['rule_id']}\n")
                    f.write(f"Command: {fix['command']}\n")
                    if fix.get('stdout'):
                        f.write(f"STDOUT: {fix['stdout']}\n")
                    if fix.get('stderr'):
                        f.write(f"STDERR: {fix['stderr']}\n")
                    f.write("\n")

                # Failed fixes
                f.write(f"\nFAILED FIXES: {len(self.failed_fixes)}\n")
                f.write("-"*80 + "\n")
                for fix in self.failed_fixes:
                    f.write(f"Rule ID: {fix['rule_id']}\n")
                    f.write(f"Command: {fix.get('command', 'N/A')}\n")
                    f.write(f"Error: {fix['error']}\n\n")

                # Skipped fixes
                f.write(f"\nSKIPPED FIXES: {len(self.skipped_fixes)}\n")
                f.write("-"*80 + "\n")
                for fix in self.skipped_fixes:
                    f.write(f"Rule ID: {fix['rule_id']}\n")
                    f.write(f"Reason: {fix['reason']}\n\n")

            if self.logger:
                self.logger.info(f"Remediation log generated: {log_file}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate remediation log: {e}")

    @property
    def summary(self):
        """Return summary statistics"""
        return {
            'total_attempted': len(self.applied_fixes) + len(self.failed_fixes),
            'successful': len(self.applied_fixes),
            'failed': len(self.failed_fixes),
            'skipped': len(self.skipped_fixes)
        }
