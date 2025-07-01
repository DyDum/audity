use std::process::Command;

/// Execute a shell verification command and translate its outcome
/// into a boolean compliance flag.
///
/// # Arguments  
/// * `cmd` – Shell command executed as `sh -c "<cmd>"`.
///
/// # Returns  
/// A `Result` whose variants mean:
/// | Variant            | Meaning                                                                           |
/// |--------------------|-----------------------------------------------------------------------------------|
/// | `Ok(true)`         | **Compliant** – the command reports success (prints `0` or exits with code 0).    |
/// | `Ok(false)`        | **Not compliant** – the command reports failure (prints `1` or exits with code 1).|
/// | `Err(String)`      | Any execution error, non-UTF-8 output, stderr content, or unexpected output.      |
/// # Errors
/// This function returns an `Err(String)` in the following cases:
/// - If the command fails to launch (I/O error).
/// - If the command prints anything on stderr.
/// - If the output is not `"0"`, `"1"`, or empty.
/// - If the exit code is not `0` or `1` when no output is produced.
pub fn execute_verification_command(cmd: &str) -> Result<bool, String> {
    let output = Command::new("sh")
        .arg("-c")
        .arg(cmd)
        .output()
        .map_err(|e| format!("Erreur système : {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

    // Treat any message on stderr as an immediate error.
    if !stderr.is_empty() {
        return Err(format!("Erreur shell : {stderr}"));
    }

    match stdout.as_str() {
        "0" => Ok(true),
        "1" => Ok(false),
        "" => match output.status.code() {
            Some(0) => Ok(true),
            Some(1) => Ok(false),
            _ => Err(format!("Erreur d'exécution : code {}", output.status.code().unwrap_or(-1)))
        },
        other => Err(format!("Sortie inattendue : '{}'", other)),
    }
}