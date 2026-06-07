"""
Importação de Municípios do IBGE → Supabase (tab_cidade)
=========================================================

PASSO 1 — Execute este SQL no Supabase SQL Editor:

    CREATE TABLE IF NOT EXISTS tab_cidade (
        id_ibge   INTEGER PRIMARY KEY,
        nome      TEXT    NOT NULL,
        uf        CHAR(2) NOT NULL,
        nome_uf   TEXT    NOT NULL
    );

PASSO 2 — Rode este script:

    python importar_cidades.py
"""

import os
import sys
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IBGE_URL     = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
BATCH_SIZE   = 500


def buscar_ibge():
    print("[1/3] Buscando municípios na API do IBGE...")
    r = requests.get(IBGE_URL, timeout=30)
    r.raise_for_status()
    dados = r.json()
    print(f"      {len(dados)} municípios recebidos.")
    return dados


def transformar(dados):
    print("[2/3] Transformando dados...")
    registros = []
    ignorados = 0
    for m in dados:
        try:
            sigla = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        except (TypeError, KeyError):
            ignorados += 1
            continue
        registros.append({
            "cod_ibge": m["id"],
            "nome":     m["nome"],
            "uf":       sigla
        })
    if ignorados:
        print(f"      {ignorados} município(s) ignorado(s) por dados incompletos.")
    return registros


def gravar(supabase, registros):
    print("[3/3] Gravando no Supabase...")
    total = 0
    for i in range(0, len(registros), BATCH_SIZE):
        lote = registros[i : i + BATCH_SIZE]
        supabase.table("tab_cidades").upsert(lote, on_conflict="cod_ibge").execute()
        total += len(lote)
        print(f"      {total}/{len(registros)} gravados...")
    return total


def main():
    print("=" * 55)
    print("  Importação Municípios IBGE → Supabase")
    print("=" * 55)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    dados     = buscar_ibge()
    registros = transformar(dados)
    total     = gravar(supabase, registros)

    print(f"\nConcluído! {total} municípios importados com sucesso.")


if __name__ == "__main__":
    print(__doc__)
    resp = input("Você já criou a tabela no Supabase SQL Editor? (s/n): ").strip().lower()
    if resp != "s":
        print("\nCrie a tabela primeiro e execute o script novamente.")
        sys.exit(0)
    print()
    main()
