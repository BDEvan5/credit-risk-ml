# autoresearch — credit-risk-ml

This document adapts the [autoresearch](https://github.com/karpathy/autoresearch/blob/master/program.md) loop to this repository: an **autonomous agent** iterates on **features and training** to improve the **test-set ROC-AUC** on the Home Credit Default Risk task, using `src/train.py` as the single entrypoint and logging results for scripted parsing.

**Primary metric (maximize):** `roc_auc` on the **held-out test split** produced inside `train()` (same stratified `train_test_split` as today). **Higher is better.**

---

## Setup

Work with the user (or self-check) before the experiment loop:

1. **Agree on a run tag** — e.g. `apr13` from today’s date. Use a dedicated branch name like `autoresearch/apr13` (must not already exist if this is a fresh run).
2. **Create the branch** — from your main branch:  
   `git checkout -b autoresearch/apr13`
3. **Read in-scope files** for full context:
   - `README.md` — data layout, DuckDB load, project aim.
   - `PROGRAM.md` — this file.
   - `src/train.py` — training config, pipeline, MLflow logging, **summary block** for agents.
   - `src/features.py` — how `sql/features/*.sql` results merge onto `application_train`.
   - `sql/features/*.sql` — applicant-level aggregates (bureau, previous apps, etc.).
   - `sql/load.sql` — table names (read-only reference; loading is a human/setup step).
4. **Verify data exists**
   - Kaggle CSVs under `data/` (not committed) and `data/home_credit.db` built via `sql/load.sql` per `README.md`.
   - If the DB is missing, stop and tell the human to load data.
5. **Initialize `results.tsv`** — create it at the repo root with **only** the header row (tab-separated):

   ```text
   commit	roc_auc	memory_gb	status	description
   ```

   Do **not** commit `results.tsv` (it is gitignored).

6. **Confirm** — DB path resolves, `uv run python -m src.train --help` works, then start the loop.

---

## What you CAN change

- **`src/train.py`** — model hyperparameters, `TrainConfig`, preprocessing (e.g. encoders), optional early stopping, run name, sample fraction for faster iteration, etc.
- **`src/features.py`** — how feature SQL outputs are merged, column naming, optional extra SQL files (if you add SQL files, wire them in here).
- **`sql/features/*.sql`** — new or edited aggregates joined on `SK_ID_CURR`.

---

## What you CANNOT change

- **`pyproject.toml`** — do not add packages or change dependency versions; use only what is already declared.
- **`src/metrics.py`** — the **definition** of ROC-AUC and related metrics stays the ground-truth implementation; do not “optimize” by redefining metrics.
- **Do not bypass `src/train.py`** — no ad-hoc notebooks or alternate training scripts for scored runs; keeps splits and logging consistent.

---

## Feature cache (important)

Training reads **`data/features.parquet`** when `use_cached_features` is true (default). After you edit **`sql/features/`** or **`src/features.py`**, you must rebuild or you will train on stale features.

- **CLI:** pass **`--rebuild-features`** on the `src.train` invocation (sets `use_cached_features=False` for that run).
- Or delete `data/features.parquet` before running (same effect).

For pure **`train.py`** / config-only experiments, omit `--rebuild-features` to save time.

---

## Running an experiment

From the **repository root**:

```bash
uv run python -m src.train --log-file run.log 2>&1
```

After **SQL/features** changes:

```bash
uv run python -m src.train --rebuild-features --log-file run.log 2>&1
```

Optional JSON overrides (unchanged behavior):

```bash
uv run python -m src.train --config my_overrides.json --log-file run.log 2>&1
```

Redirect **all** output to the log file as above (do not use `tee` in a way that floods the agent context).

**Note:** There is **no** fixed wall-clock training budget in this project (unlike the 5-minute GPU loop in Karpathy’s template). Use a **reasonable** upper bound (e.g. if a run stalls far beyond normal CPU training time for this dataset, treat as failure). Adjust `TrainConfig.sample_frac` in code or JSON if you need quicker smoke runs.

---

## Output format (grep-friendly)

When training completes successfully, the log ends with a block like:

```text
---
roc_auc:          0.769100
training_seconds: 45.2
total_seconds:    120.5
peak_memory_mb:   1234.5
n_train:          ...
n_test:           ...
n_features:       ...
```

Extract the key metric:

```bash
grep "^roc_auc:" run.log
grep "^peak_memory_mb:" run.log
```

If those lines are missing, the run failed or exited early — inspect the log (e.g. `tail -n 80 run.log`).

---

## Logging results in `results.tsv`

Append one **tab-separated** row per experiment (not comma-separated). Columns:

| Column | Meaning |
|--------|---------|
| `commit` | Short git hash (7 characters) |
| `roc_auc` | Test ROC-AUC from the summary line (6 decimals is fine); use `0.000000` for crashes |
| `memory_gb` | From `peak_memory_mb` / 1024, rounded to one decimal; use `0.0` for crashes |
| `status` | `keep`, `discard`, or `crash` |
| `description` | Short text: what this experiment tried |

Example:

```text
commit	roc_auc	memory_gb	status	description
a1b2c3d	0.756500	1.2	keep	baseline
b2c3d4e	0.761000	1.3	keep	add bureau_balance SQL aggregate X
c3d4e5f	0.755000	1.2	discard	increase max_depth to 12
d4e5f6a	0.000000	0.0	crash	OOM after widening onehot
```

Do **not** commit `results.tsv`.

---

## Experiment loop (branch discipline)

On the dedicated `autoresearch/...` branch:

1. Note current branch and commit.
2. Implement **one** experimental idea (features and/or `train.py`).
3. `git add` / `git commit` with a short message.
4. Run training with `--log-file run.log` and `--rebuild-features` when SQL/features changed.
5. Read `roc_auc` (and optional `peak_memory_mb`) from `run.log`.
6. Append a row to `results.tsv`.
7. **Advance or revert**
   - **Keep:** If `roc_auc` is **strictly higher** than the best so far on this branch for comparable setup, keep the commit (you have advanced).
   - **Discard:** If `roc_auc` is **lower or equal**, reset the branch to the previous good commit:  
     `git reset --hard <previous_commit>`
8. On **crash** (exception, hang, OOM): fix trivial bugs and retry; if the idea is invalid, log `crash`, reset if needed, move on.

**Simplicity:** Prefer small, readable changes. A tiny AUC gain that adds brittle complexity may not be worth it; a simplification that preserves AUC is valuable.

---

## Autonomy (optional)

If the user wants **fully unattended** iteration (as in the original autoresearch doc), do **not** stop to ask whether to continue once the loop has started; run until interrupted. If you run out of ideas, re-read `README.md`, `sql/eda/`, and existing feature SQL for new signals.

---

## Quick reference

| Item | Location |
|------|----------|
| Train entrypoint | `uv run python -m src.train` |
| Key metric | `roc_auc` (higher better) |
| Feature SQL | `sql/features/*.sql` |
| Merge / cache | `src/features.py` → `data/features.parquet` |
| MLflow | SQLite `mlflow.db`, experiment from `TrainConfig.experiment_name` |
