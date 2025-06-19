use crate::package_management;
use crate::audit_rules;

use audit_rules::scanner::scan_directory;
use std::process;

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
            println!("Failed to generate XML report: {}", e);
        },
    }
}

pub fn run_audit_rules() {
    let dir = "rules/apache_http";
    if let Err(e) = scan_directory(dir) {
        eprintln!("Error: {e}");
        process::exit(1);
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
