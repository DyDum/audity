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

/// Runs the full audit process: updates packages (if needed), audits packages and audit rules.
///
/// This function performs three main steps:
/// 1. Tries to update the package list (non-fatal if it fails).
/// 2. Runs the audit on installed and upgradable packages.
/// 3. Executes audit rules defined for the system configuration.
///
/// # Errors
/// This function does **not** return a `Result`, but may log errors if:
/// - The package list update fails (logged but non-blocking).
///
/// # Panics
/// This function itself does not panic, but calls to internal functions such as
/// `run_package_audit` or `run_audit_rules` may panic internally if not properly handled.
pub fn run_full_audit() {
    if let Err(e) = update_package_list_if_needed() {
        println!("Failed to update package list: {e}");
    }
    run_package_audit(false, false);
    run_audit_rules(None);
}

/// Executes the package audit workflow:
/// - Optionally updates the package list.
/// - Collects installed and upgradable packages.
/// - Generates an XML report summarizing the results.
///
/// # Arguments
/// * `update` – Whether to run `apt update`.
/// * `upgrade` – Whether to check for upgradable packages (requires root).
///
/// # Panics
/// This function panics in the following case:
/// - If writing the XML report to disk fails, it will panic via `.expect("Failed to write XML report")`.
pub fn run_package_audit(update: bool, upgrade: bool) {
    if update {
        if let Err(e) = package_management::update::update_package_list() {
            println!("Failed to update package list: {e}");
            return;
        }
    }

    if upgrade && !is_root(){
        println!("You must run as root to upgrade the package list.");
        process::exit(1);
    }

    package_management::sources::read_sources_list().unwrap_or_default();
    let total_installed: usize = package_management::list::get_installed_packages_count().unwrap_or(0);
    let installed_packages: String = package_management::list::list_installed_packages().unwrap_or_default();

    let upgradable_vec: Vec<String> = package_management::update::check_upgradable_packages().unwrap_or_default();
    let upgradable_packages: Vec<&str> = upgradable_vec.iter().map(|s| s.as_str()).collect();
    println!("📦 {} package(s) upgradable", upgradable_packages.len());
    for pkg in &upgradable_packages {
        println!("   - {}", pkg);
    }

    let upgradable_string = upgradable_packages.join("\n");

    match package_management::xml_report::generate_xml_report(
        total_installed,
        &installed_packages,
        &upgradable_string,
    ) {
        Ok(xml_data) => {
            std::fs::write("./reports/packages.xml", xml_data).expect("Failed to write XML report");
            println!("XML report generated successfully and saved to 'report.xml'.");
        }
        Err(e) => {
            println!("Failed to generate XML report: {e}");
        },
    }
}

/// Executes the audit rules by scanning a specific directory for rule definitions.
///
/// This function scans the `rules/apache_http` directory and applies each rule found.
/// If scanning fails, the program logs the error and terminates immediately.
///
/// # Panics
/// This function does not explicitly panic, but it forcibly terminates the process with
/// `process::exit(1)` if an error occurs during the directory scan.
///
/// # Errors
/// Errors during directory scanning are not returned but printed to stderr
/// before terminating the process.
pub fn run_audit_rules(filter: Option<&str>) {
    let package_file: &'static str = "reports/packages.xml";

    // Transformation du filtre si présent ("Apache Http" -> "apache_http")
    let normalized_filter: Option<String> = filter.map(|f| {
        f.to_lowercase()
            .split_whitespace()
            .collect::<Vec<&str>>()
            .join("_")
    });

    match audit_rules::scanner::load_installed_packages(package_file) {
        Ok(installed_rules) => {
            for rule in installed_rules {
                if let Some(ref filter_name) = normalized_filter {
                    if &rule != filter_name {
                        continue;
                    }
                }

                let dir: String = format!("rules/{}", rule);
                if let Err(e) = scan_directory(&dir) {
                    eprintln!("Error scanning {dir}: {e}");
                    process::exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("Failed to load installed packages: {e}");
            process::exit(1);
        }
    }
}


/// Run automatic corrections for applicable rule sets based on packages found in packages.xml.
///
/// This function checks which rule directories correspond to installed packages,
/// and runs the correction logic only on those.
pub fn run_correction() {
    run_package_audit(false, false);
    let package_file: &'static str = "reports/packages.xml";

    match audit_rules::scanner::load_installed_packages(package_file) {
        Ok(installed_rules) => {
            for rule in installed_rules {
                let dir: String = format!("rules/{}", rule);
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

/// Updates the APT package list if the program is run as root.
///
/// This function checks if the current user is root, and if so,
/// executes `apt update` using the `update_package_list()` helper.
///
/// # Returns
/// - `Ok(())` if the package list update succeeded.
/// - `Err(Box<dyn std::error::Error>)` if the update command fails.
///
/// # Errors
/// Returns an error if `apt update` fails or cannot be executed.
///
/// # Panics
/// This function does **not** panic, but it forcibly terminates the program
/// with `std::process::exit(1)` if the user is not root.
fn update_package_list_if_needed() -> Result<(), Box<dyn std::error::Error>> {
    if !is_root() {
        println!("You must run as root to update packages.");
        std::process::exit(1);
    }
    package_management::update::update_package_list()?;
    Ok(())
}

/// Checks whether the current process is running with root privileges.
///
/// This function reads the UID of the current process from `/proc/self/status`
/// and returns `true` if the UID is `0` (root), or `false` otherwise.
///
/// # Returns
/// - `true` if the process runs as root.
/// - `false` if not root, or if the status file could not be read.
///
/// # Errors
/// This function does not return an error; it silently returns `false` in case of any failure.
///
/// # Platform
/// This function is Linux-specific and relies on `/proc/self/status`.
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
    let src: &Path = src.as_ref();

    // --- derive output file name ---
    let file_str: &str = src
        .file_name()
        .and_then(|n| n.to_str())
        .context("input path is not valid UTF-8")?;

    if !file_str.ends_with(SUFFIX_IN) {
        bail!("input file name must end with {SUFFIX_IN}");
    }
    let base: &str = &file_str[..file_str.len() - SUFFIX_IN.len()];
    let dst: PathBuf = src.with_file_name(format!("Benchmark_reports/{base}{SUFFIX_OUT}"));

    // --- parse XML & render HTML ---
    let data: report::ReportData = report::data::ReportData::from_xml(src)?;
    let html: String = report::html::ReportTemplate::from(&data).render()?;

    // --- write output file ---
    if let Some(dir) = dst.parent() {
        fs::create_dir_all(dir)?;
    }
    fs::write(&dst, html)?;

    Ok(dst)
}


pub fn list_cis() {
    let directory: &'static str = "./rules";

    match fs::read_dir(directory) {
        Ok(entries) => {
            println!("List of CIS available:");
            for entry in entries.flatten() {
                let path: PathBuf = entry.path();
                if path.is_dir() {
                    if let Some(folder_name_os) = path.file_name() {
                        let folder_name: std::borrow::Cow<'_, str> = folder_name_os.to_string_lossy();

                        // Transforme "apache_http" en "Apache Http"
                        let readable_name: String = folder_name
                            .split('_')
                            .map(|s| {
                                let mut chars = s.chars();
                                match chars.next() {
                                    Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                                    None => String::new(),
                                }
                            })
                            .collect::<Vec<String>>()
                            .join(" ");

                        println!("- {}", readable_name);
                    }
                }
            }
        }
        Err(e) => {
            eprintln!("Error reading directory {}: {}", directory, e);
        }
    }
}