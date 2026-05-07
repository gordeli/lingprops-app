# LingProps Desktop

Standalone Windows executable for the LingProps concreteness &
tangibility calculator. No Python install required for end users.

## For end users

Download `LingProps_Setup_vX.Y.Z.exe` from the
[Releases](https://github.com/gordeli/lingprops-app/releases) page,
double-click, follow the installer. Launch from the Start menu.

**First launch** downloads ~30 MB of NLTK data (WordNet, taggers,
tokenizers). Subsequent launches work fully offline.

The desktop build excludes the `wsd="neural"` strategy
(sentence-transformers + torch is ~250 MB and rarely needed). Selecting
"neural" from the WSD dropdown shows a clear install hint. For neural
WSD, use the [Streamlit Cloud version](https://lingprops.streamlit.app/)
instead, or install the library from PyPI in your own Python.

## For developers — building the installer

Prereqs (one-time on the build machine):

```bash
pip install pyinstaller pandas openpyxl xlrd spacy
pip install git+https://github.com/gordeli/lingprops_test.git
python -m spacy download en_core_web_sm
```

Plus [Inno Setup 6](https://jrsoftware.org/isdl.php) for the installer
step (optional — if absent, you still get a standalone `.exe`).

Build:

```bash
cd desktop
build.bat
```

`build.bat` runs:

1. **PyInstaller** — packs the GUI + dependencies + spaCy model into
   a single `dist\LingProps.exe` (~150–200 MB).
2. **Inno Setup** (if installed) — wraps that into
   `Output\LingProps_Setup_vX.Y.Z.exe` with Start-menu and optional
   desktop shortcuts and a proper uninstaller.

### Files in this folder

| File | Purpose |
|---|---|
| `lingprops_app.py`    | Tkinter GUI source (mirror of the App_v1_1 desktop app) |
| `lingprops_app.spec`  | PyInstaller config: data files, hidden imports, exclusions |
| `installer.iss`       | Inno Setup script: install paths, shortcuts, uninstaller |
| `build.bat`           | One-command orchestrator (clean → PyInstaller → Inno Setup) |

### Publishing a release

1. Tag the commit: `git tag vX.Y.Z && git push --tags`
2. On GitHub → **Releases** → **Draft a new release** → pick the tag.
3. Upload `desktop\Output\LingProps_Setup_vX.Y.Z.exe` as a release asset.
4. Publish.

The README's download link points at `/releases`, which auto-redirects
to the latest release.
