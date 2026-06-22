# Double-Click App Packaging — Design Spec

**Date:** 2026-06-23
**Project folder:** `remote/`
**Builds on:** DeskBridge (Python/Tkinter package, entry `deskbridge.app:main`)

## 1. Goal

Produce double-click apps for DeskBridge — `DeskBridge.app` on macOS and
`DeskBridge.exe` on Windows — so users don't need Python or `pip`. Builds run
natively per OS in GitHub Actions: downloadable artifacts on every push to `main`,
and attached to a GitHub Release on version tags.

### Success criteria

- `pyinstaller DeskBridge.spec` on macOS produces a launchable `dist/DeskBridge.app`.
- The same spec on Windows produces `dist/DeskBridge.exe` (verified via CI).
- Pushing to `main` yields downloadable `DeskBridge-macos.zip` and
  `DeskBridge-windows.zip` artifacts.
- Pushing a `v*` tag publishes a GitHub Release with both zips attached.

### Non-goals (YAGNI)

- No code signing / notarization (no certificates) — apps are unsigned.
- No installer / DMG / MSI — just the app/exe in a zip.
- No auto-update.

## 2. Components

### 2a. `packaging/entry.py` (new)

A minimal launcher PyInstaller bundles as the program entry:

```python
from deskbridge.app import main

main()
```

### 2b. `DeskBridge.spec` (new)

PyInstaller build config, cross-platform:
- `Analysis(['packaging/entry.py'], pathex=['src'], …)` so the bundled program can
  import the `deskbridge` package from `src/` without installation.
- Windowed / no console (`console=False`) — it's a GUI app.
- Output name `DeskBridge`.
- On macOS, a `BUNDLE(...)` step (guarded by `sys.platform == 'darwin'`) emits
  `DeskBridge.app` with bundle identifier `org.deskbridge.app`.
- Tkinter is detected automatically by PyInstaller; no hidden-import config needed.

### 2c. `.github/workflows/build.yml` (new)

- **Triggers:** `push` to `main`, and `push` of tags matching `v*`.
- **build job** — matrix over `macos-latest` and `windows-latest`:
  1. `actions/checkout`
  2. `actions/setup-python` (3.12)
  3. `pip install pyinstaller`
  4. `pyinstaller --noconfirm DeskBridge.spec`
  5. Zip the output: macOS → `DeskBridge-macos.zip` (the `.app`);
     Windows → `DeskBridge-windows.zip` (the `.exe`).
  6. `actions/upload-artifact` with the zip.
- **release job** — runs only when the ref is a `v*` tag; `needs: build`:
  1. `actions/download-artifact` (both zips)
  2. `softprops/action-gh-release` to create/update the Release with the zips
     attached. Uses the default `GITHUB_TOKEN` (needs `contents: write`
     permission on the job).

### 2d. `README.md` (modify)

Add a "Download / Build" section:
- Grab the prebuilt app from the latest Actions run (artifacts) or a Release.
- Build locally: `pip install pyinstaller && pyinstaller DeskBridge.spec`
  → `dist/DeskBridge.app` (macOS) or `dist/DeskBridge.exe` (Windows).
- **Gatekeeper / SmartScreen note:** the apps are unsigned, so the first launch
  needs macOS right-click → **Open** (then **Open** again), or Windows
  **More info → Run anyway**.

## 3. Build flow

```
push to main ─▶ build job (mac + windows in parallel) ─▶ upload zip artifacts
push v* tag  ─▶ build job ─▶ release job ─▶ GitHub Release with both zips
```

## 4. Error handling / risks

- **Tkinter bundling:** PyInstaller bundles the Tcl/Tk that ships with the build
  Python. Mitigation: the local macOS build (below) proves the `.app` launches; if
  Tk data is missing, add it via the spec — but the default is expected to work.
- **Windows build** can't be validated locally (no Windows host); it is validated
  by the first CI run. The spec is written to be OS-neutral to minimize risk.
- **Release permissions:** the release job declares `permissions: contents: write`.

## 5. Verification

- **Local (this Mac):** `pip install pyinstaller`, run `pyinstaller DeskBridge.spec`,
  confirm `dist/DeskBridge.app` exists and its binary
  (`dist/DeskBridge.app/Contents/MacOS/DeskBridge`) launches without import errors
  (smoke-launch headless / `--version`-style check, then terminate).
- **CI:** confirmed by the first workflow run producing both artifacts (and a
  Release on a tag). Documented as a manual post-merge check.
- Existing unit tests remain green (packaging adds no runtime code paths).

## 6. Build artifacts hygiene

`.gitignore` already excludes `build/` and `dist/`; add PyInstaller's `*.spec`?
No — the spec is intentionally committed. Ensure `build/` and `dist/` stay ignored.
