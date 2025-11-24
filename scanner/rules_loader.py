#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
from lxml import etree
from typing import List, Dict

class Rule:
    """Represents a CIS rule"""
    
    def __init__(self, rule_id: str, title: str, description: str, 
                 rationale: str, severity: str, check: Dict, fix: Dict):
        self.id = rule_id
        self.title = title
        self.description = description
        self.rationale = rationale
        self.severity = severity
        self.check = check
        self.fix = fix
    
    def __repr__(self):
        return f"<Rule {self.id}: {self.title}>"

class RulesLoader:
    """Loads and parses CIS rules from XML files"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.rules = []
    
    def load_rules_from_directories(self, directories: List[str]) -> List[Rule]:
        """Load all rules from multiple directories"""
        all_rules = []
        
        for directory in directories:
            if not os.path.exists(directory):
                if self.logger:
                    self.logger.warning(f"Directory not found: {directory}")
                continue
            
            xml_files = glob.glob(os.path.join(directory, "*.xml"))
            
            if self.logger:
                self.logger.info(f"Loading rules from {directory} ({len(xml_files)} files)")
            
            for xml_file in xml_files:
                try:
                    rules = self._parse_xml_file(xml_file)
                    all_rules.extend(rules)
                    if self.logger:
                        self.logger.debug(f"  Loaded {len(rules)} rules from {os.path.basename(xml_file)}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"  Error parsing {xml_file}: {e}")
        
        self.rules = all_rules
        
        if self.logger:
            self.logger.success(f"Total rules loaded: {len(all_rules)}")
        
        return all_rules
    
    def _parse_xml_file(self, xml_file: str) -> List[Rule]:
        """Parse a single XML file and extract rules"""
        rules = []
        
        try:
            tree = etree.parse(xml_file)
            root = tree.getroot()
            
            # Détection du format XML
            if root.tag == "RulesCIS":
                # Format personnalisé
                for rule_elem in root.xpath(".//Rule"):
                    rule = self._parse_custom_rule_element(rule_elem)
                    if rule:
                        rules.append(rule)
            else:
                # Format standard
                for rule_elem in root.xpath(".//Rule"):
                    rule = self._parse_rule_element(rule_elem)
                    if rule:
                        rules.append(rule)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing XML file {xml_file}: {e}")
        
        return rules
    
    def _parse_custom_rule_element(self, rule_elem) -> Rule:
        """Parse a Rule element in custom format (RulesCIS) with CORRECTION support"""
        try:
            rule_id = rule_elem.get("id", "unknown")
            
            # Extract title (Name)
            title = rule_elem.findtext("Name", "No title").strip()
            
            # Extract description (NonCompliantComment)
            description = rule_elem.findtext("NonCompliantComment", "").strip()
            
            # Extract rationale (CorrectiveComment)
            rationale = rule_elem.findtext("CorrectiveComment", "").strip()
            
            # Determine severity from Profile level
            profiles = rule_elem.find("Profiles")
            severity = "medium"
            if profiles is not None:
                profile = profiles.find("Profile")
                if profile is not None:
                    level = profile.get("level", "1")
                    severity = "high" if level == "1" else "medium"
            
            # Check manual type (NEW: support for CORRECTION)
            manual_value = rule_elem.findtext("Manual", "NO").strip().upper()
            is_manual = manual_value == "YES"
            is_correction_manual = manual_value == "CORRECTION"
            
            # Extract check information
            base_path = rule_elem.findtext("BasePath", "").strip()
            file_name = rule_elem.findtext("FileName", "").strip()
            verification = rule_elem.findtext("Verification", "").strip()
            
            # Construire le chemin complet du fichier
            if base_path and file_name:
                file_path = os.path.join(base_path, file_name)
            elif base_path:
                file_path = base_path
            else:
                file_path = ""
            
            # Construire l'objet check
            if is_manual:
                # Règle complètement manuelle
                check = {
                    "test_type": "manual",
                    "file": file_path,
                    "command": verification,
                    "pattern": "",
                    "value": "",
                    "correction_manual": False
                }
            elif is_correction_manual:
                # Vérification automatique, mais correction manuelle
                if verification:
                    check = {
                        "test_type": "command_output",
                        "file": file_path,
                        "command": verification,
                        "pattern": "",
                        "value": "0",
                        "correction_manual": True  # ← Flag spécial
                    }
                elif file_path:
                    check = {
                        "test_type": "file_exists",
                        "file": file_path,
                        "command": "",
                        "pattern": "",
                        "value": "",
                        "correction_manual": True  # ← Flag spécial
                    }
                else:
                    check = {
                        "test_type": "manual",
                        "file": "",
                        "command": "",
                        "pattern": "",
                        "value": "",
                        "correction_manual": True  # ← Flag spécial
                    }
            else:
                # Règle automatisée normale (vérification + correction)
                if verification:
                    check = {
                        "test_type": "command_output",
                        "file": file_path,
                        "command": verification,
                        "pattern": "",
                        "value": "0",
                        "correction_manual": False
                    }
                elif file_path:
                    check = {
                        "test_type": "file_exists",
                        "file": file_path,
                        "command": "",
                        "pattern": "",
                        "value": "",
                        "correction_manual": False
                    }
                else:
                    check = {
                        "test_type": "manual",
                        "file": "",
                        "command": "",
                        "pattern": "",
                        "value": "",
                        "correction_manual": False
                    }
            
            # Extract fix information
            correction = rule_elem.findtext("Correction", "").strip()
            fix = {
                "type": "manual" if (is_manual or is_correction_manual) else "command",
                "command": correction,
                "description": rationale,
                "correction_manual": is_correction_manual  # ← Flag spécial
            }
            
            return Rule(rule_id, title, description, rationale, severity, check, fix)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing custom rule element: {e}")
            return None
    
    def _parse_rule_element(self, rule_elem) -> Rule:
        """Parse a single Rule XML element (standard format)"""
        try:
            rule_id = rule_elem.get("id", "unknown")
            severity = rule_elem.get("severity", "medium")
            
            # Extract title
            title_elem = rule_elem.find("title")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No title"
            
            # Extract description
            description_elem = rule_elem.find("description")
            description = description_elem.text.strip() if description_elem is not None and description_elem.text else ""
            
            # Extract rationale
            rationale_elem = rule_elem.find("rationale")
            rationale = rationale_elem.text.strip() if rationale_elem is not None and rationale_elem.text else ""
            
            # Extract check
            check_elem = rule_elem.find("check")
            check = self._parse_check_element(check_elem) if check_elem is not None else {}
            
            # Extract fix
            fix_elem = rule_elem.find("fix")
            fix = self._parse_fix_element(fix_elem) if fix_elem is not None else {}
            
            return Rule(rule_id, title, description, rationale, severity, check, fix)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing rule element: {e}")
            return None
    
    def _parse_check_element(self, check_elem) -> Dict:
        """Parse check element (standard format)"""
        check = {
            "test_type": check_elem.get("test-type", ""),
            "file": check_elem.findtext("file", "").strip(),
            "pattern": check_elem.findtext("pattern", "").strip(),
            "value": check_elem.findtext("value", "").strip(),
            "command": check_elem.findtext("command", "").strip(),
            "correction_manual": False  # Par défaut pour format standard
        }
        return check
    
    def _parse_fix_element(self, fix_elem) -> Dict:
        """Parse fix element (standard format)"""
        fix = {
            "type": fix_elem.get("type", "manual"),
            "command": fix_elem.findtext("command", "").strip(),
            "description": fix_elem.findtext("description", "").strip(),
            "correction_manual": False  # Par défaut pour format standard
        }
        return fix
    
    def get_rules_by_severity(self, severity: str) -> List[Rule]:
        """Filter rules by severity"""
        return [rule for rule in self.rules if rule.severity.lower() == severity.lower()]
    
    def get_rule_by_id(self, rule_id: str) -> Rule:
        """Get a specific rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
