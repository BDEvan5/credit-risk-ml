<script lang="ts">
	import { onMount } from 'svelte';

	/** Example 5 from `scripts/example_request.txt` — very high risk scenario. */
	const VERY_HIGH_RISK_PAYLOAD: Record<string, string | number> = {
		NAME_CONTRACT_TYPE: 'Cash loans',
		CODE_GENDER: 'M',
		FLAG_OWN_CAR: 'N',
		FLAG_OWN_REALTY: 'N',
		CNT_CHILDREN: 5,
		AMT_INCOME_TOTAL: 27000,
		AMT_CREDIT: 2000000,
		AMT_ANNUITY: 500000,
		AMT_GOODS_PRICE: 1900000,
		NAME_INCOME_TYPE: 'Unemployed',
		NAME_EDUCATION_TYPE: 'Lower secondary',
		NAME_FAMILY_STATUS: 'Single / not married',
		NAME_HOUSING_TYPE: 'With parents',
		DAYS_BIRTH: -7500,
		DAYS_EMPLOYED: 365243,
		OCCUPATION_TYPE: 'Low-skill Laborers',
		CNT_FAM_MEMBERS: 7,
		REGION_RATING_CLIENT: 3,
		EXT_SOURCE_1: 0.01,
		EXT_SOURCE_2: 0.01,
		EXT_SOURCE_3: 0.01,
		ratio_annuity_to_credit: 0.25,
		ratio_annuity_to_income: 18.52,
		ratio_credit_to_income: 74.07,
		ext23_product: 0.0001,
		bureau_total_debt: 1500000,
		bureau_num_active: 12,
		bureau_max_days_overdue: 360,
		bureau_total_overdue: 200000,
		inst_sum_payment: 8000000,
		inst_pct_late_last365: 0.92,
		inst_sum_late_vs_schedule: 400,
		inst_sum_underpaid: 250,
	};

	type Prediction = {
		probability: number;
		risk_tier: string;
		model_version: string;
		n_features_provided: number;
		elapsed_ms: number;
	};

	const rawApiUrl = (import.meta.env.PUBLIC_API_URL ?? '').replace(/\/$/, '');
	/** In dev, Vite proxies /__credit_risk_api → Cloud Run so CORS does not apply. */
	const apiUrl =
		import.meta.env.DEV && rawApiUrl ? '/__credit_risk_api' : rawApiUrl;
	const apiKey = import.meta.env.PUBLIC_API_KEY ?? '';

	let contractType = $state('Cash loans');
	let gender = $state('M');
	let incomeType = $state('Working');
	let occupation = $state('Laborers');
	let amtIncome = $state(180_000);
	let amtCredit = $state(270_000);
	let age = $state(36);
	let yearsEmployed = $state(8);
	let unemployed = $state(false);
	let cntChildren = $state(0);
	let extSource1Str = $state('');

	let loading = $state(false);
	let error = $state<string | null>(null);
	let prediction = $state<Prediction | null>(null);
	/** Merged on predict when set (Example 5 extras from `example_request.txt`). */
	let presetExtras = $state<Record<string, string | number>>({});

	const tierClass = $derived(
		prediction
			? prediction.risk_tier === 'Low'
				? 'tier-low'
				: prediction.risk_tier === 'Medium'
					? 'tier-medium'
					: 'tier-high'
			: '',
	);

	function wakeBackend() {
		if (!apiUrl) return;
		void fetch(`${apiUrl}/health`, {
			method: 'GET',
			cache: 'no-store',
		}).catch(() => {});
	}

	onMount(() => {
		wakeBackend();
	});

	function buildPayload(): Record<string, string | number> {
		const daysBirth = Math.round(-age * 365.25);
		const daysEmployed = unemployed ? 365243 : Math.round(-yearsEmployed * 365.25);
		const out: Record<string, string | number> = {
			NAME_CONTRACT_TYPE: contractType,
			CODE_GENDER: gender,
			NAME_INCOME_TYPE: incomeType,
			OCCUPATION_TYPE: occupation,
			AMT_INCOME_TOTAL: amtIncome,
			AMT_CREDIT: amtCredit,
			CNT_CHILDREN: cntChildren,
			DAYS_BIRTH: daysBirth,
			DAYS_EMPLOYED: daysEmployed,
		};
		const ext1 = extSource1Str.trim() === '' ? NaN : Number(extSource1Str);
		if (!Number.isNaN(ext1) && ext1 >= 0 && ext1 <= 1) {
			out.EXT_SOURCE_1 = ext1;
		}
		const keys = Object.keys(presetExtras);
		if (keys.length === 0) return out;
		return { ...out, ...presetExtras };
	}

	function formatPct(p: number) {
		return `${(p * 100).toFixed(1)}%`;
	}

	function formatUsd(n: number) {
		return n.toLocaleString('en-US', {
			style: 'currency',
			currency: 'USD',
			maximumFractionDigits: 0,
		});
	}

	async function predict() {
		error = null;
		prediction = null;
		if (!apiUrl || !apiKey) {
			error =
				'Missing API configuration. Set API_URL and API_KEY in the repository root .env (or PUBLIC_API_URL / PUBLIC_API_KEY).';
			return;
		}
		loading = true;
		try {
			const res = await fetch(`${apiUrl}/predict`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-API-Key': apiKey,
				},
				body: JSON.stringify(buildPayload()),
			});
			const text = await res.text();
			let data: unknown;
			try {
				data = JSON.parse(text);
			} catch {
				throw new Error(text.slice(0, 200) || 'Invalid response');
			}
			if (!res.ok) {
				const detail =
					typeof data === 'object' && data !== null && 'detail' in data
						? (data as { detail: unknown }).detail
						: data;
				throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
			}
			prediction = data as Prediction;
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'Request failed';
			if (
				e instanceof TypeError &&
				(msg === 'Failed to fetch' || msg.includes('Load failed'))
			) {
				error =
					'Could not reach the API (network or CORS). Try restarting `npm run dev` after pulling the latest frontend, or open this app at http://localhost:5173. If you deploy the API yourself, ensure ALLOWED_ORIGINS includes your dev URL.';
			} else {
				error = msg;
			}
		} finally {
			loading = false;
		}
	}

	function applyPreset(kind: 'safe' | 'borderline' | 'high' | 'extreme') {
		unemployed = false;
		extSource1Str = '';
		if (kind === 'extreme') {
			contractType = 'Cash loans';
			gender = 'M';
			incomeType = 'Unemployed';
			occupation = 'Low-skill Laborers';
			amtIncome = 27_000;
			amtCredit = 2_000_000;
			age = 21;
			unemployed = true;
			yearsEmployed = 0;
			cntChildren = 5;
			extSource1Str = '0.01';
			presetExtras = { ...VERY_HIGH_RISK_PAYLOAD };
			return;
		}
		presetExtras = {};
		if (kind === 'safe') {
			contractType = 'Cash loans';
			gender = 'F';
			incomeType = 'Working';
			occupation = 'Managers';
			amtIncome = 280_000;
			amtCredit = 120_000;
			age = 42;
			yearsEmployed = 14;
			cntChildren = 1;
			extSource1Str = '0.72';
		} else if (kind === 'borderline') {
			contractType = 'Cash loans';
			gender = 'M';
			incomeType = 'Working';
			occupation = 'Sales staff';
			amtIncome = 95_000;
			amtCredit = 320_000;
			age = 31;
			yearsEmployed = 3;
			cntChildren = 2;
			extSource1Str = '0.42';
		} else {
			contractType = 'Cash loans';
			gender = 'M';
			incomeType = 'Unemployed';
			occupation = 'Laborers';
			amtIncome = 45_000;
			amtCredit = 580_000;
			age = 28;
			unemployed = true;
			yearsEmployed = 0;
			cntChildren = 3;
			extSource1Str = '0.18';
		}
	}
</script>

<div class="page">
	<header class="header">
		<h1>Credit default risk</h1>
		<p class="lede">
			Explore a calibrated XGBoost model trained on Home Credit–style application data. Adjust an
			applicant profile and request a probability of default from the live API.
		</p>
	</header>

	<div class="presets">
		<span class="presets-label">Quick presets</span>
		<button type="button" class="btn btn-secondary" onclick={() => applyPreset('safe')}>Safe bet</button>
		<button type="button" class="btn btn-secondary" onclick={() => applyPreset('borderline')}>
			Borderline
		</button>
		<button type="button" class="btn btn-secondary" onclick={() => applyPreset('high')}>High risk</button>
		<button type="button" class="btn btn-secondary" onclick={() => applyPreset('extreme')}>
			Extremely high risk
		</button>
	</div>

	<div class="grid">
		<section class="card form-card">
			<h2>Application details</h2>
			<form
				class="form"
				onsubmit={(e) => {
					e.preventDefault();
					predict();
				}}
			>
				<div class="field-row">
					<label class="field">
						<span class="label">Loan type</span>
						<select bind:value={contractType} class="control">
							<option value="Cash loans">Cash loans</option>
							<option value="Revolving loans">Revolving loans</option>
						</select>
					</label>
					<label class="field">
						<span class="label">Gender</span>
						<select bind:value={gender} class="control">
							<option value="M">M</option>
							<option value="F">F</option>
							<option value="XNA">XNA</option>
						</select>
					</label>
				</div>

				<label class="field">
					<span class="label">Income type</span>
					<select bind:value={incomeType} class="control">
						<option value="Working">Working</option>
						<option value="Commercial associate">Commercial associate</option>
						<option value="Pensioner">Pensioner</option>
						<option value="State servant">State servant</option>
						<option value="Unemployed">Unemployed</option>
						<option value="Student">Student</option>
						<option value="Businessman">Businessman</option>
						<option value="Maternity leave">Maternity leave</option>
					</select>
				</label>

				<label class="field">
					<span class="label">Occupation</span>
					<select bind:value={occupation} class="control">
						<option value="Laborers">Laborers</option>
						<option value="Low-skill Laborers">Low-skill Laborers</option>
						<option value="Core staff">Core staff</option>
						<option value="Sales staff">Sales staff</option>
						<option value="Managers">Managers</option>
						<option value="Drivers">Drivers</option>
						<option value="High skill tech staff">High skill tech staff</option>
						<option value="Accountants">Accountants</option>
						<option value="IT staff">IT staff</option>
						<option value="Medicine staff">Medicine staff</option>
						<option value="Private service staff">Private service staff</option>
					</select>
				</label>

				<label class="field">
					<span class="label">Annual income (US dollars) — {formatUsd(amtIncome)}</span>
					<input type="range" class="range" min="0" max="600000" step="1000" bind:value={amtIncome} />
				</label>

				<label class="field">
					<span class="label">Credit amount requested (US dollars) — {formatUsd(amtCredit)}</span>
					<input type="range" class="range" min="0" max="1500000" step="5000" bind:value={amtCredit} />
				</label>

				<div class="field-row">
					<label class="field">
						<span class="label">Age (years)</span>
						<input type="number" class="control" min="18" max="90" bind:value={age} />
					</label>
					<label class="field">
						<span class="label">Children</span>
						<input type="number" class="control" min="0" max="20" bind:value={cntChildren} />
					</label>
				</div>

				<label class="field checkbox-field">
					<input type="checkbox" bind:checked={unemployed} />
					<span class="label inline">Currently unemployed (uses training sentinel for employment)</span>
				</label>

				{#if !unemployed}
					<label class="field">
						<span class="label">Years in current role</span>
						<input type="number" class="control" min="0" max="50" step="0.5" bind:value={yearsEmployed} />
					</label>
				{/if}

				<label class="field">
					<span class="label">External score 1 (optional, 0–1)</span>
					<input
						type="text"
						inputmode="decimal"
						class="control"
						placeholder="omit if unknown"
						bind:value={extSource1Str}
					/>
				</label>

				<button type="submit" class="btn btn-primary" disabled={loading}>
					{loading ? 'Scoring…' : 'Get risk score'}
				</button>
			</form>
		</section>

		<section class="card result-card">
			<h2>Model output</h2>
			{#if error}
				<p class="error" role="alert">{error}</p>
			{:else if prediction}
				<div class="result {tierClass}">
					<p class="tier-line">
						<span class="tier-label">Risk band</span>
						<span class="chip" data-tier={prediction.risk_tier}>{prediction.risk_tier}</span>
					</p>
					<p class="score-line">
						<span class="score-label">Default probability</span>
						<strong class="score">{formatPct(prediction.probability)}</strong>
					</p>
					<div class="bar-track" aria-hidden="true">
						<div
							class="bar-fill"
							style:width={`${Math.min(100, prediction.probability * 100)}%`}
						></div>
					</div>
					<dl class="meta">
						<div>
							<dt>Model</dt>
							<dd>{prediction.model_version}</dd>
						</div>
						<div>
							<dt>Features sent</dt>
							<dd>{prediction.n_features_provided}</dd>
						</div>
						<div>
							<dt>Server time</dt>
							<dd>{prediction.elapsed_ms} ms</dd>
						</div>
					</dl>
				</div>
			{:else}
				<p class="placeholder">Submit the form to see calibrated default probability and a low / medium / high band.</p>
			{/if}
		</section>
	</div>

	<section class="card about">
		<h2>About this demo</h2>
		<p>
			The service returns a probability of default and a coarse risk tier. The model was trained on
			tabular credit-application features; scores are for demonstration only and are not financial
			advice. Omitted fields are imputed by the same pipeline used in training.
		</p>
	</section>
</div>

<style>
	.page {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: var(--space-lg) var(--space-md);
		padding-bottom: calc(var(--space-lg) * 2);
	}

	.header {
		margin-bottom: var(--space-md);
	}

	.lede {
		color: var(--on-surface-variant);
		font-size: 1.125rem;
		max-width: 52ch;
		margin: 0;
	}

	.presets {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
	}

	.presets-label {
		font-size: 0.875rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--on-surface-variant);
		margin-right: var(--space-xs);
	}

	.grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-md);
	}

	@media (min-width: 900px) {
		.grid {
			grid-template-columns: 1fr 1fr;
			align-items: start;
		}
	}

	.card {
		background: var(--surface-container);
		border-radius: var(--radius-card);
		padding: var(--space-md);
		border: 1px solid transparent;
		box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.04);
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.field-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-sm);
	}

	@media (max-width: 600px) {
		.field-row {
			grid-template-columns: 1fr;
		}
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.checkbox-field {
		flex-direction: row;
		align-items: flex-start;
		gap: var(--space-sm);
	}

	.label {
		font-size: 0.875rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--on-surface);
	}

	.label.inline {
		font-weight: 500;
	}

	.control {
		font-family: inherit;
		font-size: 1rem;
		padding: 0.65rem 1rem;
		border-radius: var(--radius-control);
		border: 1px solid var(--input-border);
		background: var(--input-bg);
		color: var(--on-surface);
		outline: none;
		transition: border-color 0.15s ease;
	}

	.control:focus-visible {
		border-color: var(--outline-focus);
	}

	select.control {
		cursor: pointer;
	}

	.range {
		width: 100%;
		accent-color: var(--primary);
		height: 2rem;
	}

	.btn {
		font-family: inherit;
		font-size: 1rem;
		font-weight: 600;
		padding: 0.75rem 1.5rem;
		border-radius: var(--radius-control);
		cursor: pointer;
		border: none;
		transition:
			opacity 0.15s ease,
			transform 0.05s ease;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary {
		background: var(--primary);
		color: #000;
		align-self: flex-start;
	}

	.btn-primary:not(:disabled):hover {
		filter: brightness(1.05);
	}

	.btn-secondary {
		background: transparent;
		color: var(--primary);
		border: 2px solid var(--primary);
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
	}

	.btn-secondary:hover {
		background: rgba(255, 193, 7, 0.08);
	}

	.error {
		color: #ffb4a9;
		margin: 0;
	}

	.placeholder {
		color: var(--on-surface-variant);
		margin: 0;
		line-height: 1.6;
	}

	.result {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.tier-line {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin: 0;
		flex-wrap: wrap;
	}

	.tier-label {
		font-size: 0.875rem;
		color: var(--on-surface-variant);
	}

	.chip {
		display: inline-flex;
		align-items: center;
		padding: 0.35rem 0.85rem;
		border-radius: 1rem;
		font-size: 0.875rem;
		font-weight: 600;
		letter-spacing: 0.02em;
	}

	.chip[data-tier='Low'] {
		background: var(--risk-low-bg);
		color: var(--risk-low);
	}

	.chip[data-tier='Medium'] {
		background: var(--risk-medium-bg);
		color: var(--risk-medium);
	}

	.chip[data-tier='High'] {
		background: var(--risk-high-bg);
		color: var(--risk-high);
	}

	.score-line {
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.score-label {
		font-size: 0.875rem;
		color: var(--on-surface-variant);
	}

	.score {
		font-family: 'Work Sans', system-ui, sans-serif;
		font-variant-numeric: tabular-nums;
		font-size: clamp(2rem, 5vw, 2.75rem);
		font-weight: 700;
		line-height: 1.1;
		letter-spacing: -0.02em;
	}

	.result.tier-low .score {
		color: var(--risk-low);
	}

	.result.tier-medium .score {
		color: var(--risk-medium);
	}

	.result.tier-high .score {
		color: var(--risk-high);
	}

	.bar-track {
		height: 12px;
		border-radius: var(--radius-control);
		background: var(--surface-container-highest);
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: var(--radius-control);
		background: linear-gradient(90deg, var(--primary-container), #ffdf9e);
		box-shadow: 0 0 20px rgba(255, 193, 7, 0.35);
		transition: width 0.35s ease;
	}

	.result.tier-low .bar-fill {
		background: linear-gradient(90deg, #2a8f6a, var(--risk-low));
		box-shadow: 0 0 20px rgba(94, 233, 181, 0.25);
	}

	.result.tier-high .bar-fill {
		background: linear-gradient(90deg, #c62828, var(--risk-high));
		box-shadow: 0 0 20px rgba(255, 107, 107, 0.25);
	}

	.meta {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-sm);
		margin: 0;
		font-size: 0.875rem;
	}

	.meta dt {
		color: var(--on-surface-variant);
		font-weight: 600;
		margin: 0 0 0.15rem;
	}

	.meta dd {
		margin: 0;
		font-variant-numeric: tabular-nums;
	}

	.about {
		margin-top: var(--space-md);
	}

	.about p {
		margin: 0;
		color: var(--on-surface-variant);
		max-width: 70ch;
		line-height: 1.6;
	}
</style>
