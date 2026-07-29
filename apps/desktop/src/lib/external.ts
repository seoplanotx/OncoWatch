/** Open an https URL in the user's default browser (Tauri shell when available, window.open in dev). */
export async function openExternal(url: string): Promise<void> {
  if (!url.startsWith('https://')) {
    return;
  }
  try {
    const { open } = await import('@tauri-apps/plugin-shell');
    await open(url);
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}
