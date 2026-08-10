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
| **Office 2016 (32-bit)** | ✅ **Mais estável** | Teto prático de confiabilidade no Wine |
| Office 2021 (32-bit) | ⚠️ Funciona | Instalador click-to-run pode exigir ajustes |
| Office 2019 | ⚠️ Funciona | Fora do suporte mainstream desde out/2025 |
| Microsoft 365 (assinatura) | ❌ **Não roda** | Exige login Microsoft/click-to-run; AppDB: broken |
| OneDrive (cliente) | ❌ Não roda | Alternativas: web, `rclone`, `abraunegg/onedrive`, `onedriver` |

> 🔒 **Ativação:** sempre por **licença legítima**. Este guia **não** fornece cracks, ativadores, KMS ilegais, serial keys falsos ou métodos para burlar ativação.

### 2.3 Arquitetura

- **Recomendada: 32-bit** (prefixo `WINEARCH=win32`) — o Office 32-bit sofre menos problemas de registry/translation sob Wine.
- Decisão baseada em evidência da comunidade, **não por hábito**.

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
sudo apt update && sudo apt install -y wine winetricks cabextract
```

Resultado esperado:

```bash
wine --version        # → wine-10.0
winetricks --version  # → 20250102
```

### 4.2 Prefixo isolado (exclusivo do Office)

```bash
export WINEPREFIX="$HOME/wineprefixes/Office"
export WINEARCH=win32          # 32-bit — decidido na ETAPA 2
wineboot -u                   # inicializa o prefixo (cria ~/wineprefixes/Office)
```

> 🔒 O prefixo é **separado** — nada que o Office fizer afetará outros programas Windows do sistema.

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
