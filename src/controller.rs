use crate::audit_rules;
use crate::package_management;
use crate::report;

use audit_rules::scanner::scan_directory;
use std::{
    process,
    fs,
    path::{Path, PathBuf},
};

use anyhow::{bail, Context, Result};
use askama::Template;

pub fn run_full_audit() {
    if let Err(e) = update_package_list_if_needed() {
        println!("Failed to update package list: {}", e);
    }
    run_package_audit(false, false);
    run_audit_rules();
}

pub fn run_package_audit(update: bool, upgrade: bool) {
    if update {
        if let Err(e) = package_management::update::update_package_list() {
            println!("Failed to update package list: {}", e);
            return;
        }
    }

    if upgrade {
        if !is_root() {
            println!("You must run as root to upgrade the package list.");
            process::exit(1);
        }
    }

    package_management::sources::read_sources_list().unwrap_or_default();
    let total_installed = package_management::list::get_installed_packages_count().unwrap_or(0);
    let installed_packages =
        package_management::list::list_installed_packages().unwrap_or_default();
    let upgradable_packages = if upgrade {
        package_management::update::check_upgradable_packages().unwrap_or_default()
    } else {
        String::new()
    };

    match package_management::xml_report::generate_xml_report(
        total_installed,
        &installed_packages,
        &upgradable_packages,
    ) {
        Ok(xml_data) => {
            std::fs::write("./reports/packages.xml", xml_data).expect("Failed to write XML report");
            println!("XML report generated successfully and saved to 'report.xml'.");
        }
        Err(e) => {
            println!("Failed to generate XML report: {}", e);
        }
    }
}


/// Run applicable audit rule scans based on packages found in packages.xml.
///
/// This function checks which rule directories correspond to installed packages
/// and runs the scan only on those.
pub fn run_audit_rules() {
    let package_file = "reports/packages.xml";

    match audit_rules::scanner::load_installed_packages(package_file) {
        Ok(installed_rules) => {
            for rule in installed_rules {
                let dir = format!("rules/{}", rule);
                if let Err(e) = scan_directory(&dir) {
                    eprintln!("Error scanning {dir}: {e}");
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("Failed to load installed packages: {e}");
            std::process::exit(1);
        }
    }
}


/// Run automatic corrections for applicable rule sets based on packages found in packages.xml.
///
/// This function checks which rule directories correspond to installed packages,
/// and runs the correction logic only on those.
pub fn run_correction() {
    run_package_audit(false, false);
    let package_file = "reports/packages.xml";

    match audit_rules::scanner::load_installed_packages(package_file) {
        Ok(installed_rules) => {
            for rule in installed_rules {
                let dir = format!("rules/{}", rule);
                if let Err(e) = package_management::correction::correct_directory(&dir) {
                    eprintln!("Error correcting {dir}: {e}");
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("Failed to load installed packages: {e}");
            std::process::exit(1);
        }
    }
}

fn update_package_list_if_needed() -> Result<(), Box<dyn std::error::Error>> {
    if !is_root() {
        println!("You must run as root to update packages.");
        std::process::exit(1);
    }
    package_management::update::update_package_list()?;
    Ok(())
}

fn is_root() -> bool {
    if let Ok(content) = std::fs::read_to_string("/proc/self/status") {
        for line in content.lines() {
            if line.starts_with("Uid:") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(uid_str) = parts.get(1) {
                    return uid_str == &"0";
                }
            }
        }
    }
    false
}

const SUFFIX_IN: &str = "_cis_result.xml";
const SUFFIX_OUT: &str = "_cis_report.html";

/// Generate an HTML report from the given XML path.
///
/// * `src` – path to a file whose name ends with `_cis_result.xml`.
///
/// Returns the full path of the created HTML report.
pub fn generate_report<P: AsRef<Path>>(src: P) -> Result<PathBuf> {
    let src = src.as_ref();

    // --- derive output file name ---
    let file_str = src
        .file_name()
        .and_then(|n| n.to_str())
        .context("input path is not valid UTF-8")?;

    if !file_str.ends_with(SUFFIX_IN) {
        bail!("input file name must end with {SUFFIX_IN}");
    }
    let base = &file_str[..file_str.len() - SUFFIX_IN.len()];
    let dst = src.with_file_name(format!("Benchmark_reports/{base}{SUFFIX_OUT}"));

    // --- parse XML & render HTML ---
    let data = report::data::ReportData::from_xml(src)?;
    let html = report::html::ReportTemplate::from(&data).render()?;

    // --- write output file ---
    if let Some(dir) = dst.parent() {
        fs::create_dir_all(dir)?;
    }
    fs::write(&dst, html)?;

    Ok(dst)
}