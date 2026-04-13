# Modelling features

Applicant-level feature matrix for [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data): **`application_train`** as the base row, plus one row per applicant from each file in **`sql/features/`**, merged on **`SK_ID_CURR`** in **`src/features.py`** and cached as **`data/features.parquet`**.

---

## `application_train` (base)

Current-application attributes from the competition table: identity and contact flags, contract type, demographics, income and credit amounts, building/normalised housing fields, region ratings, external scores (`EXT_SOURCE_*`), social-circle defaults, credit-bureau enquiry counts, and **`TARGET`**.

---

## `application_ratios.sql` (`application_train` only)

Ratios and score mixes: annuity/credit, goods/credit, credit and annuity to income, credit minus goods mix, pairwise products of external scores, and each external score times regional population relative.

---

## `bureau_summary.sql` (`bureau`)

Per-applicant rollups over external bureau lines: record counts (distinct bureaus, active/closed/sold, card/consumer type), sums of credit/debt/limit/overdue, max overdue days and amount, credit duration stats (mean/min/max days, sum of duration), debt-to-credit and overdue-to-credit ratios.

---

## `bureau_balance_summary.sql` (`bureau` → `bureau_balance`)

Monthly bureau-balance status rolled up per bureau line then per applicant: total months and counts of months by delinquency band (1+/2+/3+ DPD), plus shares of months in each band.

---

## `previous_applications.sql` (`previous_application`)

Prior applications at Home Credit: counts and amounts (applied/credit), success and rejection stats (including first rejection reason and “was rejected” flag), decision-day range, counts by contract status (approved/refused/canceled), client type (repeater/new), payment-type and product-type diversity.

---

## `installments_payments_summary.sql` (`installments_payments`)

Payment behaviour on previous loans: per-loan then per-applicant aggregates of instalments vs payments, lateness vs schedule, underpayment counts, mean payment ratio per loan, and overall payment-to-instalment ratio.

---

## `pos_cash_summary.sql` (`POS_CASH_balance`)

POS / cash loans: row and previous-loan counts, future instalment counts (sum/mean/max), DPD and DPD-def sums and extrema, mean DPD, and counts of contract statuses (active/completed/signed).

---

## `credit_card_summary.sql` (`credit_card_balance`)

Credit card exposure: balances and limits, mean/max utilisation, drawings and payments, max/sum SK_DPD, and count of active contracts.
