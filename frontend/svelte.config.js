import adapter from '@sveltejs/adapter-static';

const dev = process.env.NODE_ENV === 'development';
/** GitHub Pages project URL path (set in CI). Local production preview: `SVELTEKIT_BASE_PATH=/credit-risk-ml npm run build` */
const prodBase =
	(process.env.SVELTEKIT_BASE_PATH && process.env.SVELTEKIT_BASE_PATH.trim()) || '/credit-risk-ml';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: undefined,
			strict: true,
		}),
		paths: {
			base: dev ? '' : prodBase,
		},
	},
};

export default config;
