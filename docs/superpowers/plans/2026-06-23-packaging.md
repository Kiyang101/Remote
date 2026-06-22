# Double-Click App Packaging — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build `DeskBridge.app` (macOS) and `DeskBridge.exe` (Windows) with PyInstaller, driven by a GitHub Actions workflow that uploads artifacts on every push to `main` and attaches them to a Release on `v*` tags.

**Architecture:** A tiny `packaging/entry.py` launcher + a committed `DeskBridge.spec` produce a windowed app per OS. A matrix CI workflow builds natively on macOS and Windows runners, zips the output, uploads artifacts, and (on tags) publishes a Release.

**Tech Stack:** PyInstaller, GitHub Actions (`setup-python`, `upload-artifact`, `download-artifact`, `softprops/action-gh-release`).

---

## File Structure

```
remote/packaging/entry.py              # new: PyInstaller entry launcher
remote/DeskBridge.spec                  # new: PyInstaller build config (committed)
remote/.github/workflows/build.yml      # new: CI matrix build + release
remote/README.md                        # modify: Download / Build section
remote/.gitignore                       # verify: build/ and dist/ ignored
```

---

### Task 1: Entry launcher + PyInstaller spec, verified by a local macOS build

**Files:**
- Create: `remote/packaging/entry.py`
- Create: `remote/DeskBridge.spec`

- [ ] **Step 1: Write the entry launcher**

`packaging/entry.py`:

```python
"""PyInstaller entry point: launch the DeskBridge GUI."""

from deskbridge.app import main

main()
```

- [ ] **Step 2: Write `DeskBridge.spec`**

Hand-written, cross-platform (guarded macOS `BUNDLE`). Analysis points at the
entry script with `pathex=['src']` so the bundled program imports `deskbridge`.
Console disabled (GUI app). The exact `EXE`/`BUNDLE` argument list must match the
installed PyInstaller version — validate in Step 4 and adjust if the API differs.
Intended content:

```python
# -*- mode: python ; coding: utf-8 -*-
import sys

a = Analysis(
    ['packaging/entry.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DeskBridge',
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='DeskBridge.app',
        icon=None,
        bundle_identifier='org.deskbridge.app',
    )
```

- [ ] **Step 3: Install PyInstaller and build locally**

Run:
```bash
cd remote
python3 -m pip install pyinstaller
python3 -m PyInstaller --noconfirm DeskBridge.spec
```
Expected: a `dist/DeskBridge.app` is produced (macOS).

- [ ] **Step 4: Verify the app launches (and fix spec API if the build failed)**

If Step 3 errored on the `EXE`/`BUNDLE` signature, adjust to the installed
version's API and rebuild until it succeeds. Then smoke-launch the bundled binary
headlessly and confirm no import error:
```bash
cd remote
DISPLAY= ./dist/DeskBridge.app/Contents/MacOS/DeskBridge &
sleep 3; kill %1 2>/dev/null || true
```
Expected: the binary starts (a window opens / process stays up) without a Python
traceback. Acceptable alternative: run it briefly and confirm it does not exit
immediately with an ImportError.

- [ ] **Step 5: Commit (spec + entry only — not build output)**

```bash
cd remote
git add packaging/entry.py DeskBridge.spec
git commit -m "build: add PyInstaller entry and spec for DeskBridge app"
```

---

### Task 2: GitHub Actions build + release workflow

**Files:**
- Create: `remote/.github/workflows/build.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Build apps

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-latest
            artifact: DeskBridge-macos
          - os: windows-latest
            artifact: DeskBridge-windows
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python -m pip install pyinstaller
      - run: python -m PyInstaller --noconfirm DeskBridge.spec

      - name: Package (macOS)
        if: runner.os == 'macOS'
        run: cd dist && zip -r ../${{ matrix.artifact }}.zip DeskBridge.app

      - name: Package (Windows)
        if: runner.os == 'Windows'
        run: Compress-Archive -Path dist/DeskBridge.exe -DestinationPath ${{ matrix.artifact }}.zip

      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: ${{ matrix.artifact }}.zip

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts
      - uses: softprops/action-gh-release@v2
        with:
          files: artifacts/**/*.zip
```

Note: the Windows build produces `dist/DeskBridge.exe` only if PyInstaller is
producing a one-file exe. If the installed PyInstaller produces a one-dir layout
(`dist/DeskBridge/DeskBridge.exe`), the Windows packaging step and the macOS spec
must agree on layout — keep the spec one-file (the `EXE` includes binaries/datas,
no `COLLECT`), which yields `dist/DeskBridge.exe` on Windows and a one-file binary
inside `DeskBridge.app` on macOS. Confirm via Task 1's local build that no
`COLLECT`/one-dir output appears.

- [ ] **Step 2: Lint the YAML locally**

Run: `cd remote && python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/build.yml')); print('yaml OK')"`
Expected: `yaml OK` (install pyyaml if needed: `python3 -m pip install pyyaml`).

- [ ] **Step 3: Commit**

```bash
cd remote
git add .github/workflows/build.yml
git commit -m "ci: build DeskBridge app/exe and release on tags"
```

---

### Task 3: README Download/Build section + gitignore check

**Files:**
- Modify: `remote/README.md`
- Verify: `remote/.gitignore`

- [ ] **Step 1: Confirm build artifacts are ignored**

Run: `cd remote && grep -E 'build/|dist/' .gitignore`
Expected: both present (they are, from v1). If `dist/` is missing, add it.

- [ ] **Step 2: Add a "Download / Build the app" section to README**

Cover: download the prebuilt app from the latest Actions run or a Release; build
locally with `pip install pyinstaller && pyinstaller DeskBridge.spec`; and the
Gatekeeper/SmartScreen note (unsigned → macOS right-click **Open**; Windows
**More info → Run anyway**).

- [ ] **Step 3: Commit**

```bash
cd remote
git add README.md .gitignore
git commit -m "docs: document downloading and building the double-click app"
```

---

## Self-Review Notes

- **Spec coverage:** entry + spec producing app/exe (Task 1); CI artifacts on push
  + Release on tag (Task 2); docs incl. Gatekeeper note (Task 3); unsigned/no
  installer scope respected.
- **Risk handling:** local macOS build validates the spec/entry and Tkinter
  bundling before merge; Windows validated by first CI run; one-file layout chosen
  so `dist/` paths are predictable on both OSes.
- **Placeholders:** the spec's exact PyInstaller API is validated/adjusted in Task 1
  Step 4 rather than assumed — explicitly called out, not left vague.
