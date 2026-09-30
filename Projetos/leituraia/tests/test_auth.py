"""Testes de autenticação do LeituraIA Brasil (PBKDF2 + JWT)."""

import pytest
from fastapi import HTTPException

from leituraia.auth import (
    UserStore,
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    get_current_user,
    hash_senha,
    verificar_senha,
)
from leituraia.rbac import Profile


class TestSenhas:
    def test_hash_e_verificacao(self):
        armazenada = hash_senha("minha-senha-segura")
        assert armazenada.startswith("pbkdf2$")
        assert verificar_senha("minha-senha-segura", armazenada)

    def test_senha_errada_falha(self):
        armazenada = hash_senha("correta")
        assert not verificar_senha("errada", armazenada)

    def test_hash_usa_salt_aleatorio(self):
        assert hash_senha("mesma") != hash_senha("mesma")

    def test_armazenada_malformada_falha_sem_explodir(self):
        assert not verificar_senha("x", "lixo")
        assert not verificar_senha("x", "")
        assert not verificar_senha("x", "a$b$c$d")

    def test_formato_do_hash(self):
        partes = hash_senha("abc").split("$")
        assert len(partes) == 4
        assert partes[0] == "pbkdf2"
        assert int(partes[1]) >= 100_000
        assert len(bytes.fromhex(partes[2])) == 16  # salt de 16 bytes


class TestTokens:
    def test_access_token_valido(self):
        token = criar_access_token("uid-123", Profile.PROFESSOR.value)
        payload = decodificar_token(token)
        assert payload is not None
        assert payload["sub"] == "uid-123"
        assert payload["perfil"] == "professor"

    def test_refresh_token_valido(self):
        token = criar_refresh_token("uid-9", Profile.ALUNO.value)
        payload = decodificar_token(token)
        assert payload is not None
        assert payload["sub"] == "uid-9"

    def test_token_lixo_retorna_none(self):
        assert decodificar_token("nao-e-um-jwt") is None

    def test_token_assinado_com_outro_segredo_retorna_none(self):
        from jose import jwt

        token_falso = jwt.encode({"sub": "x"}, "segredo-errado", algorithm="HS256")
        assert decodificar_token(token_falso) is None


class TestUserStore:
    def test_criar_e_autenticar(self):
        store = UserStore()
        u = store.criar("Maria", "Maria@Exemplo.COM", "senha123", Profile.PROFESSOR)
        assert u.email == "maria@exemplo.com"  # normalizado
        autenticado = store.autenticar("maria@exemplo.com", "senha123")
        assert autenticado is not None
        assert autenticado.uid == u.uid

    def test_email_duplicado_rejeitado(self):
        store = UserStore()
        store.criar("A", "a@x.com", "123456", Profile.ALUNO)
        with pytest.raises(ValueError, match="email"):
            store.criar("B", "a@x.com", "abcdef", Profile.ALUNO)

    def test_autenticar_email_desconhecido(self):
        store = UserStore()
        assert store.autenticar("fantasma@x.com", "123456") is None

    def test_senha_errada_nao_autentica(self):
        store = UserStore()
        store.criar("A", "a@x.com", "123456", Profile.ALUNO)
        assert store.autenticar("a@x.com", "errada") is None

    def test_listar_ordenado_por_nome_e_total(self):
        store = UserStore()
        store.criar("Zeca", "z@x.com", "123456", Profile.ALUNO)
        store.criar("Ana", "a@x.com", "123456", Profile.ALUNO)
        nomes = [u.nome for u in store.listar()]
        assert nomes == ["Ana", "Zeca"]
        assert store.total == 2

    def test_por_id(self):
        store = UserStore()
        u = store.criar("A", "a@x.com", "123456", Profile.ALUNO)
        assert store.por_id(u.uid).nome == "A"
        assert store.por_id("inexistente") is None


class TestGetCurrentUser:
    def _call(self, token: str | None):
        from fastapi.security import HTTPAuthorizationCredentials

        cred = (
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            if token
            else None
        )
        return get_current_user(cred)

    def test_credencial_ausente_401(self):
        with pytest.raises(HTTPException) as exc:
            self._call(None)
        assert exc.value.status_code == 401

    def test_token_invalido_401(self):
        with pytest.raises(HTTPException) as exc:
            self._call("token-invalido")
        assert exc.value.status_code == 401

    def test_token_valido_retorna_usuario(self):
        store = UserStore()
        u = store.criar("A", "a@x.com", "123456", Profile.ALUNO)
        # garante que o singleton usa o mesmo store
        import leituraia.auth as auth_mod

        auth_mod._user_store = store
        try:
            token = criar_access_token(u.uid, Profile.ALUNO.value)
            usuario = self._call(token)
            assert usuario.uid == u.uid
        finally:
            auth_mod._user_store = None
