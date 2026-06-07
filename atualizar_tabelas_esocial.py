"""
Importa todas as tabelas eSocial do PDF Anexo I (S-1.3) para tab_tabela_total.

Uso:
    python atualizar_tabelas_esocial.py

Requer:
    pip install pdfplumber supabase python-dotenv
"""

import os
import re
import pdfplumber
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

PDF_PATH = r"C:\Dropbox\Manuais\Leiautes do eSocial v. S-1.3 - Anexo I - Tabelas (cons. até NT 03.2025).pdf"

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# PDF número da tabela  →  num_tabela no banco
# PDF tem "Tabela 13" e "Tabela 14" que o sistema já gravou como 15 e 16
TABLE_MAP = {
    1: 1, 2: 2, 3: 3, 5: 5, 7: 7, 8: 8, 9: 9, 10: 10,
    13: 15, 14: 16,
    17: 17, 18: 18, 19: 19, 20: 20, 21: 21,
    25: 25, 26: 26, 27: 27, 28: 28, 29: 29, 30: 30,
}
TABLES_TO_IMPORT = set(TABLE_MAP.keys())


# ─────────────────────────────────────────────
# Helpers de extração
# ─────────────────────────────────────────────

def limpar(s):
    if s is None:
        return ""
    return " ".join(str(s).split())          # normaliza espaços e quebras


def e_cabecalho(cod):
    """Retorna True se a célula parece ser um cabeçalho, não um código."""
    if not cod:
        return True
    c = cod.strip().upper()
    return c in ("CÓDIGO", "CODIGO", "COD", "CÓD", "CÓDIGO/SIGLA",
                 "Nº", "N", "TIPO", "CLASSIF.", "CLASSIF")


def extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=12,
                   apenas_digitos=False, apenas_alfanum=False):
    """
    Extrai pares (codigo, texto) de uma lista de objetos pdfplumber.Page.
    Deduplica por código.
    """
    rows = []
    seen = set()
    for page in pages:
        tables = page.extract_tables()
        for tbl in tables:
            for row in tbl:
                if not row:
                    continue
                if len(row) <= max(cod_col, txt_col):
                    continue
                cod = limpar(row[cod_col])
                txt = limpar(row[txt_col])
                if not cod or not txt:
                    continue
                if e_cabecalho(cod):
                    continue
                if apenas_digitos and not cod.isdigit():
                    continue
                if apenas_alfanum and not re.match(r'^[A-Za-z0-9]+$', cod):
                    continue
                if not (min_len <= len(cod) <= max_len):
                    continue
                if cod not in seen:
                    seen.add(cod)
                    rows.append({"codigo": cod, "texto": txt})
    return rows


def extract_grouped(pages):
    """
    Tab01: estrutura com coluna GRUPO. O CÓDIGO real fica em col[1] e
    tem sempre 3 dígitos (ex.: '101', '201').
    """
    rows = []
    seen = set()
    for page in pages:
        tables = page.extract_tables()
        for tbl in tables:
            for row in tbl:
                if not row or len(row) < 3:
                    continue
                cod = limpar(row[1])
                txt = limpar(row[2]) if len(row) > 2 else ""
                if not cod or not txt:
                    continue
                if e_cabecalho(cod):
                    continue
                if not re.match(r'^\d{3}$', cod):
                    continue
                if cod not in seen:
                    seen.add(cod)
                    rows.append({"codigo": cod, "texto": txt})
    return rows


# ─────────────────────────────────────────────
# Descoberta das páginas de cada tabela
# ─────────────────────────────────────────────

def descobrir_paginas(pdf):
    """
    Retorna dict: pdf_num_tabela -> (pag_inicio, pag_fim)  (1-indexed, inclusive)
    Varre o texto de cada pagina buscando "Tabela XX" como titulo de secao.
    Paginas que mencionam muitas tabelas diferentes sao ignoradas (sumario/indice).
    """
    pattern = re.compile(r'\bTabela\s+(\d{1,2})\b', re.IGNORECASE)
    inicio = {}

    for i, page in enumerate(pdf.pages, start=1):
        txt = page.extract_text() or ""
        encontradas_nesta_pag = set()
        for m in pattern.finditer(txt):
            n = int(m.group(1))
            if n in TABLES_TO_IMPORT:
                encontradas_nesta_pag.add(n)

        # Pagina com 5+ tabelas = sumario/indice, ignorar
        if len(encontradas_nesta_pag) >= 5:
            continue

        for n in encontradas_nesta_pag:
            if n not in inicio:
                inicio[n] = i

    # Fim de cada tabela = pagina antes do inicio da proxima tabela conhecida
    order = sorted(inicio.items(), key=lambda x: x[1])
    total = len(pdf.pages)
    ranges = {}
    for idx, (num, pg_ini) in enumerate(order):
        if idx + 1 < len(order):
            pg_fim = order[idx + 1][1] - 1
        else:
            pg_fim = total
        ranges[num] = (pg_ini, pg_fim)

    return ranges


# ─────────────────────────────────────────────
# Regras específicas por tabela PDF
# ─────────────────────────────────────────────

def extrair_tabela(pdf_num, pages):
    """Escolhe a estratégia certa para cada tabela e retorna lista de dicts."""

    if pdf_num == 1:
        # Tem coluna GRUPO; CÓDIGO fica na col[1] como 3 dígitos
        return extract_grouped(pages)

    if pdf_num == 2:
        # Simples: col0=código (2 dígitos), col1=texto
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=2)

    if pdf_num == 3:
        # Natureza das Rubricas da Folha de Pagamento: cod 4 digitos (1000-9999)
        # col1 = nome curto; col2 = descricao longa (nao usada aqui)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=4, max_len=4,
                               apenas_digitos=True)

    if pdf_num == 5:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=2)

    if pdf_num == 7:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=3)

    if pdf_num == 8:
        # Tipo de Logradouro (numerico): codigo 2 digitos
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=2, max_len=2,
                               apenas_digitos=True)

    if pdf_num == 9:
        # Tipos de Arquivo do eSocial: codigos S-XXXX (ex: S-1000, S-1005)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=6, max_len=6)

    if pdf_num == 10:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=3)

    if pdf_num == 13:   # -> num_tabela 15: Parte do Corpo atingida
        # Codigo 9 digitos (ex: 753030000)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=9, max_len=9,
                               apenas_digitos=True)

    if pdf_num == 14:   # -> num_tabela 16: Agente Causador do Acidente
        # Codigo 9 digitos (ex: 302010200)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=9, max_len=9,
                               apenas_digitos=True)

    if pdf_num == 17:
        # Natureza da Lesao: codigo 9 digitos (ex: 702000000)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=9, max_len=9,
                               apenas_digitos=True)

    if pdf_num == 18:
        # Motivo do Afastamento: codigo numerico 2 digitos
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=2, max_len=2,
                               apenas_digitos=True)

    if pdf_num == 19:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=4)

    if pdf_num == 20:
        # Tipos de Logradouro (sigla): codigos alfabeticos (A, AC, ACA, BSQ...)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=6,
                               apenas_alfanum=True)

    if pdf_num == 21:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=4)

    if pdf_num == 25:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=4)

    if pdf_num == 26:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=4)

    if pdf_num == 28:
        # Treinamentos/Capacitacoes: codigo 4 digitos (1006, 1207...)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=4, max_len=4,
                               apenas_digitos=True)

    if pdf_num == 29:
        # Codigos de Receita - Reclamatoria Trabalhista: 6 digitos (113851...)
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=6, max_len=6,
                               apenas_digitos=True)

    if pdf_num == 30:
        return extract_simple(pages, cod_col=0, txt_col=1, min_len=1, max_len=4)

    return []


# ─────────────────────────────────────────────
# Upsert no Supabase
# ─────────────────────────────────────────────

def upsert_tabela(num_tabela, rows):
    # Nao apaga se a extracao nao encontrou nada — evita perder dados bons
    if not rows:
        print(f"  [{num_tabela:>3}] AVISO: 0 registros extraidos — tabela NAO foi alterada")
        return

    del_res = (supabase.table("tab_tabela_total")
               .delete()
               .eq("num_tabela", num_tabela)
               .neq("codigo", "DOC")
               .execute())
    n_del = len(del_res.data) if del_res.data else 0

    novos = [{"num_tabela": num_tabela, "codigo": r["codigo"], "texto": r["texto"]}
             for r in rows]
    ins_res = supabase.table("tab_tabela_total").insert(novos).execute()
    n_ins = len(ins_res.data) if ins_res.data else 0
    print(f"  [{num_tabela:>3}] deletados {n_del:>4} | inseridos {n_ins:>4}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print(f"Abrindo PDF: {PDF_PATH}")
    with pdfplumber.open(PDF_PATH) as pdf:
        total_pags = len(pdf.pages)
        print(f"Total de paginas: {total_pags}\n")

        print("Descobrindo paginas das tabelas...")
        ranges = descobrir_paginas(pdf)

        nao_encontradas = TABLES_TO_IMPORT - set(ranges.keys())
        if nao_encontradas:
            print(f"AVISO: tabelas nao encontradas no PDF: {sorted(nao_encontradas)}")

        print(f"Tabelas encontradas: {sorted(ranges.keys())}\n")
        for num, (ini, fim) in sorted(ranges.items()):
            num_banco = TABLE_MAP[num]
            label = f"PDF Tab{num:02d}" + (f" -> banco {num_banco}" if num_banco != num else "")
            print(f"  {label} - paginas {ini}..{fim}")

        print("\nProcessando...")
        for pdf_num in sorted(ranges.keys()):
            ini, fim = ranges[pdf_num]
            pages = pdf.pages[ini - 1: fim]           # slice 0-indexed
            rows = extrair_tabela(pdf_num, pages)
            num_banco = TABLE_MAP[pdf_num]
            upsert_tabela(num_banco, rows)

    print("\nConcluido!")


if __name__ == "__main__":
    main()
