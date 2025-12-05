use std::process::Command;
use std::str;
use std::io::{self, Error as IoError};
use std::fmt::Write;

/// Returns the count of installed packages by executing the dpkg command.
///
/// # Returns
/// A `Result` which is either:
/// - The number of installed packages.
/// - An `IoError` if the command fails or output is invalid.
/// # Errors
/// This function returns an error if:
/// - The `dpkg -l` command fails to execute (e.g. `dpkg` not found).
/// - The command executes but returns a non-zero exit code.
pub fn get_installed_packages_count() -> Result<usize, std::io::Error> {
    let output: std::process::Output = Command::new("dpkg")
        .arg("-l")
        .output()?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).lines().count() - 5) 
    } else {
        Err(std::io::Error::new(std::io::ErrorKind::Other, "Failed to list installed packages"))
    }
}


/// Lists details of all installed packages including name, version, and architecture.
///
/// # Returns
/// A `Result` which is either:
/// - A string with each package's details per line.
/// - An `IoError` if the command fails or output is invalid.
///
/// # Errors
/// Returns an error if:
/// - The `dpkg -l` command fails to execute.
/// - The command output is not valid UTF-8.
/// - There is an internal formatting failure when building the result string.
pub fn list_installed_packages() -> Result<String, IoError> {
    let output: std::process::Output = Command::new("dpkg")
        .arg("-l")
        .output()?;

    if output.status.success() {
        // Convert bytes to string and handle UTF-8 conversion errors
        let output_str: &str = str::from_utf8(&output.stdout)
            .map_err(|e| IoError::new(io::ErrorKind::InvalidData, e.to_string()))?;

        // Parse and collect package details
        let mut details: String = String::new();
        for line in output_str.lines().skip(5) { // Skipping header lines
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() > 3 {
                let package_name: &str = parts[1];
                let version: &str = parts[2];
                let architecture: &str = parts[3];
                if let Err(e) = writeln!(details, "{package_name} {version} {architecture}") {
                    return Err(IoError::new(io::ErrorKind::Other, e.to_string()));
                }
            }
        }
        Ok(details)
    } else {
        Err(IoError::new(io::ErrorKind::Other, "Failed to execute dpkg"))
    }
}