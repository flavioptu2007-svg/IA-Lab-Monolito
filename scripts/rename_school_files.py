#!/usr/bin/env python3
"""
rename_school_files.py
Renomeia arquivos educacionais com base em palavras-chave no nome original.
Classifica e move para a estrutura Johnny.Decimal + PARA.
"""

import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

SOURCE_DIR = Path("/home/flavio/Transferências")
DEST_BASE = Path("/home/flavio/Documentos/Escola")
INBOX = DEST_BASE / "00-Inbox"
INBOX.mkdir(parents=True, exist_ok=True)

# Tabela de classificação (ordem importa — primeiro match wins)
# Prioridade: mais específico primeiro
RULES = [
    # --- INSTALADORES / SOFTWARE → Inbox para revisão ---
    (re.compile(r"\.(deb|rpm|exe|dmg|pkg|msi)$", re.IGNORECASE), None),  # vai para Inbox
    (re.compile(r"\.(tar\.gz|tar\.xz|AppImage)$", re.IGNORECASE), None),  # vai para Inbox
    # --- PLANO DE AULA / PLANEJAMENTO (antes de EJA genérico) ---
    (re.compile(r"plano.*de.*aula|plano.*aula", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"plano.*de.*curso|plano.*curso|planodecurso", re.IGNORECASE), "12-Planejamentos-2026"),
    (re.compile(r"planejamento.*ensino|planejamento.*aula", re.IGNORECASE), "12-Planejamentos-2026"),
    (
        re.compile(r"planej.*(anual|semestral|curso)|plano.*(anual|semestral|curso)", re.IGNORECASE),
        "12-Planejamentos-2026",
    ),
    # --- EJA (regras de período ANTES da genérica) ---
    (
        re.compile(
            r"eja.*(4|4[ºo]).*periodo|4.*periodo.*eja|4.*ciclo.*eja|4.*semestre.*eja|eja.*4", re.IGNORECASE
        ),
        "22-EJA/22.4-4Periodo",
    ),
    (
        re.compile(
            r"eja.*(3|3[ºo]).*periodo|3.*periodo.*eja|3.*ciclo.*eja|3.*semestre.*eja|eja.*3", re.IGNORECASE
        ),
        "22-EJA/22.3-3Periodo",
    ),
    (
        re.compile(
            r"eja.*(2|2[ºo]).*periodo|2.*periodo.*eja|2.*ciclo.*eja|2.*semestre.*eja|eja.*2", re.IGNORECASE
        ),
        "22-EJA/22.2-2Periodo",
    ),
    (
        re.compile(
            r"eja.*(1|1[ºo]).*periodo|1.*periodo.*eja|1.*ciclo.*eja|1.*semestre.*eja|eja.*1", re.IGNORECASE
        ),
        "22-EJA/22.1-1Periodo",
    ),
    (
        re.compile(r"\d[ºo].*periodo.*eja|eja.*\d[ºo].*periodo", re.IGNORECASE),
        "22-EJA",
    ),  # fallback com número
    (re.compile(r"eja", re.IGNORECASE), "22-EJA"),  # genérico
    # --- AVALIAÇÕES ---
    (
        re.compile(r"prova.*bimestral|prova.*trimestral|avalia.*bimestr", re.IGNORECASE),
        "32-Avaliacoes-e-Simulados",
    ),
    (
        re.compile(r"avaliacao|avaliação|prova|saeb|simave|caed|inep|diagnóstica", re.IGNORECASE),
        "32-Avaliacoes-e-Simulados",
    ),
    # --- BNCC / CURRÍCULO ---
    (re.compile(r"bncc|curriculo|currículo|crmg|referencia", re.IGNORECASE), "33-BNCC-e-Curriculos"),
    # --- ATIVIDADES / EXERCÍCIOS / TEMAS DE HISTÓRIA ---
    (re.compile(r"ativ|exercic|simulado|gabarito|quest", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (
        re.compile(r"reforma.*protestante|luter|calvin|zwingl|contrareforma|contra.reforma", re.IGNORECASE),
        "31-Atividades-e-Exercicios",
    ),
    (re.compile(r"revolu.*frances|napoleon", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"revolu.*russa|bolchev|lenin|trotsk", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"egito.*antigo|egipcio", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"feudalis", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"pr.?colomb|maia|asteca|inca", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"haiti|independencia.*haiti", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"darwin|evolu", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"islam|islami|muçulmano|oriente.*medio", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"colonial|colonia|brasil.*colonia|aucareira", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (re.compile(r"histo.*ri.*a|historia|historiograf", re.IGNORECASE), "31-Atividades-e-Exercicios"),
    (
        re.compile(r"bingo|domino|jogo.*ensino|jogo.*historia|ludic", re.IGNORECASE),
        "31-Atividades-e-Exercicios",
    ),
    # --- IMAGENS / DIAGRAMAS / MAPAS ---
    (re.compile(r"mapa.*mental|diagrama|ilustr|caricatura|charge", re.IGNORECASE), "34-Midias-e-Imagens"),
    # --- GRP / SISTEMA ---
    (re.compile(r"grp|sistema.*paracatu", re.IGNORECASE), "24-Administracao/24.1-GRP-e-Sistema"),
    # --- PESSOAL ---
    (
        re.compile(r"milha|viagem|promoc|promoção|azul|latam|mestre.*milha", re.IGNORECASE),
        "50-Pessoal/52-Viagens",
    ),
    (
        re.compile(r"torrent|filme|bludv|dublad|legendad|revolucao.*dos.*bichos", re.IGNORECASE),
        "50-Pessoal/59-Lazer",
    ),
    (re.compile(r"mochila|compra|plus.size|camisa|adesao.bonus", re.IGNORECASE), "50-Pessoal/53-Compras"),
    (re.compile(r"contracheque|cnh|documento.*flavio|notas.*ag", re.IGNORECASE), "50-Pessoal/51-Financas"),
    (re.compile(r"proton.*recovery|github.*recovery", re.IGNORECASE), "50-Pessoal/51-Financas"),
    # --- FORMATAÇÃO / CONTINUADA ---
    (re.compile(r"formacao.*continuada", re.IGNORECASE), "24-Administracao/24.2-Formacao-Continuada"),
    # --- CHATGPT / IA IMAGES → imagens ---
    (re.compile(r"chatgpt.*image|gemini.*image|gemini.*generated", re.IGNORECASE), "34-Midias-e-Imagens"),
    # --- FONTES / TEMPLATES ---
    (re.compile(r"font", re.IGNORECASE), "36-Templates-e-Modelos"),
    # --- DOCUMENTOS PESSOAIS GENÉRICOS ---
    (
        re.compile(r"diario.*classe|diario.*eja|freq.*encia", re.IGNORECASE),
        "24-Administracao/24.3-Documentos-Funcionais",
    ),
    (
        re.compile(r"ata.*resultado|conselho.*classe", re.IGNORECASE),
        "24-Administracao/24.3-Documentos-Funcionais",
    ),
]

# Mapeamento de subpasta EJA
EJA_SUB = {
    "1": "22.1-1Periodo",
    "1º": "22.1-1Periodo",
    "2": "22.2-2Periodo",
    "2º": "22.2-2Periodo",
    "3": "22.3-3Periodo",
    "3º": "22.3-3Periodo",
    "4": "22.4-4Periodo",
    "4º": "22.4-4Periodo",
}


def slugify(text):
    """Remove acentos, converte para kebab-case."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-").lower()
    # Remove hífens duplicados
    text = re.sub(r"-{2,}", "-", text)
    return text[:80]


def classify_file(filename):
    """Retorna (categoria, subpasta) ou (None, None)."""
    for pattern, category in RULES:
        if pattern.search(filename):
            if category is None:
                return None, None
            # Se já tem subpasta na regra, usa direto
            if "/" in category:
                parts = category.split("/", 1)
                return parts[0], parts[1]
            # Verifica subpasta EJA apenas se a categoria é EJA e não tem subpasta embutida
            if "EJA" in category or "eja" in category.lower():
                for num_label, sub in EJA_SUB.items():
                    if num_label in filename:
                        return category, sub
                return category, None  # sem subpasta se não achou número
            return category, None
    return None, None


def extract_date_from_name(filename):
    """Tenta extrair uma data do nome do arquivo."""
    # AAAA-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # DD/MM/AAAA
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", filename)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # DD-MM-AAAA
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", filename)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def generate_new_name(original, category, _subfolder):
    """Gera novo nome padronizado."""
    stem = Path(original).stem
    ext = Path(original).suffix.lower()

    # Remove hashes UUID
    stem_clean = re.sub(
        r"^[0-9a-f]{8,}-[0-9a-f]{4,}-[0-9a-f]{4,}-[0-9a-f]{4,}-[0-9a-f]{12,}", "", stem, flags=re.IGNORECASE
    )
    # Remove padrões de numeração soltos no início (ex: "33-+REFORMA...")
    stem_clean = re.sub(r"^\d+[-+]+", "", stem_clean)
    stem_clean = stem_clean.strip(" -_.+()") or stem

    slug = slugify(stem_clean)
    if not slug:
        slug = "arquivo-sem-nome"

    # Adiciona contexto EJA
    if "EJA" in str(category) or "eja" in str(category).lower():
        for num_label in ["4º", "3º", "2º", "1º", "4", "3", "2", "1"]:
            if num_label in original:
                period = num_label.replace("º", "")
                slug = f"eja-{period}-periodo-{slug}"
                break

    # Tenta extrair data do nome original
    date_str = extract_date_from_name(original)
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    return f"{date_str}_{slug}_v01{ext}"


def process_files(dry_run=True):
    """Processa todos os arquivos na pasta de origem."""
    moved = 0
    inbox_count = 0
    skipped = 0
    duplicates = 0

    files = [f for f in SOURCE_DIR.iterdir() if f.is_file()]
    print(f"Arquivos encontrados: {len(files)}\n")

    for filepath in sorted(files):
        filename = filepath.name

        # Pula ocultos
        if filename.startswith("."):
            skipped += 1
            continue

        category, subfolder = classify_file(filename)

        if category is None:
            # Vai para Inbox
            dest = INBOX / filename
            action = "INBOX" if not dry_run else "[DRY] INBOX"
            print(f"  {action}: {filename}")
            if not dry_run:
                shutil.copy2(filepath, dest)
            inbox_count += 1
            continue

        # Monta caminho de destino
        dest_dir = DEST_BASE / category
        if subfolder:
            dest_dir = dest_dir / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Gera novo nome
        new_name = generate_new_name(filename, category, subfolder)
        dest_path = dest_dir / new_name

        # Evita sobrescrever
        counter = 1
        original_name = new_name
        while dest_path.exists():
            new_name = original_name.replace("_v01", f"_v{counter:02d}")
            dest_path = dest_dir / new_name
            counter += 1
            if counter > 1:
                duplicates += 1

        action = "CLASSIFICAR" if not dry_run else "[DRY] CLASSIFICAR"
        rel_path = dest_path.relative_to(DEST_BASE)
        print(f"  {action}: {filename}")
        print(f"    -> {rel_path}")
        if not dry_run:
            shutil.copy2(filepath, dest_path)
        moved += 1

    print(f"\n{'=' * 60}")
    print(f"{'[DRY RUN — nada foi movido]' if dry_run else '[EXECUTADO]'}")
    print(f"{'=' * 60}")
    print(f"  Classificados e copiados: {moved}")
    print(f"  Duplicatas renomeadas:    {duplicates}")
    print(f"  Enviados para Inbox:      {inbox_count}")
    print(f"  Pulados:                  {skipped}")
    print(f"{'=' * 60}")
    if dry_run:
        print("\nRevise acima. Se estiver correto, rode novamente com --apply")


if __name__ == "__main__":
    import sys

    dry = "--apply" not in sys.argv
    process_files(dry_run=dry)
