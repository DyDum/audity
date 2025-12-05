//! Host inventory collection, CIS XML parsing and statistics aggregation.
//!
//! The file is organised in four blocks:
//! 1. **Public data structures** – exposed by the library.
//! 2. **Private XML helpers** – low-level routines to parse the custom CIS XML.
//! 3. **`HostInfo` implementation** – gathers live host information.
//! 4. **`ReportData` builder** – turns a CIS XML file into a fully populated
//!    `ReportData` instance ready for HTML rendering.

use std::{
    collections::HashMap,
    fs::{self, File},
    io::{BufRead, BufReader},
    path::Path,
};

use anyhow::{Context, Result};
use chrono::{DateTime, Local};
use get_if_addrs::{get_if_addrs, IfAddr};
use os_info;
use quick_xml::{
    de::from_reader,
    events::{BytesStart, Event},
    Reader,
};
use serde::Deserialize;
use sys_info::{cpu_num, mem_info, os_release, hostname};

/* ───────────── host résumé & statistics ───────────── */

/// Basic hardware / OS facts detected at runtime.
#[derive(Debug, serde::Serialize)]
pub struct HostInfo {
    pub hostname: String,
    pub primary_ip: String,
    pub mac_addr: String,
    pub os: String,
    pub kernel: String,
    pub architecture: String,
    pub cpu_cores: u32,
    pub memory_mb: u64,
}

/// Global compliance counters (absolute and percentage).
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

/* ───────────────────── public API ───────────────────── */

/// Heading appearing in the CIS document (chapter, section, …).
#[derive(Debug, Clone, serde::Serialize)]
pub struct Heading {
    pub id: String,
    pub name: String,
}

/// Profile metadata (level / type) attached to a rule.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Profile {
    pub level: u8,
    #[serde(rename = "type")]
    pub r#type: String,
}

/// One line of the HTML summary table (level 0→4).
#[derive(Debug, serde::Serialize)]
pub struct SummaryRow {
    /// 0 = chapter, 1 = section, 2 = sub-section, 3 = sub-sub-section, 4 = rule.
    pub level: u8,
    /// Displayed text (e.g. `“1.2 – Disable root login”`).
    pub label: String,
    /// `Compliant`, `Non-compliant`, `Not tested` or `""` for headings.
    pub status: String,
    /// CSS class: `success`, `danger`, `warning` or `""` for headings.
    pub class: String,
    /// HTML anchor (rule id) or empty for headings.
    pub anchor: String,
}

/// Fully parsed CIS `<Rule>` enriched with headings and profiles.
#[derive(Debug, serde::Serialize)]
pub struct Rule {
    pub id: String,
    pub name: String,
    pub chapter: Heading,
    pub section: Heading,
    pub subsection: Option<Heading>,
    pub subsubsection: Option<Heading>,
    pub profiles: Vec<Profile>,
    pub description: String,
    pub corrective: String,
    pub correction_cmd: String,
    pub manual_review: String,
}

/// Top-level container returned by `ReportData::from_xml`.
#[derive(Debug, serde::Serialize)]
pub struct ReportData {
    pub profile_name: String,
    pub audit_time: DateTime<Local>,
    pub host_info: HostInfo,
    pub stats: Stats,
    pub summary: Vec<SummaryRow>,
    pub non_compliant: Vec<Rule>,
    pub not_tested: Vec<Rule>,
    pub compliant: Vec<Rule>,
}

/* ───────── private XML helper structs (raw mapping) ───────── */

#[derive(Debug, Deserialize)]
struct RuleRaw {
    #[serde(rename = "@id")]
    id: String,
    #[serde(rename = "Compliant")]
    compliant: String,
    #[serde(rename = "Manual")]
    manual: Option<String>,
}

#[derive(Debug, Deserialize)]
struct RulesCIS {
    #[serde(rename = "Rule")]
    rules: Vec<RuleRaw>,
}

/* ──────────────── small XML helper functions ─────────────── */

/// Strip a known *“Manual review required:”* prefix from a shell snippet.
///
/// Returns `Some(pure_message)` if a recognised prefix is present,  
/// otherwise `None`.
fn extract_manual(text: &str) -> Option<String> {
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

/// Read the text content of the current XML element (handles `<![CDATA[…]]>`).
fn read_text<R: BufRead>(reader: &mut Reader<R>, end: &[u8]) -> Result<String> {
    let mut buf: Vec<u8> = Vec::new();
    let mut out: String = String::new();
    loop {
        match reader.read_event_into(&mut buf)? {
            Event::Text(t) => out.push_str(&t.unescape()?),
            Event::CData(c) => out.push_str(&String::from_utf8_lossy(c.into_inner().as_ref())),
            Event::End(e) if e.name().as_ref() == end => break,
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }
    Ok(out.trim().to_owned())
}

/// Parse an XML heading (`<Chapter>`, `<Section>`, …) and return `(id, name)`.
fn read_heading<R: BufRead>(reader: &mut Reader<R>, start: &BytesStart) -> Result<(String, String)> {
    let id: String = start
        .attributes()
        .flatten()
        .find(|a| a.key.as_ref() == b"id")
        .map(|a| a.unescape_value().unwrap().to_string())
        .unwrap_or_default();
    Ok((id, read_text(reader, start.name().as_ref())?))
}

/// Collect all `<Profile>` sub-elements into a `Vec<Profile>`.
fn collect_profiles<R: BufRead>(reader: &mut Reader<R>) -> Result<Vec<Profile>> {
    let mut out: Vec<Profile> = Vec::new();
    let mut buf: Vec<u8> = Vec::new();
    loop {
        match reader.read_event_into(&mut buf)? {
            Event::Start(t) if t.name().as_ref() == b"Profile" => {
                let mut level = 0;
                let mut typ = String::new();
                for a in t.attributes().flatten() {
                    match a.key.as_ref() {
                        b"level" => level = a.unescape_value()?.parse()?,
                        b"type" => typ = a.unescape_value()?.to_string(),
                        _ => {}
                    }
                }
                let _ = read_text(reader, b"Profile")?; // consume inner text
                out.push(Profile { level, r#type: typ });
            }
            Event::End(e) if e.name().as_ref() == b"Profiles" => break,
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }
    Ok(out)
}

/// Fully parse all `<Rule>` elements from a CIS XML file.
fn parse_rules<P: AsRef<Path>>(path: P) -> Result<Vec<Rule>> {
    let mut reader: Reader<BufReader<File>> = Reader::from_reader(BufReader::new(File::open(path)?));
    reader.trim_text(true);

    let mut rules: Vec<Rule> = Vec::new();
    let mut buf: Vec<u8> = Vec::new();
    let mut cur: Option<Rule> = None;

    loop {
        match reader.read_event_into(&mut buf)? {
            // ───── rule start ─────
            Event::Start(t) if t.name().as_ref() == b"Rule" => {
                let id: std::borrow::Cow<'_, str> = t
                    .attributes()
                    .flatten()
                    .find(|a| a.key.as_ref() == b"id")
                    .context("Rule without id")?
                    .unescape_value()?;
                cur = Some(Rule {
                    id: id.to_string(),
                    name: String::new(),
                    chapter: Heading { id: String::new(), name: String::new() },
                    section: Heading { id: String::new(), name: String::new() },
                    subsection: None,
                    subsubsection: None,
                    profiles: Vec::new(),
                    description: String::new(),
                    corrective: String::new(),
                    correction_cmd: String::new(),
                    manual_review: String::new(),
                });
            }
            // ───── rule end ─────
            Event::End(e) if e.name().as_ref() == b"Rule" => {
                rules.push(cur.take().expect("unbalanced <Rule>"));
            }
            // ───── fields inside a rule ─────
            Event::Start(t) if cur.is_some() => {
                let r = cur.as_mut().unwrap();
                match t.name().as_ref() {
                    b"Name" => r.name = read_text(&mut reader, b"Name")?,
                    b"Chapter" => {
                        let (id, name) = read_heading(&mut reader, &t)?;
                        r.chapter = Heading { id, name };
                    }
                    b"Section" => {
                        let (id, name) = read_heading(&mut reader, &t)?;
                        r.section = Heading { id, name };
                    }
                    b"SubSection" => {
                        let (id, name) = read_heading(&mut reader, &t)?;
                        r.subsection = Some(Heading { id, name });
                    }
                    b"SubSubSection" => {
                        let (id, name) = read_heading(&mut reader, &t)?;
                        r.subsubsection = Some(Heading { id, name });
                    }
                    b"Profiles" => r.profiles = collect_profiles(&mut reader)?,
                    b"NonCompliantComment" => {
                        r.description = read_text(&mut reader, b"NonCompliantComment")?;
                    }
                    b"CorrectiveComment" => {
                        r.corrective = read_text(&mut reader, b"CorrectiveComment")?;
                    }
                    b"Correction" => {
                        let txt: String = read_text(&mut reader, b"Correction")?;
                        if let Some(m) = extract_manual(&txt) {
                            r.manual_review = m;
                        } else {
                            r.correction_cmd = txt;
                        }
                    }
                    b"Verification" => {
                        let txt: String = read_text(&mut reader, b"Verification")?;
                        // If no manual review yet, maybe it is stated here.
                        if r.manual_review.is_empty() {
                            if let Some(m) = extract_manual(&txt) {
                                r.manual_review = m;
                            }
                        }
                    }
                    // Any other tag → consume and discard.
                    _ => {
                        let _ = read_text(&mut reader, t.name().as_ref())?;
                    }
                }
            }
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }
    Ok(rules)
}

/* ──────────────── HostInfo implementation ─────────────── */

impl HostInfo {
    /// Collect live system information using `sys_info`, `/sys` and `get_if_addrs`.
    ///
    /// | Field         | Source                                         |
    /// |---------------|------------------------------------------------|
    /// | `hostname`    | `sys_info::hostname()`                         |
    /// | `primary_ip`  | first non-loopback V4 interface via `get_if_addrs` |
    /// | `mac_addr`    | `/sys/class/net/<iface>/address`               |
    /// | `os`          | `os_info` crate                                |
    /// | `kernel`      | `sys_info::os_release()`                       |
    /// | `architecture`| `std::env::consts::ARCH`                       |
    /// | `cpu_cores`   | `sys_info::cpu_num()`                          |
    /// | `memory_mb`   | `sys_info::mem_info().total / 1024`            |
        #[must_use] pub fn gather() -> Self {
        let hostname: String = hostname().unwrap_or_else(|_| "N/A".into());
        let (primary_ip, mac_addr) = get_if_addrs()
            .ok()
            .and_then(|ifs| {
                ifs.into_iter().find_map(|ifa| match ifa.addr {
                    IfAddr::V4(v4) if !v4.ip.is_loopback() => {
                        let mac: String = fs::read_to_string(format!("/sys/class/net/{}/address", ifa.name))
                            .map(|s| s.trim().into())
                            .unwrap_or_else(|_| "N/A".into());
                        Some((v4.ip.to_string(), mac))
                    }
                    _ => None,
                })
            })
            .unwrap_or_else(|| ("N/A".into(), "N/A".into()));
        let distro: os_info::Info = os_info::get();
        let os: String = format!("{} {}", distro.os_type(), distro.version());
        let kernel: String = os_release().unwrap_or_else(|_| "N/A".into());
        let architecture: String = std::env::consts::ARCH.to_string();
        let cpu_cores: u32 = cpu_num().unwrap_or(0) as u32;
        let memory_mb: u64 = mem_info().map(|m| m.total / 1024).unwrap_or(0);

        Self {
            hostname,
            primary_ip,
            mac_addr,
            os,
            kernel,
            architecture,
            cpu_cores,
            memory_mb,
        }
    }
}

/* ──────────────── ReportData high-level builder ─────────────── */

impl ReportData {
    /// Build a complete `ReportData` from a CIS XML export.
    ///
    /// Steps performed internally:
    /// 1. Parse the XML twice:
    ///    * once with `parse_rules` (rich `Rule` objects),
    ///    * once with **quick-xml + serde** (`RulesCIS`) to read `<Compliant>`
    ///      and `<Manual>` flags.
    /// 2. Split rules into **compliant**, **non-compliant** and **not tested**.
    /// 3. Generate a hierarchical `summary` table (4 levels).
    /// 4. Compute `Stats`.
    ///
    /// # Errors
    /// Any I/O or XML parse error is propagated wrapped in `anyhow::Result`.
    pub fn from_xml(path: &Path) -> Result<Self> {
        let rules: Vec<Rule> = parse_rules(path)?;
        let RulesCIS { rules: raw } = from_reader::<_, RulesCIS>(BufReader::new(File::open(path)?))?;

        // Map rule-id → (compliance string, manual flag)
        let mut compliance: HashMap<String, (&str, bool)> = HashMap::<String, (&str, bool)>::new();
        for r in &raw {
            compliance.insert(
                r.id.clone(),
                (
                    r.compliant.as_str(),
                    r.manual.as_deref().map(|s| s.eq_ignore_ascii_case("yes")).unwrap_or(false),
                ),
            );
        }

        // Buckets
        let mut compliant: Vec<Rule> = Vec::new();
        let mut non_compliant: Vec<Rule> = Vec::new();
        let mut not_tested: Vec<Rule> = Vec::new();

        for r in rules {
            let (cmp, manual) = compliance.get(&r.id).copied().unwrap_or(("NA", false));
            if manual {
                not_tested.push(r);
            } else if cmp == "YES" {
                compliant.push(r);
            } else if cmp == "NO" {
                non_compliant.push(r);
            } else {
                not_tested.push(r);
            }
        }

        /* ---- build summary table ---- */

        // Flatten all rules with their UI status/class.
        let mut combined: Vec<(&Rule, &'static str, &'static str)> = Vec::new();
        combined.extend(compliant.iter().map(|r| (r, "Compliant", "success")));
        combined.extend(non_compliant.iter().map(|r| (r, "Non-compliant", "danger")));
        combined.extend(not_tested.iter().map(|r| (r, "Not tested", "warning")));
        combined.sort_by(|(a, ..), (b, ..)| a.id.cmp(&b.id));

        let mut summary: Vec<SummaryRow> = Vec::<SummaryRow>::new();
        let mut last_chap: String = String::new();
        let mut last_sec: String = String::new();
        let mut last_sub: String = String::new();
        let mut last_subsub: String = String::new();

        for (r, status, class) in &combined {
            // Hierarchical headings (avoid duplicates).
            if r.chapter.id != last_chap {
                summary.push(SummaryRow {
                    level: 0,
                    label: format!("{} – {}", r.chapter.id, r.chapter.name),
                    status: String::new(),
                    class: String::new(),
                    anchor: String::new(),
                });
                last_chap = r.chapter.id.clone();
                last_sec.clear();
                last_sub.clear();
                last_subsub.clear();
            }
            if r.section.id != last_sec {
                summary.push(SummaryRow {
                    level: 1,
                    label: format!("{} – {}", r.section.id, r.section.name),
                    status: String::new(),
                    class: String::new(),
                    anchor: String::new(),
                });
                last_sec = r.section.id.clone();
                last_sub.clear();
                last_subsub.clear();
            }
            if let Some(sub) = &r.subsection {
                if sub.id != last_sub {
                    summary.push(SummaryRow {
                        level: 2,
                        label: format!("{} – {}", sub.id, sub.name),
                        status: String::new(),
                        class: String::new(),
                        anchor: String::new(),
                    });
                    last_sub = sub.id.clone();
                    last_subsub.clear();
                }
            }
            if let Some(sub2) = &r.subsubsection {
                if sub2.id != last_subsub {
                    summary.push(SummaryRow {
                        level: 3,
                        label: format!("{} – {}", sub2.id, sub2.name),
                        status: String::new(),
                        class: String::new(),
                        anchor: String::new(),
                    });
                    last_subsub = sub2.id.clone();
                }
            }
            // Actual rule line (level 4).
            summary.push(SummaryRow {
                level: 4,
                label: format!("{} – {}", r.id, r.name),
                status: (*status).into(),
                class: (*class).into(),
                anchor: r.id.clone(),
            });
        }

        // ---------- Compute statistics ----------
        let total: usize = compliant.len() + non_compliant.len() + not_tested.len();
        
        #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss, clippy::cast_sign_loss)]
        let percent = |n: usize| ((n as f64 / total as f64) * 100.0).round() as u8;

        let stats: Stats = Stats {
            total,
            pass: compliant.len(),
            fail: non_compliant.len(),
            not_tested: not_tested.len(),
            percent_pass: percent(compliant.len()),
            percent_fail: percent(non_compliant.len()),
            percent_not_tested: percent(not_tested.len()),
        };

        Ok(Self {
            profile_name: "Debian".into(),
            audit_time: Local::now(),
            host_info: HostInfo::gather(),
            stats,
            summary,
            non_compliant,
            not_tested,
            compliant,
        })
    }
}