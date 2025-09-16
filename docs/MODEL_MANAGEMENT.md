# Model Management

Tools to list/select Sentence Transformers models and run A/B comparisons.

## List available models

```bash
python tools/model_select.py list
```

Shows models under `embeddinggemma_feasibility/models/` with metadata (path, size, embedding dimension if available, and any custom `contract_config.json` tags).

## Select active model

```bash
python tools/model_select.py set-active --path embeddinggemma_feasibility/models/st_custom_v1
python tools/model_select.py show-active
```

This updates a `models/current` symlink. The extractor also respects `embed_model_custom_path` if set via:

```python
from embeddinggemma_feasibility.config import update_config
update_config(embed_model_custom_path="embeddinggemma_feasibility/models/st_custom_v1")
```

To clear:

```bash
python tools/model_select.py clear-active
```

## Side‑by‑side comparison (A/B)

Run A/B using two prediction CSVs (recommended, avoids heavy live extraction):

```bash
python tools/ab_compare_cli.py --pred-a reports/runA.csv --pred-b reports/runB.csv --sample 20 --out datasets/preferences.jsonl
```

The CLI will show per‑field values for a random sample and ask you to pick A/B/Tie/Skip. Preferences save to `datasets/preferences.jsonl`.

Export preference pairs for Sentence Transformers training:

```bash
python tools/ab_compare_cli.py --export-pairs --out datasets/preferences.jsonl --pairs-out datasets/st_pairs_pref.jsonl
```

