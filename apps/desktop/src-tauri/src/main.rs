#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendState {
    child: Mutex<Option<CommandChild>>,
}

fn spawn_backend(app: &tauri::AppHandle) -> Result<CommandChild, Box<dyn std::error::Error>> {
    let command = app
        .shell()
        .sidecar("oncowatch-backend")?
        .args(["--host", "127.0.0.1", "--port", "17845"]);
    let (mut rx, child) = command.spawn()?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            println!("[oncowatch-backend] {:?}", event);
        }
    });

    Ok(child)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState {
            child: Mutex::new(None),
        })
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            {
                let child = spawn_backend(&app.handle())
                    .map_err(|e| format!("failed to start backend sidecar: {e}"))?;
                let state = app.state::<BackendState>();
                *state.child.lock().unwrap() = Some(child);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building OncoWatch")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                let state = app_handle.state::<BackendState>();
                if let Some(child) = state.child.lock().unwrap().as_mut() {
                    let _ = child.kill();
                }
            }
        });
}
