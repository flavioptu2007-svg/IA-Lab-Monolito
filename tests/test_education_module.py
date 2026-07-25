"""Testes do módulo Education — Planos, atividades, avaliações, BNCC.

Cobre:
- Enums educacionais (AcademicYear, BNCCCompetence, etc.)
- Schemas Pydantic (LessonPlanCreate, ActivityCreate, EvaluationCreate)
- Services (EducationStore CRUD, BNCC service)
- Endpoints FastAPI em ``src/api/v2/education.py``
- Router registrado na app principal (api/server.py)
"""

from __future__ import annotations

import pytest

# ═════════════════════════════════════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════════════════════════════════════


class TestEducationEnums:
    """Testes para enums educacionais."""

    def test_academic_year_values(self):
        """Deve ter anos/séries do EF, EM e EJA."""
        from src.education.enums import AcademicYear

        assert AcademicYear.EF_6.value == "6º ano EF"
        assert AcademicYear.EM_1.value == "1º ano EM"
        assert AcademicYear.EJA_1.value == "EJA 1º segmento"

    def test_bncc_competence_count(self):
        """Deve ter 8 competências específicas de História."""
        from src.education.enums import BNCCCompetence

        assert len(list(BNCCCompetence)) == 8

    def test_evaluation_types(self):
        """Deve ter tipos de avaliação incluindo prova e projeto."""
        from src.education.enums import EvaluationType

        types = list(EvaluationType)
        assert EvaluationType.EXAM in types
        assert EvaluationType.PROJECT in types
        assert EvaluationType.ORAL in types

    def test_activity_types(self):
        """Deve ter tipos de atividade como flashcard e domino."""
        from src.education.enums import ActivityType

        assert ActivityType.FLASHCARD.value == "Flashcard"
        assert ActivityType.DOMINO.value == "Dominó"
        assert ActivityType.TIMELINE.value == "Linha do tempo"

    def test_bncc_skills_dict(self):
        """O dicionário BNCC_SKILLS deve ter habilidades mapeadas."""
        from src.education.enums import BNCC_SKILLS

        assert len(BNCC_SKILLS) >= 30
        assert "EF06HI01" in BNCC_SKILLS
        assert "EM13CHS101" in BNCC_SKILLS
        assert "tempo" in BNCC_SKILLS["EF06HI01"].lower()

    def test_lesson_moment_values(self):
        """Deve ter os 3 momentos pedagógicos."""
        from src.education.enums import LessonMoment

        assert LessonMoment.INTRODUCTION.value == "Introdução"
        assert LessonMoment.DEVELOPMENT.value == "Desenvolvimento"
        assert LessonMoment.CLOSURE.value == "Conclusão"

    def test_lesson_plan_status(self):
        """Deve ter status DRAFT, REVIEW, APPROVED, ARCHIVED."""
        from src.education.enums import LessonPlanStatus

        assert LessonPlanStatus.DRAFT.value == "Rascunho"
        assert LessonPlanStatus.APPROVED.value == "Aprovado"
        assert LessonPlanStatus.ARCHIVED.value == "Arquivado"


# ═════════════════════════════════════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════════════════════════════════════


class TestEducationSchemas:
    """Testes para schemas Pydantic."""

    def test_lesson_plan_create_minimal(self):
        """Deve criar com apenas o título obrigatório."""
        from src.education.schemas import LessonPlanCreate

        plan = LessonPlanCreate(title="Brasil Colônia")
        assert plan.title == "Brasil Colônia"
        assert plan.academic_year == "EF_8"
        assert plan.duration_minutes == 50

    def test_lesson_plan_create_completo(self):
        """Deve criar com todos os campos."""
        from src.education.schemas import LessonPlanCreate, LessonMomentContent

        plan = LessonPlanCreate(
            title="Revolução Francesa",
            topic="França pré-revolucionária",
            academic_year="EF_8",
            trimester="T2",
            subject="História",
            learning_objectives=["Compreender causas da Revolução"],
            bncc_skills=["EF08HI03"],
            duration_minutes=100,
            moments=[
                LessonMomentContent(
                    moment="INTRODUÇÃO",
                    title="Contexto",
                    description="Contexto histórico",
                    duration_minutes=20,
                    methodology="Aula expositiva dialogada",
                    order=0,
                )
            ],
        )
        assert plan.title == "Revolução Francesa"
        assert len(plan.moments) == 1

    def test_activity_create(self):
        """Deve criar atividade com campos obrigatórios."""
        from src.education.schemas import ActivityCreate

        activity = ActivityCreate(
            title="Linha do tempo do Brasil Império", activity_type="TIMELINE"
        )
        assert activity.title == "Linha do tempo do Brasil Império"
        assert activity.difficulty == "MÉDIO"
        assert activity.duration_minutes == 20

    def test_evaluation_create(self):
        """Deve criar avaliação com questões."""
        from src.education.schemas import EvaluationCreate, QuestionSchema

        eval_data = EvaluationCreate(
            title="Prova - Brasil República",
            evaluation_type="EXAM",
            academic_year="EF_9",
            questions=[
                QuestionSchema(
                    number=1,
                    type="OBJETIVA",
                    command="Qual ano da Proclamação da República?",
                    options=["1888", "1889", "1890", "1891"],
                    correct_answer="1889",
                    score=2.0,
                )
            ],
        )
        assert eval_data.title == "Prova - Brasil República"
        assert len(eval_data.questions) == 1
        assert eval_data.questions[0].correct_answer == "1889"
        assert eval_data.total_score == 10.0

    def test_bncc_filter_params(self):
        """Deve criar filtro BNCC."""
        from src.education.schemas import BNCCFilterParams

        filtro = BNCCFilterParams(year="EF_8", competence="CE03", query="Revolução")
        assert filtro.year == "EF_8"
        assert filtro.competence == "CE03"

    def test_calendar_event_create(self):
        """Deve criar evento de calendário."""
        from datetime import date
        from src.education.schemas import CalendarEventCreate

        event = CalendarEventCreate(
            title="Avaliação bimestral", event_date=date(2026, 6, 15), event_type="PROVA"
        )
        assert event.title == "Avaliação bimestral"
        assert str(event.event_date) == "2026-06-15"

    def test_lesson_plan_response_defaults(self):
        """O schema de resposta deve ter defaults seguros."""
        from src.education.schemas import LessonPlanResponse

        resp = LessonPlanResponse()
        assert resp.title == ""
        assert resp.status == "rascunho"
        assert resp.moments == []
        assert resp.is_ai_generated is False

    def test_school_schema(self):
        """Deve criar schema de escola."""
        from src.education.schemas import SchoolSchema

        school = SchoolSchema(
            name="Escola Municipal José de Alencar",
            short_name="EMJA",
            cnpj="12.345.678/0001-90",
            city="São Paulo",
            state="SP",
        )
        assert school.name == "Escola Municipal José de Alencar"
        assert school.is_active is True


# ═════════════════════════════════════════════════════════════════════════════
# Services — EducationStore
# ═════════════════════════════════════════════════════════════════════════════


class TestEducationStore:
    """Testes para EducationStore CRUD."""

    @pytest.fixture
    def store(self):
        """Retorna uma instância limpa do EducationStore."""
        from src.education.services import get_store

        # Reseta o singleton para cada teste
        import src.education.services as svc

        svc._store = None
        return get_store()

    def test_create_lesson_plan(self, store):
        """Deve criar e armazenar um plano de aula."""
        from src.education.schemas import LessonPlanCreate

        plan = store.create_lesson_plan(LessonPlanCreate(title="Ditadura Militar"))
        assert plan.id
        assert plan.title == "Ditadura Militar"
        assert len(store._lesson_plans) == 1

    def test_get_lesson_plan(self, store):
        """Deve recuperar plano pelo ID."""
        from src.education.schemas import LessonPlanCreate

        created = store.create_lesson_plan(LessonPlanCreate(title="Era Vargas"))
        fetched = store.get_lesson_plan(created.id)
        assert fetched is not None
        assert fetched.title == "Era Vargas"

    def test_get_lesson_plan_inexistente(self, store):
        """Deve retornar None para ID inexistente."""
        result = store.get_lesson_plan("nao_existe")
        assert result is None

    def test_list_lesson_plans_com_filtro(self, store):
        """Deve filtrar planos por ano/série."""
        from src.education.schemas import LessonPlanCreate

        store.create_lesson_plan(LessonPlanCreate(title="A", academic_year="EF_6"))
        store.create_lesson_plan(LessonPlanCreate(title="B", academic_year="EF_8"))
        store.create_lesson_plan(LessonPlanCreate(title="C", academic_year="EF_8"))

        filtered = store.list_lesson_plans(academic_year="EF_8")
        assert len(filtered) == 2

    def test_update_lesson_plan(self, store):
        """Deve atualizar campos do plano."""
        from src.education.schemas import LessonPlanCreate, LessonPlanUpdate

        created = store.create_lesson_plan(LessonPlanCreate(title="Original"))
        updated = store.update_lesson_plan(
            created.id, LessonPlanUpdate(title="Modificado", status="approved")
        )
        assert updated is not None
        assert updated.title == "Modificado"
        assert updated.status == "approved"

    def test_update_lesson_plan_inexistente(self, store):
        """Deve retornar None ao atualizar ID inexistente."""
        from src.education.schemas import LessonPlanUpdate

        result = store.update_lesson_plan("fake_id", LessonPlanUpdate(title="X"))
        assert result is None

    def test_delete_lesson_plan(self, store):
        """Deve remover plano e retornar True."""
        from src.education.schemas import LessonPlanCreate

        created = store.create_lesson_plan(LessonPlanCreate(title="Remover"))
        assert store.delete_lesson_plan(created.id) is True
        assert store.get_lesson_plan(created.id) is None

    def test_delete_lesson_plan_inexistente(self, store):
        """Deve retornar False ao remover ID inexistente."""
        from src.education.services import get_store

        assert get_store().delete_lesson_plan("fake_id") is False

    def test_create_activity(self, store):
        """Deve criar atividade."""
        from src.education.schemas import ActivityCreate

        act = store.create_activity(
            ActivityCreate(title="Quiz Roma Antiga", activity_type="FLASHCARD")
        )
        assert act.id
        assert act.title == "Quiz Roma Antiga"

    def test_create_evaluation(self, store):
        """Deve criar avaliação com questões."""
        from src.education.schemas import EvaluationCreate, QuestionSchema

        eval_data = store.create_evaluation(
            EvaluationCreate(
                title="Prova - Grécia Antiga",
                questions=[
                    QuestionSchema(number=1, type="OBJETIVA", command="?", correct_answer="A")
                ],
            )
        )
        assert eval_data.id
        assert len(eval_data.questions) == 1

    def test_calendar_crud(self, store):
        """Deve criar e listar eventos do calendário."""
        from datetime import date
        from src.education.schemas import CalendarEventCreate

        store.create_event(
            CalendarEventCreate(
                title="Prova bimestral", event_date=date(2026, 6, 15), event_type="PROVA"
            )
        )
        store.create_event(
            CalendarEventCreate(title="Feriado", event_date=date(2026, 7, 9), event_type="FERIADO")
        )
        events = store.list_events()
        assert len(events) == 2

        filtered = store.list_events(event_type="PROVA")
        assert len(filtered) == 1
        assert filtered[0].title == "Prova bimestral"


# ═════════════════════════════════════════════════════════════════════════════
# Services — BNCC
# ═════════════════════════════════════════════════════════════════════════════


class TestBNCCService:
    """Testes para serviços BNCC."""

    def test_list_bncc_skills_sem_filtro(self):
        """Deve listar todas as habilidades sem filtro."""
        from src.education.services import list_bncc_skills

        skills = list_bncc_skills()
        assert len(skills) == len(
            __import__("src.education.enums", fromlist=["BNCC_SKILLS"]).BNCC_SKILLS
        )

    def test_list_bncc_skills_por_ano(self):
        """Deve filtrar habilidades por ano/série."""
        from src.education.services import list_bncc_skills

        ef6 = list_bncc_skills(year="EF_6")
        em = list_bncc_skills(year="EM")
        assert all(s.code.startswith("EF06") for s in ef6)
        assert all(s.code.startswith("EM") for s in em)

    def test_list_bncc_skills_por_competencia(self):
        """Deve filtrar habilidades por competência."""
        from src.education.services import list_bncc_skills

        skills = list_bncc_skills(competence="CE01")
        assert len(skills) > 0
        assert all(s.code in ["EF06HI01", "EF06HI02", "EF07HI01"] for s in skills)

    def test_list_bncc_skills_busca_textual(self):
        """Deve buscar habilidades por texto."""
        from src.education.services import list_bncc_skills

        results = list_bncc_skills(query="tempo")
        assert len(results) > 0
        assert any("tempo" in s.description.lower() for s in results)

    def test_get_bncc_competences(self):
        """Deve listar competências BNCC."""
        from src.education.services import get_bncc_competences

        comps = get_bncc_competences()
        assert len(comps) == 8
        assert comps[0]["code"] in ["CE01", "BNCCCompetence.CE01"]

    def test_bncc_skill_schema_academic_year(self):
        """O schema BNCC deve ter ano/série preenchido."""
        from src.education.services import list_bncc_skills

        skills = list_bncc_skills(year="EF_8")
        for s in skills:
            assert s.academic_year == "EF_8"


# ═════════════════════════════════════════════════════════════════════════════
# Endpoints FastAPI
# ═════════════════════════════════════════════════════════════════════════════


class TestEducationEndpoints:
    """Testes para os endpoints FastAPI do módulo Education."""

    @pytest.fixture
    def client(self):
        """Cria um TestClient com a app principal."""
        from api.server import app
        from fastapi.testclient import TestClient

        return TestClient(app)

    def test_health_endpoint(self, client):
        """GET /api/v2/education/health deve retornar 200."""
        response = client.get("/api/v2/education/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "education"
        assert "stats" in data

    def test_bncc_skills_endpoint(self, client):
        """GET /api/v2/education/bncc/skills deve retornar habilidades."""
        response = client.get("/api/v2/education/bncc/skills")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["total"] > 0
        assert len(data["skills"]) > 0

    def test_bncc_skills_filtro_ano(self, client):
        """GET /api/v2/education/bncc/skills?year=EF_6."""
        response = client.get("/api/v2/education/bncc/skills", params={"year": "EF_6"})
        assert response.status_code == 200
        data = response.json()
        assert all(s["code"].startswith("EF06") for s in data["skills"])

    def test_bncc_competences_endpoint(self, client):
        """GET /api/v2/education/bncc/competences."""
        response = client.get("/api/v2/education/bncc/competences")
        assert response.status_code == 200
        assert len(response.json()["competences"]) == 8

    def test_create_lesson_plan_endpoint(self, client):
        """POST /api/v2/education/lesson-plans deve criar plano."""
        response = client.post("/api/v2/education/lesson-plans", json={"title": "Brasil Colônia"})
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["lesson_plan"]["title"] == "Brasil Colônia"

    def test_get_lesson_plan_endpoint(self, client):
        """GET /api/v2/education/lesson-plans/{id}."""
        # Primeiro cria
        create_resp = client.post(
            "/api/v2/education/lesson-plans", json={"title": "Império Romano"}
        )
        plan_id = create_resp.json()["lesson_plan"]["id"]

        # Depois busca
        response = client.get(f"/api/v2/education/lesson-plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["lesson_plan"]["title"] == "Império Romano"

    def test_get_lesson_plan_not_found(self, client):
        """GET com ID inexistente deve retornar 404."""
        response = client.get("/api/v2/education/lesson-plans/fake-id")
        assert response.status_code == 404

    def test_list_lesson_plans_endpoint(self, client):
        """GET /api/v2/education/lesson-plans."""
        # Cria alguns planos
        for title in ["A", "B", "C"]:
            client.post("/api/v2/education/lesson-plans", json={"title": title})

        response = client.get("/api/v2/education/lesson-plans")
        assert response.status_code == 200
        assert response.json()["total"] >= 3

    def test_update_lesson_plan_endpoint(self, client):
        """PATCH /api/v2/education/lesson-plans/{id}."""
        create_resp = client.post("/api/v2/education/lesson-plans", json={"title": "Antigo"})
        plan_id = create_resp.json()["lesson_plan"]["id"]

        response = client.patch(
            f"/api/v2/education/lesson-plans/{plan_id}", json={"title": "Novo Título"}
        )
        assert response.status_code == 200
        assert response.json()["lesson_plan"]["title"] == "Novo Título"

    def test_delete_lesson_plan_endpoint(self, client):
        """DELETE /api/v2/education/lesson-plans/{id}."""
        create_resp = client.post("/api/v2/education/lesson-plans", json={"title": "Remover"})
        plan_id = create_resp.json()["lesson_plan"]["id"]

        response = client.delete(f"/api/v2/education/lesson-plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_create_activity_endpoint(self, client):
        """POST /api/v2/education/activities."""
        response = client.post(
            "/api/v2/education/activities",
            json={"title": "Quiz Grécia Antiga", "activity_type": "FLASHCARD"},
        )
        assert response.status_code == 201
        assert response.json()["activity"]["title"] == "Quiz Grécia Antiga"

    def test_create_evaluation_endpoint(self, client):
        """POST /api/v2/education/evaluations."""
        response = client.post(
            "/api/v2/education/evaluations",
            json={
                "title": "Prova - Brasil República",
                "evaluation_type": "EXAM",
                "questions": [
                    {
                        "number": 1,
                        "type": "OBJETIVA",
                        "command": "Ano da Proclamação?",
                        "options": ["1888", "1889", "1890"],
                        "correct_answer": "1889",
                        "score": 2.0,
                    }
                ],
            },
        )
        assert response.status_code == 201
        assert response.json()["evaluation"]["title"] == "Prova - Brasil República"
        assert len(response.json()["evaluation"]["questions"]) == 1

    def test_calendar_endpoint(self, client):
        """POST + GET /api/v2/education/calendar."""
        # Cria evento
        post_resp = client.post(
            "/api/v2/education/calendar",
            json={"title": "Avaliação", "event_date": "2026-06-15", "event_type": "PROVA"},
        )
        assert post_resp.status_code == 201

        # Lista eventos
        get_resp = client.get("/api/v2/education/calendar")
        assert get_resp.status_code == 200
        assert get_resp.json()["total"] >= 1

    def test_router_registrado_na_app(self, client):
        """O router education deve estar registrado na app principal."""
        from api.server import app

        def _extrair_paths(route_obj):
            paths = []
            if hasattr(route_obj, "path"):
                paths.append(route_obj.path)
            for router_attr in ("original_router", "router"):
                router = getattr(route_obj, router_attr, None)
                if router and hasattr(router, "routes"):
                    for sub in router.routes:
                        if hasattr(sub, "path"):
                            paths.append(sub.path)
                    break
            return paths

        all_paths = []
        for r in app.routes:
            all_paths.extend(_extrair_paths(r))

        assert "/api/v2/education/health" in all_paths
        assert "/api/v2/education/lesson-plans" in all_paths
        assert "/api/v2/education/activities" in all_paths
        assert "/api/v2/education/evaluations" in all_paths
        assert "/api/v2/education/calendar" in all_paths
        assert "/api/v2/education/bncc/skills" in all_paths


# ═════════════════════════════════════════════════════════════════════════════
# Módulo __init__.py
# ═════════════════════════════════════════════════════════════════════════════


class TestEducationModule:
    """Testes para o pacote src.education."""

    def test_version_exportada(self):
        """O módulo deve exportar __version__."""
        import src.education  # noqa: F811

        assert hasattr(src.education, "__version__")
