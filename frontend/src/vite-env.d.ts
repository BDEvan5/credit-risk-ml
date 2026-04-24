/// <reference types="svelte" />
/// <reference types="@sveltejs/kit" />

interface ImportMetaEnv {
	readonly PUBLIC_API_URL: string;
	readonly PUBLIC_API_KEY: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
