# Ferramentas locais gratuitas para educação e apresentações

Esta extensão adiciona plugins internos, três agentes de aplicação e três skills
reutilizáveis. Não instala plugins na conta do ChatGPT, não usa serviços de slides
pagos e não cria assinaturas. A geração continua no Ollama já configurado.

## Instalação no servidor do projeto

```bash
pip install -e ".[dev,presentations]"
```

O extra `presentations` instala **python-pptx**, biblioteca de código aberto com
licença MIT. O exportador HTML usa apenas a biblioteca padrão do Python. O
PowerPoint é opcional: se o extra não estiver instalado, o painel informa que o
plugin está indisponível e o HTML continua funcionando.

A biblioteca python-pptx não exige Microsoft Office nem licença de PowerPoint
para gerar os arquivos. Para editar, use uma aplicação compatível, como
LibreOffice Impress, ou um editor já disponível ao usuário. A aparência pode
variar conforme as fontes instaladas no computador de destino.

## Plugins e capacidades

| Plugin | Uso | Dependência externa |
| --- | --- | --- |
| `html_slides` | Apresentação HTML offline, temas e notas; impressão pelo navegador | Nenhuma |
| `python_pptx` | PowerPoint 16:9 com textos e formas editáveis e notas do apresentador | python-pptx, MIT |

Os plugins são registrados em `src/education/presentation_plugins.py`. São
extensões locais com funções explícitas, sem download ou execução de código de
terceiros em tempo de execução. `/api/v2/education/tools` informa disponibilidade.

## Agentes e skills

| Agente | Skill empacotada | Tarefa |
| --- | --- | --- |
| `education_planner` | `education-planning` | Planejar uma sequência de aprendizagem |
| `presentation_designer` | `professional-presentations` | Criar narrativa, slides concisos e notas |
| `education_reviewer` | `education-review` | Apontar questões de clareza, acessibilidade e adequação |

As skills ficam em `ai/agents/skills/*/SKILL.md` e são incluídas na distribuição
Python. Seus arquivos podem ser revisados e ajustados para as práticas da escola.
Os agentes são registrados no mecanismo existente em `ai/agents/base.py` e usam
diretamente Ollama; uma tentativa de escolher um provedor diferente é rejeitada.
Não usam fallback de nuvem nem executam buscas ou ferramentas arbitrárias.

Exemplo no contrato de chat existente:

```json
{
  "agent": "education_planner",
  "provider": "ollama",
  "prompt": "Planeje uma sequência de 50 minutos para o 6º ano sobre fontes históricas.",
  "use_rag": false
}
```

Envie esse corpo a `POST /api/chat`. O agente de apresentações é usado pelo fluxo
de geração de apresentações; planejador e revisor ficam disponíveis para tarefas
explícitas. Os três não são executados automaticamente em cadeia. A revisão
editorial automática de slides é uma checagem determinística separada, que não
certifica fatos e não substitui o professor.

## Criar uma apresentação

1. Abra **Educação → Criar e revisar com IA** e informe a chave da escola, se exigida.
2. Escolha **Apresentação profissional**, tema, ano e duração.
3. Escolha de 3 a 20 slides e o tema visual **Azul profundo** ou **Papel claro**.
4. Informe objetivos e orientações, incluindo referências que realmente tenha
   consultado. A skill orienta a IA a não inventar referências.
5. Gere o rascunho. A saída precisa corresponder à quantidade de slides pedida.
6. Revise títulos, subtítulos, tópicos, notas e fontes. Reordene, acrescente ou
   remova slides. Cada slide admite até quatro tópicos de até 110 caracteres;
   as fontes seguem o mesmo limite por entrada. Use as notas para os detalhes.
7. Salve as alterações. **Verificar qualidade editorial** aponta pendências como
   ausência de abertura, fechamento, notas ou fontes; não verifica a história.
8. Confirme a revisão docente e aprove. Exporte **PowerPoint** ou **HTML**.

As prévias do painel ajudam a revisar o conteúdo, mas o arquivo exportado deve
ser inspecionado no ambiente em que será apresentado. A exportação só usa a
versão salva. Rascunhos recebem uma indicação de revisão pendente; apresentações
aprovadas recebem a indicação de revisão pelo professor. Não há identificação
individual ou assinatura de quem aprovou nesta etapa.

O HTML contém tudo em um arquivo, sem fontes remotas, imagens ou scripts externos.
As notas ficam em seções expansíveis abaixo dos slides; na impressão, são ocultadas.
O PowerPoint contém textos e formas nativos, com notas preservadas. Esta versão
não acrescenta imagens de bancos comerciais, vídeos, animações ou gráficos de dados.

## Rotas novas

Todas usam a autenticação `X-API-Key` existente do módulo educacional.

| Método | Rota | Uso |
| --- | --- | --- |
| GET | `/api/v2/education/tools` | Plugins, agentes e skills disponíveis |
| GET | `/api/v2/education/materials/presentation/{id}/checks` | Pendências editoriais |
| GET | `/api/v2/education/materials/presentation/{id}/export/html` | Download offline |
| GET | `/api/v2/education/materials/presentation/{id}/export/pptx` | Download editável |

A geração e revisão usam as rotas do [fluxo existente](EDUCATION_AI_WORKFLOW.md),
com `material_type=presentation`, `slide_count` e `theme`. As apresentações ficam
na mesma base SQLite e participam do acervo e do controle de versões. Não há
migração destrutiva: a tabela já utilizada recebe a coleção `presentations`.

## Validação e limites

A IA é simulada nos testes automatizados. Foram verificados estrutura do arquivo
PowerPoint, textos editáveis, notas, proporção 16:9, HTML escapado, autenticação,
persistência e aprovação. A integração de navegador exercita o adaptador Ollama
com uma resposta local simulada e baixa os dois formatos.

A qualidade do conteúdo de um modelo real deve ser avaliada com exemplos da
escola. O acervo de referências é fornecido pelo professor; esta extensão não
implementa pesquisa documental ou verificação histórica automática. Revise o
resultado antes de usá-lo em aula. Não é necessário contratar um serviço de slides.

Este PR depende do fluxo de geração/revisão do PR #29 e da persistência do #28;
integre essas etapas antes desta extensão. A branch deste PR contém as três etapas.

## Legibilidade dos subtítulos no PowerPoint

Quebras de linha inseridas no subtítulo são normalizadas em espaços na exportação
PowerPoint. As caixas de texto usam ajuste automático ao espaço disponível para
que textos válidos não invadam os tópicos seguintes. O conteúdo salvo no acervo
permanece intacto. Confira também o arquivo no editor utilizado pela escola,
pois a aparência depende das fontes e do suporte a ajuste automático desse editor.
