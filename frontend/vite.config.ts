import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
	const repoRoot = path.resolve(__dirname, '..');
	const frontendEnv = loadEnv(mode, __dirname, '');
	const rootEnv = loadEnv(mode, repoRoot, '');
	const url =
		frontendEnv.PUBLIC_API_URL ||
		rootEnv.PUBLIC_API_URL ||
		rootEnv.API_URL ||
		'';
	const key =
		frontendEnv.PUBLIC_API_KEY ||
		rootEnv.PUBLIC_API_KEY ||
		rootEnv.API_KEY ||
		'';
	return {
		plugins: [sveltekit()],
		define: {
			'import.meta.env.PUBLIC_API_URL': JSON.stringify(url),
			'import.meta.env.PUBLIC_API_KEY': JSON.stringify(key),
		},
		// Same-origin in dev so the browser never hits cross-origin CORS against Cloud Run.
		// Production static builds still call PUBLIC_API_URL directly (GitHub Pages → API).
		server:
			mode === 'development' && url
				? {
						proxy: {
							'/__credit_risk_api': {
								target: url,
								changeOrigin: true,
								rewrite: (p) => p.replace(/^\/__credit_risk_api/, ''),
							},
						},
					}
				: {},
	};
});
