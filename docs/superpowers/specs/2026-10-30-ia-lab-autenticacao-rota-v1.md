# EGM Spec — Segurança: autorização em rotas v1 do monolito

- Status: **revisão pendente (riscos registrados)** — NÃO alterado ainda. Requer decisão/dashboard.
- Repositório: `flavioptu2007-svg/IA-Lab-Monolito` (working copy `main`, branch `main`)
- Componente: `api/server.py` + `src/api/v2/chat_coragi.py`, `src/api/v2/education.py`, `src/api/v2/openvino.py`

## Contexto
A autenticação por `IA_LAB_API_TOKEN` está aplicada aos routers `/api/v2/**`
(chat, education, openvino) via `require_api_key` (header `X-API-Key`). As rotas
**v1** — `/api/chat`, `/api/providers`, `/api/agents` e `/api/history` — não
passam por `require_api_key` e estão **expostas sem autenticação** independente
de `IA_LAB_API_TOKEN`.

## Decisão
Manter as rotas v1 **sem token** até que o dashboard/portal consuma `X-API-Key`
e a exposição possa ser endurecida. A justificativa é que o navegador/portal
(front-end) não envia `X-API-Key` atualmente, e adicionar a validação v1 exige
migrar o cliente desses endpoints. Registro legal e reversível; a lei é do
dashboard, não da API.

## Risco identificado
| Risco | Severidade | Impacto | Mitigação |
|---|---|---|---|
| Rotas v1 sem token | ALTA | Qualquer cliente (incl. não autorizado) chama `/api/chat` | Proteger apenas quando o cliente puder envia-lo; resolver no dashboard |
| `IA_LAB_API_TOKEN` vazio (dev) desabilita auth | MÉDIA | Dev local expõe sem proteção | O aviso `warn_if_auth_disabled` é registrado no boot; prod Kelley `IA_LAB_API_TOKEN` vazio | flag | falsa |

## Como aplicar (quando o dashboard puder enviar o header)
1. Certificar que o dashboard (`web/dashboard`) envia `X-API-Key` em `/api/chat` e
   companions.
2. Adicionar `dependencies=[Depends(require_api_key)]` às rotas v1 que forem
   expostas pela API (ex.: `/api/v1/chat`), respeitando o contrato do cliente.
3. Reiniciar e testar: sem token → 401; com token válido → 200.
4. Atualizar `.env.example`/documentação com o header obrigatório.

## Evidências
- Login da API real (porta 8011, `IA_LAB_API_TOKEN=supersecrettoken`): v1 `/api/chat`
  não foi testado pois depende do cliente v1; o v2 já confirmou 401/200.
- Saúde: `/api/health/live` e `/api/health/ready` = ok; `qdrant=skipped`
  (RAG disabled), `ollama=ok`.

## Ações pendentes só com autorização
- Fazer o dashboard enviar `X-API-Key` (issue no dashboard).
- Proteger as rotas v1 sem quebrar o cliente.
