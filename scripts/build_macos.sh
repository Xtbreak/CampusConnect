#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'macOS 应用必须在 Mac 上构建。' >&2
  exit 1
fi
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys, tkinter; assert sys.version_info >= (3, 10), "需要 Python 3.10+"; assert tkinter.TkVersion >= 8.6, "需要 Tk 8.6+"'
"$PYTHON" -m venv .venv-build
.venv-build/bin/python -m pip install -r requirements/build.txt
.venv-build/bin/python -m unittest discover -s tests -v
mkdir -p build dist
.venv-build/bin/python - <<'PY'
from PIL import Image
with Image.open('assets/campus-icon.png') as image:
    image.save('build/campus.icns', format='ICNS')
PY
signing=(--osx-entitlements-file "$PWD/config/macos-entitlements.plist")
if [[ -n "${MACOS_SIGNING_IDENTITY:-}" ]]; then
  signing+=(--codesign-identity "$MACOS_SIGNING_IDENTITY")
fi
.venv-build/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir \
  --paths "$PWD" --collect-all customtkinter --hidden-import pystray._darwin \
  --hidden-import keyring.backends.macOS --add-data "$PWD/assets:assets" \
  --icon "$PWD/build/campus.icns" --specpath build --distpath dist \
  --osx-bundle-identifier io.github.xtbreak.CampusConnect \
  "${signing[@]}" --name CampusConnect scripts/launch.py
APP=dist/CampusConnect.app
codesign --verify --deep --strict "$APP"
ARCH="$(.venv-build/bin/python -c 'import platform; print(platform.machine())')"
ZIP="dist/CampusConnect-macOS-${ARCH}.zip"
if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
  if [[ -z "${MACOS_SIGNING_IDENTITY:-}" ]]; then
    echo '公证需要 MACOS_SIGNING_IDENTITY。' >&2
    exit 1
  fi
  ditto -c -k --sequesterRsrc --keepParent "$APP" build/notarization.zip
  xcrun notarytool submit build/notarization.zip --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
  xcrun stapler staple "$APP"
  xcrun stapler validate "$APP"
  spctl --assess --type execute --verbose "$APP"
else
  echo '未执行 Apple 公证；此包适合测试，不能宣称已通过 Gatekeeper。'
fi
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
STAGING="$(mktemp -d "$PWD/build/dmg.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT
ditto "$APP" "$STAGING/CampusConnect.app"
ln -s /Applications "$STAGING/Applications"
DMG="dist/CampusConnect-macOS-${ARCH}.dmg"
hdiutil create -ov -volname CampusConnect -srcfolder "$STAGING" -format UDZO "$DMG"
if [[ -n "${MACOS_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --timestamp --sign "$MACOS_SIGNING_IDENTITY" "$DMG"
fi
if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
  xcrun notarytool submit "$DMG" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
  xcrun stapler validate "$DMG"
fi
(cd dist && shasum -a 256 "$(basename "$ZIP")" "$(basename "$DMG")" > "SHA256-macOS-${ARCH}.txt")
echo "已生成 ${APP}、${ZIP}、${DMG}"
