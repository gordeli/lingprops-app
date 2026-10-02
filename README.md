# lingprops-app

Two frontends for the [lingprops](https://github.com/gordeli/lingprops_test)
library — both compute WordNet-based **concreteness** and BWK
**tangibility** scores for the rows of an uploaded Excel file.

| Frontend | Where | Best for |
|---|---|---|
| **Web app** (Streamlit) | [https://lingprops.streamlit.app/](https://lingprops.streamlit.app/) | Anyone with a browser; share a link with collaborators |
| **Desktop app** (Windows .exe) | [Releases](https://github.com/gordeli/lingprops-app/releases) | Offline / sensitive-data workflows; no Python needed |

The two share the same scoring logic and UI; the desktop build excludes
the `wsd="neural"` strategy to keep the binary under 200 MB. See
[`desktop/`](./desktop/) for the build pipeline.

This is the user-facing frontend. The scoring methodology lives in the
[lingprops](https://github.com/gordeli/lingprops_test) library and is
documented in:

- Kronrod, A., Gordeliy, I., & Lee, J. K. (2023). *Been There, Done
  That: How Episodic and Semantic Memory Affects the Language of
  Authentic and Fictitious Reviews.* **Journal of Consumer Research**,
  50(2), 405–425. https://doi.org/10.1093/jcr/ucac056

---

## What the app outputs

For each row of the uploaded file, ten metrics. The **Output variables** page in the
web app (sidebar) and the **"What do the columns mean?"** button in the desktop app
explain each one, and every result file carries the same definitions on a
*Variable definitions* sheet plus the options used on a *Run settings* sheet.

| Column | Previous name | What it is |
|---|---|---|
| `concreteness_specificity_score` | `normalized_score_norep` | Concreteness as specificity: mean of log(d+1) over the text's unique content-word lemmas, where d is the number of distinct WordNet ancestors of the word's sense. Natural-log units, typically 1.6–2.4. Higher = more specific. |
| `concreteness_specificity_words` | `count_norep` | The number of words that made a **non-zero** contribution to the concreteness score — its denominator. Words with no WordNet noun sense are not counted. |
| `concreteness_tangibility_score` | `tang_normalized_score` | Mean human concreteness rating (Brysbaert, Warriner & Kuperman 2014), 1 = abstract to 5 = concrete, over content-word tokens **with** repetitions. |
| `concreteness_tangibility_words` | `tang_count` | The number of tokens found in the BWK list — the denominator of `concreteness_tangibility_score`. |
| `word_count` | *(unchanged)* | Total word tokens including function words. Neither score is divided by it. |
| `nouns_count` | `content_words_NN` | Noun tokens, with repetitions (NN, NNS, NNP, NNPS). |
| `verbs_count` | `content_words_VB` | Verb tokens, with repetitions (all VB*). |
| `adjectives_count` | `content_words_JJ` | Adjective tokens, with repetitions (JJ, JJR, JJS). |
| `adverbs_count` | `content_words_RB` | Adverb tokens, with repetitions (RB, RBR, RBS). |
| `numbers_count` | `content_words_CD` | Cardinal-number tokens, with repetitions (CD). |

> **Column names changed in October 2026.** Files produced earlier use the names in the
> middle column; the mapping above is also written into every new output file.

Note the deliberate asymmetry: concreteness counts each unique lemma once, tangibility
counts every token. The part-of-speech counts are counts of *candidates* for scoring, not
of scored words.

---

## Library options exposed in the sidebar

All match `lingprops.compute_concreteness` defaults:

| Option | Default | Other choices |
|---|---|---|
| WSD strategy   | `lesk`   | `first`, `neural` |
| Use NER        | on       | off  |
| NER backend    | `spacy`  | `nltk`, `auto` |

The sidebar also includes a sizing guide telling users when to switch
strategies based on dataset size (small / medium / large / very large /
reproducing prior published results).

---

## Run locally

```bash
git clone https://github.com/gordeli/lingprops-app.git
cd lingprops-app
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## Deploy to Streamlit Community Cloud

1. Push this repo to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, pick this repo, branch `main`, and entry point
   `streamlit_app.py`.
4. Click **Deploy**. First deploy takes ~5 min while spaCy/torch install.

Configuration files in this repo that Streamlit Cloud reads automatically:

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies (incl. spaCy model wheel and `lingprops` from GitHub) |
| `runtime.txt`      | Python version pin (`python-3.12`) |

### Resource notes

Streamlit Community Cloud's free tier provides ~1 GB RAM. Our deps
(numpy, scipy, spaCy + `en_core_web_sm`, torch CPU + sentence-transformers)
fit, but neural WSD is on the boundary for very large uploads. If the app
OOMs:

- Remove `sentence-transformers` from `requirements.txt` (drops ~250 MB
  for torch). Users will keep `wsd="first"` and `wsd="lesk"`; selecting
  `"neural"` will fail with a clear install hint.
- Or run locally instead.

---

## How to cite

If this app or the underlying library helps your research, please cite
the methodology paper and (optionally) the library. A `CITATION.cff`
file in this repo makes GitHub render a *"Cite this repository"* button
on the right-hand sidebar.

### APA

- Kronrod, A., Gordeliy, I., & Lee, J. K. (2023). *Been There, Done
  That: How Episodic and Semantic Memory Affects the Language of
  Authentic and Fictitious Reviews.* **Journal of Consumer Research**,
  50(2), 405–425. https://doi.org/10.1093/jcr/ucac056
- Kronrod, A., Lee, J. K., & Gordeliy, I. (2017). *Detecting fictitious
  consumer reviews: A theory-driven approach combining automated text
  analysis and experimental design.* **Marketing Science Institute
  Working Papers Series**, 17–124.

### BibTeX

```bibtex
@article{KronrodGordeliyLee2023JCR,
  author  = {Kronrod, Ann and Gordeliy, Ivan and Lee, Jeffrey K},
  title   = {Been There, Done That: How Episodic and Semantic Memory
             Affects the Language of Authentic and Fictitious Reviews},
  journal = {Journal of Consumer Research},
  year    = {2023},
  volume  = {50},
  number  = {2},
  pages   = {405--425},
  doi     = {10.1093/jcr/ucac056}
}

@techreport{KronrodLeeGordeliy2017MSI,
  author      = {Kronrod, Ann and Lee, Jeffrey K. and Gordeliy, Ivan},
  title       = {Detecting fictitious consumer reviews: A theory-driven
                 approach combining automated text analysis and
                 experimental design},
  institution = {Marketing Science Institute},
  type        = {Working Paper},
  number      = {17-124},
  year        = {2017}
}
```

### Underlying datasets and tools

The library (`lingprops`) builds on:

- **WordNet** (Miller, 1995; Fellbaum, 1998) — concreteness via hypernym depth
- **Brysbaert et al. (2014)** — BWK human-rated concreteness norms
  (~40 k words, 1–5 scale) used by the *tangibility* metric
- **NLTK** (Bird, Klein & Loper, 2009) — tokenisation, POS tagging,
  WordNet access, fallback NER
- **spaCy** (Honnibal & Montani, 2017) — default NER backend

---

## License

MIT — see `LICENSE`.
