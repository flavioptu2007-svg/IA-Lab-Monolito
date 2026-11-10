# Materiais educacionais persistentes

Planos de aula, atividades, avaliações e calendário são gravados em SQLite.
O banco é consultado a cada operação: reiniciar a aplicação mantém os materiais,
inclusive questões, respostas, momentos pedagógicos e edições do professor.
O fluxo de geração local e revisão está descrito em
[EDUCATION_AI_WORKFLOW.md](EDUCATION_AI_WORKFLOW.md).

## Configurar

O padrão é `education.db` no diretório em que o servidor é iniciado. Para evitar
que diferentes diretórios de execução criem bancos distintos, configure um
caminho absoluto em `.env`:

```dotenv
IA_LAB_EDUCATION_DB_URL=sqlite:////caminho/persistente/education.db
```

Use um diretório gravável pelo processo. Em containers, o arquivo precisa estar
em um volume persistente. Trocar a URL seleciona outro banco; não migra os dados.
Não guarde o banco no repositório Git.

As formas `sqlite:///` e `sqlite+aiosqlite:///` são aceitas. A segunda mantém
compatibilidade com a configuração existente; esta implementação usa `sqlite3`
da biblioteca padrão, sem instalar aiosqlite. URLs de outros bancos e URLs com
parâmetros ou fragmentos são rejeitadas; não há fallback silencioso para memória.

Para uma execução temporária, escolha explicitamente:

```dotenv
IA_LAB_EDUCATION_DB_URL=sqlite:///:memory:
```

Nesse modo os materiais desaparecem ao reiniciar. Os testes usam memória por
padrão; os testes de persistência criam arquivos temporários próprios.

## Verificar a persistência

1. Configure a URL do banco e inicie a API.
2. Em `/docs`, use `POST /api/v2/education/lesson-plans` com
   `{"title":"Plano de verificação"}` e anote o `id` retornado.
3. Reinicie a API usando a mesma URL e diretório de dados.
4. Consulte `GET /api/v2/education/lesson-plans/{id}`: o plano deve permanecer.
5. Edite, reinicie e consulte novamente para conferir a revisão.

Quando `IA_LAB_API_TOKEN` estiver configurado, envie o header `X-API-Key`.
As rotas e os formatos de resposta permanecem; atualizações que tornariam o
registro inválido (por exemplo, `title: null`) retornam 422 sem substituir o
material anterior. O diagnóstico educacional conta os registros do banco.

## Backup e recuperação

Use a API de backup do SQLite para obter uma cópia consistente mesmo com o
servidor em execução. Substitua os caminhos e escolha um destino novo:

```python
import sqlite3
from contextlib import closing

with closing(sqlite3.connect("/caminho/persistente/education.db")) as source:
    with closing(sqlite3.connect("/caminho/backup/education-copia.db")) as target:
        source.backup(target)
```

Para recuperar: pare a API, preserve uma cópia do banco atual, coloque o backup
no caminho configurado e reinicie. Consulte um material conhecido para conferir.
Proteja o backup com as mesmas permissões do banco original.

## Limites desta entrega

- O armazenamento anterior em memória não possui dados em disco para migrar.
  Exporte materiais da instância antiga antes de desligá-la, se ainda estiver ativa.
- SQLite é adequado a uma instalação local com arquivo compartilhado entre seus
  processos. Esta entrega não implementa sincronização entre servidores distintos.
- A listagem mantém os filtros e a paginação existentes; ainda carrega a coleção
  antes de filtrar. Grandes acervos precisam de uma etapa de indexação e consulta SQL.
- A autenticação existente é preservada. Esta entrega não adiciona contas de
  professores nem separação dos materiais por usuário.
- Esta tabela é nova (`education_materials`); não importa automaticamente tabelas
  preexistentes de outros projetos.

As rotas educacionais síncronas são executadas pelo FastAPI em threads, evitando
bloquear o loop assíncrono durante I/O SQLite. As atualizações usam transações para
preservar alterações concorrentes em campos diferentes. Falhas de disco são
propagadas, sem confirmar uma gravação que não ocorreu.
