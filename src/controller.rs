use crate::package_management;
use crate::audit_rules;

use audit_rules::scanner::scan_directory;
use std::process;

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
    run_audit_rules();
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
    let total_installed = package_management::list::get_installed_packages_count().unwrap_or(0);
    let installed_packages = package_management::list::list_installed_packages().unwrap_or_default();
    let upgradable_packages = if upgrade {
        package_management::update::check_upgradable_packages().unwrap_or_default()
    } else {
        String::new()
    };

    match package_management::xml_report::generate_xml_report(total_installed, &installed_packages, &upgradable_packages) {
        Ok(xml_data) => {
            std::fs::write("./reports/packages.xml", xml_data).expect("Failed to write XML report");
            println!("XML report generated successfully and saved to 'report.xml'.");
        },
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
pub fn run_audit_rules() {
    let dir = "rules/apache_http";
    if let Err(e) = scan_directory(dir) {
        eprintln!("Error: {e}");
        process::exit(1);
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
