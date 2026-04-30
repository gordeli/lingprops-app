#!/usr/bin/env python3
"""LingProps Web App - Concreteness & Tangibility Calculator.

Streamlit web frontend for the `lingprops` library
(https://github.com/gordeli/lingprops_test).

Deploy: push to GitHub, connect to share.streamlit.io.
Local:  streamlit run streamlit_app.py
"""
from __future__ import annotations

# --- Suppress noisy third-party output BEFORE any heavy imports ---
import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import logging
for _name in ("transformers", "huggingface_hub", "sentence_transformers"):
    logging.getLogger(_name).setLevel(logging.ERROR)

import warnings
warnings.filterwarnings("ignore")

import io

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="LingProps - Concreteness & Tangibility",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Metric registry  -  normalised quantities + word counts
# ---------------------------------------------------------------------------

METRIC_GROUPS = {
    "Concreteness (no repetitions)": [
        ("normalized_score_norep", "Normalized (norep)"),
        ("count_norep",            "Norm count (norep)"),
    ],
    "Tangibility BWK (with repetitions)": [
        ("tang_normalized_score", "Normalized"),
        ("tang_count",            "BWK word count"),
    ],
    "Word counts": [
        ("word_count",        "Total word count"),
        ("content_words_NN",  "Noun count"),
        ("content_words_VB",  "Verb count"),
        ("content_words_JJ",  "Adjective count"),
        ("content_words_RB",  "Adverb count"),
        ("content_words_CD",  "Cardinal-number count"),
    ],
}


def compute_row(text, *, wsd, ner, ner_backend):
    """Emit only the standard reporting set: concreteness (no-rep),
    tangibility (with-rep), and word counts."""
    from lingprops import compute_concreteness, compute_tangibility

    row = {}
    r = compute_concreteness(text, wsd=wsd, ner=ner, ner_backend=ner_backend)
    t = r["total"]
    row["normalized_score_norep"] = t["normalized_score_norep"]
    row["count_norep"]            = t["count_norep"]
    row["word_count"]             = t["word_count"]
    for pos in ("NN", "VB", "JJ", "RB", "CD"):
        row[f"content_words_{pos}"] = t["content_word_counts"][pos]

    tr = compute_tangibility(text)
    tt = tr["total"]
    row["tang_normalized_score"] = tt["normalized_score"]
    row["tang_count"]            = tt["count"]
    return row


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("LingProps - Concreteness & Tangibility Calculator")
st.markdown(
    "Upload an Excel file with text data. The app computes WordNet-based "
    "concreteness and BWK tangibility scores for each row.  "
    "Built on the [lingprops](https://github.com/gordeli/lingprops_test) "
    "library (Kronrod, Gordeliy & Lee 2023, *Journal of Consumer Research*)."
)

# --- Library options (sidebar) ---------------------------------------------
with st.sidebar:
    st.header("Library options")
    st.caption("Defaults match `lingprops.compute_concreteness` defaults.")
    wsd = st.selectbox(
        "WSD strategy",
        options=["first", "lesk", "neural"],
        index=1,  # 'lesk' is the library default
        help="`lesk` (default) uses gloss-overlap with MFS fallback - "
             "context-aware at ~2x the cost of `first`. `first` reproduces "
             "the original library behaviour and is fastest. `neural` uses "
             "a sentence-transformer and is the most accurate.",
    )
    ner = st.checkbox(
        "Use NER",
        value=True,
        help="Substitute proper nouns not in WordNet (e.g. 'Alice') with "
             "the lemma of their entity category before computing depth.",
    )
    ner_backend = st.selectbox(
        "NER backend",
        options=["spacy", "nltk", "auto"],
        index=0,
        disabled=not ner,
        help="`spacy` (default, recommended) is ~13x faster and ~40 F1 "
             "points more accurate than `nltk`. `auto` falls back to NLTK "
             "if the spaCy model is not installed.",
    )

    st.markdown("---")
    st.markdown("**Choosing parameters by dataset size**")
    st.caption(
        "- **< 10k texts** (small) - try `wsd=neural` for the highest "
        "accuracy; the ~100x CPU cost (~3-4 min for 10k) is usually fine.\n"
        "- **10k - 1M texts** (medium) - keep `wsd=lesk` (the default); "
        "context-aware and fast.\n"
        "- **1M - 100M texts** (large) - keep `wsd=lesk`; consider "
        "`ner_backend=nltk` only if spaCy is unavailable.\n"
        "- **> 100M texts** (very large) - `wsd=first` saves time when "
        "the synset pick matters less than throughput.\n"
        "- **Reproducing prior published results** - use `wsd=first` and "
        "uncheck *Use NER*."
    )

    st.markdown("---")
    st.caption(
        "Source: [lingprops-app](https://github.com/) | "
        "Library: [lingprops](https://github.com/gordeli/lingprops_test)"
    )

# --- Upload ----------------------------------------------------------------
uploaded = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

if uploaded is not None:
    df = pd.read_excel(uploaded)
    st.success(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    col = st.selectbox(
        "Select the text column",
        options=df.columns.tolist(),
        index=next(
            (i for i, c in enumerate(df.columns)
             if "text" in c.lower() or "review" in c.lower()),
            0,
        ),
    )

    st.subheader("Preview")
    st.dataframe(df[[col]].head(5), use_container_width=True)

    # --- Metric selection ---
    st.subheader("Select output metrics")
    selected_keys: list[str] = []
    cols_ui = st.columns(3)
    for gi, (group_name, metrics) in enumerate(METRIC_GROUPS.items()):
        with cols_ui[gi % 3]:
            st.markdown(f"**{group_name}**")
            for key, desc in metrics:
                if st.checkbox(desc, value=True, key=f"cb_{key}"):
                    selected_keys.append(key)

    # --- Run ---
    if st.button("Run", type="primary", disabled=len(selected_keys) == 0):
        from lingprops import ensure_nltk_data

        progress = st.progress(0, text="Initialising...")

        ensure_nltk_data()

        if ner and ner_backend in ("spacy", "auto"):
            try:
                from lingprops import ensure_spacy_model
                ensure_spacy_model()
            except Exception as e:
                if ner_backend == "spacy":
                    st.error(f"spaCy model unavailable: {e}")
                    st.stop()
                st.warning(f"spaCy unavailable; using NLTK fallback ({e}).")

        from lingprops import compute_concreteness
        compute_concreteness("warmup", wsd=wsd, ner=ner, ner_backend=ner_backend)

        n = len(df)
        rows = []
        for i, text in enumerate(df[col]):
            if pd.isna(text) or str(text).strip() == "":
                rows.append({k: None for k in selected_keys})
            else:
                full = compute_row(str(text), wsd=wsd, ner=ner,
                                   ner_backend=ner_backend)
                rows.append({k: full.get(k) for k in selected_keys})

            if (i + 1) % max(1, n // 100) == 0 or i == n - 1:
                progress.progress((i + 1) / n,
                                  text=f"Processing {i+1}/{n}...")

        progress.progress(1.0, text="Done!")

        result_df = pd.DataFrame(rows)
        out = pd.concat([df, result_df], axis=1)

        st.subheader("Results")
        st.dataframe(out.head(20), use_container_width=True)

        buf = io.BytesIO()
        out.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button(
            label="Download Results (Excel)",
            data=buf,
            file_name="lingprops_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
