use quick_xml::{Writer, events::{Event, BytesEnd, BytesStart, BytesText}};
use std::io::Cursor;
use std::io::{self, Error as IoError};

/// Generates an XML report of package statistics and details.
///
/// # Arguments
/// * `total_installed` - Total number of installed packages.
/// * `installed_packages` - String containing details of each installed package.
/// * `upgradable_packages` - String containing details of each upgradable package.
///
/// # Returns
/// A `Result` which is either:
/// - An XML string on success.
/// - An `IoError` on failure.
pub fn generate_xml_report(total_installed: usize, installed_packages: &str, upgradable_packages: &str) -> Result<String, IoError> {
    // Initialize XML writer with indentation for readability.
    let mut writer = Writer::new_with_indent(Cursor::new(Vec::new()), b' ', 4);

    // Start the XML document with the root element.
    writer.write_event(Event::Start(BytesStart::borrowed_name(b"packages")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;

    // Section for total number of installed packages.
    writer.write_event(Event::Start(BytesStart::borrowed_name(b"installed")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    writer.write_event(Event::Text(BytesText::from_plain_str(&total_installed.to_string())))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    writer.write_event(Event::End(BytesEnd::borrowed(b"installed")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;

    // Section for the number of upgradable packages.
    writer.write_event(Event::Start(BytesStart::borrowed_name(b"upgradable")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    writer.write_event(Event::Text(BytesText::from_plain_str(&upgradable_packages.lines().count().to_string())))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    writer.write_event(Event::End(BytesEnd::borrowed(b"upgradable")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;

    // List details of each installed package under the <total> tag.
    writer.write_event(Event::Start(BytesStart::borrowed_name(b"total")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    for line in installed_packages.lines() {
        let details: Vec<&str> = line.split_whitespace().collect();
        if details.len() > 1 {
            let package_name = details[0];
            let version_info = details[1];

            // Writing each package with its name and version as a self-closing tag.
            let mut pkg = BytesStart::borrowed_name(b"package");
            pkg.push_attribute(("name", package_name));
            pkg.push_attribute(("version", version_info));

            writer.write_event(Event::Empty(pkg))
                .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
        }
    }
    writer.write_event(Event::End(BytesEnd::borrowed(b"total")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;

    // List details of each upgradable package under the <upgrade> tag.
    writer.write_event(Event::Start(BytesStart::borrowed_name(b"upgrade")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
    for line in upgradable_packages.lines() {
        let details: Vec<&str> = line.split_whitespace().collect();
        if details.len() > 1 {
            let package_name = details[0];

            // Writing each upgradable package as a self-closing tag.
            let mut pkg = BytesStart::borrowed_name(b"package");
            pkg.push_attribute(("name", package_name));

            writer.write_event(Event::Empty(pkg))
                .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;
        }
    }
    writer.write_event(Event::End(BytesEnd::borrowed(b"upgrade")))
        .map_err(|e| IoError::new(io:: ErrorKind::Other, e.to_string()))?;

    // Close the root element and the document.
    writer.write_event(Event::End(BytesEnd::borrowed(b"packages")))
        .map_err(|e| IoError::new(io::ErrorKind::Other, e.to_string()))?;

    // Convert the XML data stored in the writer to a String and return it.
    Ok(String::from_utf8(writer.into_inner().into_inner()).map_err(|e| IoError::new(io::ErrorKind::InvalidData, e.to_string()))?)
}
