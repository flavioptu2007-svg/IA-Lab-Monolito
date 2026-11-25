import { isFingerprintError, start, type Agent, type GetResult } from "@fingerprint/agent";

/**
 * Agente JavaScript do Fingerprint (identificação de dispositivo).
 *
 * A public API key vem do ambiente no build do Vite
 * (`VITE_FINGERPRINT_PUBLIC_API_KEY`, veja `.env.example`). Sem a chave o
 * agente simplesmente não é inicializado e o dashboard segue funcionando.
 */
const publicApiKey = import.meta.env.VITE_FINGERPRINT_PUBLIC_API_KEY?.trim();

let agente: Agent | null = null;
let inicializacao: Promise<GetResult | null> | null = null;
let visitorId: string | null = null;

function criarAgente(): Agent | null {
  if (agente) return agente;
  if (!publicApiKey) return null;
  agente = start({ apiKey: publicApiKey });
  return agente;
}

/**
 * Carrega o agente e faz a primeira identificação do visitante.
 *
 * O resultado (e a falha) é memorizado: chamadas seguintes reaproveitam a mesma
 * promise em vez de disparar novas identificações.
 */
export function iniciarFingerprint(): Promise<GetResult | null> {
  if (inicializacao) return inicializacao;

  const instancia = criarAgente();
  if (!instancia) {
    if (import.meta.env.DEV) {
      console.warn(
        "[fingerprint] VITE_FINGERPRINT_PUBLIC_API_KEY ausente — agente não inicializado.",
      );
    }
    return Promise.resolve(null);
  }

  inicializacao = instancia
    .get()
    .then((resultado) => {
      visitorId = resultado.visitor_id ?? null;
      return resultado;
    })
    .catch((erro: unknown) => {
      // Falha de identificação não pode derrubar a aplicação: libera nova tentativa.
      inicializacao = null;
      const motivo = isFingerprintError(erro) ? `${erro.code}: ${erro.message}` : String(erro);
      console.warn("[fingerprint] não foi possível identificar o visitante:", motivo);
      return null;
    });

  return inicializacao;
}

/**
 * Identificador já resolvido, ou `null` se a identificação ainda não terminou
 * (ou não está configurada). Não bloqueia: use em cabeçalhos de requisição.
 */
export function visitorIdAtual(): string | null {
  return visitorId;
}

/** Identificador do visitante, ou `null` se o agente não estiver configurado/disponível. */
export async function obterVisitorId(): Promise<string | null> {
  await iniciarFingerprint();
  return visitorId;
}
