#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rules Integrity Checker
Verifies MD5 hash integrity of all rules files
"""

import os
import hashlib
from datetime import datetime

class RulesIntegrityChecker:
    """Check and verify integrity of rules files"""

    def __init__(self, rules_dir="./rules", integrity_file="rules_integrity.txt", logger=None):
        self.rules_dir = rules_dir
        self.integrity_file = integrity_file
        self.logger = logger
        self.current_hashes = {}
        self.stored_hashes = {}
        self.modifications = {
            'modified': [],
            'deleted': [],
            'new': [],
            'unchanged': []
        }

    @staticmethod
    def md5_of_file(file_path):
        """Calculate MD5 hash of a file"""
        h = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error computing hash for {file_path}: {e}")
            return None

    def scan_rules_directory(self):
        """Scan rules directory and compute all hashes"""
        self.current_hashes = {}
        
        if not os.path.exists(self.rules_dir):
            if self.logger:
                self.logger.error(f"Rules directory not found: {self.rules_dir}")
            return False

        for root, dirs, files in os.walk(self.rules_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                md5_hash = self.md5_of_file(file_path)
                if md5_hash:
                    self.current_hashes[file_path] = md5_hash

        if self.logger:
            self.logger.info(f"Scanned {len(self.current_hashes)} files in {self.rules_dir}")
        
        return len(self.current_hashes) > 0

    def load_stored_hashes(self):
        """Load previously stored hashes from integrity file"""
        self.stored_hashes = {}
        
        if not os.path.exists(self.integrity_file):
            return False

        try:
            with open(self.integrity_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(' = ')
                    if len(parts) == 2:
                        file_path, md5_hash = parts
                        self.stored_hashes[file_path] = md5_hash

            if self.logger:
                self.logger.info(f"Loaded {len(self.stored_hashes)} stored hashes from {self.integrity_file}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading stored hashes: {e}")
            return False

    def generate_integrity_file(self):
        """Generate new integrity file with current hashes"""
        try:
            with open(self.integrity_file, 'w') as f:
                f.write(f"# Rules Integrity File\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total files: {len(self.current_hashes)}\n")
                f.write(f"# Format: PATH = MD5_HASH\n\n")
                
                for file_path in sorted(self.current_hashes.keys()):
                    md5_hash = self.current_hashes[file_path]
                    f.write(f"{file_path} = {md5_hash}\n")

            if self.logger:
                self.logger.success(f"Integrity file generated: {self.integrity_file}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating integrity file: {e}")
            return False

    def compare_hashes(self):
        """Compare current hashes with stored hashes"""
        self.modifications = {
            'modified': [],
            'deleted': [],
            'new': [],
            'unchanged': []
        }

        # Check for modifications and unchanged
        for file_path, current_hash in self.current_hashes.items():
            if file_path in self.stored_hashes:
                stored_hash = self.stored_hashes[file_path]
                if current_hash == stored_hash:
                    self.modifications['unchanged'].append(file_path)
                else:
                    self.modifications['modified'].append({
                        'path': file_path,
                        'current': current_hash,
                        'stored': stored_hash
                    })
            else:
                self.modifications['new'].append(file_path)

        # Check for deleted files
        for file_path in self.stored_hashes.keys():
            if file_path not in self.current_hashes:
                self.modifications['deleted'].append(file_path)

        return self.modifications

    def verify_integrity(self):
        """
        Main verification process:
        1. If integrity file exists, load and compare
        2. If not exists, generate it
        Return True if all checks pass, False otherwise
        """
        # Step 1: Scan current rules directory
        if not self.scan_rules_directory():
            if self.logger:
                self.logger.error("Failed to scan rules directory")
            return False

        # Step 2: Check if integrity file exists
        if not os.path.exists(self.integrity_file):
            if self.logger:
                self.logger.warning(f"Integrity file not found: {self.integrity_file}")
                self.logger.info("Generating new integrity file...")
            
            return self.generate_integrity_file()

        # Step 3: Load stored hashes
        if not self.load_stored_hashes():
            if self.logger:
                self.logger.warning("Failed to load stored hashes, regenerating...")
            return self.generate_integrity_file()

        # Step 4: Compare hashes
        self.compare_hashes()

        # Step 5: Report results
        return self.report_integrity_status()

    def report_integrity_status(self):
        """Generate and display integrity report"""
        modified_count = len(self.modifications['modified'])
        deleted_count = len(self.modifications['deleted'])
        new_count = len(self.modifications['new'])
        unchanged_count = len(self.modifications['unchanged'])

        if self.logger:
            self.logger.info("\n" + "="*60)
            self.logger.info("RULES INTEGRITY CHECK")
            self.logger.info("="*60)
            self.logger.success(f"✓ Unchanged files: {unchanged_count}")
            
            if new_count > 0:
                self.logger.warning(f"⚠️  New files: {new_count}")
            
            if modified_count > 0:
                self.logger.error(f"✗ Modified files: {modified_count}")
                for item in self.modifications['modified']:
                    self.logger.error(f"   - {item['path']}")
                    self.logger.error(f"     Current:  {item['current']}")
                    self.logger.error(f"     Expected: {item['stored']}")
            
            if deleted_count > 0:
                self.logger.error(f"✗ Deleted files: {deleted_count}")
                for file_path in self.modifications['deleted']:
                    self.logger.error(f"   - {file_path}")
            
            self.logger.info("="*60 + "\n")

        # Return True only if no modifications or deletions detected
        # New files are allowed (but logged as warning)
        if modified_count > 0 or deleted_count > 0:
            if self.logger:
                self.logger.error("⚠️  INTEGRITY CHECK FAILED - Rules have been modified or deleted!")
            return False

        if self.logger:
            self.logger.success("✓ INTEGRITY CHECK PASSED - All rules are unchanged")
        
        return True

    def update_integrity_file(self):
        """Update integrity file with current hashes (after fixes applied)"""
        if self.logger:
            self.logger.info("Updating integrity file with current hashes...")
        
        return self.generate_integrity_file()
