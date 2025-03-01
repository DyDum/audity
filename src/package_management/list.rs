use std::process::Command;
use std::str;
use std::io::{self, Error as IoError};

/// Returns the count of installed packages by executing the dpkg command.
///
/// # Returns
/// A `Result` which is either:
/// - The number of installed packages.
/// - An `IoError` if the command fails or output is invalid.
pub fn get_installed_packages_count() -> Result<usize, std::io::Error> {
    let output = Command::new("dpkg")
        .arg("-l")
        .output()?;

    if !output.status.success() {
        Err(std::io::Error::new(std::io::ErrorKind::Other, "Failed to list installed packages"))
    } else {
        // Subtract header lines to count only the package lines
        Ok(String::from_utf8_lossy(&output.stdout).lines().count() - 5) 
    }
}

/// Lists details of all installed packages including name, version, and architecture.
///
/// # Returns
/// A `Result` which is either:
/// - A string with each package's details per line.
/// - An `IoError` if the command fails or output is invalid.
pub fn list_installed_packages() -> Result<String, IoError> {
    let output = Command::new("dpkg")
        .arg("-l")
        .output()?;

    if !output.status.success() {
        Err(IoError::new(io::ErrorKind::Other, "Failed to execute dpkg"))
    } else {
        // Convert bytes to string and handle UTF-8 conversion errors
        let output_str = str::from_utf8(&output.stdout)
            .map_err(|e| IoError::new(io::ErrorKind::InvalidData, e.to_string()))?;

        // Parse and collect package details
        let mut details = String::new();
        for line in output_str.lines().skip(5) { // Skipping header lines
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() > 3 {
                let package_name = parts[1];
                let version = parts[2];
                let architecture = parts[3];
                details.push_str(&format!("{} {} {}\n", package_name, version, architecture));
            }
        }
        Ok(details)
    }
}