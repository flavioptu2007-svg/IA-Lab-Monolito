import { useEffect, type ReactNode } from "react";
import { FingerprintProvider, useVisitorData } from "@fingerprint/react";

/**
 * Identificação de dispositivo com o SDK React do Fingerprint.
 *
 * A public API key vem do ambiente no build do Vite
 * (`VITE_FINGERPRINT_PUBLIC_API_KEY`, veja `.env.example`). Sem a chave o
 * provider nem é montado e o dashboard segue funcionando.
 */
const apiKey = import.meta.env.VITE_FINGERPRINT_PUBLIC_API_KEY?.trim();

/**
 * Snapshot do último visitante identificado, para quem está fora do React
 * (ex.: cabeçalhos do cliente de API). Atualizado pelo `<SincronizarVisitorId>`.
 */
let visitorId: string | null = null;

if (import.meta.env.DEV && !apiKey) {
  console.warn("[fingerprint] VITE_FINGERPRINT_PUBLIC_API_KEY ausente — identificação desativada.");
}

/** Identificador já resolvido, ou `null` se ainda não houve identificação. */
export function visitorIdAtual(): string | null {
  return visitorId;
}

/** Publica o resultado do hook fora do React e registra falhas sem quebrar a UI. */
function SincronizarVisitorId() {
  const { data, error } = useVisitorData();

  useEffect(() => {
    visitorId = data?.visitor_id ?? null;
  }, [data]);

  useEffect(() => {
    if (error) {
      console.warn("[fingerprint] não foi possível identificar o visitante:", error.message);
    }
  }, [error]);

  return null;
}

/** Monta o `FingerprintProvider` quando há chave configurada. */
export function FingerprintRoot({ children }: { children: ReactNode }) {
  if (!apiKey) return <>{children}</>;

  return (
    <FingerprintProvider apiKey={apiKey}>
      <SincronizarVisitorId />
      {children}
    </FingerprintProvider>
  );
}
