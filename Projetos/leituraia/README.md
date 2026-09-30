# 📖 LeituraIA Brasil — Módulo (MVP)

Plataforma SaaS de **compreensão leitora com IA** para escolas brasileiras, alinhada à **BNCC** e ao **CRMG** (Currículo Referência de Minas Gerais). Este módulo é o **MVP funcional** escafoldado a partir do IA-Lab Monolito — inspirado na ReadWorks, porém original, com foco em História e material didático em português.

> ⚠️ **Status:** MVP (fase 1 do Prompt Mestre). Autenticação em memória, banco de textos semeados local, gerador com fallback offline. As próximas fases trocam o store por PostgreSQL, adicionam microsserviços de IA e o banco vetorial Qdrant (já disponível no monolito).

---

## ✅ O que já funciona

| Módulo | Descrição |
|---|---|
| 🔐 **Auth + RBAC** | JWT + refresh token, 11 perfis (admin → aluno/responsável), permissões por rota (`leituraia/rbac.py`) |
| 📚 **Biblioteca** | Textos semeados (Feudalismo 7º, Caminha 1500, Gandavo) com filtros: ano, disciplina, BNCC, tema, palavras, tempo de leitura |
| 🤖 **Gerador IA** | Gera texto + glossário + curiosidades + perguntas a partir de (ano, disciplina, tema, BNCC, palavras, nível). **Offline-first**: sem chave de API, cai no template pedagógico local |
| 📖 **Leitor Digital** | Página HTML acessível renderizada **no servidor** (sem fetch autenticado, sem vazar gabarito): fonte A+/A/A−, alto contraste, impressão, glossário e perguntas de compreensão |
| 📊 **Dashboard** | Leituras, desempenho médio, habilidades trabalhadas (agregados in-memory) |
| 🧠 **Busca semântica** | Endpoint preparado com embeddings (usa o `VectorStore` do monolito quando `LEITURAIA_EMBEDDINGS=1`) |

---

## 🚀 Como rodar

```bash
# 1. Servidor (porta 8010 para não colidir com o monolito)
cd ~
LEITURAIA_OFFLINE=1 python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8010

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

---

## 📁 Estrutura

```
leituraia/
├── __init__.py    # versão e export do router
├── config.py      # configuração (JWT secret, expiração, offline)
├── rbac.py        # 11 perfis + matriz de permissões + dependency FastAPI
├── auth.py        # JWT access/refresh, hash PBKDF2 (stdlib, sem deps)
├── models.py      # schemas Pydantic (usuário, texto, questão, leitura…)
├── generator.py   # gerador IA com fallback offline (template pedagógico)
├── library.py     # catálogo de textos semeados (Feudalismo + Gutenberg)
├── routes.py      # APIRouter: auth, biblioteca, gerador, dashboard, leitor
└── README.md
```

**Integração:** o router é registrado em `src/core/routers.py` (prefixo `/api/leituraia`). Testes: `tests/test_leituraia.py` (19 testes).

---

## 🔒 Segurança (fase 1)

- Hash de senha **PBKDF2-SHA256** (stdlib `hashlib`/`hmac` + salt) — sem dependência externa
- JWT com expiração de access (60 min) e refresh (7 dias), assinatura HS256
- RBAC por perfil em todas as rotas (ex.: aluno não gera materiais, admin gerencia tudo)
- LGPD básica: nenhum dado sai da memória; docs pedem avaliação para produção

---

## 🗺️ Roadmap (próximas fases)

1. **Fase 2 — Persistência:** PostgreSQL + Prisma/ORM, migrar stores em memória
2. **Fase 3 — IA real:** agentes especializados (BNCC, CRMG, Inclusiva) no padrão `ai/agents/` do monolito + Qdrant p/ busca semântica
3. **Fase 4 — Editor Inteligente:** tipTap/ProseMirror (texto, imagens, tabelas, comentários)
4. **Fase 5 — Gamificação:** XP, missões, medalhas (reusa conceitos do HistóriaGames)
5. **Fase 6 — Exportação:** DOCX/PDF via `python-docx`/`reportlab`
6. **Fase 7 — Acessibilidade ampliada:** modo TEA/TDAH/Dislexia (OpenDyslexic), Libras
