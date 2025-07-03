use std::{fs, path::Path, };
use crate::audit_rules::{scanner::ScanError, scanner::pretty_xml};
use quick_xml::de::from_str;

use crate::audit_rules::{
    exec_command::execute_verification_command,
    rule::{CompliantStatus, RulesCis},
};

pub fn correct_directory(dir: &str) -> anyhow::Result<()> {
    let mut files: Vec<_> = fs::read_dir(dir)?
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().map(|ext| ext == "xml").unwrap_or(false))
        .collect();
    files.sort_by_key(|e| e.file_name());

    let mut global: RulesCis = RulesCis::default();

    for file in files {
        let raw: String = fs::read_to_string(file.path())?;
        let local: RulesCis = from_str(&raw)?;

        for mut rule in local.rules {
            rule.compliant = match rule.manual.as_deref() {
                Some("NO") | Some("VERIFICATION") => {
                    match execute_verification_command(&rule.verification) {
                        Ok(true) => CompliantStatus::Yes,
                        Ok(false) | Err(_) => {
                            // 🚫 Filtrage des règles à haut risque
                            let risky: bool = rule.id.starts_with("1.1.")
                                || rule.correction.contains("/usr/lib")
                                || rule.correction.contains("/usr/bin")
                                || rule.correction.contains("chmod -R");

                            if risky {
                                println!("Rule {} of package {} skipped: too risky", rule.id, dir.to_string());
                                CompliantStatus::NotTested
                            } else {
                                let _ = execute_verification_command(&rule.correction);
                                // Vérifier à nouveau
                                match execute_verification_command(&rule.verification) {
                                    Ok(true) => CompliantStatus::Yes,
                                    Ok(false) | Err(_) => CompliantStatus::No,
                                }
                            }
                        }
                    }
                }
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

    let file_path: String = format!("reports/{}_correction.xml", folder_name);
    fs::write(&file_path, xml)?;

    println!("Correction report written to {}", file_path);
    Ok(())
}

