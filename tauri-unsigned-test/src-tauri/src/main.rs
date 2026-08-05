// Prevent an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::Read;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

const SIDECAR_TIMEOUT: Duration = Duration::from_secs(45);

/// Locate `python/sidecar.py` next to the executable (walking up a few
/// levels to cover debug builds during development).
fn find_sidecar() -> Option<PathBuf> {
    let mut dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    for _ in 0..5 {
        let candidate = dir.join("python").join("sidecar.py");
        if candidate.is_file() {
            return Some(candidate);
        }
        if !dir.pop() {
            break;
        }
    }
    None
}

/// Run the Python sidecar one-shot and parse its JSON response.
/// This mirrors how the real app shells out to Python (ContractDownloader
/// uses subprocess for `fab`, `python` scripts, etc.).
#[tauri::command]
fn run_python(command: String, args_json: Option<String>) -> Result<serde_json::Value, String> {
    let script = find_sidecar()
        .ok_or_else(|| "python/sidecar.py not found next to the executable".to_string())?;
    let args = args_json.unwrap_or_else(|| "{}".to_string());

    let mut cmd = Command::new(if cfg!(windows) { "python" } else { "python3" });
    cmd.arg(&script)
        .arg(&command)
        .arg(&args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NO_WINDOW: do not flash a console next to the GUI window.
        cmd.creation_flags(0x0800_0000);
    }

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("failed to start python sidecar: {e}"))?;
    let mut stdout = child
        .stdout
        .take()
        .ok_or_else(|| "sidecar stdout unavailable".to_string())?;
    let mut stderr = child
        .stderr
        .take()
        .ok_or_else(|| "sidecar stderr unavailable".to_string())?;

    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        let mut out = String::new();
        let mut err = String::new();
        let _ = stdout.read_to_string(&mut out);
        let _ = stderr.read_to_string(&mut err);
        let _ = tx.send((out, err));
    });

    match rx.recv_timeout(SIDECAR_TIMEOUT) {
        Ok((out, err)) => {
            let _ = child.wait();
            let text = if out.trim().is_empty() { err } else { out };
            serde_json::from_str(&text).map_err(|e| {
                format!("sidecar returned invalid JSON ({e}):\n{}", text.chars().take(500).collect::<String>())
            })
        }
        Err(_) => {
            let _ = child.kill();
            Err("python sidecar timed out".to_string())
        }
    }
}

#[tauri::command]
fn app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "tauri-unsigned-test",
        "version": env!("CARGO_PKG_VERSION"),
        "tauri": tauri::VERSION,
        "sidecar_timeout_s": SIDECAR_TIMEOUT.as_secs(),
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_python, app_info])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
