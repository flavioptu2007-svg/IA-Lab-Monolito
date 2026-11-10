# Gerar, revisar e salvar materiais de História

O fluxo oferece planos de aula, atividades e avaliações com IA local, revisão do
professor e gravação na mesma base SQLite dos materiais educacionais.

## Preparar o ambiente

Esta funcionalidade depende da persistência do PR #28. Para executar os dois
recursos juntos antes do merge, use a branch deste PR, que já inclui sua base.

1. Instale o projeto com `pip install -e ".[dev]"`.
2. Configure `IA_LAB_EDUCATION_DB_URL` para um arquivo persistente; consulte
   [EDUCATION_STORAGE.md](EDUCATION_STORAGE.md) para caminhos, volumes e backup.
3. Tenha Ollama ativo no servidor com um modelo instalado. Configure
   `IA_LAB_OLLAMA_BASE_URL` (padrão `http://localhost:11434`) e
   `IA_LAB_OLLAMA_MODEL` com o nome do modelo existente.
4. Inicie a API com `uvicorn api.server:app --host 127.0.0.1 --port 8000`.
5. No diretório `web/dashboard`, execute `npm ci` e `npm run dev`.

A geração chama diretamente o provedor Ollama e não usa fallback para nuvem.
Não é necessário configurar chaves de provedores pagos. Modelos menores podem
retornar respostas incompletas; nesse caso o sistema informa a falha sem criar
um material vazio.

## Fluxo do professor

1. No painel, abra **Educação → Criar e revisar com IA**.
2. Se a API exigir autenticação, informe a chave de acesso da escola. Ela fica
   apenas no estado da tela e precisa ser informada novamente após recarregar.
3. Escolha plano de aula, atividade ou avaliação. Informe tema, ano, duração e
   orientações. Os objetivos são opcionais; para planos, os objetivos informados
   são preservados na resposta.
4. Opcionalmente, informe códigos BNCC do catálogo existente para o ano escolhido.
   A validação verifica o catálogo local, que não representa uma certificação de
   cobertura ou correção integral da BNCC oficial.
5. Clique **Gerar e salvar rascunho**. O material é validado e salvo com indicação
   de origem por IA e estado `rascunho`; a geração não aprova automaticamente.
6. Revise e edite título, conteúdo, orientações e, nas avaliações, questões,
   alternativas, gabaritos e pontuação. Nos planos, momentos pedagógicos podem
   ser adicionados e removidos. As avaliações também permitem adicionar/remover questões.
7. Use **Salvar revisão como rascunho** para continuar depois. Para aprovar,
   marque a confirmação de revisão e clique **Aprovar e salvar**.
8. O acervo **Materiais salvos** permite reabrir as versões após reiniciar a API
   ou recarregar o painel. Inclui também materiais criados pelas rotas anteriores.

A aprovação registra `status=aprovado` e `reviewed_at`. Uma nova edição salva
como rascunho remove a aprovação anterior. Se outra sessão tiver alterado o
material, a revisão retorna conflito e mantém o texto que você estava editando
na tela. Reabra a versão recente pelo acervo e reaplique as alterações desejadas.

## Contrato da API

As rotas usam a mesma autenticação `X-API-Key` de `/api/v2/education`.

| Método | Rota | Resultado |
| --- | --- | --- |
| POST | `/api/v2/education/generate` | Gera e persiste um rascunho validado |
| GET | `/api/v2/education/materials?limit=20&offset=0` | Lista o acervo unificado por atualização recente |
| POST | `/api/v2/education/materials/{kind}/{id}/review` | Salva revisão ou aprovação com controle de versão |

`kind` aceita `lesson_plan`, `activity` ou `evaluation`.

Exemplo de solicitação de geração:

```json
{
  "material_type": "lesson_plan",
  "topic": "Fontes históricas e memória da comunidade",
  "academic_year": "EF_6",
  "duration_minutes": 50,
  "learning_objectives": ["Comparar diferentes fontes históricas"],
  "bncc_skills": ["EF06HI02"],
  "instructions": "Proponha trabalho em duplas com cartas e fotografias."
}
```

A resposta contém `material_type` e `material`. Para revisar, envie:

- `content`: somente os campos do schema de criação do tipo escolhido, com suas
  correções; exclua `id`, datas, `status` e `is_ai_generated`.
- `expected_updated_at`: valor exato de `material.updated_at` da versão aberta.
- `approve`: `false` para salvar rascunho; `true` para registrar a aprovação.

O servidor rejeita campos de metadados no conteúdo. As avaliações precisam de
questões com enunciado e gabarito, soma dos pontos igual à pontuação total e nota
mínima não superior ao total. Falhas de validação retornam 422; versão antiga,
409; resposta inválida do modelo, 502; Ollama inacessível ou erro HTTP, 503.
Nesses erros de geração, nenhum rascunho novo é criado. Falhas de gravação na base
continuam sendo propagadas, sem informar que o material foi salvo.

## Verificação e limites

Os testes automatizados simulam o modelo local e verificam geração, edição,
aprovação, reabertura, conflitos e falhas. O teste no navegador usa a aplicação e
o adaptador HTTP Ollama reais, com a resposta do modelo simulada por um servidor
local. Não certifica a qualidade das respostas de um modelo instalado na escola.

O professor deve verificar correção histórica, referências, gabaritos e adequação
à turma. O registro de aprovação expressa a confirmação enviada pela API; não há
assinatura ou identificação individual do professor nesta entrega. A autenticação
continua compartilhada por chave. Não há exportação para PDF/Word, integração
com o Copilot ou sincronização entre servidores nesta etapa.

## Conferir a preservação da revisão entre abas

Com um rascunho aberto, altere um campo sem salvar, abra a aba BNCC Habilidades e
retorne a Criar e revisar com IA. O texto editado e a chave de acesso informada
devem continuar disponíveis. As abas educacionais mantêm o estúdio montado;
essa garantia não equivale a salvar no banco. Use Salvar revisão como rascunho
antes de fechar a página ou navegar para outra seção do painel.
