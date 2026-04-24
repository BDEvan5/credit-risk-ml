<script lang="ts">
	import { onMount } from 'svelte';

	const HISTORY_KEY = 'credit-risk-simulation-history';
	const MAX_HISTORY = 40;

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

	type HistoryRow = {
		id: string;
		at: number;
		category: string;
		amtCredit: number;
		probability: number;
		riskTier: string;
	};

	const rawApiUrl = (import.meta.env.PUBLIC_API_URL ?? '').replace(/\/$/, '');
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
	let presetExtras = $state<Record<string, string | number>>({});
	let history = $state<HistoryRow[]>([]);

	const tierClass = $derived(
		prediction
			? prediction.risk_tier === 'Low'
				? 'tier-low'
				: prediction.risk_tier === 'Medium'
					? 'tier-medium'
					: 'tier-high'
			: '',
	);

	const reliabilityScore = $derived(
		prediction
			? Math.round(Math.min(980, Math.max(220, 280 + (1 - prediction.probability) * 700)))
			: null,
	);

	const gaugePct = $derived(prediction ? Math.min(1, Math.max(0, 1 - prediction.probability)) : 0);

	function wakeBackend() {
		if (!apiUrl) return;
		void fetch(`${apiUrl}/health`, {
			method: 'GET',
			cache: 'no-store',
		}).catch(() => {});
	}

	function readHistory(): HistoryRow[] {
		if (typeof localStorage === 'undefined') return [];
		try {
			const raw = localStorage.getItem(HISTORY_KEY);
			if (!raw) return [];
			const parsed = JSON.parse(raw) as unknown;
			if (!Array.isArray(parsed)) return [];
			return parsed.filter(
				(r): r is HistoryRow =>
					r &&
					typeof r === 'object' &&
					'id' in r &&
					'at' in r &&
					'category' in r &&
					'amtCredit' in r &&
					'probability' in r &&
					'riskTier' in r,
			) as HistoryRow[];
		} catch {
			return [];
		}
	}

	function writeHistory(rows: HistoryRow[]) {
		if (typeof localStorage === 'undefined') return;
		localStorage.setItem(HISTORY_KEY, JSON.stringify(rows.slice(0, MAX_HISTORY)));
	}

	function appendHistory(pred: Prediction) {
		const id = `CR-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
		const category = `${incomeType} · ${occupation}`.slice(0, 48);
		const row: HistoryRow = {
			id,
			at: Date.now(),
			category,
			amtCredit,
			probability: pred.probability,
			riskTier: pred.risk_tier,
		};
		const next = [row, ...history].slice(0, MAX_HISTORY);
		history = next;
		writeHistory(next);
	}

	function statusLabel(tier: string): string {
		if (tier === 'Low') return 'APPROVED';
		if (tier === 'Medium') return 'PENDING';
		return 'REJECTED';
	}

	function statusClass(tier: string): string {
		if (tier === 'Low') return 'status-approved';
		if (tier === 'Medium') return 'status-pending';
		return 'status-rejected';
	}

	function formatTime(ts: number) {
		return new Date(ts).toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	function downloadHistoryCsv() {
		const header = ['Application ID', 'Time', 'Client category', 'Loan USD', 'Default prob', 'Tier', 'Status'];
		const lines = history.map((h) =>
			[
				h.id,
				new Date(h.at).toISOString(),
				`"${h.category.replace(/"/g, '""')}"`,
				String(h.amtCredit),
				String(h.probability),
				h.riskTier,
				statusLabel(h.riskTier),
			].join(','),
		);
		const blob = new Blob([header.join(',') + '\n' + lines.join('\n')], {
			type: 'text/csv;charset=utf-8',
		});
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.download = 'risksense-simulation-history.csv';
		a.click();
		URL.revokeObjectURL(a.href);
	}

	function clearHistory() {
		history = [];
		writeHistory([]);
	}

	onMount(() => {
		wakeBackend();
		history = readHistory();
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
			const pred = data as Prediction;
			prediction = pred;
			appendHistory(pred);
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

	const R = 52;
	const C = 2 * Math.PI * R;
</script>

<div class="shell">
	<nav class="topnav" aria-label="Primary">
		<a href="#application-information" class="brand">
			<span class="brand-mark" aria-hidden="true"></span>
			RiskSense
		</a>
		<div class="nav-links">
			<a href="#application-information">Application information</a>
			<a href="#profile">Profile</a>
			<a href="#history">History</a>
		</div>
		<div class="nav-trailing">
			<div class="presets presets--nav" aria-label="Quick presets">
				<span class="presets-label">Presets</span>
				<button type="button" class="btn-ghost" onclick={() => applyPreset('safe')}>Safe bet</button>
				<button type="button" class="btn-ghost" onclick={() => applyPreset('borderline')}>Borderline</button>
				<button type="button" class="btn-ghost" onclick={() => applyPreset('high')}>High risk</button>
				<button
					type="button"
					class="btn-ghost"
					title="Extremely high risk (Example 5)"
					onclick={() => applyPreset('extreme')}>Extreme</button>
			</div>
			<div class="nav-actions" aria-hidden="true">
				<span class="nav-dot"></span>
				<span class="nav-dot"></span>
				<span class="nav-avatar"></span>
			</div>
		</div>
	</nav>

	<p class="hero">
		Analyze borrower reliability with our precision-engineered credit risk engine.
	</p>

	<!-- Section 1: Application information -->
	<section id="application-information" class="panel intake">
		<div class="panel-title-row">
			<span class="panel-icon" aria-hidden="true">
				<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
					<polyline points="14 2 14 8 20 8" />
					<line x1="8" y1="13" x2="16" y2="13" />
					<line x1="8" y1="17" x2="14" y2="17" />
				</svg>
			</span>
			<h2 class="panel-title">Application information</h2>
		</div>

		<form
			class="intake-form"
			onsubmit={(e) => {
				e.preventDefault();
				predict();
			}}
		>
			<div class="form-grid">
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
					<span class="label">Employment / income type</span>
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
					<span class="label">Annual income (USD)</span>
					<input type="text" class="control control-readonly" readonly value={formatUsd(amtIncome)} />
				</label>

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

				<label class="field">
					<span class="label">Credit amount (USD)</span>
					<input type="text" class="control control-readonly" readonly value={formatUsd(amtCredit)} />
				</label>

				<label class="field">
					<span class="label">Age (years)</span>
					<input type="number" class="control" min="18" max="90" bind:value={age} />
				</label>

				<label class="field">
					<span class="label">Dependents (children)</span>
					<input type="number" class="control" min="0" max="20" bind:value={cntChildren} />
				</label>

				<label class="field">
					<span class="label">External score 1 (0–1, optional)</span>
					<input
						type="text"
						inputmode="decimal"
						class="control"
						placeholder="—"
						bind:value={extSource1Str}
					/>
				</label>
			</div>

			<label class="field span-full">
				<span class="label">Annual income (USD) — adjust</span>
				<input type="range" class="range" min="0" max="600000" step="1000" bind:value={amtIncome} />
			</label>

			<label class="field span-full">
				<span class="label">Credit amount requested (USD) — adjust</span>
				<input type="range" class="range" min="0" max="1500000" step="5000" bind:value={amtCredit} />
			</label>

			<div class="employment-row span-full">
				<label class="field checkbox-field employment-check">
					<input type="checkbox" bind:checked={unemployed} />
					<span class="label inline">Currently unemployed (training sentinel)</span>
				</label>
				{#if !unemployed}
					<label class="field years-field">
						<span class="label">Years in current role</span>
						<input type="number" class="control" min="0" max="50" step="0.5" bind:value={yearsEmployed} />
					</label>
				{/if}
			</div>

			<button type="submit" class="btn-cta" disabled={loading}>
				<span class="bolt" aria-hidden="true">⚡</span>
				{loading ? 'Calculating…' : 'Generate risk profile'}
			</button>
		</form>
	</section>

	<!-- Section 2: Calculated Risk Profile -->
	<section id="profile" class="panel profile">
		<div class="live-pill" aria-live="polite">
			<span class="live-dot"></span>
			LIVE CALCULATION
		</div>
		<h2 class="panel-title profile-heading">Calculated Risk Profile</h2>

		<div class="profile-layout">
			<div class="profile-main">
				{#if error}
					<p class="error" role="alert">{error}</p>
				{:else if prediction}
					<p class="profile-lede">
						Calibrated probability of default from the live model. Lower default probability implies a
						more favorable profile for this demo.
					</p>
					<div class="metric-grid">
						<div class="metric">
							<span class="metric-label">Default probability</span>
							<span class="metric-value">{formatPct(prediction.probability)}</span>
						</div>
						<div class="metric">
							<span class="metric-label">Model latency</span>
							<span class="metric-value">{prediction.elapsed_ms} ms</span>
						</div>
						<div class="metric">
							<span class="metric-label">Features provided</span>
							<span class="metric-value">{prediction.n_features_provided}</span>
						</div>
						<div class="metric">
							<span class="metric-label">Model version</span>
							<span class="metric-value metric-mono">{prediction.model_version}</span>
						</div>
					</div>
					<div class="tier-row">
						<span class="tier-label">Risk band</span>
						<span class="chip" data-tier={prediction.risk_tier}>{prediction.risk_tier}</span>
					</div>
					<div class="bar-track" aria-hidden="true">
						<div
							class="bar-fill {tierClass}"
							style:width={`${Math.min(100, prediction.probability * 100)}%`}
						></div>
					</div>
				{:else}
					<p class="placeholder">
						Run <strong>Generate risk profile</strong> above to populate this panel with default
						probability, tier, and a reliability ring derived from the score.
					</p>
				{/if}
			</div>

			<div class="gauge-wrap" aria-hidden={prediction ? undefined : 'true'}>
				{#if prediction && reliabilityScore !== null}
					{@const dash = C * gaugePct}
					<svg class="gauge-svg" viewBox="0 0 120 120" role="img" aria-label="Reliability ring">
						<circle class="gauge-bg" cx="60" cy="60" r={R} fill="none" />
						<circle
							class="gauge-arc {tierClass}"
							cx="60"
							cy="60"
							r={R}
							fill="none"
							stroke-dasharray={`${dash} ${C}`}
							transform="rotate(-90 60 60)"
						/>
					</svg>
					<div class="gauge-center">
						<span class="gauge-score">{reliabilityScore}</span>
						<span class="gauge-sub">
							{prediction.risk_tier === 'Low'
								? 'FAVORABLE'
								: prediction.risk_tier === 'Medium'
									? 'ELEVATED'
									: 'SEVERE'}
						</span>
						<span class="gauge-hint">Reliability index</span>
					</div>
				{:else}
					<div class="gauge-empty">
						<span class="gauge-score muted">—</span>
						<span class="gauge-sub">Awaiting run</span>
					</div>
				{/if}
			</div>
		</div>
	</section>

	<!-- Section 3: Simulation History -->
	<section id="history" class="panel history">
		<div class="history-head">
			<h2 class="panel-title">Simulation History</h2>
			<div class="history-toolbar">
				<button
					type="button"
					class="btn-icon"
					disabled={history.length === 0}
					onclick={downloadHistoryCsv}
					title="Download CSV"
				>
					↓
				</button>
				{#if history.length > 0}
					<button type="button" class="btn-icon danger" onclick={clearHistory} title="Clear history">
						⌫
					</button>
				{/if}
			</div>
		</div>

		<div class="table-wrap">
			{#if history.length === 0}
				<p class="table-empty">No simulations yet. Generate a risk profile to build your history.</p>
			{:else}
				<table class="data-table">
					<thead>
						<tr>
							<th>Application ID</th>
							<th>Client category</th>
							<th>Loan amount</th>
							<th>Risk</th>
							<th>Status</th>
							<th>Time</th>
						</tr>
					</thead>
					<tbody>
						{#each history as row (row.id)}
							<tr>
								<td class="mono">{row.id}</td>
								<td class="category">{row.category}</td>
								<td class="num">{formatUsd(row.amtCredit)}</td>
								<td class="risk-cell">
									<span class="risk-pct">{formatPct(row.probability)}</span>
									<div class="mini-track">
										<div
											class="mini-fill {row.riskTier === 'Low'
												? 'tier-low'
												: row.riskTier === 'Medium'
													? 'tier-medium'
													: 'tier-high'}"
											style:width={`${Math.min(100, row.probability * 100)}%`}
										></div>
									</div>
								</td>
								<td>
									<span class="status-pill {statusClass(row.riskTier)}">{statusLabel(row.riskTier)}</span>
								</td>
								<td class="muted time">{formatTime(row.at)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>
	</section>

	<p class="footer-note">
		Demo only — not financial advice. History is stored in your browser (localStorage) and never sent to a
		server except the prediction request payload.
	</p>
</div>

<style>
	.shell {
		max-width: 1120px;
		margin: 0 auto;
		padding: var(--space-md) var(--space-md) calc(var(--space-lg) * 2);
	}

	.topnav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		flex-wrap: wrap;
		row-gap: 0.75rem;
		padding: var(--space-sm) 0 var(--space-md);
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
		margin-bottom: var(--space-lg);
	}

	.brand {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		font-family: Manrope, system-ui, sans-serif;
		font-weight: 700;
		font-size: 1.25rem;
		color: var(--on-surface);
		text-decoration: none;
		letter-spacing: -0.02em;
	}

	.brand:hover {
		color: var(--primary);
	}

	.brand-mark {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--primary);
		box-shadow: 0 0 12px rgba(255, 193, 7, 0.6);
	}

	.nav-trailing {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		flex-wrap: wrap;
		margin-left: auto;
	}

	.nav-links {
		display: none;
		gap: var(--space-md);
	}

	@media (min-width: 640px) {
		.nav-links {
			display: flex;
			flex: 1;
			justify-content: center;
			min-width: 0;
		}
	}

	.nav-links a {
		color: var(--on-surface-variant);
		text-decoration: none;
		font-size: 0.9rem;
		font-weight: 500;
	}

	.nav-links a:hover {
		color: var(--primary);
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.nav-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.15);
	}

	.nav-avatar {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: linear-gradient(135deg, var(--surface-container-high), var(--surface-container-highest));
		border: 2px solid rgba(255, 193, 7, 0.35);
	}

	.hero {
		text-align: center;
		font-family: Manrope, system-ui, sans-serif;
		font-size: clamp(1.15rem, 2.5vw, 1.45rem);
		font-weight: 600;
		line-height: 1.35;
		color: var(--on-surface);
		margin: 0 0 var(--space-lg);
		max-width: 40em;
		margin-left: auto;
		margin-right: auto;
		letter-spacing: -0.02em;
	}

	.panel {
		background: var(--surface-container);
		border-radius: var(--radius-card);
		padding: var(--space-md) var(--space-md);
		margin-bottom: var(--space-md);
		border: 1px solid rgba(255, 255, 255, 0.05);
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
		scroll-margin-top: 1.25rem;
	}

	.panel-title-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		margin-bottom: var(--space-sm);
	}

	.panel-icon {
		display: flex;
		color: var(--primary);
	}

	.panel-title {
		font-family: Manrope, system-ui, sans-serif;
		font-size: 1.35rem;
		font-weight: 600;
		margin: 0;
		letter-spacing: -0.02em;
	}

	.presets {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem;
		margin-bottom: var(--space-md);
		padding-bottom: var(--space-md);
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	.presets--nav {
		margin-bottom: 0;
		padding-bottom: 0;
		border-bottom: none;
		max-width: min(100%, 28rem);
		justify-content: flex-end;
	}

	.presets--nav .btn-ghost {
		padding: 0.3rem 0.55rem;
		font-size: 0.72rem;
	}

	.presets-label {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--on-surface-variant);
		margin-right: 0.25rem;
	}

	.btn-ghost {
		font-family: inherit;
		font-size: 0.8rem;
		font-weight: 600;
		padding: 0.4rem 0.85rem;
		border-radius: var(--radius-control);
		border: 1px solid rgba(255, 193, 7, 0.35);
		background: transparent;
		color: var(--primary);
		cursor: pointer;
	}

	.btn-ghost:hover {
		background: rgba(255, 193, 7, 0.08);
	}

	.intake-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-md);
	}

	@media (min-width: 768px) {
		.form-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	.span-full {
		grid-column: 1 / -1;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.checkbox-field {
		flex-direction: row;
		align-items: center;
		gap: 0.65rem;
	}

	.employment-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-md);
	}

	.employment-check {
		flex: 1 1 16rem;
		min-width: 0;
		margin: 0;
	}

	.years-field {
		flex: 0 0 9rem;
	}

	.label {
		font-size: 0.8rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--on-surface-variant);
	}

	.label.inline {
		font-weight: 500;
		color: var(--on-surface);
	}

	.control {
		font-family: inherit;
		font-size: 0.95rem;
		padding: 0.65rem 1rem;
		border-radius: 1rem;
		border: 1px solid var(--input-border);
		background: var(--input-bg);
		color: var(--on-surface);
		outline: none;
	}

	.control:focus-visible {
		border-color: var(--outline-focus);
	}

	.control-readonly {
		opacity: 0.95;
		cursor: default;
	}

	select.control {
		cursor: pointer;
	}

	.range {
		width: 100%;
		accent-color: var(--primary);
		height: 1.75rem;
	}

	.btn-cta {
		width: 100%;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		font-family: Manrope, system-ui, sans-serif;
		font-size: 1rem;
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		padding: 1rem 1.25rem;
		border: none;
		border-radius: 1.25rem;
		background: var(--primary);
		color: #0a0a0a;
		cursor: pointer;
		margin-top: 0.25rem;
	}

	.btn-cta:disabled {
		opacity: 0.65;
		cursor: not-allowed;
	}

	.btn-cta:not(:disabled):hover {
		filter: brightness(1.06);
	}

	.bolt {
		font-size: 1.1rem;
	}

	.live-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.7rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		color: var(--primary);
		border: 1px solid rgba(255, 193, 7, 0.35);
		padding: 0.35rem 0.75rem;
		border-radius: var(--radius-control);
		margin-bottom: 0.65rem;
	}

	.live-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--primary);
		animation: pulse 1.8s ease-in-out infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.35;
		}
	}

	.profile-heading {
		margin-bottom: var(--space-md);
	}

	.profile-layout {
		display: grid;
		grid-template-columns: 1fr;
		gap: var(--space-lg);
		align-items: center;
	}

	@media (min-width: 800px) {
		.profile-layout {
			grid-template-columns: 1fr minmax(200px, 260px);
		}
	}

	.profile-lede {
		color: var(--on-surface-variant);
		margin: 0 0 var(--space-md);
		line-height: 1.55;
		max-width: 36rem;
	}

	.metric-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-md);
		margin-bottom: var(--space-md);
	}

	.metric-label {
		display: block;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--on-surface-variant);
		margin-bottom: 0.2rem;
	}

	.metric-value {
		font-family: Manrope, system-ui, sans-serif;
		font-size: 1.25rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.metric-mono {
		font-family: ui-monospace, monospace;
		font-size: 0.95rem;
		font-weight: 500;
	}

	.tier-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		margin-bottom: 0.75rem;
	}

	.tier-label {
		font-size: 0.85rem;
		color: var(--on-surface-variant);
	}

	.chip {
		display: inline-flex;
		padding: 0.3rem 0.75rem;
		border-radius: 1rem;
		font-size: 0.8rem;
		font-weight: 700;
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

	.bar-track {
		height: 10px;
		border-radius: var(--radius-control);
		background: rgba(255, 255, 255, 0.06);
		overflow: hidden;
		max-width: 28rem;
	}

	.bar-fill {
		height: 100%;
		border-radius: var(--radius-control);
		transition: width 0.35s ease;
	}

	.bar-fill.tier-low {
		background: linear-gradient(90deg, #2a8f6a, var(--risk-low));
	}

	.bar-fill.tier-medium {
		background: linear-gradient(90deg, #8a6a00, var(--risk-medium));
	}

	.bar-fill.tier-high {
		background: linear-gradient(90deg, #a32020, var(--risk-high));
	}

	.gauge-wrap {
		position: relative;
		width: 200px;
		height: 200px;
		margin: 0 auto;
	}

	.gauge-svg {
		width: 100%;
		height: 100%;
	}

	.gauge-bg {
		stroke: rgba(255, 255, 255, 0.08);
		stroke-width: 10;
	}

	.gauge-arc {
		stroke-width: 10;
		stroke-linecap: round;
		transform-origin: 60px 60px;
	}

	.gauge-arc.tier-low {
		stroke: #5ee9b5;
	}

	.gauge-arc.tier-medium {
		stroke: #ffc107;
	}

	.gauge-arc.tier-high {
		stroke: #ff6b6b;
	}

	.gauge-center {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		pointer-events: none;
	}

	.gauge-score {
		font-family: Manrope, system-ui, sans-serif;
		font-size: 2.35rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		line-height: 1;
		color: var(--on-surface);
	}

	.gauge-score.muted {
		font-size: 1.75rem;
		opacity: 0.35;
	}

	.gauge-sub {
		font-size: 0.72rem;
		font-weight: 800;
		letter-spacing: 0.14em;
		color: var(--primary);
		margin-top: 0.35rem;
	}

	.gauge-hint {
		font-size: 0.65rem;
		color: var(--on-surface-variant);
		margin-top: 0.25rem;
		letter-spacing: 0.04em;
	}

	.gauge-empty {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		border: 2px dashed rgba(255, 255, 255, 0.1);
		border-radius: 50%;
	}

	.error {
		color: #ffb4a9;
		margin: 0;
	}

	.placeholder {
		color: var(--on-surface-variant);
		margin: 0;
		line-height: 1.6;
		max-width: 36rem;
	}

	.history-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		margin-bottom: var(--space-md);
	}

	.history-toolbar {
		display: flex;
		gap: 0.35rem;
	}

	.btn-icon {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: rgba(255, 255, 255, 0.04);
		color: var(--on-surface);
		cursor: pointer;
		font-size: 1rem;
		line-height: 1;
	}

	.btn-icon:hover:not(:disabled) {
		border-color: var(--primary);
		color: var(--primary);
	}

	.btn-icon:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.btn-icon.danger:hover {
		border-color: #ff6b6b;
		color: #ff6b6b;
	}

	.table-wrap {
		overflow-x: auto;
		border-radius: 1rem;
		border: 1px solid rgba(255, 255, 255, 0.06);
	}

	.table-empty {
		margin: 0;
		padding: var(--space-lg);
		color: var(--on-surface-variant);
		text-align: center;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.data-table th,
	.data-table td {
		padding: 0.85rem 1rem;
		text-align: left;
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	.data-table th {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--on-surface-variant);
		font-weight: 700;
		background: rgba(0, 0, 0, 0.2);
	}

	.data-table tbody tr:hover {
		background: rgba(255, 255, 255, 0.03);
	}

	.mono {
		font-family: ui-monospace, monospace;
		font-size: 0.8rem;
		color: var(--tertiary);
		white-space: nowrap;
	}

	.category {
		max-width: 14rem;
		color: var(--on-surface);
	}

	.num {
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.risk-cell {
		min-width: 7rem;
	}

	.risk-pct {
		display: block;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		margin-bottom: 0.25rem;
	}

	.mini-track {
		height: 6px;
		border-radius: 99px;
		background: rgba(255, 255, 255, 0.08);
		overflow: hidden;
	}

	.mini-fill {
		height: 100%;
		border-radius: 99px;
		transition: width 0.25s ease;
	}

	.mini-fill.tier-low {
		background: var(--risk-low);
	}

	.mini-fill.tier-medium {
		background: var(--risk-medium);
	}

	.mini-fill.tier-high {
		background: var(--risk-high);
	}

	.status-pill {
		display: inline-block;
		padding: 0.25rem 0.6rem;
		border-radius: 6px;
		font-size: 0.68rem;
		font-weight: 800;
		letter-spacing: 0.06em;
	}

	.status-approved {
		background: rgba(94, 233, 181, 0.15);
		color: var(--risk-low);
	}

	.status-pending {
		background: rgba(255, 255, 255, 0.08);
		color: var(--on-surface-variant);
	}

	.status-rejected {
		background: rgba(255, 107, 107, 0.15);
		color: var(--risk-high);
	}

	.muted.time {
		font-size: 0.8rem;
		color: var(--on-surface-variant);
		white-space: nowrap;
	}

	.footer-note {
		font-size: 0.8rem;
		color: var(--on-surface-variant);
		text-align: center;
		max-width: 44rem;
		margin: var(--space-lg) auto 0;
		line-height: 1.5;
	}
</style>
