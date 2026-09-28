# AGENTS.md — Regras permanentes para agentes de IA neste ambiente

## Regra nº 1 — Custo zero, sempre ( ZERO-SPENDING POLICY )

**Nenhuma ação pode gerar custo financeiro, em nenhuma circunstância, sem aprovação
explícita e prévia do Flavio.** Isto vale para todas as decisões, automáticas ou não.

### Proibido por padrão
- Chamar APIs de IA/infra **pagas** (modelos pagos da OpenRouter, OpenAI, Anthropic, Gemini pago, AWS/Azure/GCP faturáveis etc.)
- Criar contas, assinaturas, trials que exijam **cartão de crédito**
- Comprar, alugar ou provisionar qualquer recurso pago (domínios, VPS, storage, GPUs em nuvem)
- Instalar dependências que exijam licença paga

### Autorizado por padrão (lista de preferência, nesta ordem)
1. **Modelos locais** — Ollama (system store) e LM Studio já instalados neste machine
2. **Modelos gratuitos** — OpenRouter com sufixo `:free` (pricing 0/0), free tiers sem cartão
3. Ferramentas open-source, repositórios públicos, documentação
4. Free tiers de serviços (somente os que não exigem cartão e não convertem para pago sozinhos)

### Salvaguardas já implementadas
- `chat_openrouter.py` **recusa modelos pagos** por padrão (verifica pricing na API;
  escape explícito: `--allow-paid`, nunca usar sem pedido expresso do Flavio)
- `.env` não contém chave da OpenRouter → chamadas pagas falham por falta de credencial;
  **não adicionar chaves pagas sem pedido expresso**

### Decisão autônoma
Exceto gastos, o agente pode decidir sozinho: limpeza de disco (respeitando os
guardrails dos scripts `monthly-*`), organização, criação/edição de arquivos,
diagnósticos e otimizações locais. Ações irreversíveis fora do ambiente local
(git push, deploys, envio de e-mail, publicações) continuam exigindo confirmação.

---
*Mandato dado por Flavio em 2026-09-13: "Tomar todas as decisões sem nunca gastar dinheiro".*
