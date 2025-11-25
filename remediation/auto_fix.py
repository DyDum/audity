#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
from datetime import datetime

class RemediationEngine:
    """Engine to apply corrections for failed rules"""

    def __init__(self, logger=None):
        self.logger = logger

    def apply_fixes_for_failed_rules(self, failed_results, get_rule_by_id, interactive=True):
        for result in failed_results:
            rule = get_rule_by_id(result.rule_id)
            
            # ===== AJOUT CRITIQUE =====
            # Si la règle est en correction manuelle, ne pas appliquer/proposer de correction
            if rule is None:
                continue
            if rule.fix.get("correction_manual", False) or rule.fix.get("type") == "manual":
                if self.logger:
                    self.logger.info(f"⏭️  Règle {rule.id} ignorée : correction manuelle ('CORRECTION')")
                continue
            # ==========================

            fix_command = rule.fix.get("command", "").strip()
            if not fix_command:
                if self.logger:
                    self.logger.warning(f"Pas de commande de correction définie pour la règle {rule.id}")
                continue

            # Proposer la correction en mode interactif
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
                        self.logger.info(f"Correction ignorée pour {rule.id}")
                    continue

            # Création d'un backup
            target_file = rule.check.get("file", "")
            if target_file and os.path.exists(target_file):
                backup_dir = "./backups/"
                os.makedirs(backup_dir, exist_ok=True)
                backup_name = f"{os.path.basename(target_file)}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_path = os.path.join(backup_dir, backup_name)
                shutil.copy2(target_file, backup_path)
                if self.logger:
                    self.logger.info(f"Backup created: {backup_path}")

            # Appliquer la correction
            try:
                if self.logger:
                    self.logger.info(f"Applying fix for {rule.id}...")
                result_process = subprocess.run(
                    fix_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if result_process.returncode == 0:
                    if self.logger:
                        self.logger.info(f"✓ Fix applied successfully for {rule.id}")
                else:
                    if self.logger:
                        self.logger.error(f"✗ Fix failed for {rule.id}. STDERR: {result_process.stderr}")
            except subprocess.TimeoutExpired:
                if self.logger:
                    self.logger.error(f"Fix timeout for {rule.id}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Fix exception for {rule.id}: {e}")
