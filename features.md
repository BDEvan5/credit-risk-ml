# Feature expansion and pruning plan

This document ties together **what we add** to the modelling matrix (aligned with strong public work on the [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk) competition), and **how we prune** features so the final model keeps signal without redundant or unstable columns.

References used for patterns (conceptually aligned with kernels such as [detailed feature engineering](https://www.kaggle.com/code/mathchi/home-credit-risk-with-detailed-feature-engineering) and [LightGBM with simple features](https://www.kaggle.com/code/jsaguiar/lightgbm-with-simple-features)): multi-table **aggregations** (counts, sums, means, max delinquency), **payment behaviour** from instalments, **utilisation** from credit card balances, **POS cash** delinquency flags, and **simple application-level ratios** (annuity/credit, credit/income, external-score interactions).

---

## 1. Features to add (implemented in `sql/features/`)

### 1.1 Application-level ratios (`application_ratios.sql`)

| Idea | Rationale |
|------|-----------|
| `ratio_annuity_to_credit`, `ratio_goods_price_to_credit` | Standard affordability / pricing structure signals used across kernels. |
| `ratio_credit_to_income`, `ratio_annuity_to_income` | Debt-service and leverage vs stated income. |
| `ratio_credit_minus_goods_to_credit` | Consumer vs car/house goods financing mix. |
| `ext12_product`, `ext13_product`, `ext23_product` | Nonlinear combinations of bureau-style scores (common in ensemble solutions). |
| `ext*_times_pop_rel` | Interaction of external scores with regional population density. |

These are joined in `src/features.py` with duplicate base columns removed so ratios are not double-counted.

### 1.2 Bureau (`bureau_summary.sql`)

Beyond counts and totals, we add:

- Mix of **credit types** and **active/closed/sold** counts.
- **Duration** features: mean `DAYS_CREDIT`, min/max `DAYS_CREDIT_ENDDATE`, sum of credit duration.
- **Risk ratios**: debt-to-total-credit, overdue-to-total-credit.

### 1.3 Bureau balance (`bureau_balance_summary.sql`)

Existing monthly delinquency rates retained; no change required for this iteration.

### 1.4 Previous applications (`previous_applications.sql`)

- **Temporal**: min/max `DAYS_DECISION` (how recent / spread of past decisions).
- **Status mix**: approved / refused / canceled counts.
- **Client type**: repeater vs new.
- **Diversity**: distinct product types; payment type counts where informative.

### 1.5 Instalments (`installments_payments_summary.sql`)

Per previous loan, then per applicant:

- Late vs schedule (`DAYS_ENTRY_PAYMENT` vs `DAYS_INSTALMENT`).
- Underpayment vs instalment amount.
- Aggregated payment-to-instalment ratios (overall and mean per loan).

### 1.6 POS cash (`pos_cash_summary.sql`)

- Future instalment counts (`CNT_INSTALMENT_FUTURE`).
- **SK_DPD** / **SK_DPD_DEF** sums and maxima (delinquency exposure).
- Contract status counts (active/completed/signed).

### 1.7 Credit card (`credit_card_summary.sql`)

- Balances and limits; **mean and max utilisation** (`AMT_BALANCE` / limit).
- Drawings and payments; max/sum DPD.

---

## 2. Feature pruning: methods to use

Goal: reduce dimensionality and **correlated redundancy** while keeping **out-of-sample** usefulness. Methods below are standard for gradient-boosted trees on tabular credit data.

### 2.1 Filter: highly correlated features

- **What**: Compute Pearson |correlation| on numeric training columns; for pairs above a threshold (e.g. 0.95), drop one.
- **Why**: Tree models split on one of a redundant pair; keeping both can add noise and instability.
- **Implementation**: `src/feature_selection.py` → `drop_highly_correlated` (optional `keep_order` to protect known strong columns such as external scores).

### 2.2 Embedded: gain / split importance (LightGBM / XGBoost)

- **What**: Train a model with strong regularisation; read `feature_importances_` (gain).
- **Why**: Fast, scales to many columns; identifies features the ensemble actually uses.
- **Caveat**: Correlated features can **share** importance; combine with §2.1 or per-fold importance.
- **Implementation**: `mean_lgbm_gain_importance` (cross-validated mean importance).

### 2.3 Wrapper: `SelectFromModel` (median / tuned threshold)

- **What**: Use sklearn’s `SelectFromModel` on a pre-fitted tree model with `prefit=True`.
- **Why**: Drops mass of low-importance noise in one step; threshold can be tuned on validation AUC.
- **Implementation**: `select_from_lgbm_model`.

### 2.4 Recursive / iterative elimination (optional)

- **What**: Recursive Feature Elimination (RFE) or manual loops: remove bottom-k features by importance, retrain, repeat until validation metric stops improving.
- **Why**: **Minimal-optimal** subset for deployment; more expensive than §2.2–2.3.
- **Caveat**: Must use **cross-validation** or a held-out set **inside** the selection loop to avoid optimistic bias.

### 2.5 “All-relevant” (optional): Boruta / Greedy Boruta

- **What**: Compare importance of real features to **shadow** (permuted) features; keep those that consistently beat shadows.
- **Why**: Reduces false positives from random noise in high dimensions; heavier compute.
- **When**: If many engineered columns are suspected spurious after §2.1–2.3.

### 2.6 Stability selection

- **What**: Run importance or selection on several CV folds or bootstrap samples; **keep features that appear in the top set repeatedly**.
- **Why**: Improves reproducibility for credit models under sample variation.

### 2.7 SHAP-based refinement (post-hoc)

- **What**: After a candidate model, global SHAP ranking for sanity checks and business narrative.
- **Why**: Not a primary pruning rule (costly at full scale) but excellent for validating that retained features align with domain intuition.

---

## 3. Recommended end-to-end pruning pipeline

1. **Train/validation split** (or stratified K-fold) **before** any selection that uses the target.
2. **Filter**: `drop_highly_correlated` on numeric columns (threshold 0.95–0.99); optionally protect `EXT_SOURCE_*` and key ratios via `keep_order`.
3. **Fit baseline LightGBM** (or XGBoost) on the filtered matrix; log validation ROC-AUC / Gini.
4. **Importance**: `mean_lgbm_gain_importance` across folds; drop features with near-zero mean importance (or use `select_from_lgbm_model` with `threshold="median"` and tune).
5. **Re-evaluate** on the same CV scheme; if AUC is unchanged or improves with fewer columns, keep the smaller set.
6. **Optional**: RFE or Boruta if further reduction is needed for deployment or interpretability.
7. **Persist** the final column list (e.g. JSON next to the trained pipeline) so inference uses the same features.

---

## 4. Repository mapping

| Artifact | Role |
|----------|------|
| `sql/features/*.sql` | Applicant-level aggregates and ratios |
| `src/features.py` | Loads SQL, merges onto `application_train`, caches Parquet |
| `src/feature_selection.py` | Correlation filter, CV importance, `SelectFromModel` helper |
| Modelling notebook | Wires pruning into the train/validate loop and MLflow |

This plan is intentionally incremental: you can ship more SQL features first, then tighten with §3 without changing the database load contract (`sql/load.sql` already includes all auxiliary tables).
