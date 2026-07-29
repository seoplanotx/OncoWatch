/**
 * Getting a generated report out of Firstlight.
 *
 * Reports are already files on this computer, so the desktop shell opens them
 * directly rather than "downloading" them. Every Tauri call lives here (and is
 * imported lazily) so components stay shell-agnostic and tests can mock this
 * module wholesale — the same pattern as `lib/external.ts`.
 */

import { isTauri } from '@tauri-apps/api/core';

export type SaveResult = 'saved' | 'cancelled' | 'unavailable';

/** True inside the Tauri desktop shell; false in `vite dev`, vitest, and Playwright. */
export function isDesktopShell(): boolean {
  try {
    return isTauri();
  } catch {
    return false;
  }
}

/** What this platform calls the file manager, for button copy. */
export function revealLabel(): string {
  const platform = typeof navigator === 'undefined' ? '' : navigator.userAgent;
  if (/Mac|iPhone|iPad/i.test(platform)) return 'Show in Finder';
  if (/Windows/i.test(platform)) return 'Show in File Explorer';
  return 'Show in file manager';
}

/** Open the PDF with whatever the OS uses for PDFs. Returns false if the shell refused. */
export async function openReportFile(path: string): Promise<boolean> {
  if (!path) return false;
  try {
    const { openPath } = await import('@tauri-apps/plugin-opener');
    await openPath(path);
    return true;
  } catch {
    return false;
  }
}

/** Select the file in Finder/Explorer, rather than just opening its folder. */
export async function revealReportFile(path: string): Promise<boolean> {
  if (!path) return false;
  try {
    const { revealItemInDir } = await import('@tauri-apps/plugin-opener');
    await revealItemInDir(path);
    return true;
  } catch {
    return false;
  }
}

/**
 * Save a copy wherever the user picks. The save dialog grants write access to
 * the chosen path, so no broad filesystem permission is needed.
 */
export async function saveReportCopy(suggestedName: string, getBytes: () => Promise<Blob>): Promise<SaveResult> {
  let save: typeof import('@tauri-apps/plugin-dialog').save;
  let writeFile: typeof import('@tauri-apps/plugin-fs').writeFile;
  try {
    ({ save } = await import('@tauri-apps/plugin-dialog'));
    ({ writeFile } = await import('@tauri-apps/plugin-fs'));
  } catch {
    return 'unavailable';
  }

  const destination = await save({
    defaultPath: suggestedName,
    filters: [{ name: 'PDF', extensions: ['pdf'] }]
  });
  if (!destination) return 'cancelled';

  const blob = await getBytes();
  await writeFile(destination, new Uint8Array(await blob.arrayBuffer()));
  return 'saved';
}

/**
 * Browser fallback for `npm run dev` and the Playwright smoke test.
 *
 * The anchor must be in the document and the object URL must outlive the click,
 * or the transfer never starts — see `SupportPage` for the same shape.
 */
export function downloadInBrowser(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** A stable, non-colliding filename for a saved copy: `firstlight-appointment-prep-2026-07-28.pdf`. */
export function suggestedFileName(reportType: string, generatedAt: string): string {
  const stamp = new Date(generatedAt);
  const date = Number.isNaN(stamp.getTime()) ? '' : `-${stamp.toISOString().slice(0, 10)}`;
  return `firstlight-${reportType.replace(/_/g, '-')}${date}.pdf`;
}
