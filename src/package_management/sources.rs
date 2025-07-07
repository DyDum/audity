use std::fs;

/// Reads the contents of the sources.list file.
///
/// # Returns
/// A `Result` which is either:
/// - A string containing the contents of the sources.list file.
/// - An `IoError` if the file cannot be read.
/// # Errors
/// This function returns an error if:
/// - The file `/etc/apt/sources.list` does not exist or is inaccessible.
/// - The file cannot be opened or read due to permissions or I/O errors.
pub fn read_sources_list() -> Result<String, std::io::Error> {
    let content = fs::read_to_string("/etc/apt/sources.list")?;
    Ok(content)
}
