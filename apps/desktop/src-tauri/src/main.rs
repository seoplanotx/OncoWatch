#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;

struct BackendState {
    child: Mutex<Option<CommandChild>>,
}

/// Tracks whether the user has been told the app keeps running in the tray,
/// so the "still running in the background" hint only fires once per session.
static TRAY_HINT_SHOWN: AtomicBool = AtomicBool::new(false);

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

fn build_tray(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let open_item = MenuItem::with_id(app, "open", "Open Firstlight", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit Firstlight", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open_item, &quit_item])?;

    let mut builder = TrayIconBuilder::with_id("firstlight-tray")
        .tooltip("Firstlight — monitoring in the background")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => show_main_window(app),
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { .. } = event {
                show_main_window(tray.app_handle());
            }
        });

    if let Some(icon) = app.default_window_icon().cloned() {
        builder = builder.icon(icon);
    }

    builder.build(app)?;
    Ok(())
}

/// When the window is closed, keep Firstlight running in the tray so the
/// scheduler can keep monitoring in the background. Real quit happens only
/// from the tray "Quit Firstlight" item.
fn hide_to_tray(app: &tauri::AppHandle, window: &tauri::Window) {
    let _ = window.hide();

    if !TRAY_HINT_SHOWN.swap(true, Ordering::SeqCst) {
        use tauri_plugin_notification::NotificationExt;
        let _ = app
            .notification()
            .builder()
            .title("Firstlight is still running")
            .body("Monitoring continues in the background. Open it again from the menu bar or system tray.")
            .show();
    }
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

#[cfg(not(debug_assertions))]
fn check_for_updates(app: tauri::AppHandle) {
    use tauri_plugin_updater::UpdaterExt;

    tauri::async_runtime::spawn(async move {
        let updater = match app.updater() {
            Ok(updater) => updater,
            Err(error) => {
                eprintln!("[updater] unavailable: {error}");
                return;
            }
        };

        match updater.check().await {
            Ok(Some(update)) => {
                println!("[updater] installing update {}", update.version);
                match update.download_and_install(|_, _| {}, || {}).await {
                    Ok(_) => {
                        println!("[updater] update installed, restarting");
                        app.restart();
                    }
                    Err(error) => eprintln!("[updater] install failed: {error}"),
                }
            }
            Ok(None) => println!("[updater] up to date"),
            Err(error) => eprintln!("[updater] check failed: {error}"),
        }
    });
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendState {
            child: Mutex::new(None),
        })
        .setup(|app| {
            build_tray(app.handle())?;

            #[cfg(not(debug_assertions))]
            {
                check_for_updates(app.handle().clone());
                match spawn_backend(&app.handle()) {
                    Ok(child) => {
                        let state = app.state::<BackendState>();
                        *state.child.lock().unwrap() = Some(child);
                    }
                    Err(error) => {
                        eprintln!("failed to start backend sidecar: {error}");
                    }
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                hide_to_tray(window.app_handle(), window);
            }
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
