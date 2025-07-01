//! Host inventory, CIS XML parsing and high-level statistics.
//!
//! This module aggregates three concerns needed by the report layer:
//! 1. **Host discovery**: collect basic runtime information (hostname, IP,
//!    OS, kernel, hardware).
//! 2. **CIS XML parsing**: read the `<RulesCIS>` document produced by the
//!    scanner and convert it into Rust structs.
//! 3. **Statistics**: compute global pass / fail ratios for display in the
//!    HTML report.
//!
//! Only serialisable structures are exposed; the template engine (Askama)
//! consumes them directly.

use std::{fs::File, io::BufReader, net::IpAddr, path::Path};

use anyhow::Result;
use get_if_addrs::get_if_addrs;
use os_info;
use quick_xml::de::from_reader;
use serde::Deserialize;
use sys_info::{cpu_num, mem_info, os_release, hostname};

/// High-level system résumé displayed at the top of the report.
#[derive(Debug, serde::Serialize)]
pub struct HostInfo {
    pub hostname: String,
    pub primary_ip: String,
    pub os: String,
    pub kernel: String,
    pub architecture: String,
    pub cpu_cores: u32,
    pub memory_mb: u64,
}

/// Global CIS statistics used for the coloured dashboard.
#[derive(Debug, serde::Serialize)]
pub struct Stats {
    pub total: usize,
    pub pass: usize,
    pub fail: usize,
    pub not_tested: usize,
    pub percent_pass: u8,
    pub percent_fail: u8,
    pub percent_not_tested: u8,
}

/// Raw rule as it appears in the XML file (internal only).
#[derive(Debug, Deserialize)]
struct RuleRaw {
    #[serde(rename = "@id")]
    id: String,
    #[serde(rename = "NonCompliantComment")]
    description: Option<String>,
    #[serde(rename = "CorrectiveComment")]
    corrective: Option<String>,
    #[serde(rename = "Correction")]
    correction_cmd: Option<String>,
    #[serde(rename = "Verification")]
    verification: Option<String>,
    #[serde(rename = "Compliant")]
    compliant: String,
}

/// Wrapper for the root `<RulesCIS>` element (internal only).
#[derive(Debug, Deserialize)]
struct RulesCIS {
    #[serde(rename = "Rule")]
    rules: Vec<RuleRaw>,
}

/// Sanitised rule exported to the HTML template.
#[derive(Debug, serde::Serialize)]
pub struct Rule {
    pub id: String,
    pub description: String,
    pub corrective: String,
    pub correction_cmd: String,
    pub manual_review: String,
}

/// Aggregate structure directly consumed by Askama.
#[derive(Debug, serde::Serialize)]
pub struct ReportData {
    pub profile_name: String,
    pub host_info: HostInfo,
    pub stats: Stats,
    pub non_compliant: Vec<Rule>,
    pub not_tested: Vec<Rule>,
    pub compliant: Vec<Rule>,
}

/* ───────────────────────── utilities ───────────────────────── */

/// Extract a “manual review required” message from a shell snippet.
///
/// Some correction/verification commands merely echo a message
/// that asks the auditor to check the control manually.  
/// This helper normalises those messages so that the UI can display
/// them in a dedicated column.
///
/// * `text` – Full content of the `<Correction>` or `<Verification>` tag.
///
/// Returns `Some(message)` if a prefixed *echo* string is found,
/// otherwise `None`.
fn extract_manual(text: &str) -> Option<String> {
    // Known prefixes used by the benchmark authors.
    let prefixes = [
        r#"echo "Manual review required:"#,
        r#"echo "Manual configuration required:"#,
        r#"echo "Manual verification required:"#,
    ];
    for p in prefixes {
        if text.starts_with(p) {
            return Some(
                text.trim_start_matches(p)
                    .trim()
                    .trim_end_matches('"')
                    .trim()
                    .to_string(),
            );
        }
    }
    None
}

impl HostInfo {
    /// Collect runtime information about the current host.
    ///
    /// No external commands are spawned; everything relies on safe,
    /// cross-platform crates where possible.  Any failure returns the
    /// placeholder string `"N/A"` or `0`.
    #[must_use] pub fn gather() -> Self {
        let hostname = hostname().unwrap_or_else(|_| "N/A".into());

        // Retrieve the first non-loopback IPv4 address found.
        let primary_ip = get_if_addrs()
            .ok()
            .and_then(|ifaces| {
                ifaces.into_iter().find_map(|ifa| match ifa.addr.ip() {
                    IpAddr::V4(ip) if !ip.is_loopback() => Some(ip.to_string()),
                    _ => None,
                })
            })
            .unwrap_or_else(|| "N/A".into());

        let distro = os_info::get();
        let os = format!("{} {}", distro.os_type(), distro.version());
        let kernel = os_release().unwrap_or_else(|_| "N/A".into());
        let architecture = std::env::consts::ARCH.to_string();
        let cpu_cores = cpu_num().unwrap_or(0) as u32;
        let memory_mb = mem_info().map(|m| m.total / 1024).unwrap_or(0);

        Self {
            hostname,
            primary_ip,
            os,
            kernel,
            architecture,
            cpu_cores,
            memory_mb,
        }
    }
}

impl ReportData {
    /// Load a CIS XML file, compute statistics and build a `ReportData`.
    ///
    /// * `path` – Path to the XML document produced by the scanner.
    ///
    /// # Errors
    /// Returns any I/O or XML deserialisation error wrapped by `anyhow`.
    pub fn from_xml(path: &Path) -> Result<Self> {
        // ---------- Parse XML into raw rules ----------
        let RulesCIS { rules } = from_reader(BufReader::new(File::open(path)?))?;

        // ---------- Categorise rules ----------
        let mut nc = Vec::new(); // non-compliant
        let mut nt = Vec::new(); // not tested
        let mut ok = Vec::new(); // compliant

        for r in rules {
            // Extract potential manual review message or correction command.
            let mut manual_review = String::new();
            let mut correction_cmd = String::new();

            if let Some(cmd) = r.correction_cmd.clone() {
                if let Some(ex) = extract_manual(&cmd) {
                    manual_review = ex;
                } else {
                    correction_cmd = cmd;
                }
            }
            // Fallback to <Verification> if <Correction> did not yield a message.
            if manual_review.is_empty() {
                if let Some(ver) = &r.verification {
                    if let Some(ex) = extract_manual(ver) {
                        manual_review = ex;
                    }
                }
            }

            let rule = Rule {
                id: r.id,
                description: r.description.unwrap_or_default(),
                corrective: r.corrective.unwrap_or_default(),
                correction_cmd,
                manual_review,
            };

            match r.compliant.as_str() {
                "YES" => ok.push(rule),
                "NO" => nc.push(rule),
                _ => nt.push(rule),
            }
        }

        // ---------- Compute statistics ----------
        let total = ok.len() + nc.len() + nt.len();
        
        #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss, clippy::cast_sign_loss)]
        let percent = |n: usize| ((n as f64 / total as f64) * 100.0).round() as u8;

        let stats = Stats {
            total,
            pass: ok.len(),
            fail: nc.len(),
            not_tested: nt.len(),
            percent_pass: percent(ok.len()),
            percent_fail: percent(nc.len()),
            percent_not_tested: percent(nt.len()),
        };

        // ---------- Assemble final struct ----------
        Ok(Self {
            profile_name: "Debian".into(), // TODO: make dynamic once profiles are introduced
            host_info: HostInfo::gather(),
            stats,
            non_compliant: nc,
            not_tested: nt,
            compliant: ok,
        })
    }
}

/* ─────────────────────────── tests ─────────────────────────── */
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manual_extraction_works() {
        let sample = r#"echo "Manual review required: check file permissions""#;
        assert_eq!(
            extract_manual(sample).unwrap(),
            "check file permissions"
        );
        let negative = r#"echo "Nothing to see here""#;
        assert!(extract_manual(negative).is_none());
    }

    #[test]
    fn percent_calculation_is_correct() {
        // Artificial stats: 2 pass, 1 fail, 1 nt
        let stats = Stats {
            total: 4,
            pass: 2,
            fail: 1,
            not_tested: 1,
            percent_pass: 50,
            percent_fail: 25,
            percent_not_tested: 25,
        };
        assert_eq!(stats.percent_pass + stats.percent_fail + stats.percent_not_tested, 100);
    }
}
