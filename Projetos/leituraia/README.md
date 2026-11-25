# 📖 LeituraIA Brasil — Módulo (MVP)

Plataforma SaaS de **compreensão leitora com IA** para escolas brasileiras, alinhada à **BNCC** e ao **CRMG** (Currículo Referência de Minas Gerais). Este módulo é o **MVP funcional** escafoldado a partir do IA-Lab Monolito — inspirado na ReadWorks, porém original, com foco em História e material didático em português.

> ✅ **Status:** MVP (fases 1 e 2 do Prompt Mestre). Autenticação, biblioteca e leituras persistidas via **SQLAlchemy 2.0** — PostgreSQL em produção (`LEITURAIA_DATABASE_URL`) e SQLite local por padrão no desenvolvimento (configurável por `LEITURAIA_DB_PATH`), com migrações versionadas no Alembic. Textos semeados e gerador com fallback offline. As próximas fases evoluem para microsserviços de IA e o banco vetorial Qdrant (já disponível no monolito).

---

## ✅ O que já funciona

| Módulo | Descrição |
|---|---|
| 🔐 **Auth + RBAC** | JWT + refresh token, 11 perfis (admin → aluno/responsável), permissões por rota (`leituraia/rbac.py`) |
| 💾 **Persistência** | SQLAlchemy 2.0 (`leituraia/orm.py` + `leituraia/db.py`): usuários, textos e leituras em PostgreSQL ou SQLite — o acervo semeado não duplica ao reiniciar |
| 📚 **Biblioteca** | Textos semeados (Feudalismo 7º, Caminha 1500, Gandavo) com filtros: ano, disciplina, BNCC, tema, palavras, tempo de leitura |
| 🏠 **Página inicial** | `/leituraia` lista a biblioteca em HTML com filtros por disciplina, ano e busca de tema, e leva ao Leitor Digital |
| 🤖 **Gerador IA** | Gera texto + glossário + curiosidades + perguntas a partir de (ano, disciplina, tema, BNCC, palavras, nível). **Offline-first**: sem chave de API, cai no template pedagógico local |
| 📖 **Leitor Digital** | Página HTML acessível renderizada **no servidor** (sem fetch autenticado, sem vazar gabarito): fonte A+/A/A−, alto contraste, impressão, glossário e perguntas de compreensão. Registra a leitura **automaticamente** (endpoint público idempotente por sessão) |
| 📊 **Dashboard** | Leituras, desempenho médio, habilidades trabalhadas (agregados in-memory) |
| 🧠 **Busca semântica** | Endpoint preparado com embeddings (usa o `VectorStore` do monolito quando `LEITURAIA_EMBEDDINGS=1`) |

---

## 🚀 Como rodar

```bash
# 1. Servidor (porta 8010 para não colidir com o monolito)
cd ~/Projetos
LEITURAIA_OFFLINE=1 python3 -m uvicorn web.api.server:app --host 127.0.0.1 --port 8010

# 2. Registrar usuário (retorna access_token)
curl -X POST http://127.0.0.1:8010/api/leituraia/auth/registro \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Prof. Ana","email":"ana@escola.edu.br","senha":"senha123","perfil":"professor"}'

# 3. Listar biblioteca (Bearer token)
curl http://127.0.0.1:8010/api/leituraia/biblioteca \
  -H "Authorization: Bearer <token>"

# 4. Abrir o Leitor Digital (página pública renderizada no servidor)
#    http://127.0.0.1:8010/leituraia/leitor/<id-do-texto>
```

**Sem chave de API?** Funciona tudo em modo offline (`LEITURAIA_OFFLINE=1`). Para usar LLM real, configure `OPENAI_API_KEY`/`OLLAMA` (reusa `ai/settings.py` do monolito).

**Banco:** em desenvolvimento o SQLite é criado automaticamente em `leituraia/data/leituraia.db`; defina `LEITURAIA_DB_PATH` para usar outro arquivo ou `LEITURAIA_DATABASE_URL` para qualquer banco suportado pelo SQLAlchemy (ex.: `postgresql+psycopg://usuario:senha@host/leituraia`). Enquanto a tabela estiver vazia, o acervo inicial é semeado na primeira conexão (os testes usam um banco temporário). O painel não exige o pacote `ai/`: sem ele, `/api/health` reporta `monolito: unavailable` e os endpoints de IA respondem 503.

**Registro de leitura:** o Leitor Digital envia sozinho `POST /leituraia/leitor/{id}/leitura` (sem login) ao sair da página, ao trocar de aba ou após 30 s; visitas menores que 5 s não contam e a mesma sessão (`crypto.randomUUID()`) nunca é contada duas vezes. O endpoint autenticado `POST /api/leituraia/biblioteca/{id}/leitura/registro` continua disponível para clientes com token.

---

## 🗄️ Migrações (Alembic)

O schema é versionado em `leituraia/migrations/versions` e tem como fonte da verdade o ORM (`leituraia/orm.py`). Em produção, aplique as migrações em vez de deixar o app criar as tabelas:

```bash
cd ~/Projetos
LEITURAIA_DATABASE_URL='postgresql+psycopg://usuario:senha@host/leituraia' \
  python3 -m alembic -c leituraia/alembic.ini upgrade head
```

Em desenvolvimento/testes, `init_db()` usa `create_all` no SQLite local — não é preciso rodar Alembic. A suíte aceita `LEITURAIA_TEST_DATABASE_URL` para rodar contra um PostgreSQL de verdade (as tabelas são truncadas antes de cada teste):

```bash
cd ~/Projetos
LEITURAIA_TEST_DATABASE_URL='postgresql+psycopg://leituraia:leituraia@localhost:5432/leituraia' \
  python3 -m pytest leituraia/tests -q
```

Nesse modo, `tests/test_postgres.py` valida a **migração** de ponta a ponta: `upgrade head` cria o schema e grava a revisão, `upgrade` repetido não duplica a versão, `downgrade base` remove as tabelas, o índice único parcial por sessão existe e o schema migrado é idêntico ao do ORM (`compare_metadata` vazio). Em seguida exercita a API sobre esse schema — registro/login, publicação de texto, leitura autenticada e pública (idempotente por sessão), página do Leitor Digital sem gabarito e persistência para uma nova conexão. Sem a variável, esses testes são pulados e a suíte roda em SQLite.

---

## 📁 Estrutura

```
leituraia/
├── __init__.py    # versão e export do router
├── config.py      # configuração (JWT secret, expiração, offline)
├── db.py          # engine/sessões SQLAlchemy, URL do banco e init_db
├── orm.py         # modelos ORM (usuarios, textos, leituras)
├── migrations/    # migrações Alembic (env.py + versions/)
├── alembic.ini    # configuração do Alembic (URL vem do ambiente)
├── rbac.py        # 11 perfis + matriz de permissões + dependency FastAPI
├── auth.py        # JWT access/refresh, hash PBKDF2 (stdlib, sem deps)
├── models.py      # schemas Pydantic (usuário, texto, questão, leitura…)
├── generator.py   # gerador IA com fallback offline (template pedagógico)
├── library.py     # acervo e leituras no banco (sementes: Feudalismo, Caminha, Ciclo da água)
├── routes.py      # APIRouter: auth, biblioteca, gerador, dashboard, páginas HTML
├── data/          # banco SQLite local (ignorado pelo git)
└── README.md
```

**Integração:** o `web/api/server.py` monta os routers do módulo (`/api/leituraia`, a página inicial `/leituraia` e o Leitor Digital em `/leituraia/leitor/{id}`). Testes: `leituraia/tests/` (unitários, incluindo `test_db.py`) e `web/api/tests/test_server.py` (integração com o painel).

---

## 🔒 Segurança (fase 1)

- Hash de senha **PBKDF2-SHA256** (stdlib `hashlib`/`hmac` + salt) — sem dependência externa
- JWT com expiração de access (60 min) e refresh (7 dias), assinatura HS256
- RBAC por perfil em todas as rotas (ex.: aluno não gera materiais, admin gerencia tudo)
- LGPD básica: dados ficam no banco local/da escola (sem envio externo); docs pedem avaliação para produção

---

## 🗺️ Roadmap (próximas fases)

1. **Fase 2 — Persistência:** ✅ SQLAlchemy 2.0 + Alembic (PostgreSQL em produção, SQLite no desenvolvimento) para múltiplas instâncias
2. **Fase 3 — IA real:** agentes especializados (BNCC, CRMG, Inclusiva) no padrão `ai/agents/` do monolito + Qdrant p/ busca semântica
3. **Fase 4 — Editor Inteligente:** tipTap/ProseMirror (texto, imagens, tabelas, comentários)
4. **Fase 5 — Gamificação:** XP, missões, medalhas (reusa conceitos do HistóriaGames)
5. **Fase 6 — Exportação:** DOCX/PDF via `python-docx`/`reportlab`
6. **Fase 7 — Acessibilidade ampliada:** modo TEA/TDAH/Dislexia (OpenDyslexic), Libras
