# Troubleshooting — falha dos testes de containment do odysseus neste host

**Sintoma (2026-11-11, bubblewrap 0.11.1):** `./scripts/test_all.sh` fecha com
`10 ok, 1 falha`, e o odysseus falha com

```
FAILED tests/test_containment_enforcement.py::test_namespace_handshake_closes_model_stdin
FAILED tests/test_containment_enforcement.py::test_execution_environment_cannot_replace_probed_bwrap[False]
2 failed, 13834 passed, 61 skipped
```

Não é regressão do projeto nem do clone: é o host vazando ruído de stderr para
dentro do sandbox.

## Causa

O sandbox do odysseus roda `bash -lc`, que carrega `/etc/profile` → todas as
`/etc/profile.d/*` — inclusive `/etc/profile.d/im-config_wayland.sh`, que faz
`. /usr/share/im-config/initializer`. Esse initializer define

```sh
LOGGER='/usr/bin/systemd-cat -p 6 -t "im-config" echo'
logger_info() { eval "$LOGGER \"$1\""; }
```

O sandbox monta `/usr`, `/etc`, `/proc`, `/dev` e um `/tmp` vazio, mas **não
monta `/run`** — então o socket do journald (`/run/systemd/journal/stdout`) não
existe, e cada `logger_info` escreve no stderr:

```
Failed to create stream fd: No such file or directory
```

São três linhas por sessão de login. Os testes de containment comparam o stdout
exato do comando e tratam qualquer stderr inesperado como falha, daí o vermelho.

## Reprodução mínima (sem o odysseus)

```sh
bwrap --ro-bind /usr /usr --ro-bind /etc /etc --ro-bind /usr/bin /bin --ro-bind /usr/lib /lib --ro-bind /usr/lib64 /lib64 --proc /proc --dev /dev --tmpfs /tmp /bin/bash -lc 'echo ok'
# 3 linhas de "Failed to create stream fd" no stderr

bwrap --ro-bind /run /run --ro-bind /usr /usr --ro-bind /etc /etc --ro-bind /usr/bin /bin --ro-bind /usr/lib /lib --ro-bind /usr/lib64 /lib64 --proc /proc --dev /dev --tmpfs /tmp /bin/bash -lc 'echo ok'
# stderr limpo
```

O `scripts/test_all.sh` já reconhece esse caso (`motivo_ambiental` /
`explica_ambiental`): quando o log do pytest traz a mensagem acima, a matriz
imprime a explicação e marca a falha com `:: falha ambiental
(im-config/systemd-cat)`. A falha continua contando como falha e o script segue
saindo com código 1.

## Por que não corrigimos no clone

As duas saídas testadas quebram mais do que consertam, medido com a suíte
completa em paralelo (`-n auto`, ~110 s):

| Tentativa | Resultado |
|---|---|
| Nada (controle) | 2 falhas, 13834 passed |
| Montar `/run` no `_bwrap_prefix` | some com as 2, mas aparecem 6–7 falhas/timeouts: sockets do host vazam para o sandbox e contaminam ids parametrizados (`[/run#-[::1]:17654]`) |
| Trocar `-lc` por `-c` | 5–9 falhas: 9 testes dependem do ambiente de login (PATH, locale, variáveis do `/etc/profile`) |

O clone `odysseus/` é de terceiros e não é versionado aqui; mexer nele não
sobrevive a um `git pull`. A decisão (montar `/run` só nos testes de
containment, ou isolar o sandbox do `/etc/profile` do host) é do upstream.

## O que não fazer

- Não montar `/run` inteiro por padrão no sandbox: expõe sockets do host e
  quebra testes alheios por contenção de recursos.
- Não trocar `bash -lc` por `bash -c` para "limpar" o stderr: derruba os testes
  que contam com o ambiente de login.
- Não marcar os dois testes como `xfail`/skip: eles passam em host sem esse
  hook — o defeito é o isolamento do sandbox, não os testes.
