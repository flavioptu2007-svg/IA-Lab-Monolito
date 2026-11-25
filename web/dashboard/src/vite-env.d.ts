/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public API key do workspace Fingerprint, usada pelo agente em `src/fingerprint.ts`. */
  readonly VITE_FINGERPRINT_PUBLIC_API_KEY?: string;
}
