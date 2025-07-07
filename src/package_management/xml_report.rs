use quick_xml::events::{BytesEnd, BytesStart, BytesText, Event}; // Import XML event types
use quick_xml::Writer; // XML writer
use std::io::{Cursor, Error as IoError, ErrorKind, Result}; // I/O types and error handling

/// Generates an XML report listing installed and upgradable packages.
///
/// # Arguments
/// * `total_installed` – total number of installed packages.
/// * `installed_packages` – multiline string: each line contains a package name and version.
/// * `upgradable_packages` – multiline string: each line contains a package name.
///
/// # Returns
/// A `Result` which is either:
/// - `Ok(String)` — the XML-formatted string.
/// - `Err(IoError)` — if any error occurs during XML generation or conversion to UTF-8.
/// # Errors
/// This function returns an error if:
/// - Writing to the internal XML buffer fails (e.g. XML formatting issue).
/// - The final output cannot be converted from bytes to UTF-8.
/// - Any quick-xml internal error occurs and is wrapped into an I/O error.
pub fn generate_xml_report(
    total_installed: usize,
    installed_packages: &str,
    upgradable_packages: &str,
) -> Result<String> {
    // Initialize the writer with 4-space indentation, writing to memory buffer.
    let mut writer: Writer<Cursor<Vec<u8>>> = Writer::new_with_indent(Cursor::new(Vec::new()), b' ', 4);

    // Closure to convert quick_xml errors into IoError.
    let map_err = |e: quick_xml::Error| IoError::new(ErrorKind::Other, e.to_string());

    // Write <packages> root element.
    writer.write_event(Event::Start(BytesStart::new("packages"))).map_err(map_err)?;

    // Write <installed> section with total count.
    writer.write_event(Event::Start(BytesStart::new("installed"))).map_err(map_err)?;
    writer.write_event(Event::Text(BytesText::new(&total_installed.to_string()))).map_err(map_err)?;
    writer.write_event(Event::End(BytesEnd::new("installed"))).map_err(map_err)?;

    // Write <upgradable> section with line count of upgradable packages.
    writer.write_event(Event::Start(BytesStart::new("upgradable"))).map_err(map_err)?;
    writer.write_event(Event::Text(BytesText::new(
        &upgradable_packages.lines().count().to_string(),
    ))).map_err(map_err)?;
    writer.write_event(Event::End(BytesEnd::new("upgradable"))).map_err(map_err)?;

    // Write <total> section with detailed installed packages.
    writer.write_event(Event::Start(BytesStart::new("total"))).map_err(map_err)?;
    for line in installed_packages.lines() {
        let details: Vec<&str> = line.split_whitespace().collect(); // Expect: name + version
        if details.len() > 1 {
            // Write <package name="..." version="..." />.
            let mut pkg: BytesStart<'_> = BytesStart::new("package");
            pkg.push_attribute(("name", details[0]));
            pkg.push_attribute(("version", details[1]));
            writer.write_event(Event::Empty(pkg)).map_err(map_err)?;
        }
    }
    writer.write_event(Event::End(BytesEnd::new("total"))).map_err(map_err)?;

    // Write <upgrade> section with upgradable package names.
    writer.write_event(Event::Start(BytesStart::new("upgrade"))).map_err(map_err)?;
    for line in upgradable_packages.lines() {
        let details: Vec<&str> = line.split_whitespace().collect(); // Expect: name only
        if !details.is_empty() {
            // Write <package name="..." />.
            let mut pkg: BytesStart<'_> = BytesStart::new("package");
            pkg.push_attribute(("name", details[0]));
            writer.write_event(Event::Empty(pkg)).map_err(map_err)?;
        }
    }
    writer.write_event(Event::End(BytesEnd::new("upgrade"))).map_err(map_err)?;

    // Close </packages> root.
    writer.write_event(Event::End(BytesEnd::new("packages"))).map_err(map_err)?;

    // Convert the memory buffer (Vec<u8>) into UTF-8 string and return.
    let output: Vec<u8> = writer.into_inner().into_inner();
    String::from_utf8(output).map_err(|e| IoError::new(ErrorKind::InvalidData, e))
}
