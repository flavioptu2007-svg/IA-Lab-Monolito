# Q5 — linha de base do tempo de adaptação manual

O critério da Fase 5 é comparar o fluxo (redação + montagem + revisão) com o
tempo de uma adaptação feita **sem** o pipeline. O lado automático é medido; o
lado humano não pode ser simulado por script — é o professor cronometrando uma
adaptação real.

## O que cronometrar

1–2 adaptações reais, de temas e séries diferentes, feitas como o professor faz
hoje (pegar a prova/caderno original, reescrever, montar o arquivo).

* **Começa** quando o professor abre o material de origem.
* **Termina** quando o `.docx` está pronto para imprimir (impressão não conta).
* Anotar tema, ano, modo (regular/adaptado) e se houve retrabalho depois.

## Formulário impresso

O papel que vai para a mesa é gerado pelo próprio pipeline, no mesmo padrão do
roteiro de conferência:

```bash
python3 -m src.historia_gen tempo-formulario        # 2 vias (padrão), uma por adaptação
python3 -m src.historia_gen tempo-formulario --vias 1 --saida /tmp/q5.docx
```

[`q5-formulario.docx`](q5-formulario.docx) é o arquivo versionado (Arial, A4, sem
cabeçalho, uma página por medição). Cada via traz:

* **identificação da adaptação** — professor, data, ano/turma, modo (regular ou
  adaptado), tema, material de origem;
* **tempo por etapa** — ler o material, reescrever, preparar as questões,
  digitar, revisar — com início, fim e minutos, e o **total** em destaque;
* **retrabalho** — se o arquivo precisou ser refeito depois de pronto, quanto
  tempo a mais e o quê;
* **como o papel vira linha de base** — o comando `tempo-manual` com o total,
  que grava no CSV abaixo.

Só o total entra no registro; as etapas existem para o professor ver onde o
tempo foi gasto.

## Como registrar

```bash
python3 -m src.historia_gen tempo-manual \
  --tema "Roma Antiga" --ano "6º ano EF" --modo adaptado \
  --minutos 65 --quem "Prof. …" --observacao "sem retrabalho"
```

Grava em [`q5-linha-de-base.csv`](q5-linha-de-base.csv), uma linha por medição —
o arquivo versionado só tem o cabeçalho até a primeira medição real.

## Como comparar

```bash
python3 -m src.historia_gen tempo-manual --comparar \
  --registros saida/registros.jsonl
```

Compara a **mediana** manual (minutos) com a mediana de `duracao_s` das
gerações. Sem medição manual — ou sem log com `duracao_s` — o comando sai com
código 1 e não imprime ganho: a linha de base não é inventada.

## Limite da comparação

A conta cobre só a **montagem** (validação + gravação), não a redação do
`atividade.json` nem a revisão humana. Um número de ganho que ignore a redação
superestima o pipeline; registrar o tempo total da adaptação manual é o que
torna a Fase 5 comparável de verdade.
