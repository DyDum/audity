//! Scans a directory containing CIS rule XML files, evaluates each rule’s
//! compliance and writes a pretty-printed report to
//! `reports/<folder>_cis_result.xml`.
//
//  ─ Workflow ─
//  1. Collect and sort every `*.xml` file in the given folder.
//  2. Merge all `<Rule>` elements into one `RulesCis` struct.
//  3. For each rule:
//     • If `<Manual>` is `NO` or `CORRECTION` → run its verification
//       command and set `<Compliant>` to `YES` or `NO` accordingly.
//     • Otherwise mark it `NOT_TESTED`.
//  4. Pretty-print the aggregated XML with 4-space indentation.
//  5. Save the result in `reports/…_cis_result.xml` (folder name prefix).

use crate::audit_rules::{
    exec_command::execute_verification_command,
    rule::{CompliantStatus, RulesCis},
};
use quick_xml::{de::from_str, se::Serializer};
use serde::Serialize;
use std::{fs::{self, DirEntry, File}, io::{self, BufRead, BufReader}, path::Path};
use thiserror::Error;

/// Errors returned by [`scan_directory`].
#[derive(Debug, Error)]
pub enum ScanError {
    #[error("I/O: {0}")]
    Io(#[from] io::Error),
    #[error("XML: {0}")]
    Xml(#[from] quick_xml::DeError),
    #[error("Duplicate id: {0}")]
    Duplicate(String),
    #[error("Serialisation: {0}")]
    Ser(#[from] quick_xml::Error),
}

/// Convert any serialisable value to a pretty-printed XML string
/// using four spaces per indentation level.
pub fn pretty_xml<T: Serialize>(value: &T) -> Result<String, ScanError> {
    let mut buf: String = String::new();
    let mut ser: Serializer<'_, '_, String> = Serializer::new(&mut buf);
    ser.indent(' ', 4);
    value.serialize(ser)?;
    Ok(buf)
}

/// Scan a folder of rule files and generate the consolidated report.
///
/// * `dir` – Folder path (e.g. `"rules/debian"`).
///
/// # Output
/// * Creates `reports/<folder>_cis_result.xml`.
///
/// # Errors
/// Any I/O, XML or serialisation error is wrapped in [`ScanError`].
pub fn scan_directory(dir: &str) -> Result<(), ScanError> {
    let mut files: Vec<_> = fs::read_dir(dir)?
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().is_some_and(|ext| ext == "xml"))
        .collect();
    files.sort_by_key(DirEntry::file_name);

    let mut global: RulesCis = RulesCis::default();

    for file in files {
        let raw: String = fs::read_to_string(file.path())?;

        let local: RulesCis = match from_str::<RulesCis>(&raw) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("Erreur XML dans «{}» : {}", file.path().display(), e);
                return Err(ScanError::Xml(e));
            }
        };

        for mut rule in local.rules {
            // Compliance decision
            rule.compliant = match rule.manual.as_deref() {
                Some("NO" | "CORRECTION") => match execute_verification_command(&rule.verification) {
                    Ok(true)  => CompliantStatus::Yes,
                    Ok(false) | Err(_) => CompliantStatus::No,
                },
                _ => CompliantStatus::NotTested,
            };

            global.push_unique(rule).map_err(ScanError::Duplicate)?;
        }
    }

    let xml: String = pretty_xml(&global)?;

    fs::create_dir_all("reports")?;
  
    let folder_name: &str = Path::new(dir)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("output");

    let file_path: String = format!("reports/{folder_name}_cis_result.xml");
    fs::write(&file_path, xml)?;

    println!("Report written to {file_path}");
    Ok(())
}

/// Load installed packages by comparing rule folder names directly with lines in packages.xml.
///
/// This is more efficient than loading and parsing the whole XML file.
///
/// * `packages_path` – Path to the packages.xml file.
///
/// # Returns
/// A list of rule names for which a corresponding package was found.
pub fn load_installed_packages(packages_path: &str) -> anyhow::Result<Vec<String>> {
    let rules_dir: fs::ReadDir = fs::read_dir("rules")?;
    let file: File = File::open(packages_path)?;
    let reader: BufReader<File> = BufReader::new(file);

    let mut installed: Vec<String> = Vec::new();
    let lines: Vec<_> = reader.lines().flatten().collect();

    for entry in rules_dir.flatten() {
        let rule_dir: std::path::PathBuf = entry.path();
        if !rule_dir.is_dir() {
            continue;
        }

        if let Some(rule_name) = rule_dir.file_name().and_then(|s| s.to_str()) {
            if lines.iter().any(|line| rule_matches_package(rule_name, line)) {
                installed.push(rule_name.to_string());
            }
        }
    }

    Ok(installed)
}

fn rule_matches_package(rule_name: &str, line: &str) -> bool {
    match rule_name {
        "apache_http" => line.contains("name=\"apache2\""),
        "apache_tomcat_10.1" => line.contains("name=\"tomcat10\""),
        "debian" => line.contains("name=\"debianutils\"") || line.contains("name=\"debian-faq\""),
        "nginx" => line.contains("name=\"nginx\""),
        "mariadb" => line.contains("name=\"mariadb\""),
        "postgresql" => line.contains("name=\"postgresql\""),
        "mongodb" => line.contains("name=\"mongodb\""),
        "sql_server" => line.contains("name=\"mssql\"") || line.contains("name=\"sql-server\""),
        _ => line.contains(&format!("name=\"{}\"", rule_name)), // fallback : nom exact
    }
}