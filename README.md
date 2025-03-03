# 🔍 Audity - Security Scanner for Linux Servers

**Audity** is a Linux server scanning and analysis tool. It identifies misconfigurations, outdated package versions, and potential vulnerabilities. The goal is to enhance server security by providing a **detailed HTML report**, including a **global security score** and **concrete recommendations**.

## 📌 Features

- 🔎 **Configuration Analysis**
  - Checks system configuration files (e.g., `/etc/ssh/sshd_config`).
  - Identifies deviations from security best practices.

- 🛡️ **Vulnerability Tests**
  - **Open Services**: Detects active ports and exposed services.
  - **Outdated Versions**: Identifies outdated or unsupported software.
  - **Critical Permissions**: Checks file permissions for sensitive files (`/etc/passwd`, `/etc/shadow`, etc.).

- 📊 **HTML Report Generation**
  - Provides a **global security score (0-100)**.
  - Includes a **detailed list of detected issues**.
  - Offers a **"Recommended Improvements" section** with corrective actions.

---

## 🚀 Installation

### Prerequisites
- **Rust** (≥ 1.XX)
- A **Linux** server (Debian, Ubuntu, CentOS, etc.)
- Administrator access (`sudo`)

### Installation from source
```bash
git clone https://github.com/DyDum/audity.git
cd audity
cargo build
```

### Running a Scan
```bash
./target/release/audity
```

---

## 📝 Configuration

Audity is based on **rules defined in XML**, updated **manually every month** to reflect the latest security recommendations.

---

## 📄 Report Format

Audity generates its reports **directly in HTML**, viewable in a browser:

- **Detailed HTML report** with formatting and explanations of detected vulnerabilities.
- **XML files** storing scan results and detection rules:
  - `rules.xml`: Contains security best practices and detection rules.
  - `scan_results.xml`: Archives results from each scan.


---

## 🛠️ Contribution

Contributions are welcome! 🎉

Before contributing, please read the [`CONTRIBUTING.md`](CONTRIBUTING.md) file, which explains the best practices for submitting improvements or fixes.

---

## 📜 License

This project is licensed under the **MIT** license. You are free to use and modify it as long as you comply with this license.

📧 **Contact**: For any questions or suggestions, open an issue on GitHub or contact us directly!
