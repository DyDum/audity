mod audit_rules;
mod package_management;
use audit_rules::scanner::scan_directory;


fn main() {
    // Update the package list to ensure it is up-to-date.
    if let Err(e) = package_management::update::update_package_list() {
        println!("Failed to update package list: {}", e);
        return;
    }

    // Read the sources list if needed for the report or verification.
    let sources = package_management::sources::read_sources_list().unwrap_or_else(|e| {
        println!("Failed to read sources list: {}", e);
        return String::new();  // Provide an empty string in case of failure.
    });

    // Retrieve the total count of installed packages. If the operation fails, default to 0.
    let total_installed = package_management::list::get_installed_packages_count().unwrap_or(0);

    // Retrieve detailed information about installed packages. If the operation fails, default to an empty string.
    let installed_packages = package_management::list::list_installed_packages().unwrap_or_default();

    // Retrieve detailed information about upgradable packages. If the operation fails, default to an empty string.
    let upgradable_packages = package_management::update::check_upgradable_packages().unwrap_or_default();

    // Generate the XML report using the gathered data.
    match package_management::xml_report::generate_xml_report(total_installed, &installed_packages, &upgradable_packages) {
        Ok(xml_data) => {
            // If the XML data is successfully generated, write it to a file.
            std::fs::write("./reports/report.xml", xml_data).expect("Failed to write XML report");
            println!("XML report generated successfully and saved to 'report.xml'.");
        },
        Err(e) => {
            // If there was an error generating the XML report, log the error.
            println!("Failed to generate XML report: {}", e);
        },
    }
    // TODO : Fix the path to the rules directory to automatically select the rights one.
    let dir = "rules/debian";

    if let Err(e) = scan_directory(dir) {
        eprintln!("Error : {e}");
        std::process::exit(1);
    }
}

