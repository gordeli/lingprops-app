# lingprops-app

Streamlit web app for the [lingprops](https://github.com/gordeli/lingprops_test)
library — computes WordNet-based **concreteness** and BWK **tangibility**
scores for the rows of an uploaded Excel file.

> **Live demo:** *(URL goes here once deployed to Streamlit Community Cloud)*

This is the user-facing frontend. The scoring methodology lives in the
[lingprops](https://github.com/gordeli/lingprops_test) library and is
documented in:

- Kronrod, A., Gordeliy, I., & Lee, J. K. (2023). *Been There, Done
  That: How Episodic and Semantic Memory Affects the Language of
  Authentic and Fictitious Reviews.* **Journal of Consumer Research**,
  50(2), 405–425. https://doi.org/10.1093/jcr/ucac056

---

## What the app outputs

For each row of the uploaded file, ten metrics:

| Group | Metric | Meaning |
|---|---|---|
| **Concreteness** (no repetitions) | `normalized_score_norep` | WordNet hypernym-depth concreteness, averaged over unique noun lemmas |
|                                    | `count_norep`            | Number of unique noun lemmas the score is based on |
| **Tangibility BWK** (with repetitions) | `tang_normalized_score` | Brysbaert et al. (2014) human-rated concreteness, averaged over tokens |
|                                         | `tang_count`            | Number of tokens covered by the BWK lexicon |
| **Word counts**                    | `word_count`             | Total words in the text |
|                                    | `content_words_NN`       | Noun token count |
|                                    | `content_words_VB`       | Verb token count |
|                                    | `content_words_JJ`       | Adjective token count |
|                                    | `content_words_RB`       | Adverb token count |
|                                    | `content_words_CD`       | Cardinal-number token count |

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
git clone https://github.com/<your-user>/lingprops-app.git
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

## License

MIT — see `LICENSE`.
