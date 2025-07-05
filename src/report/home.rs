//! Askama helpers & template to build the **home page** (`index.html`) that
//! lists every generated CIS report and optional Debian package statistics.
//!
//! ──────────────────────────────────────────────────────────────
//! 1. **Reports history**  – scanned from `reports/Benchmark_reports/*.html`  
//! 2. **Packages summary** – parsed from  `reports/packages.xml` (optional)  
//! ──────────────────────────────────────────────────────────────

use askama::Template;
use chrono::{DateTime, Local};
use roxmltree::Document;
use std::{fs, io, path::Path};

/// One HTML report detected on disk.
///
/// | Field         | Description                                           |
/// |---------------|-------------------------------------------------------|
/// | `file_name`   | Exact file name (`*.html`) inside `Benchmark_reports` |
/// | `display_name`| Name shown in the HTML table (currently identical)    |
/// | `modified`    | Local timestamp formatted `YYYY-MM-DD HH:MM`          |
#[derive(Debug)]
pub struct ReportEntry {
    pub file_name: String,
    pub display_name: String,
    pub modified: String,
}

/// One `<package name="…" version="…"/>` extracted from *packages.xml*.
#[derive(Debug)]
pub struct PackageEntry {
    pub name: String,
    pub version: String,
}

/// Global package statistics (counts + optional detailed list).
///
/// | Field        | Meaning                                   |
/// |--------------|-------------------------------------------|
/// | `installed`  | Total installed packages                  |
/// | `upgradable` | Packages that have an upgrade available   |
/// | `list`       | Detailed list, present when `<total>` exists |
#[derive(Debug, Default)]
pub struct PackagesData {
    pub installed: u32,
    pub upgradable: u32,
    pub list: Vec<PackageEntry>,
}

/// Return every `*.html` found in **`dir`**, sorted newest first.
///
/// # Errors
/// Relays any I/O failure originating from the filesystem API.
pub fn collect_reports<P: AsRef<Path>>(dir: P) -> io::Result<Vec<ReportEntry>> {
    let mut entries: Vec<ReportEntry> = Vec::new();

    for entry in fs::read_dir(dir)? {
        let entry: fs::DirEntry = entry?;
        let path: std::path::PathBuf = entry.path();

        if path.extension().map_or(false, |ext| ext == "html") {
            let meta: fs::Metadata = entry.metadata()?;
            let modified: DateTime<Local> = meta.modified()?.into();
            let file_name: String = path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned();

            entries.push(ReportEntry {
                display_name: file_name.clone(),
                file_name,
                modified: modified.format("%Y-%m-%d %H:%M").to_string(),
            });
        }
    }

    entries.sort_by(|a, b| b.modified.cmp(&a.modified));
    Ok(entries)
}

/// Parse Debian-like `packages.xml` into [`PackagesData`].
///
/// On any error (file absent, malformed XML, …) this function returns a
/// default/empty structure so that HTML rendering never panics.
pub fn parse_packages_xml<P: AsRef<Path>>(path: P) -> PackagesData {
    let text: String = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return PackagesData::default(),
    };

    let doc: Document<'_> = match Document::parse(&text) {
        Ok(d) => d,
        Err(_) => return PackagesData::default(),
    };

    // <installed> and <upgradable>
    let installed: u32 = doc
        .descendants()
        .find(|n| n.has_tag_name("installed"))
        .and_then(|n| n.text())
        .and_then(|t| t.parse::<u32>().ok())
        .unwrap_or(0);

    let upgradable: u32 = doc
        .descendants()
        .find(|n| n.has_tag_name("upgradable"))
        .and_then(|n| n.text())
        .and_then(|t| t.parse::<u32>().ok())
        .unwrap_or(0);

    // Each <package …/>
    let list: Vec<PackageEntry> = doc
        .descendants()
        .filter(|n| n.has_tag_name("package"))
        .filter_map(|n| {
            Some(PackageEntry {
                name: n.attribute("name")?.to_owned(),
                version: n.attribute("version")?.to_owned(),
            })
        })
        .collect();

    PackagesData {
        installed,
        upgradable,
        list,
    }
}

/// Askama HTML template for the *home page* (`index.html`).
#[derive(Template)]
#[template(
    source = r###"<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>Audity – CIS Reports</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<link rel='preconnect' href='https://fonts.gstatic.com'>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root{--bg:#f7f9fc;--fg:#1f2937;--muted:#475569;--surface:#ffffff;
--border:#e2e8f0;--shadow:0 2px 6px rgba(0,0,0,.06);}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Inter,system-ui}
.container{max-width:960px;margin:auto;padding:2.2rem 1rem}
.brand{display:flex;align-items:center;gap:1rem;margin-bottom:1.4rem}
.brand h1{margin:0;font-size:2.3rem;font-weight:700;color:var(--fg)}
.logo{width:64px;height:auto;border-radius:8px;box-shadow:var(--shadow)}
h1.page-title{margin:0 0 1.2rem;font-size:2rem;font-weight:700;color:var(--fg)}
table{width:100%;border-collapse:collapse;background:var(--surface);box-shadow:var(--shadow);
       border:1px solid var(--border);border-radius:8px;font-size:.95rem}
th,td{padding:.55rem .9rem;text-align:left}
tr:nth-child(even){background:#fafafa}
button.toggle{border:none;background:none;font-size:1.25rem;cursor:pointer;transition:transform .25s}
.toggle[aria-expanded=false]{transform:rotate(-90deg)}
footer{margin:3rem 0 1rem;text-align:center;font-size:.8rem;color:var(--muted)}
</style>
<script>
function toggleSection(id){
  const s=document.getElementById(id),b=document.getElementById(id+'-btn');
  const e=b.getAttribute('aria-expanded')==='true';
  b.setAttribute('aria-expanded',(!e).toString());
  s.style.display=e?'none':'';
}
</script>
</head>
<body>
<main class='container'>

  <!-- brand block (logo + title) -->
  <div class='brand'>
    <img src='logo/audity.png' alt='Audity logo' class='logo'>
    <h1>Audity</h1>
  </div>

  <h1 class='page-title'>Generated CIS Reports</h1>

  <!-- Reports history -->
  <h2><button id='rep-btn' class='toggle' aria-expanded='true'
      onclick="toggleSection('rep')">▼</button>Reports history</h2>
  <div id='rep'>
    <table>
      <thead><tr><th>Report</th><th>Generated on</th></tr></thead>
      <tbody>
      {% for r in reports %}
        <tr>
          <td><a href='Benchmark_reports/{{ r.file_name }}'>{{ r.display_name }}</a></td>
          <td>{{ r.modified }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Packages statistics (optional) -->
  <h2><button id='pkg-btn' class='toggle' aria-expanded='false'
      onclick="toggleSection('pkg')">▼</button>Packages
      — installed: {{ packages.installed }}, upgradable: {{ packages.upgradable }}</h2>
  <div id='pkg' style='display:none'>
    <table>
      <thead><tr><th>Package</th><th>Version</th></tr></thead>
      <tbody>
      {% for p in packages.list %}
        <tr><td>{{ p.name }}</td><td>{{ p.version }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <footer>Generated by Audity</footer>
</main>
</body>
</html>"###,
    ext = "html"
)]

pub struct HomeTemplate<'a> {
    /// Slice of report entries (newest first).
    pub reports: &'a [ReportEntry],
    /// Package statistics parsed from XML.
    pub packages: &'a PackagesData,
}

impl<'a> HomeTemplate<'a> {
    /// Shorthand constructor for lifetime ergonomics.
    #[inline]
    pub fn new(reports: &'a [ReportEntry], packages: &'a PackagesData) -> Self {
        Self { reports, packages }
    }
}

/// Generate (or update) `reports/index.html`.
///
/// 1. Collect reports with [`collect_reports`].  
/// 2. Parse package statistics with [`parse_packages_xml`].  
/// 3. Render the [`HomeTemplate`] and write it to disk.
pub fn build_homepage() -> io::Result<()> {
    let reports = collect_reports("reports/Benchmark_reports")?;
    let packages = parse_packages_xml("reports/packages.xml");

    let tpl = HomeTemplate::new(reports.as_slice(), &packages);
    fs::write("reports/index.html", tpl.render().unwrap())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::{self, File};
    use tempfile::TempDir;

    /// Ensure `collect_reports` only returns `.html` files.
    #[test]
    fn collects_only_html() {
        let dir = TempDir::new().unwrap();
        File::create(dir.path().join("a.html")).unwrap();
        File::create(dir.path().join("b.txt")).unwrap();

        let list = collect_reports(dir.path()).unwrap();
        assert_eq!(list.len(), 1);
        assert!(list[0].file_name.ends_with(".html"));
    }

    /// Parse a minimal XML sample.
    #[test]
    fn parse_packages() {
        let xml = r#"
            <packages>
              <installed>2</installed>
              <upgradable>1</upgradable>
              <total>
                <package name="foo" version="1.0"/>
                <package name="bar" version="2.0"/>
              </total>
            </packages>
        "#;
        let path = TempDir::new().unwrap().path().join("packages.xml");
        fs::write(&path, xml).unwrap();

        let data = parse_packages_xml(&path);
        assert_eq!(data.installed, 2);
        assert_eq!(data.list.len(), 2);
    }

    /// Verify that the template renders without panicking.
    #[test]
    fn template_renders() {
        let dummy_reports = [ReportEntry {
            file_name: "demo.html".into(),
            display_name: "demo.html".into(),
            modified: "2025-06-29 10:00".into(),
        }];

        let pkgs = PackagesData {
            installed: 1,
            upgradable: 0,
            list: vec![PackageEntry {
                name: "demo".into(),
                version: "0.1".into(),
            }],
        };

        let html = HomeTemplate::new(&dummy_reports, &pkgs).render().unwrap();
        assert!(html.contains("demo.html"));
        assert!(html.contains("demo"));
    }
}