# -*- coding: utf-8 -*-
"""Extrai o PDF cbo2002_lista.pdf -> _cbo_pdf.json  (somente linhas do tipo Ocupacao).

Formato das linhas: "6125-10 Abacaxicultor Sinonimo" / "... Ocupacao"
"""
import json, re, unicodedata
import pdfplumber

PDF = r"C:\Folha10-Simples\cbo2002_lista.pdf"

RE_LINHA = re.compile(r"^(\d{4})-(\d{2})\s+(.*?)\s+(Ocupa\S*o|Sin\S*nimo)\s*$")

ocupacoes = {}   # codigo6 -> nome oficial
sinonimos = {}   # codigo6 -> [nomes]
ignoradas = []
total_linhas = 0

with pdfplumber.open(PDF) as pdf:
    for pag in pdf.pages:
        txt = pag.extract_text() or ""
        for linha in txt.split("\n"):
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("CBO2002 -") or linha.startswith("Data:") \
               or linha.startswith("Hora:") or linha.startswith("Relat") \
               or linha.startswith("CBO 2002"):
                continue
            total_linhas += 1
            m = RE_LINHA.match(linha)
            if not m:
                ignoradas.append(linha)
                continue
            fam, seq, titulo, tipo = m.groups()
            cod = fam + seq
            titulo = re.sub(r"\s+", " ", titulo).strip()
            if tipo.startswith("Ocupa"):
                ocupacoes.setdefault(cod, []).append(titulo)
            else:
                sinonimos.setdefault(cod, []).append(titulo)

print("linhas lidas:", total_linhas)
print("codigos com 'Ocupacao':", len(ocupacoes))
print("codigos com sinonimo:", len(sinonimos))
print("linhas NAO reconhecidas:", len(ignoradas))
for l in ignoradas[:25]:
    print("   >>", l)

multi = {k: v for k, v in ocupacoes.items() if len(v) > 1}
print("codigos com MAIS DE UM titulo 'Ocupacao':", len(multi))
for k, v in list(multi.items())[:10]:
    print("   ", k, v)

with open(r"C:\folha10-simples\_cbo_pdf.json", "w", encoding="utf-8") as f:
    json.dump({"ocupacoes": {k: v[0] for k, v in ocupacoes.items()},
               "ocupacoes_multi": multi,
               "sinonimos": sinonimos}, f, ensure_ascii=False, indent=1)
print("gravado _cbo_pdf.json")

# amostra para conferir acentuacao
for k in list(ocupacoes)[:5]:
    print(k, "|", ocupacoes[k][0].encode("unicode_escape").decode("ascii"))
