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
    "Concreteness as specificity (no repetitions)": [
        ("concreteness_specificity_score", "Score"),
        ("concreteness_specificity_words", "Words used"),
    ],
    "Concreteness as tangibility, BWK (with repetitions)": [
        ("concreteness_tangibility_score", "Score"),
        ("concreteness_tangibility_words", "Words used"),
    ],
    "Word counts": [
        ("word_count",       "Total words"),
        ("nouns_count",       "Nouns"),
        ("verbs_count",       "Verbs"),
        ("adjectives_count",  "Adjectives"),
        ("adverbs_count",     "Adverbs"),
        ("numbers_count",     "Cardinal numbers"),
    ],
}


# Keep this block in sync between streamlit_app.py and desktop/lingprops_app.py
# ---------------------------------------------------------------------------


VARIABLE_DEFS = [   # (column, previous name, group, units, definition)
    ("concreteness_specificity_score", "normalized_score_norep", "Specificity", "nats (natural-log units); typically 1.6-2.4",
     "Concreteness as specificity. Each content word (noun, verb, adjective, adverb, cardinal "
     "number) is mapped to a WordNet noun sense; d is the number of distinct ancestors "
     "(hypernyms) of that sense, and the word contributes log(d + 1). The score is the mean of "
     "those contributions over the text's UNIQUE word lemmas - each lemma counted once, within "
     "its part of speech. Higher = more specific (words sitting lower in the WordNet hierarchy). "
     "Divided by concreteness_specificity_words, NOT by word_count."),

    ("concreteness_specificity_words", "count_norep", "Specificity", "count of unique lemmas",
     "The number of words that made a NON-ZERO contribution to the concreteness score - that "
     "is, the denominator of concreteness_specificity_score. A content word contributes nothing, "
     "and is not counted here, if WordNet has no noun sense for it after lemmatisation and NER "
     "substitution (brand names, slang, typos, neologisms), if the lemma is shorter than two "
     "characters, or if it is on the exclusion list. The one word at depth 0 - 'entity', the "
     "root of the WordNet noun hierarchy - does count, contributing zero. Each lemma counts at "
     "most once. Always smaller than or equal "
     "to the sum of the part-of-speech counts below. The tangibility score has its "
     "own, separate count: concreteness_tangibility_words."),

    ("concreteness_tangibility_score", "tang_normalized_score", "Tangibility", "1 (abstract) to 5 (concrete)",
     "Tangibility: the mean human concreteness rating of the text's content words, taken from "
     "Brysbaert, Warriner & Kuperman (2014), who collected ratings for 40,000 English lemmas on "
     "a 1-5 scale. Counted WITH repetitions - every token counts. Words absent from the BWK list "
     "are ignored."),

    ("concreteness_tangibility_words", "tang_count", "Tangibility", "count of tokens",
     "The number of words used to compute concreteness_tangibility_score: content-word tokens found in the "
     "Brysbaert et al. list. Counted WITH repetitions, so it is not the same thing as "
     "concreteness_specificity_words, the unique-lemma count behind the specificity score."),

    ("word_count", "word_count (unchanged)", "Word counts", "count of tokens",
     "Total number of word tokens in the text, including function words (the, of, and ...). "
     "Reported for reference only: neither score is divided by it."),

    ("nouns_count", "content_words_NN", "Word counts", "count of tokens",
     "Noun tokens, with repetitions (Penn Treebank tags NN, NNS, NNP, NNPS)."),

    ("verbs_count", "content_words_VB", "Word counts", "count of tokens",
     "Verb tokens, with repetitions (all VB* tags)."),

    ("adjectives_count", "content_words_JJ", "Word counts", "count of tokens",
     "Adjective tokens, with repetitions (JJ, JJR, JJS)."),

    ("adverbs_count", "content_words_RB", "Word counts", "count of tokens",
     "Adverb tokens, with repetitions (RB, RBR, RBS)."),

    ("numbers_count", "content_words_CD", "Word counts", "count of tokens",
     "Cardinal-number tokens, with repetitions (CD) - for example 'three', '2019'."),
]

VARIABLE_NOTES = [
    "The two scores are built differently on purpose: concreteness counts each unique lemma "
    "once (no repetitions), tangibility counts every token (with repetitions).",
    "The two scores are on different scales (log depth vs a 1-5 rating) and should not be "
    "compared in absolute value - only across texts, within one measure.",
    "The part-of-speech counts are counts of CANDIDATES for scoring, not of scored words: a "
    "word counted there can still be unscored if it has no WordNet sense.",
    "Settings change the numbers. The word-sense disambiguation strategy and named-entity "
    "recognition both affect concreteness_specificity_score; the run settings are recorded on "
    "the 'Run settings' sheet of every output file.",
    "Very short texts give unstable scores, because the mean is taken over few words. Treat "
    "texts with fewer than about 30 scored words with caution.",
    "Reference: Kronrod, A., Gordeliy, I., & Lee, J. K. (2023). Been There, Done That. "
    "Journal of Consumer Research, 50(2), 405-425. Brysbaert, M., Warriner, A. B., & Kuperman, "
    "V. (2014). Concreteness ratings for 40 thousand generally known English word lemmas. "
    "Behavior Research Methods, 46(3), 904-911.",
]


def compute_row(text, *, wsd, ner, ner_backend):
    """Emit only the standard reporting set: concreteness (no-rep),
    tangibility (with-rep), and word counts."""
    from lingprops import compute_concreteness, compute_tangibility

    row = {}
    r = compute_concreteness(text, wsd=wsd, ner=ner, ner_backend=ner_backend)
    t = r["total"]
    row["concreteness_specificity_score"] = t["normalized_score_norep"]
    row["concreteness_specificity_words"] = t["count_norep"]
    row["word_count"]                     = t["word_count"]
    for pos, name in (("NN", "nouns"), ("VB", "verbs"), ("JJ", "adjectives"),
                      ("RB", "adverbs"), ("CD", "numbers")):
        row[f"{name}_count"] = t["content_word_counts"][pos]

    tr = compute_tangibility(text)
    tt = tr["total"]
    row["concreteness_tangibility_score"] = tt["normalized_score"]
    row["concreteness_tangibility_words"] = tt["count"]
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

# --- Page selector ---------------------------------------------------------
PAGE_CALC, PAGE_VARS = "Calculator", "Output variables"
page = st.sidebar.radio("Page", [PAGE_CALC, PAGE_VARS], index=0)


def render_variable_page():
    """Information page: what every column of the output file means."""
    st.header("Output variables")
    st.markdown(
        "Every column the app adds to your file, what it means, and what it is "
        "measured in. The same table is written to a **Variable definitions** "
        "sheet inside each result file, next to a **Run settings** sheet that "
        "records the options used."
    )
    for group in ("Specificity", "Tangibility", "Word counts"):
        st.subheader(group)
        for col, old, grp, units, text in VARIABLE_DEFS:
            if grp != group:
                continue
            st.markdown(f"**`{col}`** — *{units}*")
            st.markdown(text)
            st.caption(f"Called `{old}` in files produced before October 2026.")
            st.markdown("")
    st.subheader("Things worth knowing")
    for note in VARIABLE_NOTES:
        st.markdown(f"- {note}")


if page == PAGE_VARS:
    render_variable_page()
    st.stop()

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
        "Source: [lingprops-app](https://github.com/gordeli/lingprops-app) | "
        "Library: [lingprops](https://github.com/gordeli/lingprops_test) "
        "(pinned to v1.2.0)"
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

        st.caption(
            "Not sure what a column means? See the **Output variables** page "
            "in the sidebar — the same definitions are included in the file."
        )

        defs_df = pd.DataFrame(
            [(c, old, grp, units, text) for c, old, grp, units, text in VARIABLE_DEFS],
            columns=["column", "previous name (before Oct 2026)", "group",
                     "units / range", "definition"],
        )
        notes_df = pd.DataFrame({"note": VARIABLE_NOTES})
        try:
            from importlib.metadata import version as _pkg_version
            _lib_version = _pkg_version("lingprops")
        except Exception:
            _lib_version = "unknown"
        settings_df = pd.DataFrame(
            [("app", "LingProps web app"),
             ("lingprops version", _lib_version),
             ("run (UTC)", pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M")),
             ("text column", str(col)),
             ("rows processed", str(len(df))),
             ("WSD strategy", str(wsd)),
             ("NER", "on" if ner else "off"),
             ("NER backend", str(ner_backend) if ner else "n/a")],
            columns=["setting", "value"],
        )

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as _xl:
            out.to_excel(_xl, index=False, sheet_name="Results")
            defs_df.to_excel(_xl, index=False, sheet_name="Variable definitions")
            notes_df.to_excel(_xl, index=False, sheet_name="Notes")
            settings_df.to_excel(_xl, index=False, sheet_name="Run settings")
        buf.seek(0)
        st.download_button(
            label="Download Results (Excel)",
            data=buf,
            file_name="lingprops_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
