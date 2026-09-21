# MODEL_CARD — Coraci Chat

## Estado documentado em 2026-09-21

O Coraci possui dois caminhos de execução:
- aplicativo Flask legado em `Aplicativo_Coraci/`;
- endpoint integrado FastAPI em `src/api/v2/chat_coraci.py`.

A configuração versionada usa Ollama local por padrão:
- endpoint: `http://localhost:11434/v1`;
- modelo: `glm4:latest`.

O modelo remoto anteriormente identificado como `glm-5.2-colibri` não tem proveniência de checkpoint ou dataset documentada neste repositório e não é tratado como modelo local disponível.

## Segurança

API keys não devem ser armazenadas em `config.json`. O código aceita `CORACI_API_KEY` por variável de ambiente e, ao persistir a configuração, grava o campo `api_key` vazio.

Também são aceitos por ambiente:
- `CORACI_API_BASE_URL`;
- `CORACI_MODEL`;
- `CORACI_API_KEY`.

## Parâmetros

`temperature` aceita valores de 0 a 2.
`max_tokens` aceita inteiros maiores ou iguais a 0.

Valores explícitos iguais a zero são preservados durante a chamada ao provedor.

## Reprodutibilidade

Não foi identificado checkpoint fine-tuned versionado neste repositório para o modelo original `glm-5.2-colibri`. Qualquer modelo customizado deve ter origem, versão, hash/checksum e dataset documentados antes de ser tratado como reproduzível.

## Fallback

O fallback Ollama foi aplicado para eliminar a dependência operacional do endpoint local indisponível em `localhost:8000`. O benchmark registrado na auditoria local de 2026-09-21 apontou menor latência e maior throughput para `glm4:latest` do que para `deepseek-r1:8b`; esses valores são específicos daquela máquina e execução e não constituem garantia de desempenho futuro.
