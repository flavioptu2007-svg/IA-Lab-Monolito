# Exemplo de `atividade.json`

`atividade-exemplo.json` é o modelo versionado do contrato de entrada do
pipeline: Roma Antiga (6º ano, `EF06HI11X`, catálogo CRMG p. 566), fontes
primárias de domínio público (Tito Lívio e Suetônio). Ele é carregado e
validado pelos testes, então quebrar o esquema quebra o build.

## Regras que o exemplo demonstra

- `habilidade` é a **cópia literal** da entrada do catálogo — código nunca é
  texto livre. Na montagem, o texto impresso vem sempre do catálogo.
- `confirmado_pelo_professor` precisa ser `true`: o par tema↔habilidade é
  decisão pedagógica confirmada na sessão de redação.
- Toda leitura, item e par tem `fonte` completa; `origem: "web"` exige `url` e
  `data_acesso` (`AAAA-MM-DD`).
- `frase_com_lacuna` contém `___` (exatamente a lacuna), com `resposta` e
  `distratores` fora dela.
- `quantidade_questoes` bate com o total preenchido (blocos com pergunta +
  itens de parear + itens de marcar + afirmações V/F + itens de ordenar +
  itens de completar + pares de ligar).
- `itens_marcar` é a resposta de menor exigência motora: `enunciado` (o comando),
  `frase` opcional, 2 a 4 `opcoes` e `correta` — a folha imprime `( )` antes de cada
  opção, então nada é escrito; `correta` precisa estar entre as opções.
- `itens_vf` traz `afirmacao` + `verdadeiro`; quando a afirmação é falsa,
  `correcao` é obrigatória (é ela que o gabarito imprime, para o estudante ver o
  que é certo).
- `itens_parear` imprime a mesma palavra nas duas colunas, em ordens diferentes:
  a resposta é um traço entre palavras idênticas, sem escrita nem leitura nova.
- `itens_ordenar` traz `enunciado` + `itens` na **ordem correta**; a folha sai
  embaralhada com `(    )` para numerar e o gabarito imprime a sequência.
- `figuras` recebe `caminho` de uma imagem **PNG ou JPEG** local (absoluto ou
  relativo à pasta do `atividade.json`), `legenda` opcional e `fonte`. Sem o
  arquivo, ou em outro formato, a folha é recusada — o pipeline não desenha
  substituto no lugar da imagem.
- Na folha, a ordem é da menor para a maior exigência: figura → parear → marcar →
  V/F → ordenar → completar → ligar.
- No modo `adaptado`, cada bloco precisa de uma `pergunta` logo após o texto.
- `gabarito: true` gera o `<tema>-gabarito.docx` em arquivo separado.
- `registro_mediacao: true` acrescenta uma **página final de uso do professor**
  (como aplicar, grade sozinho / apoio parcial / apoio total por item, data, tempo
  e observações). Ela é marcada como página que não vai para o estudante e não
  substitui o gabarito, que continua em arquivo separado.
- `vocabulario` (opcional, até 8 palavras) abre a folha com a **caixa de
  vocabulário** — as palavras-chave que percorrem as tarefas, como no caderno de
  referência. No suporte 3 a caixa volta no topo de cada tarefa, pelo mesmo
  motivo do banco de palavras: a página anterior já foi recolhida.
- `planejamento` (opcional) imprime a **ficha do caderno do professor** no topo
  da página: objetivo, duração, metodologia, recursos e público/PDI, num bloco
  único. Exige `registro_mediacao: true` (sem a página não há onde imprimir) e só
  os campos preenchidos aparecem; com a ficha, a caixa de observações cede
  1,4 cm para a página continuar fechando em uma folha.
- `orientacoes_aplicacao` é uma lista livre do professor: entra nessa página
  **depois** das orientações geradas da própria folha (banco de palavras, ligar,
  gabarito).

## Como usar

```bash
# só valida contra o catálogo versionado (não exige revisão aprovada)
python3 -m src.historia_gen verificar src/historia_gen/exemplos/atividade-exemplo.json

# monta a folha (exige catálogo com revisao_aprovada=true)
python3 -m src.historia_gen montar src/historia_gen/exemplos/atividade-exemplo.json --saida ~/Documentos/Escola/Atividades
```

Para criar a sua, copie o arquivo, troque `tema`, `habilidade` (com a cópia
exata do catálogo), os textos e as fontes — e rode `verificar` antes de montar.
