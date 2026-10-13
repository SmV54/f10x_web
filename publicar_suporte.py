# -*- coding: utf-8 -*-
"""Publica os guias de suporte no sistema.

Copia os PDFs de C:\\Dropbox\\Folha10-Simples\\Suporte para a pasta suporte/
do repositório, que vai para o Render no push (o Render não enxerga o
Dropbox). Espelha a pasta: guia renomeado ou apagado no Dropbox sai daqui
também. Só os PDFs — o Word fica no Dropbox para edição.

O número do início do nome é a sequência do card no Menu Principal
(1 Cadastros, 3 Eventuais, 4 Movimento Mês...; 0 = antes do menu); a tela
Ajuda agrupa por ele.

Uso:  python publicar_suporte.py   (depois: commit + push da pasta suporte/)
"""
import os
import re
import shutil

ORIGEM  = r"C:\Dropbox\Folha10-Simples\Suporte"
DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suporte")
NOME_OK = re.compile(r"^\d+-.+\.pdf$", re.IGNORECASE)


def main():
    os.makedirs(DESTINO, exist_ok=True)
    fonte = {f for f in os.listdir(ORIGEM) if NOME_OK.match(f)}
    fora  = sorted(f for f in os.listdir(ORIGEM)
                   if f.lower().endswith(".pdf") and f not in fonte)
    novos = alterados = 0
    for f in sorted(fonte):
        o, d = os.path.join(ORIGEM, f), os.path.join(DESTINO, f)
        if not os.path.exists(d):
            novos += 1
        elif os.path.getsize(d) != os.path.getsize(o) or os.path.getmtime(d) < os.path.getmtime(o):
            alterados += 1
        else:
            continue
        shutil.copy2(o, d)
        print("  copiado:", f)
    removidos = 0
    for f in os.listdir(DESTINO):
        if f.lower().endswith(".pdf") and f not in fonte:
            os.remove(os.path.join(DESTINO, f))
            removidos += 1
            print("  removido:", f)
    for f in fora:
        print("  IGNORADO (nome sem 'N-' no inicio):", f)
    print(f"{len(fonte)} guia(s) publicados — {novos} novo(s), {alterados} atualizado(s), "
          f"{removidos} removido(s).")


if __name__ == "__main__":
    main()
