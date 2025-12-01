#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audity - CIS Benchmark Security Scanner
Main entry point for the application

Authors: Dylan CARBON - Clément LAVALLÉE
"""

import sys
import os
import argparse
import configparser
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger
from utils.privilege_checker import require_admin, get_current_user
from scanner.system_detector import SystemDetector
from scanner.rules_loader import RulesLoader
from scanner.vulnerability_checker import VulnerabilityChecker, CheckResult
from reports.xml_generator import XMLReportGenerator
from reports.html_generator import HTMLReportGenerator
from remediation.auto_fix import RemediationEngine
from integrity.rules_integrity import RulesIntegrityChecker

def load_config(config_file: str) -> configparser.ConfigParser:
    """Load configuration from file"""
    config = configparser.ConfigParser()

    config['scanner'] = {
        'rules_dir': './rules',
        'output_dir': './reports',
        'log_level': 'INFO',
        'log_file': './logs/audity.log',
        'max_threads': '1'
    }
    config['reports'] = {
        'generate_html': 'true',
        'generate_xml': 'true',
        'format_version': '1.0'
    }
    config['remediation'] = {
        'create_backup': 'true',
        'backup_dir': './backups',
        'interactive': 'true'
    }

    if os.path.exists(config_file):
        config.read(config_file)

    return config

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Audity - CIS Benchmark Security Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a complete scan
  sudo python main.py scan --rules ./rules --output ./reports

  # Run scan with remediation
  sudo python main.py scan --rules ./rules --output ./reports --fix

  # Run scan with specific number of threads
  sudo python main.py scan --rules ./rules --threads 8

  # View existing report
  python main.py report --input ./reports/scan_20241104.xml
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.ini',
        help='Configuration file path (default: config.ini)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output (DEBUG level)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    scan_parser = subparsers.add_parser('scan', help='Run security scan')
    scan_parser.add_argument(
        '--rules',
        type=str,
        help='Path to rules directory'
    )
    scan_parser.add_argument(
        '--output',
        type=str,
        help='Output directory for reports'
    )
    scan_parser.add_argument(
        '--threads',
        type=int,
        help='Number of threads for parallel scanning'
    )
    scan_parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply automatic fixes for failed checks'
    )
    scan_parser.add_argument(
        '--no-interactive',
        action='store_true',
        help='Disable interactive confirmation for fixes'
    )

    report_parser = subparsers.add_parser('report', help='View existing report')
    report_parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to XML report file'
    )

    return parser.parse_args()

def run_scan(args, config, logger):
    """Execute security scan with integrity check"""
    logger.info("="*60)
    logger.info("AUDITY SECURITY SCANNER")
    logger.info("="*60)
    logger.info(f"User: {get_current_user()}")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # ═══════════════════════════════════════════════════════════
    # STEP 0: Rules Integrity Check (NEW)
    # ═══════════════════════════════════════════════════════════
    logger.info("\n[0/6] Checking rules integrity...")
    
    rules_dir_for_integrity = args.rules or config.get('scanner', 'rules_dir')
    integrity_checker = RulesIntegrityChecker(rules_dir=rules_dir_for_integrity, logger=logger)
    
    if not integrity_checker.verify_integrity():
        logger.error("\n" + "="*60)
        logger.error("⚠️  CRITICAL: Rules integrity check failed!")
        logger.error("="*60)
        logger.error("Possible causes:")
        logger.error("  - Rules files have been modified")
        logger.error("  - Rules files have been deleted")
        logger.error("  - Unauthorized changes detected")
        logger.error("\nAborting scan.")
        logger.error("If changes are intentional, regenerate rules_integrity.txt")
        logger.error("="*60 + "\n")
        return 1

    logger.success("✓ Integrity check passed - All rules are unchanged\n")

    # ═══════════════════════════════════════════════════════════
    # STEP 1: System Detection
    # ═══════════════════════════════════════════════════════════
    rules_dir = args.rules or config.get('scanner', 'rules_dir')
    output_dir = args.output or config.get('scanner', 'output_dir')
    max_threads = args.threads or config.getint('scanner', 'max_threads')

    os.makedirs(output_dir, exist_ok=True)

    logger.info("[1/6] Detecting system configuration...")
    detector = SystemDetector(logger)
    os_info = detector.detect_os()
    packages = detector.detect_packages()

    # ═══════════════════════════════════════════════════════════
    # STEP 2: Load Rules
    # ═══════════════════════════════════════════════════════════
    logger.info("\n[2/6] Loading CIS rules...")
    applicable_dirs = detector.get_applicable_rules_dirs(rules_dir)

    if not applicable_dirs:
        logger.error(f"No applicable rules found in {rules_dir}")
        logger.error("Make sure the rules directory structure is correct:")
        logger.error("  rules/")
        logger.error("    ├── debian/")
        logger.error("    ├── apache_http/")
        logger.error("    └── ...")
        return 1

    rules_loader = RulesLoader(logger)
    rules = rules_loader.load_rules_from_directories(applicable_dirs)

    if not rules:
        logger.error("No rules loaded. Cannot proceed with scan.")
        return 1

    # ═══════════════════════════════════════════════════════════
    # STEP 3: Run Security Checks
    # ═══════════════════════════════════════════════════════════
    logger.info(f"\n[3/6] Running security checks ({max_threads} threads)...")
    checker = VulnerabilityChecker(logger, max_workers=1)
    results = checker.check_rules(rules, parallel=False)

    stats = checker.get_statistics()

    logger.info("\n" + "="*60)
    logger.info("SCAN RESULTS")
    logger.info("="*60)
    logger.info(f"Total rules checked: {stats['total']}")
    logger.success(f"Passed: {stats['pass']}")
    logger.error(f"Failed: {stats['fail']}")
    logger.warning(f"Errors: {stats['error']}")
    logger.info(f"Not checked: {stats['notchecked']}")
    logger.info(f"Compliance: {stats['compliance_percentage']:.2f}%")
    logger.info("="*60)

    # ═══════════════════════════════════════════════════════════
    # STEP 4: Generate Reports
    # ═══════════════════════════════════════════════════════════
    logger.info("\n[4/6] Generating reports...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if config.getboolean('reports', 'generate_xml'):
        xml_file = os.path.join(output_dir, f"scan_{timestamp}.xml")
        xml_generator = XMLReportGenerator(logger)
        xml_generator.generate_report(results, xml_file, os_info)

    if config.getboolean('reports', 'generate_html'):
        html_file = os.path.join(output_dir, f"scan_{timestamp}.html")
        html_generator = HTMLReportGenerator(logger)
        html_generator.generate_report(results, html_file, os_info)

    # ═══════════════════════════════════════════════════════════
    # STEP 5: Apply Remediation (if --fix)
    # ═══════════════════════════════════════════════════════════
    if args.fix:
        logger.info("\n[5/6] Applying remediation fixes...")

        failed_results = [r for r in results if r.status == CheckResult.STATUS_FAIL]

        if not failed_results:
            logger.info("No failed checks to remediate.")
        else:
            # Utilitaire pour retrouver la règle à partir de l'ID
            def get_rule_by_id(rule_id):
                return next((rule for rule in rules if rule.id == rule_id), None)

            # Initialisation du moteur de remediation
            engine = RemediationEngine(logger)
            engine.apply_fixes_for_failed_rules(
                failed_results, 
                get_rule_by_id, 
                interactive=not args.no_interactive
            )

            remediation_log = os.path.join(output_dir, f"remediation_{timestamp}.log")
            if hasattr(engine, "generate_remediation_log"):
                engine.generate_remediation_log(remediation_log)

            # Résumé/remplissage basique si pas d'attribut summary
            summary = {
                "total_attempted": len(failed_results),
                "successful": "N/A",
                "failed": "N/A",
                "skipped": "N/A"
            }
            if hasattr(engine, "summary"):
                summary = engine.summary

            logger.info("\n" + "="*60)
            logger.info("REMEDIATION SUMMARY")
            logger.info("="*60)
            logger.info(f"Total attempted: {summary.get('total_attempted')}")
            logger.success(f"Successful: {summary.get('successful')}")
            logger.error(f"Failed: {summary.get('failed')}")
            logger.warning(f"Skipped: {summary.get('skipped')}")
            logger.info("="*60)

            # ═══════════════════════════════════════════════════════════
            # STEP 6: Update Integrity File (after fixes applied)
            # ═══════════════════════════════════════════════════════════
            if summary.get('successful', 0) > 0:
                logger.info("\n[6/6] Updating rules integrity file...")
                integrity_checker.scan_rules_directory()
                integrity_checker.update_integrity_file()
                logger.success("✓ Integrity file updated with new hashes")
    else:
        logger.info("\n[5/6] Skipping remediation (use --fix to apply fixes)")
        logger.info("[6/6] Skipping integrity update")

    logger.info("\n" + "="*60)
    logger.success("SCAN COMPLETED SUCCESSFULLY")
    logger.info("="*60)
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60 + "\n")

    return 0

def view_report(args, logger):
    """View existing report"""
    report_file = args.input

    if not os.path.exists(report_file):
        logger.error(f"Report file not found: {report_file}")
        return 1

    logger.info(f"Viewing report: {report_file}")
    logger.info("Report file found. Open it in a browser or XML viewer.")

    return 0

def main():
    """Main entry point"""
    args = parse_arguments()

    config = load_config(args.config)

    log_level = 'DEBUG' if args.verbose else config.get('scanner', 'log_level')
    log_file = config.get('scanner', 'log_file')

    import logging
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    logger = get_logger('audity', log_file, level_map.get(log_level, logging.INFO))

    if args.command == 'scan':
        require_admin()
        return run_scan(args, config, logger)

    elif args.command == 'report':
        return view_report(args, logger)

    else:
        logger.error("No command specified. Use --help for usage information.")
        return 1

if __name__ == "__main__":
    sys.exit(main())