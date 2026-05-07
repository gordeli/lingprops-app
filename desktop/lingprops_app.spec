# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the lingprops desktop app.

Builds a single-file Windows executable with the GUI bundled and the
spaCy `en_core_web_sm` model included.  NLTK data (~30 MB) downloads
on first run via `ensure_nltk_data()` so that the binary stays small.

Build:  python -m PyInstaller lingprops_app.spec --noconfirm
Output: dist/LingProps.exe

The `wsd="neural"` strategy (sentence-transformers + torch, ~250 MB)
is intentionally excluded to keep the binary under 200 MB.  Users
who need neural can either install the library via pip + run from
source, or use the Streamlit Cloud version.
"""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# --- Surgical data inclusion ------------------------------------------
# `collect_all('spacy')` and `collect_all('thinc')` wrongly pull torch
# DLLs (~250 MB) because thinc *can* use torch as a backend.  We grab
# only the data files we actually need.

# spaCy itself: data files (tokenizer rules, tagger weights bundled
# with the language pipelines), no binaries beyond what PyInstaller's
# built-in spacy hook discovers.
spacy_datas    = collect_data_files("spacy")
en_datas       = collect_data_files("en_core_web_sm")

# thinc data (config schemas etc), no binaries -- excludes torch DLLs.
thinc_datas    = collect_data_files("thinc")

# lingprops package data (Concreteness_ratings_Brysbaert_et_al_BRM.xls)
lingprops_datas = collect_data_files("lingprops")

datas = spacy_datas + en_datas + thinc_datas + lingprops_datas

# --- Hidden imports ----------------------------------------------------
hiddenimports = (
    collect_submodules("lingprops")
    + collect_submodules("nltk")
    + collect_submodules("en_core_web_sm")
    + [
        # spaCy language pipeline pieces sometimes imported lazily
        "spacy.lang.en",
        "spacy.pipeline._parser_internals",
        "spacy.pipeline._parser_internals.ner",
        "spacy.pipeline._parser_internals.arc_eager",
        "spacy.kb.candidate",
        "spacy.kb.kb_in_memory",
        # scipy hidden imports auto-detection sometimes misses
        "scipy._lib.array_api_compat.numpy.fft",
        "scipy.special._cdflib",
        "scipy.special.cython_special",
        # tkinter pieces that occasionally get dropped
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
    ]
)

# --- Excludes: heavy ML deps the desktop build does not use ------------
# This is the main mechanism keeping the binary under 200 MB.
excludes = [
    # Deep-learning frameworks (torch comes via thinc's optional backend)
    "torch", "torchvision", "torchaudio",
    "torch.distributed", "torch.testing",
    # NLP libs that follow torch in
    "sentence_transformers", "transformers", "tokenizers",
    # thinc backends that only matter if torch / mxnet / jax is installed
    "thinc.layers.pytorch_wrapper",
    "thinc.layers.mxnet_wrapper",
    "thinc.layers.tensorflow_wrapper",
    "thinc.shims.pytorch", "thinc.shims.mxnet", "thinc.shims.tensorflow",
    "thinc.backends.cupy_ops",
    # pandas pulls pyarrow which adds ~50 MB of arrow/parquet DLLs we
    # don't use (we read Excel via openpyxl, not Parquet)
    "pyarrow",
    # PIL is pulled by pandas/Streamlit transitively but not used here
    "PIL",
    # Other heavy ML stacks
    "tensorflow", "keras", "jax", "jaxlib",
    "matplotlib", "IPython", "jupyter", "notebook",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "pytest", "sphinx",
    # Linux-only stdlib bits (clean up the warn log)
    "pwd", "grp", "fcntl", "resource", "termios",
]

block_cipher = None

a = Analysis(
    ["lingprops_app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

# Final scrub: defensively drop bundled artefacts we know we don't need.
# `ensure_nltk_data()` handles first-run NLTK download, so the personal
# nltk_data tree pulled in by PyInstaller's NLTK hook is dead weight.
def _is_unwanted(item):
    name, src, _kind = item
    blob = (name + " " + (src or "")).lower()
    needles = (
        "\\torch\\", "/torch/",
        "nltk_data",                 # ~80 MB of corpora; downloaded on first run
        "\\pyarrow\\", "/pyarrow/",  # ~50 MB of arrow/parquet DLLs (excluded above too)
        "\\pil\\", "/pil/",          # imaging lib not used by this app
        "_cuda", "cudnn",            # GPU runtime stubs
    )
    return any(n in blob for n in needles)

a.binaries = [b for b in a.binaries if not _is_unwanted(b)]
a.datas    = [d for d in a.datas    if not _is_unwanted(d)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LingProps",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # set True if you have UPX installed for ~30% smaller exe
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,    # GUI app  -  no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="icon.ico",  # optional, drop a 256x256 ico next to this file
)
