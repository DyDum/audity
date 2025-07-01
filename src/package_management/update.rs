use std::process::Command;
use std::str;
use std::io::{self, Error as IoError};

/// Executes the 'sudo apt update' command to update the package list.
///
/// # Returns
/// A `Result` which is either:
/// - `Ok(())` if the update command is successful.
/// - An `IoError` if the update command fails.
/// # Errors
/// This function returns an error if:
/// - The command `sudo apt update` cannot be executed (e.g. missing `sudo` or `apt`).
/// - The command returns a non-zero exit code.
pub fn update_package_list() -> Result<(), io::Error> {
    let status = Command::new("sudo")
        .arg("apt")
        .arg("update")
        .status()?;

    if status.success() {
        Ok(())
    } else {
        Err(io::Error::new(io::ErrorKind::Other, "Failed to update package list"))
    }
}

/// Checks for upgradable packages by executing the 'apt list --upgradable' command.
///
/// # Returns
/// A `Result` which is either:
/// - A string listing upgradable packages.
/// - An `IoError` if the command fails or the output is invalid.
/// # Errors
/// This function returns an error if:
/// - The `apt list --upgradable` command cannot be executed.
/// - The command returns a non-zero exit code.
/// - The command output is not valid UTF-8.
/// - An error message is emitted to stderr.
pub fn check_upgradable_packages() -> Result<String, IoError> {
    let output = Command::new("apt")
        .arg("list")
        .arg("--upgradable")
        .output()?;

    if output.status.success() {
        // Decode the output from bytes to string and handle potential UTF-8 errors.
        let upgradable_packages = str::from_utf8(&output.stdout)
            .map_err(|e| IoError::new(io::ErrorKind::InvalidData, e.to_string()))?;

        // Skip the first line of the output, usually a header.
        let packages_details = upgradable_packages.lines().skip(1).collect::<Vec<_>>().join("\n");

        Ok(packages_details)
    } else {
        // Decode the error message and return it as an IoError.
        let error_message = str::from_utf8(&output.stderr)
            .unwrap_or("Failed to decode error message")  // Provide a fallback error message.
            .to_string();
        
        Err(IoError::new(io::ErrorKind::Other, error_message))
    }
}