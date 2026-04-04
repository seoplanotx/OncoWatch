#!/usr/bin/env bash

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[oncowatch] build_macos_dmg.sh only supports macOS" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAURI_DIR="$ROOT_DIR/apps/desktop/src-tauri"
APP_NAME="OncoWatch"
APP_PATH="$TAURI_DIR/target/release/bundle/macos/$APP_NAME.app"
DMG_DIR="$TAURI_DIR/target/release/bundle/dmg"
VERSION="$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' "$TAURI_DIR/tauri.conf.json" | head -n 1)"

case "$(uname -m)" in
  arm64)
    ARCH="aarch64"
    ;;
  x86_64)
    ARCH="x86_64"
    ;;
  *)
    ARCH="$(uname -m)"
    ;;
esac

if [[ -z "$VERSION" ]]; then
  echo "[oncowatch] unable to determine app version from tauri.conf.json" >&2
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "[oncowatch] expected app bundle at $APP_PATH" >&2
  exit 1
fi

mkdir -p "$DMG_DIR"
STAGING_DIR="$(mktemp -d "$DMG_DIR/oncowatch-dmg.XXXXXX")"
OUTPUT_DMG="$DMG_DIR/${APP_NAME}_${VERSION}_${ARCH}.dmg"

cleanup() {
  rm -rf "$STAGING_DIR"
}

trap cleanup EXIT

rm -f "$OUTPUT_DMG"
cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

echo "[oncowatch] creating DMG at $OUTPUT_DMG"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  -fs HFS+ \
  "$OUTPUT_DMG" \
  >/dev/null

echo "[oncowatch] created $OUTPUT_DMG"
