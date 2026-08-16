# Microsoft Office no Linux — Guia de Configuração (Wine)

Guia seguro e passo a passo para instalar e executar o Microsoft Office (Word, Excel e PowerPoint) no Linux, priorizando **estabilidade**, **compatibilidade** e **facilidade de manutenção** — dentro de um ambiente Wine **isolado**, sem afetar os demais programas do computador.

> ⚠️ **Regra principal:** nada é instalado ou alterado antes da **ETAPA 3 (autorização)**. As etapas 1 e 2 são somente leitura.

---

## Fluxo em etapas

| Etapa | Nome | O que acontece |
|:---:|------|----------------|
| 1 | Diagnóstico | Coleta informações do sistema (somente leitura) |
| 2 | Recomendação técnica | Escolha da ferramenta, versão do Office e arquitetura |
| 3 | Autorização | Você aprova o plano antes de qualquer alteração |
| 4 | Instalação | Dependências, prefixo isolado, winetricks e instalador |
| 5 | Configuração | Idioma pt-BR, impressão, atalhos e associação de arquivos |
| 6 | Testes | Word, Excel e PowerPoint (abrir/criar/salvar, copiar/colar, imprimir) |
| 7 | Correções | 1 erro → 1 correção (diagnóstico disciplinado, nada de tentativa e erro) |
| 8 | Relatório final | Registro do ambiente + comandos de manutenção |

---

## ETAPA 1 — Diagnóstico

Execute a partir da raiz do repositório (ou por caminho absoluto — o script **não depende** do diretório):

```bash
# Opção A — da raiz do repositório
cd /caminho/para/ia-lab-monolito
./scripts/diagnose_office_linux.sh

# Opção B — de qualquer pasta, com caminho absoluto
bash /caminho/para/ia-lab-monolito/scripts/diagnose_office_linux.sh
```

> 💡 O erro `Ficheiro ou pasta inexistente` acontece quando se roda `./scripts/...` fora da raiz do projeto. Use o caminho absoluto (`bash /caminho/...`) e o problema desaparece.

**O que o script coleta (tudo somente leitura):**

| Item | Exemplos |
|------|----------|
| Sistema | SO e versão, kernel, arquitetura, LSB release |
| Hardware | CPU, memória RAM, espaço em disco |
| Gerenciadores | apt, dnf, pacman, zypper, flatpak, snap |
| Camada Windows | Wine (+ versão), Winetricks, PlayOnLinux, Bottles |
| Arquiteturas dpkg | `amd64` / `i386` (i386 é necessário p/ Office 32-bit) |
| Dependências | cabextract, curl, wget, unzip, 7z, winbind, cups, lpstat, fontconfig |
| Impressão | Serviço CUPS, impressora padrão |
| Idioma | Locale, layout de teclado |
| Histórico | Prefixos Wine existentes, instalações anteriores do Office |
| Instaladores | Busca por `.exe`/`.iso`/`.msi`/`.cab`/`.img` em Downloads, Documentos etc. |
| Repositórios | Candidatos `apt` de wine/winetricks/cabextract |

**O que enviar de volta:** a saída completa + a versão do Office que você possui com **licença legítima** (ex.: Office 2016, 2019, 2021 ou Microsoft 365) e onde está o instalador.

---

## ETAPA 2 — Recomendação técnica

### 2.1 Escolha da ferramenta

| Opção | Veredito | Justificativa |
|-------|:---:|----------------|
| **PlayOnLinux** | ❌ | Legado, sem manutenção ativa — não é escolhido só por ser mencionado |
| **Bottles** | ⚠️ Viável | Excelente, mas a camada Flatpak complica impressão/associação de arquivos e o pinning de versões |
| **Wine puro + Winetricks** | ✅ **Recomendado** | Controle total, prefixo `WINEPREFIX` exclusivo, mais fácil de diagnosticar e atualizar — caminho oficial da comunidade WineHQ para Office |

### 2.2 Versão do Office (base WineHQ AppDB)

| Versão | Veredito | Observação |
|--------|:---:|------------|
| **Office 2016 (32-bit MSI)** | ✅ **Mais estável** | Teto prático de confiabilidade no Wine — **requer mídia .iso/.exe MSI** (não Click-to-Run) |
| Office 2021 (32-bit) | ❌ **Não funciona** | Click-to-Run exige NT service (`{5b99fa76...}`) não implementado no Wine — ver Case Study em anexo |
| Office 2019 | ❌ **Não funciona** | Mesma razão: Click-to-Run. Fora do suporte mainstream desde out/2025 |
| Microsoft 365 (assinatura) | ❌ **Não roda** | Exige login Microsoft/click-to-run; AppDB: broken |
| OneDrive (cliente) | ❌ Não roda | Alternativas: web, `rclone`, `abraunegg/onedrive`, `onedriver` |

> ⚠️ **Importante (atualizado em ago/2026):** os vereditos acima foram confirmados por tentativa real documentada no final deste guia. **Apenas Office 2016 MSI** (não Click-to-Run) tem chance real de funcionar no Wine atual. Para uso prático de DOCX/XLSX/PPTX no Linux, considere **LibreOffice** como alternativa nativa mais confiável.

> 🔒 **Ativação:** sempre por **licença legítima**. Este guia **não** fornece cracks, ativadores, KMS ilegais, serial keys falsos ou métodos para burlar ativação.

### 2.3 Arquitetura

- **Recomendada: 32-bit** — o Office 32-bit sofre menos problemas de registry/translation sob Wine.
- Decisão baseada em evidência da comunidade, **não por hábito**.
- ⚠️ **Wine 8+ (incluindo 10):** o prefixo é **`win64` (WoW64)** mesmo para rodar Office 32-bit. NÃO use mais `WINEARCH=win32` (falha com *"not supported in wow64 mode"*). Binários 32-bit vão para `Program Files (x86)/...`. Ver Case Study em anexo.

---

## ETAPA 3 — Autorização

Nenhum comando de instalação é executado antes desta etapa. A recomendação da ETAPA 2 é apresentada com:

1. o comando;
2. o que ele faz;
3. o resultado esperado;
4. o que enviar de volta caso apareça erro.

---

## ETAPA 4 — Instalação

### 4.1 Dependências do sistema (somente repositórios oficiais)

```bash
sudo apt update && sudo apt install -y wine wine32:i386 wine64 winetricks cabextract winbind
```

> 💡 **Ubuntu 26.04+:** o `dpkg --add-architecture i386` **não é mais necessário** (já vem habilitado). O Wine 10 já vem nos repositórios oficiais do Ubuntu — não precisa adicionar repositório WineHQ externo.

Resultado esperado:

```bash
wine --version        # → wine-10.0 (Ubuntu)
winetricks --version  # → 20250102 - sha256sum: ...
```

### 4.2 Prefixo isolado (exclusivo do Office)

```bash
export WINEPREFIX="$HOME/wineprefixes/Office"
# ⚠️ Wine 10 / WoW64: usar win64 (mesmo para Office 32-bit)
WINEARCH=win64 wineboot -u      # inicializa o prefixo (cria ~/wineprefixes/Office)
```

> 🔒 O prefixo é **separado** — nada que o Office fizer afetará outros programas Windows do sistema.
>
> ❌ **Não use mais `WINEARCH=win32`** no Wine 10: falha com *"WINEARCH is set to 'win32' but this is not supported in wow64 mode"*. O WoW64 permite rodar binários 32-bit dentro do prefixo win64 nativamente.

### 4.3 Dependências winetricks (somente as necessárias p/ a versão escolhida)

Para **Office 2016 (32-bit)**:

```bash
winetricks corefonts msls31 riched20 riched30 gdiplus msxml3 msxml6 vcrun2010 vcrun2013
```

Adicione `dotnet48 d3dcompiler_47` **apenas se** a versão instalada exigir. Não instale dezenas de componentes desnecessários.

### 4.4 Executar o instalador oficial

```bash
wine ~/Downloads/setup.exe        # ajuste para o arquivo real da sua mídia
# Se for .iso, extraia antes (ou use: 7z x office2016.iso -o~/Downloads/office2016)
```

> 💡 **Automatize com o script do projeto** ([`scripts/install_office2016_msi.sh`](../scripts/install_office2016_msi.sh)): extrai o `.iso` com `7z`, detecta se a mídia é MSI ou Click-to-Run, reusa o prefixo `~/.wine-office` e gera log completo em `~/office2016_install.log`:
>
> ```bash
> bash scripts/install_office2016_msi.sh ~/Downloads/Office2016ProPlus.iso
> # ou direto do executável: bash scripts/install_office2016_msi.sh ~/Downloads/setup.exe
> ```
>
> (O script usa `~/.wine-office` por padrão; se você criou outro prefixo nas etapas acima, informe com `WINEPREFIX=/caminho/do/prefixo bash script.sh ...`.)

### 4.5 Registro do ambiente (backup da configuração)

| Item | Valor |
|------|-------|
| WINEPREFIX | `~/wineprefixes/Office` |
| Versão do Wine | registrar a saída de `wine --version` |
| Versão do Office | 2016 (32-bit) |
| Dependências | as instaladas via winetricks |
| Local dos arquivos | prefixo + mídia de instalação |

---

## ETAPA 5 — Configuração

### 5.1 Português do Brasil

O Office herda o locale do sistema; se o sistema for `pt_PT`, configure o idioma de exibição do Office:

```bash
# Interface do Office em pt-BR (dentro do prefixo):
winecontrol  # Idioma → adicionar Português (Brasil) e definir como padrão
```

> ⚠️ **`winetricks locale=pt_BR` não funciona mais** (verb removido em versões recentes do winetricks). Aplicar locale via registro direto:
>
> ```bash
> wine reg add "HKCU\Control Panel\International" /v LocaleName /t REG_SZ /d pt-BR /f
> wine reg add "HKCU\Control Panel\International" /v Locale /t REG_SZ /d 00000416 /f
> ```
>
> Observação: o Wine reescreve essa chave ao iniciar processos baseado no `LANG` do sistema. Para pt-BR efetivo, ou o sistema tem `LANG=pt_BR.UTF-8`, ou você define o idioma dentro do próprio Word/Excel (Arquivo → Opções → Idioma).

Verifique: acentuação, `ç`, corretor ortográfico, separadores decimais, formato de data.

### 5.2 Impressão

O Wine usa o CUPS do Linux — se o sistema imprime, o Office normalmente imprime:

```bash
lpstat -d                  # impressora padrão
systemctl status cups      # serviço ativo
```

Se houver problema, diagnostique **antes** de mexer: CUPS → impressora padrão → drivers → Wine printing.

### 5.3 Atalhos

```bash
# Exemplos (ajuste caminhos após a instalação real):
wine start /unix "$WINEPREFIX/drive_c/Program Files/Microsoft Office/root/Office16/WINWORD.EXE"
```

Crie atalhos `.desktop` em `~/.local/share/applications/` para Word, Excel e PowerPoint (e Outlook, se compatível), e associe DOCX/XLSX/PPTX quando possível.

---

## ETAPA 6 — Testes obrigatórios

### Word
- [ ] abrir DOCX
- [ ] criar documento
- [ ] salvar DOCX
- [ ] abrir documento existente
- [ ] copiar e colar
- [ ] impressão
- [ ] fontes
- [ ] corretor ortográfico

### Excel
- [ ] abrir XLSX
- [ ] criar planilha
- [ ] fórmulas
- [ ] gráficos
- [ ] salvar XLSX
- [ ] copiar e colar
- [ ] impressão

### PowerPoint
- [ ] abrir PPTX
- [ ] criar apresentação
- [ ] inserir imagem
- [ ] inserir texto
- [ ] salvar PPTX
- [ ] apresentação de slides

> 🏫 **Uso educacional:** atenção especial a documentos escolares, provas, tabelas, imagens, gráficos e arquivos DOCX/XLSX/PPTX.

---

## ETAPA 7 — Correções (metodologia)

Se o Office não funcionar, **não** tente aleatoriamente dezenas de configurações:

1. capture o erro;
2. identifique em qual etapa ocorreu;
3. consulte a compatibilidade da versão (WineHQ AppDB);
4. verifique o log (`wine` imprime no terminal; prefixo tem logs em `~/wineprefixes/Office/`);
5. determine a causa provável;
6. proponha **uma** correção;
7. aplique somente a correção necessária;
8. teste novamente.

Se a versão escolhida for incompatível, a recomendação passa a ser a versão do Office com maior probabilidade de funcionamento.

---

## ETAPA 8 — Relatório final

Ao finalizar, preencha:

```text
Sistema:
Wine:
Winetricks:
Gerenciador utilizado:
Office:
Versão:
Arquitetura:
WINEPREFIX:
Local da instalação:
Word:
Excel:
PowerPoint:
Impressão:
DOCX:
XLSX:
PPTX:
Idioma:
Status:
```

### Comandos de manutenção futura

```bash
# Abrir um aplicativo do Office:
export WINEPREFIX="$HOME/wineprefixes/Office"
wine start /unix "$WINEPREFIX/drive_c/Program Files/Microsoft Office/root/Office16/WINWORD.EXE"

# Abrir winetricks (instalar/remover componentes):
export WINEPREFIX="$HOME/wineprefixes/Office"
winetricks --gui

# Verificar versão do Wine:
wine --version
```

---

## Regras de segurança (vale para todo o fluxo)

- ❌ **Nunca** execute `rm -rf` sem especificar o caminho e obter autorização quando houver risco de perda de dados.
- ❌ **Nunca** execute scripts baixados da internet sem antes verificar o conteúdo.
- ❌ **Nunca** adicione repositórios desconhecidos — priorize repositórios oficiais, WineHQ, Ubuntu/Debian e fontes confiáveis.
- ❌ **Não** desinstale/substitua componentes existentes sem necessidade.
- ❌ **Não** altere configurações globais do Wine se for possível trabalhar dentro do `WINEPREFIX` exclusivo.
- ❌ **Não** altere Docker, Python, Node.js, Ollama, ComfyUI, VS Code ou outros ambientes existentes — o objetivo é **adicionar** o Office, não reconstruir o Linux.

## Atualizações

**Não** atualize automaticamente componentes críticos do Wine depois que o Office estiver funcionando. Antes de atualizar:

1. identifique a versão atual;
2. explique o risco;
3. verifique compatibilidade;
4. faça backup do prefixo (`cp -a ~/wineprefixes/Office ~/wineprefixes/Office.bak`);
5. somente depois atualize.

---

## Referências

- WineHQ AppDB — compatibilidade por versão do Office: https://appdb.winehq.org
- Winetricks — catálogo de componentes: https://github.com/Winetricks/winetricks
- Diagnóstico automático: [`scripts/diagnose_office_linux.sh`](../scripts/diagnose_office_linux.sh)
- Preparo do prefixo Wine (M365/Office): [`scripts/setup_office_wine.sh`](../scripts/setup_office_wine.sh)
- Instalação do Office 2016 MSI: [`scripts/install_office2016_msi.sh`](../scripts/install_office2016_msi.sh)

---

## 📚 Lições aprendidas — Case Study (Ubuntu 26.04 + Wine 10.0 + Office 2021)

> Tentativa real executada em **10/08/2026** no Ubuntu 26.04 LTS (kernel 7.0.0-29-generic, Intel i7-13620H, 30 GiB RAM). Documentada para pouparr trabalho futuro — inclui **erros, workarounds e o veredito final**.

### Ambiente testado

| Componente | Versão |
|------------|--------|
| Sistema | Ubuntu 26.04 LTS (codename `resolute`) |
| Kernel | 7.0.0-29-generic x86_64 |
| Wine | **10.0** (`10.0~repack-12ubuntu1`, repositório oficial Ubuntu) |
| Winetricks | `20250102-1build1` (repositório oficial Ubuntu) |
| Office | **2021 ProPlus Volume** (canal `PerpetualVL2021`, 32-bit, pt-BR) via Office Deployment Tool |
| Prefixo | `~/.wine-office` (win64/WoW64) |

### ✅ O que funcionou (manter como referência)

#### 1. Wine 10 está nos repositórios oficiais do Ubuntu 26.04

**Não é mais necessário adicionar repositório WineHQ externo.** `sudo apt install wine wine32:i386 wine64 winetricks` traz a versão 10.0 estável direto do Ubuntu. **Mais seguro** (mantém tudo dentro do gerenciador de pacotes).

#### 2. O `dpkg --add-architecture i386` já vem feito no Ubuntu 26.04

A arquitetura `i386` já estava habilitada por padrão. Um passo a menos.

#### 3. EULA do `ttf-mscorefonts-installer` é problemática

Se você tiver problemas com o `ttf-mscorefonts-installer` travando a instalação (tela debconf presa, dpkg meio-configurado), **pule-o** e instale as fontes via `winetricks corefonts` dentro do prefixo. É mais limpo e isolado. As fontes core vêm do GitHub (`pushcx/corefonts`), não do instável SourceForge.

#### 4. ⚠️ Wine 10 não suporta mais `WINEARCH=win32`

Comando que **falha**:
```bash
WINEPREFIX=~/.wine-office WINEARCH=win32 wineboot
# wine: WINEARCH is set to 'win32' but this is not supported in wow64 mode.
```

Comando **correto** (Wine 10 / WoW64):
```bash
WINEPREFIX=~/.wine-office WINEARCH=win64 wineboot
```

O Wine 8+ consolidou tudo no modo **WoW64**: o prefixo é `win64` mas executa binários 32-bit nativamente via camada de compatibilidade. **Você não perde nada** — Office 32-bit roda igual ou melhor neste modo. O binário vai para `Program Files (x86)/Microsoft Office/` (e não `Program Files/`).

#### 5. Sequência winetricks que funcionou

```bash
WINEPREFIX=~/.wine-office winetricks -q corefonts
WINEPREFIX=~/.wine-office winetricks -q vcrun2019 dotnet48
WINEPREFIX=~/.wine-office winetricks -q win10
```

> ⚠️ As mensagens `err:environ:init_peb starting ... in experimental wow64 mode` são **normais** no Wine 10 e não indicam falha.

#### 6. `locale=pt_BR` não existe mais como verb do winetricks

Sintaxe antiga falha: `winetricks -q locale=pt_BR` → `Unknown arg`. Aplicar locale via registro direto:

```bash
WINEPREFIX=~/.wine-office wine reg add "HKCU\Control Panel\International" /v LocaleName /t REG_SZ /d pt-BR /f
WINEPREFIX=~/.wine-office wine reg add "HKCU\Control Panel\International" /v Locale /t REG_SZ /d 00000416 /f
```

> Observação: o Wine reescreve essa chave ao iniciar processos baseado no `LANG` do sistema. Para forçar pt-BR de verdade, ou o sistema tem `LANG=pt_BR.UTF-8`, ou você configura o idioma de exibição dentro do próprio Word/Excel (Arquivo → Opções → Idioma).

#### 7. URL oficial atual do Office Deployment Tool

A URL muda (a Microsoft rotaciona). Em **14/07/2026** a versão era `16.0.20131.20090`:

```bash
wget -O officedeploymenttool.exe \
  "https://download.microsoft.com/download/6c1eeb25-cf8b-41d9-8d0d-cc1dbc032140/officedeploymenttool_20131-20090.exe"
```

**Sempre confirmar a URL atual** em https://www.microsoft.com/en-us/download/details.aspx?id=49117 antes de baixar.

#### 8. Aqui-doc (`cat << EOF`) pode falhar em terminais com pager/visualizador

Se o seu shell tem `bat`, `eza cat` ou similar interceptando stdout, o here-doc pode resultar em arquivo vazio. **Workaround:** usar `printf '%s\n' linha1 linha2 ... > arquivo`.

#### 9. Download do Office 2021 via `setup.exe /download` FUNCIONOU

Apesar dos erros `err:ole:create_server class {5b99fa76-...}` durante o download, **os 1.7 GB foram baixados com sucesso** para `Office/Data/16.0.14334.20806/`. Esses erros COM são **não-fatais** para o `/download` (só afetam o `/configure`).

### ❌ O que NÃO funcionou (não tente de novo)

#### 1. `setup.exe /configure` falha no Wine — Click-to-Run Service não implementado

```
0160:err:ole:create_server class {5b99fa76-721c-423c-adac-56d03c8a8007} not registered
wine: Unhandled exception 0xe0434352 ... InspectorOfficeGadget.exe ... TypeLoadException
0258:err:seh:NtRaiseException Unhandled exception code c0000409 (integrator.exe)
```

**O GUID `{5b99fa76-721c-423c-adac-56d03c8a8007}`** é o **Microsoft Office ClickToRun Service** — um NT service que o Wine ainda não implementa completamente.

#### 2. `InspectorOfficeGadget.exe` e `integrator.exe` crasham

Estes componentes do C2R crasham com `TypeLoadException` (.NET) e `STATUS_STACK_BUFFER_OVERRUN`. Eles cuidam do registro final de COM/DLLs e da criação de tarefas agendadas.

#### 3. Mesmo com 2.4 GB de binários extraídos, Word/Excel/PowerPoint não abrem

Os binários `WINWORD.EXE`, `EXCEL.EXE`, `POWERPNT.EXE` foram extraídos para `~/.wine-office/drive_c/Program Files (x86)/Microsoft Office/root/Office16/` — mas ao tentar executar direto:

```
0024:err:module:import_dll Library AppVIsvSubsystems32.dll not found
0024:err:module:loader_init ... status c0000135
```

Mesmo copiando manualmente as DLLs AppV (de `i320.cab`) para `Office16/`, `system32/` e `syswow64/`, o Word **sai silenciosamente** sem abrir janela. O launcher `c2rdll` do Office exige o Click-toRun service ativo para mapear a virtualização App-V.

#### 4. Segunda execução do `setup.exe /configure` DESINSTALA o Office

Após o primeiro `/configure` falhar, rodar de novo faz o Click-toRun entender que há instalação parcial corrompida e iniciar `TaskRemoveInstallation` (desinstalação). Confirmado no log:

```
Click-To-Run Task Error  TaskRemoveInstallation::ShutdownService
"ContextData": "Unable to stop service. Giving up"
```

### 🎯 Veredito técnico final

**Office 2021 Click-to-Run é fundamentalmente incompatível com o Wine atual** (testado até Wine 10.0 em ago/2026). Não há workaround confiável. A AppDB do WineHQ classifica Office 2021 como **Garbage**.

#### Recomendações para uso real de documentos DOCX/XLSX/PPTX no Linux

| Alternativa | Compatibilidade MS Office | Observação |
|-------------|--------------------------|------------|
| **LibreOffice** | ⭐⭐⭐⭐ | Alternativa clássica, compatibilidade muito boa. `sudo apt install libreoffice` |
| **WPS Office** | ⭐⭐⭐⭐ | Boa compatibilidade, interface familiar. Download em https://www.wps.com |
| **Office Online (web)** | ⭐⭐⭐⭐⭐ | Microsoft 365 gratuito no navegador — perfeito para uso ocasional. https://www.office.com |

#### Quando o Wine faz sentido (para Office)

A **única** versão Office com histórico WineHQ confiável é **Office 2016 MSI** (não Click-to-Run). Requer:

- Mídia física `.iso`/`.exe` MSI legítima do Office 2016 (não está mais à venda na Microsoft)
- Não funciona com Office 2019, 2021 ou Microsoft 365 (todos Click-to-Run)

### 📜 Comandos finais utilizados (referência)

```bash
# 1. Instalar Wine 10 + dependências (Ubuntu 26.04)
sudo apt install -y wine wine32:i386 wine64 winetricks cabextract winbind

# 2. Criar prefixo isolado (Wine 10 / WoW64)
WINEPREFIX=~/.wine-office WINEARCH=win64 wineboot

# 3. Configurar prefixo
WINEPREFIX=~/.wine-office winetricks -q corefonts vcrun2019 dotnet48 win10

# 4. Baixar Office Deployment Tool
wget -O officedeploymenttool.exe \
  "https://download.microsoft.com/download/6c1eeb25-cf8b-41d9-8d0d-cc1dbc032140/officedeploymenttool_20131-20090.exe"
cabextract -q officedeploymenttool.exe -d odt-extracted

# 5. Criar configuration.xml (aqui: Office 2021 ProPlus 32-bit pt-BR)
printf '%s\n' \
'<Configuration>' \
'  <Add OfficeClientEdition="32" Channel="PerpetualVL2021">' \
'    <Product ID="ProPlus2021Volume">' \
'      <Language ID="pt-BR" />' \
'      <ExcludeApp ID="OneDrive" />' \
'      <ExcludeApp ID="Teams" />' \
'    </Product>' \
'  </Add>' \
'  <Display Level="Full" AcceptEULA="TRUE" />' \
'  <Logging Level="Standard" Path="%temp%" />' \
'</Configuration>' > configuration.xml

# 6. Download dos arquivos do Office (FUNCIONA)
WINEPREFIX=~/.wine-office wine odt-extracted/setup.exe /download configuration.xml

# 7. Instalação (FALHA — Click-to-Run não implementado no Wine)
# WINEPREFIX=~/.wine-office wine odt-extracted/setup.exe /configure configuration.xml
```

### 🧹 Limpeza (se quiser reverter)

```bash
# Remover prefixo Wine do Office (4.6 GB na data da atualização)
rm -rf ~/.wine-office

# Remover arquivos baixados do Office 2021 (1.7 GB)
rm -rf ~/Downloads/office2021-installer

# Desinstalar Wine + Winetricks (opcional, se não usar para outros fins)
# sudo apt autoremove --purge wine wine32:i386 wine64 winetricks cabextract winbind

# Cache do winetricks (~/.cache/winetricks/) pode ser removido
rm -rf ~/.cache/winetricks
```

> ⚠️ **Atenção:** nunca rode `rm -rf ~/.wine-office` sem confirmar antes que o caminho está correto e que não há outros prefixos Wine dentro dessa pasta. Sempre verifique com `ls ~/.wine-office/` antes.
>
> 💡 **Atualização (11/08/2026):** o prefixo foi **reaproveitado** para a preparação do Office 2016 MSI — **não remova ainda** (ver seção abaixo; o tamanho atual é **4,6 GB**, não mais 2,4 GB).

### 📖 Referências extras (estudo)

- WineHQ Bug 50894 — workaround `w_workaround_wine_bug-50894` aplicado pelo winetricks durante a instalação do vcrun2019
- Microsoft Learn — [Office Deployment Tool overview](https://learn.microsoft.com/en-us/deployoffice/overview-office-deployment-tool)
- Microsoft Learn — [Configuration options for the Office Deployment Tool](https://learn.microsoft.com/en-us/deployoffice/office-deployment-tool-configuration-options)
- Repositório `pushcx/corefonts` no GitHub — mirror estável das fontes core Microsoft usadas pelo `winetricks corefonts`

---

## 📋 Preparação para Office 2016 MSI — ago/2026

> Continuação do Case Study acima. Após o veredito ❌ do Office 2021 Click-to-Run, o prefixo `~/.wine-office` foi **reaproveitado e preparado para receber a única versão com chance real no Wine: Office 2016 MSI**. Registro do ambiente final em **11/08/2026**.

### Estado atual do prefixo `~/.wine-office`

| Componente | Valor |
|------------|-------|
| Prefixo | `~/.wine-office` (win64/WoW64) — **4,6 GB** |
| Wine | 10.0 (repositório oficial Ubuntu) |
| Versão Windows reportada | **10.0** (build 19045) — aplicada via registro direto + `wineserver -k` (`winecfg -v win10` não persistia sozinho) |
| DLLs nativas (validadas por checksum) | `gdiplus` (1,6 MB) · `msxml3` (1,2 MB) · `msxml6` (1,4 MB) · `riched20` (431 KB) |
| Overrides de registro | `gdiplus=native` · `msxml3=native` · `msxml6=native,builtin` · `riched20=native,builtin` |
| Winetricks (preparação MSI) | `corefonts`, `vcrun2010`, `vcrun2013` |
| Winetricks (da tentativa C2R, mantidas) | `vcrun2019`, `dotnet48`, `win10` |

Comando de referência usado na preparação (na ordem: primeiro os que funcionam, depois os opcionais):

```bash
export WINEPREFIX=~/.wine-office WINEDEBUG=-all
winetricks -q corefonts riched20 gdiplus msxml3 msxml6 vcrun2010 vcrun2013

# Opcionais — falham se o mirror web.archive.org estiver bloqueado:
# winetricks -q msls31 riched30
```

### 🛠️ Tabela de manutenção — como verificar a preparação

Execute sempre com o prefixo exportado (`export WINEPREFIX=~/.wine-office WINEDEBUG=-all`). Os valores abaixo são o estado **verificado em 11/08/2026**:

| Item | Estado esperado | Comando de verificação |
|------|-----------------|------------------------|
| Prefixo existe e tem tamanho coerente | `~/.wine-office` com **≈4,6 GB** | `du -sh ~/.wine-office` |
| Versão do Wine | `wine-10.0 (Ubuntu 10.0~repack-12ubuntu1)` | `wine --version` |
| Versão Windows reportada | `10.0`, build **19045**, ProductName `Microsoft Windows 10` | `wine reg query 'HKLM\Software\Microsoft\Windows NT\CurrentVersion' \| grep -iE '^[[:space:]]*(CurrentBuildNumber\|CurrentVersion\|ProductName)'` |
| DLLs nativas em `syswow64` | `gdiplus` 1,6 MB · `msxml3` 1,2 MB · `msxml6` 1,4 MB · `riched20` 431 KB | `ls -la ~/.wine-office/drive_c/windows/syswow64/{gdiplus,msxml3,msxml6,riched20}.dll` |
| Overrides de registro | `gdiplus=native` · `msxml3=native` · `msxml6=native,builtin` · `riched20=native,builtin` | `wine reg query 'HKCU\Software\Wine\DllOverrides' \| grep -iE 'gdiplus\|msxml3\|msxml6\|riched20'` |
| Fontes core instaladas | `arial*.ttf`, `times*.ttf`, `verdana*.ttf`, `georgia*.ttf`, `cour*.ttf` em `Fonts/` | `ls ~/.wine-office/drive_c/windows/Fonts/ \| grep -iE 'arial\|times\|verdana\|georgia\|cour'` |
| Verbs winetricks executados | `corefonts`, `vcrun2010`, `vcrun2013`, `gdiplus`, `msxml3`, `msxml6` (mais `vcrun2019`, `dotnet48`, `win10` da tentativa C2R) | `grep -iE 'corefonts\|vcrun2010\|vcrun2013\|msxml3\|msxml6\|gdiplus' ~/.wine-office/winetricks.log` |
| Office 2016 instalado | ⏳ **Pendente** — aguardando a mídia MSI (ver ⚠️ Pendências) | `ls ~/.wine-office/drive_c/Program\ Files\ \(x86\)/Microsoft\ Office/Office16/WINWORD.EXE` |

> 💡 **Observação sobre os overrides:** os verbs do winetricks gravam com prefixo `*` (ex.: `*gdiplus`, `*msxml6`). Existe também uma entrada manual `riched20` (sem `*`). As **duas entradas de `riched20`** (`*riched20` e a manual) têm `native,builtin`; já `*gdiplus` e `*msxml3` são apenas `native`. É o estado correto — nada a remover.

**Diagnóstico de 1 minuto** — valida a preparação inteira de uma vez:

```bash
export WINEPREFIX=~/.wine-office WINEDEBUG=-all
# A primeira chamada wine inicia o wineserver — deixe-a ser a query (evita corrida):
wine reg query 'HKLM\Software\Microsoft\Windows NT\CurrentVersion' | grep -iE '^[[:space:]]*(CurrentBuildNumber|CurrentVersion|ProductName)'
wine reg query 'HKCU\Software\Wine\DllOverrides' | grep -iE 'gdiplus|msxml3|msxml6|riched20'
du -sh ~/.wine-office
ls -la ~/.wine-office/drive_c/windows/syswow64/gdiplus.dll ~/.wine-office/drive_c/windows/syswow64/msxml3.dll ~/.wine-office/drive_c/windows/syswow64/msxml6.dll ~/.wine-office/drive_c/windows/syswow64/riched20.dll
wine --version
```

> ⚠️ Se as queries `wine reg query` retornarem **vazio**, o wineserver pode estar iniciando ou reiniciando — rode `wineserver -k` e repita o bloco.

### 🩹 Downloads corrompidos corrigidos no cache do winetricks

Dois arquivos em `~/.cache/winetricks/` estavam inválidos e **quebravam os verbs** (o `cabextract` falhava silenciosamente):

| Arquivo | Problema | Correção |
|---------|----------|----------|
| `win7sp1/windows6.1-KB976932-X64.exe` | Truncado (450 MB vs ~533 MB; checksum ≠ `f4d1d418…`) | Rebaixado com `wget -c` de `download.windowsupdate.com` + checksum validado |
| `win2ksp4/W2KSP4_EN.EXE` | Variante errada (sem `i386/riched20.dl_`; checksum ≠ `167bb78d…`) | Baixada a versão completa (135 MB) de `x3270.bgp.nu` + checksum validado |

> 💡 **Diagnóstico rápido:** se um verb do winetricks falhar, confira o checksum com `sha256sum` e compare com o esperado em `/usr/bin/winetricks` antes de rebaixar — download truncado é a causa mais comum.

### ⚠️ Pendências

- **`msls31` e `riched30` não instalados** — o mirror `web.archive.org` usado por esses verbs está bloqueado nesta rede. São **opcionais** (o Wine já tem `msls31` builtin); se aparecer erro de `msls31.dll` durante o uso do Word/Excel, resolver na hora.
- **Mídia MSI do Office 2016 ainda não disponível no sistema** — fontes legítimas:
  1. Contrato **Volume License** (VLSC / M365 admin center) → download do `Office 2016 ProPlus.iso`;
  2. **Chave de produto + conta Microsoft** com licença do Office 2016;
  3. **DVD físico** original.

### 🚀 Instalação (quando a mídia chegar)

Usar o script de primeira parte [`scripts/install_office2016_msi.sh`](../scripts/install_office2016_msi.sh):

```bash
bash scripts/install_office2016_msi.sh ~/Downloads/Office2016ProPlus.iso   # ou o setup.exe direto
# Log completo em: ~/office2016_install.log
```

O script: extrai `.iso` com `7z` (limpando extrações antigas), detecta se a mídia é MSI ou Click-to-Run (aviso, não bloqueia), reusa o prefixo `~/.wine-office` (cria se não existir), executa o instalador e verifica se `WINWORD.EXE`/`EXCEL.EXE` foram instalados. Validado com `bash -n`, `shellcheck` e teste end-to-end com um `.iso` de mentira.

> ⚠️ **Resíduos do C2R 2021 no prefixo:** os binários da tentativa anterior estão em `Program Files (x86)/Microsoft Office/root/Office16/` (~2,4 GB) com registro incompleto. O MSI 2016 instala em `Microsoft Office/Office16/` (sem `root/`) — **sem colisão de arquivos**. Se o instalador reclamar de instalação existente, remova os resíduos e rode o script de novo.
