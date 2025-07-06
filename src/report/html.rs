//! Askama template that renders a **single CIS benchmark report**
//! as a fully self-contained HTML page.
//!
//! The template is embedded *inline* (via the `source` attribute) so that the
//! whole page lives in a single Rust source file – handy for packaging a
//! standalone CLI.  The visual design is intentionally lightweight:
//! * **Responsive**: media-queries are not required thanks to the centred
//!   `.container` and fluid widths.
//! * **Dark-aware colours** can be added later by extending the `:root`
//!   palette (CSS variables).
//! * **Animated chevrons**: the arrow buttons rotate when sections are
//!   collapsed / expanded, powered only by a tiny inline script.
//
//!   The public API of this module is limited to `ReportTemplate`, which
//!   dereferences to the underlying `askama::Template`.  All rendering logic
//!   stays in the HTML; Rust merely passes a strongly-typed `ReportData`.

use askama::Template;
use super::data::ReportData;

/// Concrete Askama template wrapping a borrowed `ReportData`.
///
/// The HTML is supplied through the `source` attribute to avoid touching the
/// filesystem at runtime.  The template language is *Jinja-like* – see
/// <https://docs.rs/askama> for syntax.
///
/// * `'a` – lifetime of the borrowed `ReportData`.
#[derive(Template)]
#[template(
    source = r###"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audity – CIS Benchmark {{ data.profile_name }}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root{--bg:#f7f9fc;--fg:#1f2937;--muted:#475569;--surface:#ffffff;
      --border:#e2e8f0;--shadow:0 2px 6px rgba(0,0,0,.06);
      --danger:#e74c3c;--warning:#f39c12;--success:#27ae60;
      --badge-bg:#e2e8f0;--badge-fg:#334155}
*{box-sizing:border-box}
body{margin:0;font-family:Inter,system-ui,Arial,sans-serif;background:var(--bg);color:var(--fg);line-height:1.55;font-size:16px}
.container{max-width:960px;margin:auto;padding:2.2rem 1rem}
.brand{display:flex;align-items:center;gap:1rem;margin-bottom:1.4rem}
.brand h1{margin:0;font-size:2.3rem;font-weight:700}
.logo{width:64px;height:auto;border-radius:8px;box-shadow:var(--shadow)}
h1{margin:0;font-size:2.1rem;font-weight:700}
h2{margin:2.2rem 0 .6rem;font-size:1.3rem;font-weight:600;display:flex;align-items:center;gap:.6rem}

table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{padding:.55rem .9rem;text-align:left}
tr:nth-child(even){background:#fafafa}
.card{background:var(--surface);border:1px solid var(--border);border-left-width:5px;border-radius:8px;box-shadow:var(--shadow);padding:1rem 1.25rem;margin:.9rem 0}
.card.danger{border-color:var(--danger)}
.card.warning{border-color:var(--warning)}
ul.compliant-list{padding-left:1.1rem;margin:.9rem 0}
button.toggle{border:none;background:none;color:var(--fg);font-size:1.25rem;cursor:pointer;transition:transform .25s}
.toggle[aria-expanded=false]{transform:rotate(-90deg)}
.copy-wrap{display:flex;align-items:flex-start;gap:.6rem;margin-top:.4rem}
.copy-wrap pre{flex:1 1 auto;min-width:0;background:#f1f5f9;border-radius:6px;padding:.6rem;overflow-x:auto;margin:0}
.copy-btn{flex:none;background:var(--surface);border:1px solid var(--border);padding:.25rem .8rem;font-size:.8rem;border-radius:4px;cursor:pointer;display:flex;align-items:center;gap:.3rem}
.copy-btn::before{content:"📋";font-size:.9rem}
table.meta,table.stats{margin:1.2rem 0;border:1px solid var(--border);border-radius:8px;overflow:hidden;box-shadow:var(--shadow)}
table.stats td:first-child{font-weight:600}table.stats td:nth-child(2){text-align:right}
.success{color:var(--success)}.danger{color:var(--danger)}.warning{color:var(--warning)}
td.danger{color:var(--danger)}td.warning{color:var(--warning)}td.success{color:var(--success)}
.timestamp{color:var(--muted);font-size:.9rem;margin-bottom:1.2rem}
footer{margin:4rem 0 1rem;text-align:center;font-size:.8rem;color:var(--muted)}
.path{font-size:.85rem;color:var(--muted);margin:.2rem 0 .6rem}
.badge{display:inline-block;padding:.15rem .5rem;margin-right:.3rem;border-radius:.45rem;
       background:var(--badge-bg);color:var(--badge-fg);font-size:.75rem;font-weight:600}
.badge[level="1"]{background:#dbeafe;color:#1e3a8a}
.badge[level="2"]{background:#fee2e2;color:#991b1b}

table.toc{width:100%;border-collapse:collapse;font-size:.95rem;margin:1.2rem 0}
table.toc td{padding:.4rem .8rem}
table.toc a{text-decoration:none;color:inherit}
table.toc a:hover{text-decoration:underline}
td.level0,td.level1,td.level2,td.level3{font-weight:600}
td.level0{border-top:1px solid var(--border)}
td.level1{padding-left:1.5rem}
td.level2{padding-left:2.5rem}
td.level3{padding-left:3.5rem}
td.level4{padding-left:4.5rem}
</style>

<script>
function toggleSection(id){
  const s=document.getElementById(id),b=document.getElementById(id+'-btn');
  const e=b.getAttribute('aria-expanded')==='true';
  b.setAttribute('aria-expanded',(!e).toString());
  s.style.display = e ? 'none' : '';
}
function copyCmd(btn){
  const code=btn.previousElementSibling.innerText;
  navigator.clipboard.writeText(code).then(()=>{
    btn.textContent='Copied!';
    setTimeout(()=>btn.textContent='Copy',1500);
  });
}
</script>
</head>
<body>
<main class="container">

  <div class="brand">
    <img src="https://i.ibb.co/1Gvvhdkj/audity.png" alt="Audity logo" class="logo">
    <h1>Audity</h1>
  </div>

  <p class="timestamp">CIS audit "{{ data.profile_name }}" – {{ data.audit_time }}</p>

  <div class="header"><h1>CIS Benchmark {{ data.profile_name }}</h1></div>

  <table class="meta">
    <tr><td><strong>Hostname</strong></td><td>{{ data.host_info.hostname }}</td></tr>
    <tr><td><strong>IP address</strong></td><td>{{ data.host_info.primary_ip }}</td></tr>
    <tr><td><strong>MAC address</strong></td><td>{{ data.host_info.mac_addr }}</td></tr>
    <tr><td><strong>OS</strong></td><td>{{ data.host_info.os }}</td></tr>
    <tr><td><strong>Kernel</strong></td><td>{{ data.host_info.kernel }}</td></tr>
    <tr><td><strong>Architecture</strong></td><td>{{ data.host_info.architecture }}</td></tr>
    <tr><td><strong>CPU cores</strong></td><td>{{ data.host_info.cpu_cores }}</td></tr>
    <tr><td><strong>Memory</strong></td><td>{{ data.host_info.memory_mb }} MB</td></tr>
  </table>

  <table class="stats">
    <tr><td>Total rules</td><td>{{ data.stats.total }}</td></tr>
    <tr><td class="success">Compliant</td><td>{{ data.stats.pass }} ({{ data.stats.percent_pass }} %)</td></tr>
    <tr><td class="danger">Non-compliant</td><td>{{ data.stats.fail }} ({{ data.stats.percent_fail }} %)</td></tr>
    <tr><td class="warning">Not tested</td><td>{{ data.stats.not_tested }} ({{ data.stats.percent_not_tested }} %)</td></tr>
  </table>

  <h2><button id="sum-btn" class="toggle" aria-expanded="true" onclick="toggleSection('sum')">▼</button>Summary</h2>
  <div id="sum">
    <table class="toc">
      {% for row in data.summary %}
        <tr>
          <td class="level{{ row.level }}">
            {% if row.anchor != "" %}
              <a href="#rule-{{ row.anchor }}">{{ row.label }}</a>
            {% else %}
              {{ row.label }}
            {% endif %}
          </td>
          <td>{% if row.status != "" %}<span class="{{ row.class }}">{{ row.status }}</span>{% endif %}</td>
        </tr>
      {% endfor %}
    </table>
  </div>

  <h2><button id="nc-btn" class="toggle" aria-expanded="true" onclick="toggleSection('nc')">▼</button>Non-compliant rules ({{ data.non_compliant.len() }})</h2>
  <div id="nc">
  {% for r in data.non_compliant %}
    <div id="rule-{{ r.id }}" class="card danger">
      <h3>{{ r.id }} – {{ r.name }}</h3>
      <p class="path">
        {{ r.chapter.id }} {{ r.chapter.name }}
        / {{ r.section.id }} {{ r.section.name }}
        {% if r.subsection.is_some() %}/ {{ r.subsection.as_ref().unwrap().id }} {{ r.subsection.as_ref().unwrap().name }}{% endif %}
        {% if r.subsubsection.is_some() %}/ {{ r.subsubsection.as_ref().unwrap().id }} {{ r.subsubsection.as_ref().unwrap().name }}{% endif %}
      </p>
      <p>
        {% for p in r.profiles %}
          <span class="badge" level="{{ p.level }}">{{ p.type }}</span>
        {% endfor %}
      </p>
      <p>{{ r.description }}</p>
      {% if r.corrective != "" %}<p><em><strong>Fix:</strong> {{ r.corrective }}</em></p>{% endif %}
      {% if r.correction_cmd != "" %}
        <div class="copy-wrap">
          <pre><code>{{ r.correction_cmd }}</code></pre>
          <button class="copy-btn" onclick="copyCmd(this)">Copy</button>
        </div>
      {% endif %}
    </div>
  {% endfor %}
  </div>

  <h2><button id="nt-btn" class="toggle" aria-expanded="true" onclick="toggleSection('nt')">▼</button>Not-tested rules ({{ data.not_tested.len() }})</h2>
  <div id="nt">
  {% for r in data.not_tested %}
    <div id="rule-{{ r.id }}" class="card warning">
      <h3>{{ r.id }} – {{ r.name }}</h3>
      <p class="path">
        {{ r.chapter.id }} {{ r.chapter.name }}
        / {{ r.section.id }} {{ r.section.name }}
        {% if r.subsection.is_some() %}/ {{ r.subsection.as_ref().unwrap().id }} {{ r.subsection.as_ref().unwrap().name }}{% endif %}
        {% if r.subsubsection.is_some() %}/ {{ r.subsubsection.as_ref().unwrap().id }} {{ r.subsubsection.as_ref().unwrap().name }}{% endif %}
      </p>
      <p>
        {% for p in r.profiles %}
          <span class="badge" level="{{ p.level }}">{{ p.type }}</span>
        {% endfor %}
      </p>
      <p>{{ r.description }}</p>
      {% if r.manual_review != "" %}<p><strong>Manual review:</strong> {{ r.manual_review }}</p>{% endif %}
      {% if r.corrective != "" %}<p><em><strong>Fix:</strong> {{ r.corrective }}</em></p>{% endif %}
      {% if r.correction_cmd != "" %}
        <div class="copy-wrap">
          <pre><code>{{ r.correction_cmd }}</code></pre>
          <button class="copy-btn" onclick="copyCmd(this)">Copy</button>
        </div>
      {% endif %}
    </div>
  {% endfor %}
  </div>

  <h2><button id="ok-btn" class="toggle" aria-expanded="true" onclick="toggleSection('ok')">▼</button>Compliant rules ({{ data.compliant.len() }})</h2>
  <div id="ok">
    <ul class="compliant-list">
      {% for r in data.compliant %}
        <li id="rule-{{ r.id }}"><strong>{{ r.id }}</strong> – {{ r.name }}</li>
      {% endfor %}
    </ul>
  </div>

  <footer>Generated by Audity – {{ data.profile_name }} • {{ data.host_info.hostname }}</footer>
</main>
</body>
</html>
"###,
    ext = "html"
)]
pub struct ReportTemplate<'a> {
    /// Reference to the fully parsed report data.
    pub data: &'a ReportData,
}

impl<'a> From<&'a ReportData> for ReportTemplate<'a> {
    #[inline]
    fn from(data: &'a ReportData) -> Self {
        Self { data }
    }
}