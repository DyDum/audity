//! Askama HTML template for the CIS report.
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
    source = r#"
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>CIS Benchmark {{ data.profile_name }}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<!-- ===== fonts & colour palette =================================== -->
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root{
  --bg        : #f7f9fc;
  --fg        : #1f2937;
  --muted     : #475569;
  --surface   : #ffffff;
  --border    : #e2e8f0;
  --shadow    : 0 2px 6px rgba(0,0,0,.06);
  --danger    : #e74c3c;
  --warning   : #f39c12;
  --success   : #27ae60;
}
/* ===== generic reset & basic layout =============================== */
*{box-sizing:border-box}
body{
  margin:0;
  font-family:"Inter",system-ui,Arial,sans-serif;
  background:var(--bg);
  color:var(--fg);
  line-height:1.55;
  font-size:16px;
}
h1{margin:0 0 1rem;font-size:2.1rem;font-weight:700;color:var(--fg)}
h2{margin:2.2rem 0 .6rem;font-size:1.3rem;font-weight:600;color:var(--fg);display:flex;align-items:center;gap:.6rem}
.container{max-width:960px;margin:auto;padding:2.2rem 1rem}
/* ===== table, card & misc components ============================= */
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{padding:.55rem .9rem;text-align:left}
tr:nth-child(even){background:#fafafa}
.card{background:var(--surface);border:1px solid var(--border);border-left-width:5px;border-radius:8px;box-shadow:var(--shadow);padding:1rem 1.25rem;margin:.9rem 0}
.card.danger{border-color:var(--danger)}
.card.warning{border-color:var(--warning)}
ul.compliant-list{padding-left:1.1rem;margin:.9rem 0}
/* ===== toggle buttons ============================================ */
button.toggle{
  border:none;background:none;color:var(--fg);font-size:1.25rem;cursor:pointer;
  transform:rotate(0);transition:transform .25s ease}
button.toggle[aria-expanded="false"]{transform:rotate(-90deg)}
/* ===== code blocks & statistics ================================== */
pre{background:#f1f5f9;border-radius:6px;padding:.6rem;overflow-x:auto}
table.meta,table.stats{margin:1.2rem 0;border:1px solid var(--border);border-radius:8px;overflow:hidden;box-shadow:var(--shadow)}
table.stats td:first-child{font-weight:600}
table.stats tr td:nth-child(2){text-align:right}
td.danger{color:var(--danger)}td.warning{color:var(--warning)}td.success{color:var(--success)}
footer{margin:4rem 0 1rem;text-align:center;font-size:.8rem;color:var(--muted)}
</style>

<!-- ===== tiny script to collapse / expand sections ================ -->
<script>
function toggleSection(id){
  const block=document.getElementById(id);
  const btn=document.getElementById(id+'-btn');
  const expanded=btn.getAttribute('aria-expanded')==='true';
  btn.setAttribute('aria-expanded',(!expanded).toString());
  block.style.display=expanded?'none':'';
}
</script>
</head>
<body>
  <main class="container">

    <h1>CIS Benchmark {{ data.profile_name }}</h1>

    <!-- Host résumé --------------------------------------------------->
    <table class="meta">
      <tr><td><strong>Hostname</strong></td><td>{{ data.host_info.hostname }}</td></tr>
      <tr><td><strong>Adresse IP</strong></td><td>{{ data.host_info.primary_ip }}</td></tr>
      <tr><td><strong>OS</strong></td><td>{{ data.host_info.os }}</td></tr>
      <tr><td><strong>Kernel</strong></td><td>{{ data.host_info.kernel }}</td></tr>
      <tr><td><strong>Architecture</strong></td><td>{{ data.host_info.architecture }}</td></tr>
      <tr><td><strong>CPU cores</strong></td><td>{{ data.host_info.cpu_cores }}</td></tr>
      <tr><td><strong>Mémoire</strong></td><td>{{ data.host_info.memory_mb }} MB</td></tr>
    </table>

    <!-- Global statistics -------------------------------------------->
    <table class="stats">
      <tr><td>Total de règles</td><td>{{ data.stats.total }}</td></tr>
      <tr><td class="success">Conformes</td><td>{{ data.stats.pass }} ({{ data.stats.percent_pass }} %)</td></tr>
      <tr><td class="danger">Non conformes</td><td>{{ data.stats.fail }} ({{ data.stats.percent_fail }} %)</td></tr>
      <tr><td class="warning">Non testées</td><td>{{ data.stats.not_tested }} ({{ data.stats.percent_not_tested }} %)</td></tr>
    </table>

    <!-- Non-compliant rules ----------------------------------------->
    <h2>
      <button id="nc-btn" class="toggle" aria-expanded="true" onclick="toggleSection('nc')">▼</button>
      Règles non conformes ({{ data.non_compliant.len() }})
    </h2>
    <div id="nc">
      {% for r in data.non_compliant %}
        <div class="card danger">
          <h3>{{ r.id }}</h3>
          <p>{{ r.description }}</p>
          {% if r.corrective != "" %}<p><em><strong>Correctif :</strong> {{ r.corrective }}</em></p>{% endif %}
          {% if r.correction_cmd != "" %}<pre><code>{{ r.correction_cmd }}</code></pre>{% endif %}
        </div>
      {% endfor %}
    </div>

    <!-- Not-tested rules --------------------------------------------->
    <h2>
      <button id="nt-btn" class="toggle" aria-expanded="true" onclick="toggleSection('nt')">▼</button>
      Règles non testées ({{ data.not_tested.len() }})
    </h2>
    <div id="nt">
      {% for r in data.not_tested %}
        <div class="card warning">
          <h3>{{ r.id }}</h3>
          <p>{{ r.description }}</p>
          {% if r.manual_review != "" %}<p><strong>Manual Review :</strong> {{ r.manual_review }}</p>{% endif %}
          {% if r.corrective != "" %}<p><em><strong>Correctif :</strong> {{ r.corrective }}</em></p>{% endif %}
          {% if r.correction_cmd != "" %}<pre><code>{{ r.correction_cmd }}</code></pre>{% endif %}
        </div>
      {% endfor %}
    </div>

    <!-- Compliant rules ---------------------------------------------->
    <h2>
      <button id="ok-btn" class="toggle" aria-expanded="true" onclick="toggleSection('ok')">▼</button>
      Règles conformes ({{ data.compliant.len() }})
    </h2>
    <div id="ok">
      <ul class="compliant-list">
        {% for r in data.compliant %}
          <li><strong>{{ r.id }}</strong> – {{ r.description }}</li>
        {% endfor %}
      </ul>
    </div>

    <footer>Généré par Audity – {{ data.profile_name }} • {{ data.host_info.hostname }}</footer>
  </main>
</body>
</html>
"#,
    ext = "html"
)]
pub struct ReportTemplate<'a> {
    /// Borrowed data model to be rendered.
    pub data: &'a ReportData,
}

impl<'a> From<&'a ReportData> for ReportTemplate<'a> {
    /// Convenient conversion so that `ReportData::render()` can be called as:
    /// `ReportTemplate::from(&report).render()?;`
    fn from(data: &'a ReportData) -> Self {
        Self { data }
    }
}