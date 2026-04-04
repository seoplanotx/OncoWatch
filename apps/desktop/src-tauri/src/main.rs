#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;

struct BackendState {
    child: Mutex<Option<CommandChild>>,
}

#[cfg(not(debug_assertions))]
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
        .setup(|_app| {
            #[cfg(not(debug_assertions))]
            {
                match spawn_backend(&_app.handle()) {
                    Ok(child) => {
                        let state = _app.state::<BackendState>();
                        *state.child.lock().unwrap() = Some(child);
                    }
                    Err(error) => {
                        eprintln!("failed to start backend sidecar: {error}");
                    }
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building OncoWatch")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                let state = app_handle.state::<BackendState>();
                let mut child_guard = state.child.lock().unwrap();
                if let Some(child) = child_guard.take() {
                    let _ = child.kill();
                }
            }
        });
}
