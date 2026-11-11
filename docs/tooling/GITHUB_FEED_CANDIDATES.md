# Catálogo de candidatos a partir do feed GitHub

Este catálogo incorpora as sugestões enviadas pelo usuário ao planejamento do
IA-Lab. A curadoria consultou os READMEs e arquivos de licença indicados abaixo.
É um registro de candidatos: não instala dependências, executa modelos, adiciona
segredos, habilita serviços nem muda os provedores usados pelo projeto.

O registro estruturado está em
[github-feed-candidates.json](github-feed-candidates.json). Cada evidência inclui
repositório, caminho e SHA do blob consultado. Os links apontam para a branch
padrão e podem mudar; os hashes permitem reconhecer a versão efetivamente lida.
As versões e datas de todos os anúncios do feed não foram auditadas. Contagem de
estrelas e notificações de seguidores não foram usadas como critérios técnicos.

## Prioridades

| Candidato | Aplicação | Licença e condição observadas | Decisão |
| --- | --- | --- | --- |
| [Presenton](https://github.com/presenton/presenton) | Templates, editor visual, API/MCP e exportação de apresentações | Apache-2.0; declara suporte a Ollama e LM Studio | Prioridade 1: prova de conceito local |
| [Astryx](https://github.com/meta/astryx) | Componentes acessíveis e temas para o dashboard | MIT; beta, requer React 19+ | Prioridade 2: avaliar um componente isolado |
| [Graphweaver](https://github.com/exogee-technology/graphweaver) | Agregação de fontes via GraphQL | LICENSE.md é Apache-2.0; README contém referências MIT conflitantes | Adiar até haver necessidade e esclarecer o licenciamento dos pacotes |
| [Trigger.dev Docker](https://github.com/triggerdotdev/docker) | Tarefas assíncronas e processamento em lote | Licença dos templates não confirmada nos arquivos consultados; núcleo trigger.dev tem Apache-2.0 | Adiar; conferir documentação e versões de autohospedagem |
| [Nango](https://github.com/NangoHQ/nango) | OAuth, tokens e integrações | ELv2; README descreve autohospedagem gratuita com recursos limitados | Condicional às APIs e funcionalidades necessárias |
| [BitNet de kyegomez](https://github.com/kyegomez/BitNet) | Pesquisa em quantização e treinamento PyTorch | MIT; exige modelos e treinamento apropriados | Pesquisa; não substituir o provedor existente automaticamente |
| [Junie GitHub Action](https://github.com/JetBrains/junie-github-action) | Programação e revisão no GitHub | README exige chave Junie ou de provedor; uso sem cobrança não confirmado | Fora da seleção de custo zero por enquanto |
| [HGhub](https://github.com/Minireel/HGhub) | Nenhum uso educacional estabelecido | README informa fim da manutenção e retirada do código | Indisponível para integração |

O feed contém nomes traduzidos. `presente/presente` foi associado provisoriamente
a Presenton: o `package.json` consultado declara `0.9.12-beta`, coincidindo com o
anúncio colado. A descrição de “tecelão de gráficos” é compatível com Graphweaver.
Essas correspondências precisam da URL original do item antes de uma integração.

## Fontes e ressalvas específicas

- **Presenton:** [README](https://github.com/presenton/presenton/blob/main/README.md),
  [LICENSE](https://github.com/presenton/presenton/blob/main/LICENSE),
  [package.json](https://github.com/presenton/presenton/blob/main/package.json) e
  [Docker Compose](https://github.com/presenton/presenton/blob/main/docker-compose.yml).
  Ter licença aberta não torna gratuitas as APIs de texto/imagem que podem ser
  configuradas. O código consultado também menciona ofertas Enterprise; elas
  não fazem parte da proposta local.
- **Astryx:** [README](https://github.com/meta/astryx/blob/main/README.md) e
  [LICENSE](https://github.com/meta/astryx/blob/main/LICENSE). A compatibilidade
  anunciada com React 19 é um ponto favorável, não um teste da integração com
  nosso dashboard.
- **Graphweaver:** [README](https://github.com/exogee-technology/graphweaver/blob/main/README.md)
  e [LICENSE.md](https://github.com/exogee-technology/graphweaver/blob/main/LICENSE.md).
  O arquivo de licença consultado é Apache-2.0; a divergência no README foi
  mantida explícita no catálogo.
- **Nango:** [README](https://github.com/NangoHQ/nango/blob/master/README.md),
  [LICENSE](https://github.com/NangoHQ/nango/blob/master/LICENSE) e
  [package.json](https://github.com/NangoHQ/nango/blob/master/package.json).
  O pacote consultado declara `0.72.4`. A ELv2 restringe serviço gerenciado e
  funcionalidades protegidas por chave; não tratar a plataforma como um pacote
  MIT/Apache irrestrito nem presumir que todos os recursos sejam gratuitos.
- **Trigger.dev:** [templates Docker](https://github.com/triggerdotdev/docker/blob/main/README.md)
  e [licença do núcleo](https://github.com/triggerdotdev/trigger.dev/blob/main/LICENSE).
  O próprio README dos templates recomenda a documentação atual de autohospedagem.
  A licença do núcleo não foi automaticamente atribuída aos templates ou a todas
  as imagens e dependências.
- **Junie:** [README](https://github.com/JetBrains/junie-github-action/blob/main/README.md).
  BYOK significa fornecer uma chave, não garantia de inferência gratuita. Não
  adicionar workflows ou permissões de aprovação automática como consequência
  desta curadoria. A licença não foi confirmada nos nomes LICENSE, LICENSE.md e
  LICENSE.txt consultados; isso não prova ausência de licença em outros caminhos.
- **BitNet:** [README](https://github.com/kyegomez/BitNet/blob/main/README.md) e
  [LICENSE](https://github.com/kyegomez/BitNet/blob/main/LICENSE). A documentação
  alerta que trocar camadas de um modelo já treinado não basta para obter um
  modelo BitNet utilizável. Esta implementação de pesquisa é distinta do
  provedor BitNet já registrado no Monolito.
- **HGhub:** [README](https://github.com/Minireel/HGhub/blob/main/README.md). O
  mantenedor informa que retirou código, releases e registros de build e parou
  de manter o projeto.

## Próxima avaliação proposta: Presenton

Esta é uma proposta verificável para uma etapa futura, não uma instalação feita.

1. Confirmar a URL do anúncio original e escolher uma versão/commit explícito.
2. Avaliar em ambiente separado, com texto fictício e sem dados de alunos.
3. Usar somente o modelo local já disponível. Não configurar APIs pagas de texto,
   imagens, pesquisa ou nuvem. Conferir as conexões externas e as opções de dados
   e telemetria da versão escolhida antes de executar.
4. Gerar os mesmos materiais de referência usados para avaliar os exportadores
   atuais: abertura, comparação, explicação de fontes históricas e fechamento.
5. Conferir correção e referências com o professor, notas, editabilidade do PPTX,
   fontes, contraste, excesso de texto e abertura no editor usado pela escola.
6. Medir tempo e consumo local e verificar a preservação da revisão docente e do
   acervo. Acesso ao modelo local não elimina necessidade de hardware e manutenção.
7. Só então propor um adaptador com contrato, desligamento simples e teste de
   regressão; preservar os exportadores HTML/python-pptx que já funcionam.

## Como atualizar o catálogo

Reabrir as fontes antes de mudar uma decisão, atualizar seus hashes e registrar
mudanças de licença, requisitos e custo. Um candidato só deve ser apresentado
como instalado depois de implementação e verificação próprias. A rota `/tools`
continua mostrando os recursos efetivamente integrados; este catálogo não altera
seu inventário nem dispara atualização automática a partir do feed.
