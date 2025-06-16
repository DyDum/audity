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
use std::{fs, io, path::Path};
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
fn pretty_xml<T: Serialize>(value: &T) -> Result<String, ScanError> {
    let mut buf = String::new();              // `String` implements `fmt::Write`
    let mut ser = Serializer::new(&mut buf);
    ser.indent(' ', 4);                       // 4-space indentation
    value.serialize(ser)?;                    // move the serializer into `serialize`
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
    // Collect `*.xml` files and sort alphabetically
    let mut files: Vec<_> = fs::read_dir(dir)?
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().map(|ext| ext == "xml").unwrap_or(false))
        .collect();
    files.sort_by_key(|e| e.file_name());

    let mut global = RulesCis::default();

    // Parse each file and evaluate compliance
    for file in files {
        println!("{}",file.file_name().to_string_lossy());
        let raw = fs::read_to_string(file.path())?;
        let local: RulesCis = from_str(&raw)?;

        for mut rule in local.rules {
            // Compliance decision
            rule.compliant = match rule.manual.as_deref() {
                Some("NO") | Some("CORRECTION") => match execute_verification_command(&rule.verification) {
                    Ok(true)  => CompliantStatus::Yes,
                    Ok(false) | Err(_) => CompliantStatus::No,
                },
                _ => CompliantStatus::NotTested,
            };

            global.push_unique(rule).map_err(ScanError::Duplicate)?;
        }
    }

    // Pretty-print and write to `reports/<folder>_cis_result.xml`
    let xml = pretty_xml(&global)?;

    fs::create_dir_all("reports")?;

    // Get the folder name from the path:
    // e.g. "rules/debian" → "debian" 
    let folder_name = Path::new(dir)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("output");

    let file_path = format!("reports/{}_cis_result.xml", folder_name);
    fs::write(&file_path, xml)?;

    println!("Report written to {}", file_path);
    Ok(())
}