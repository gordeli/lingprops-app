#!/usr/bin/env python3
"""LingProps Desktop App v1.1 - GUI for computing concreteness and tangibility.

Changes from v1.0:
  - Output trimmed: only normalised quantities and word counts are exposed
    (raw scores and per-POS scores are dropped).  POS word counts kept.
  - Library option controls: WSD strategy, NER on/off, NER backend.
    Defaults match `lingprops.compute_concreteness` defaults exactly:
        wsd          = "lesk"
        ner          = True
        ner_backend  = "spacy"

Launch:  python lingprops_app.py
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

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


# ---------------------------------------------------------------------------
# Metric registry  -  v1.1: normalised quantities + word counts only
# ---------------------------------------------------------------------------

METRIC_GROUPS = {
    "Concreteness (no repetitions)": [
        ("normalized_score_norep", "Concreteness normalized (norep)"),
        ("count_norep",            "Concreteness norm count (norep)"),
    ],
    "Tangibility BWK (with repetitions)": [
        ("tang_normalized_score", "Tangibility normalized"),
        ("tang_count",            "Tangibility BWK word count"),
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


# ---------------------------------------------------------------------------
# Per-row computation
# ---------------------------------------------------------------------------

def compute_row(text, *, wsd, ner, ner_backend):
    """Compute the v1.1 metric set for a single text.  Returns a flat dict.

    Only the metrics surfaced in METRIC_GROUPS are emitted:
    concreteness no-repetitions, tangibility with-repetitions, and word
    counts.  This matches the standard reporting convention used in the
    JCR 2023 paper and follow-up analyses.
    """
    from lingprops import compute_concreteness, compute_tangibility

    row = {}

    # Concreteness (parametrised by the UI's library options)
    r = compute_concreteness(
        text, wsd=wsd, ner=ner, ner_backend=ner_backend,
    )
    t = r["total"]
    row["normalized_score_norep"] = t["normalized_score_norep"]
    row["count_norep"]            = t["count_norep"]
    row["word_count"]             = t["word_count"]
    for pos in ("NN", "VB", "JJ", "RB", "CD"):
        row[f"content_words_{pos}"] = t["content_word_counts"][pos]

    # Tangibility (with-repetitions, the standard reporting convention)
    tr = compute_tangibility(text)
    tt = tr["total"]
    row["tang_normalized_score"]  = tt["normalized_score"]
    row["tang_count"]             = tt["count"]

    return row


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class LingPropsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LingProps v1.1 - Concreteness & Tangibility Calculator")
        self.root.geometry("780x780")
        self.root.resizable(True, True)

        # IO state
        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.text_column = tk.StringVar()
        self.columns: list[str] = []

        # Metric checkboxes
        self.metric_vars: dict[str, tk.BooleanVar] = {}

        # Library option state - defaults mirror lingprops library defaults
        self.wsd_var = tk.StringVar(value="lesk")
        self.ner_var = tk.BooleanVar(value=True)
        self.ner_backend_var = tk.StringVar(value="spacy")

        self._build_ui()

    # -- UI -----------------------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Input ---
        f_in = ttk.LabelFrame(self.root, text="Input")
        f_in.pack(fill="x", **pad)

        ttk.Label(f_in, text="Excel file:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(f_in, textvariable=self.input_path, width=55).grid(
            row=0, column=1, sticky="ew", **pad)
        ttk.Button(f_in, text="Browse...", command=self._browse_input).grid(
            row=0, column=2, **pad)

        ttk.Label(f_in, text="Text column:").grid(row=1, column=0, sticky="w", **pad)
        self.col_combo = ttk.Combobox(
            f_in, textvariable=self.text_column, state="readonly", width=40)
        self.col_combo.grid(row=1, column=1, sticky="w", **pad)
        f_in.columnconfigure(1, weight=1)

        # --- Library options ---
        f_opt = ttk.LabelFrame(self.root, text="Library options")
        f_opt.pack(fill="x", **pad)

        ttk.Label(f_opt, text="WSD strategy:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(f_opt, textvariable=self.wsd_var, state="readonly",
                     values=["first", "lesk", "neural"], width=12).grid(
            row=0, column=1, sticky="w", **pad)
        ttk.Label(f_opt, text="(default: lesk)").grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(f_opt, text="Use NER", variable=self.ner_var,
                        command=self._on_ner_toggle).grid(
            row=1, column=0, sticky="w", **pad)
        ttk.Label(f_opt, text="(default: on)").grid(row=1, column=2, sticky="w")

        ttk.Label(f_opt, text="NER backend:").grid(row=2, column=0, sticky="w", **pad)
        self.ner_backend_combo = ttk.Combobox(
            f_opt, textvariable=self.ner_backend_var, state="readonly",
            values=["spacy", "nltk", "auto"], width=12)
        self.ner_backend_combo.grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(f_opt, text="(default: spacy)").grid(row=2, column=2, sticky="w")

        # Sizing guide
        ttk.Label(
            f_opt,
            text=(
                "Tip: switch WSD to 'neural' for small datasets (< ~10k texts) "
                "for the highest accuracy.\n"
                "      Keep 'lesk' for medium datasets (10k - 1M texts).\n"
                "      Use 'first' (with NER off) only to reproduce numbers "
                "from prior publications,\n"
                "      or for very large jobs (> 100M texts) where speed "
                "dominates."
            ),
            foreground="#555", justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 6))

        # --- Metrics ---
        f_met = ttk.LabelFrame(self.root, text="Output metrics")
        f_met.pack(fill="both", expand=True, **pad)

        canvas = tk.Canvas(f_met, borderwidth=0, height=260)
        scrollbar = ttk.Scrollbar(f_met, orient="vertical", command=canvas.yview)
        self.metrics_frame = ttk.Frame(canvas)
        self.metrics_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.metrics_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row_i = 0
        for group_name, metrics in METRIC_GROUPS.items():
            ttk.Label(self.metrics_frame, text=group_name,
                      font=("", 9, "bold")).grid(
                row=row_i, column=0, columnspan=2, sticky="w",
                padx=4, pady=(8, 2))
            row_i += 1
            for key, desc in metrics:
                var = tk.BooleanVar(value=True)
                self.metric_vars[key] = var
                ttk.Checkbutton(self.metrics_frame, text=desc, variable=var
                                ).grid(row=row_i, column=0, sticky="w", padx=20)
                row_i += 1

        f_sel = ttk.Frame(f_met)
        f_sel.pack(fill="x", pady=2)
        ttk.Button(f_sel, text="Select all",
                   command=self._select_all).pack(side="left", padx=8)
        ttk.Button(f_sel, text="Deselect all",
                   command=self._deselect_all).pack(side="left", padx=4)

        # --- Output ---
        f_out = ttk.LabelFrame(self.root, text="Output")
        f_out.pack(fill="x", **pad)

        ttk.Label(f_out, text="Save as:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(f_out, textvariable=self.output_path, width=55).grid(
            row=0, column=1, sticky="ew", **pad)
        ttk.Button(f_out, text="Browse...", command=self._browse_output).grid(
            row=0, column=2, **pad)
        f_out.columnconfigure(1, weight=1)

        # --- Run row ---
        f_run = ttk.Frame(self.root)
        f_run.pack(fill="x", **pad)

        self.progress = ttk.Progressbar(f_run, mode="determinate")
        self.progress.pack(fill="x", side="left", expand=True, padx=(0, 8))

        self.status_label = ttk.Label(f_run, text="Ready")
        self.status_label.pack(side="left", padx=(0, 8))

        self.run_btn = ttk.Button(f_run, text="Run", command=self._run)
        self.run_btn.pack(side="right")

        self._on_ner_toggle()

    # -- Callbacks ----------------------------------------------------------

    def _on_ner_toggle(self):
        state = "readonly" if self.ner_var.get() else "disabled"
        self.ner_backend_combo.configure(state=state)

    def _browse_input(self):
        path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")])
        if path:
            self.input_path.set(path)
            self._load_columns(path)

    def _load_columns(self, path):
        try:
            import pandas as pd
            df = pd.read_excel(path, nrows=0)
            self.columns = list(df.columns)
            self.col_combo["values"] = self.columns
            if self.columns:
                for c in self.columns:
                    if "text" in c.lower() or "review" in c.lower():
                        self.text_column.set(c)
                        break
                else:
                    self.text_column.set(self.columns[0])
            base = Path(path)
            self.output_path.set(
                str(base.parent / (base.stem + "_lingprops" + base.suffix)))
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{e}")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if path:
            self.output_path.set(path)

    def _select_all(self):
        for v in self.metric_vars.values(): v.set(True)

    def _deselect_all(self):
        for v in self.metric_vars.values(): v.set(False)

    def _run(self):
        if not self.input_path.get():
            messagebox.showwarning("Missing input", "Please select an input file.")
            return
        if not self.text_column.get():
            messagebox.showwarning("Missing column", "Please select the text column.")
            return
        if not self.output_path.get():
            messagebox.showwarning("Missing output", "Please specify an output file.")
            return
        selected = [k for k, v in self.metric_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No metrics", "Please select at least one metric.")
            return

        self.run_btn.config(state="disabled")
        self.status_label.config(text="Initialising...")
        self.progress["value"] = 0

        threading.Thread(target=self._process, args=(selected,), daemon=True).start()

    def _process(self, selected_keys):
        try:
            import pandas as pd
            from lingprops import ensure_nltk_data

            wsd = self.wsd_var.get()
            ner = bool(self.ner_var.get())
            ner_backend = self.ner_backend_var.get()

            self._update_status("Downloading NLTK data (if needed)...")
            ensure_nltk_data()

            if ner and ner_backend in ("spacy", "auto"):
                self._update_status("Ensuring spaCy model...")
                try:
                    from lingprops import ensure_spacy_model
                    ensure_spacy_model()
                except Exception as e:
                    if ner_backend == "spacy":
                        raise
                    # auto -> let the backend fall through to NLTK
                    self._update_status(f"spaCy unavailable ({e}); falling back to NLTK")

            self._update_status("Warming up...")
            from lingprops import compute_concreteness
            compute_concreteness("warmup", wsd=wsd, ner=ner, ner_backend=ner_backend)

            self._update_status("Loading Excel file...")
            df = pd.read_excel(self.input_path.get())
            col = self.text_column.get()
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
                    self._update_progress(int((i + 1) / n * 100),
                                          f"Processing {i+1}/{n}...")

            result_df = pd.DataFrame(rows)
            out = pd.concat([df, result_df], axis=1)
            out.to_excel(self.output_path.get(), index=False, engine="openpyxl")

            self._update_status(f"Done! {n} rows saved.")
            self.root.after(0, lambda: messagebox.showinfo(
                "Complete",
                f"Processed {n} rows.\nSaved to:\n{self.output_path.get()}"))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda err=err: messagebox.showerror("Error", err))
            self._update_status("Error")
        finally:
            self.root.after(0, lambda: self.run_btn.config(state="normal"))

    def _update_status(self, msg):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def _update_progress(self, pct, msg):
        self.root.after(0, lambda: self.progress.configure(value=pct))
        self.root.after(0, lambda: self.status_label.config(text=msg))


def main():
    root = tk.Tk()
    LingPropsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
