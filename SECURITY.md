# Política de Segurança

Este é um projeto pessoal, local-first e de custo zero — mantido por uma pessoa,
sem bug bounty e sem infraestrutura em nuvem paga. Levamos a sério, ainda assim,
qualquer falha que possa causar perda de dados, execução de código ou vazamento
de credenciais na máquina de quem roda o monolito.

## Versões suportadas

| Versão | Suporte de segurança |
| ------ | -------------------- |
| 2.1.x (branch `main`) | ✅ correções aplicadas |
| < 2.1 | ❌ sem suporte — atualize |

## Como reportar

**Não abra uma issue pública** para vulnerabilidades. Use um dos canais privados:

1. **GitHub Security Advisories (preferido)**
   <https://github.com/flavioptu2007-svg/IA-Lab-Monolito/security/advisories/new>
   Permite discutir e corrigir o problema em um fork privado até a divulgação
   coordenada, com crédito automático a quem reportou.
2. **E-mail:** `flavioptu2007@gmail.com`, com o assunto `[SECURITY] IA-Lab-Monolito`.

### O que incluir no relatório

- versão/commit afetado (`git rev-parse HEAD`) e sistema operacional;
- passos de reprodução ou PoC mínima (evite tocar em dados reais);
- impacto esperado e se há exploração conhecida;
- como você quer ser creditado — ou se prefere permanecer anônimo.

### Prazos (melhor esforço)

| Etapa | Alvo |
| ----- | ---- |
| Confirmação de recebimento | 7 dias |
| Avaliação inicial de severidade | 14 dias |
| Correção ou plano com data | 30 dias |
| Divulgação coordenada | junto da release com a correção |

Não há recompensa financeira. Relatórios gerados apenas por scanner automático,
sem impacto demonstrado, podem ser fechados sem análise detalhada.

## Escopo

**Em escopo:**

- API FastAPI (`api/`, `src/`, `ai/`) — rotas, validação de entrada, SSRF,
  autenticação, injeção, path traversal, exposição de segredos em resposta/log;
- scripts shell versionados (`scripts/`) — injeção de comando, uso inseguro de
  `eval`/globbing, escrita em caminho arbitrário;
- dashboards Vite (`web/dashboard/`, `web/ui/`) — XSS, exposição de token;
- aplicativos em `Projetos/` (`next-app`, `web`, `leituraia`) naquilo que é
  construído pelo CI/CD deste repositório;
- workflows de CI/CD (`.github/workflows/`) — injeção por entrada de workflow,
  permissões de token, exfiltração de segredos em PRs de fork.

**Fora de escopo:**

- o ambiente local do mantenedor (`.env`, Ollama/LM Studio, Qdrant, Redis —
  nada disso é exposto por este repositório);
- vulnerabilidades em serviços de terceiros (Ollama, Qdrant, Redis, provedores
  de LLM): reporte ao fornecedor;
- subir a API sem `IA_LAB_API_TOKEN` **e** expô-la fora de `localhost`: a
  ausência de autenticação nesse cenário é documentada, avisada no boot
  (`src/core/security.py`) e não é tratada como vulnerabilidade;
- engenharia social, força bruta, spam e DoS volumétrico.

## Modelo de ameaça (resumo)

O projeto é **local-first**: roda na máquina do usuário, normalmente em
`localhost` ou na LAN doméstica, sem multiusuário, sem cookies e sem sessão.
Todas as salvaguardas partem daí.

Controles já presentes no código:

- **API key opcional** nos routers `/api/v2` via `IA_LAB_API_TOKEN`
  (`X-API-Key`, comparada com `hmac.compare_digest` para não vazar por timing);
- **validação anti-SSRF** de `api_base_url`: bloqueia esquemas não-HTTP(S),
  hosts de metadata de cloud e endereços link-local; hosts privados/loopback só
  passam com `IA_LAB_ALLOW_PRIVATE_API_HOSTS=true` (default, por ser local-first);
- **guarda de boot do segredo JWT**: com `IA_LAB_ENVIRONMENT=production` a
  aplicação **se recusa a subir** com o valor padrão de
  `IA_LAB_EDUCATION_JWT_SECRET`; em desenvolvimento apenas registra aviso;
- **segredos fora do repositório**: chaves em variáveis de ambiente/`.env`
  (gitignored), sem credencial versionada; `.dockerignore` em allowlist para o
  contexto de build não levar o repositório inteiro;
- **custo zero por design**: nenhuma chamada paga é feita sem autorização
  explícita — em HTTP 402/429 o chat cai para modelo gratuito ou provedor local.

Para expor a API além de `localhost`, o mínimo aceitável é:

1. definir `IA_LAB_API_TOKEN` (`openssl rand -hex 32`);
2. definir `IA_LAB_EDUCATION_JWT_SECRET` forte;
3. `IA_LAB_ALLOW_PRIVATE_API_HOSTS=false`;
4. terminar TLS em um proxy reverso (a API não fala HTTPS sozinha).

## Divulgação

Corrigimos primeiro, publicamos depois, e creditamos quem autorizar. Se você
encontrar algo que este documento não cobre, mande mesmo assim — preferimos um
relatório a mais do que uma falha silenciosa.

---

*Última atualização: 2026-09-30*
