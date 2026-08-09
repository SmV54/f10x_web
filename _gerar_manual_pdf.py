# -*- coding: utf-8 -*-
"""Exporta para PDF todos os manuais (.docx) da pasta manual/.

Usa o proprio Word instalado na maquina, pelo COM. Assim o PDF sai identico ao
documento — mesmas quebras, mesmas tabelas — em vez de ser um segundo desenho
do mesmo conteudo, que sairia desalinhado do .docx a cada edicao.

Rodar sempre DEPOIS de gerar os .docx:
    python _gerar_manual.py            (manual interno, de regras)
    python _gerar_manual_usuario.py    (manual do usuario)
    python _gerar_manual_pdf.py        (os dois em PDF)

E rotina local: precisa do Word. No servidor os PDFs chegam pelo repositorio.
"""
import glob
import os
import sys

PASTA = r"C:\folha10-simples\manual"

WD_FORMATO_PDF = 17          # wdExportFormatPDF
WD_OTIMIZA_IMPRESSAO = 0     # wdExportOptimizeForPrint
WD_DOC_INTEIRO = 0           # wdExportAllDocument
WD_SEM_MARCACAO = 0          # wdExportDocumentContent
WD_MARCADORES_TITULOS = 1    # wdExportCreateHeadingBookmarks

docs = sorted(glob.glob(os.path.join(PASTA, "*.docx")))
docs = [d for d in docs if not os.path.basename(d).startswith("~$")]  # temporarios do Word
if not docs:
    sys.exit(f"Nenhum .docx em {PASTA}. Rode antes os geradores dos manuais.")

import win32com.client as win32

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    for caminho_docx in docs:
        caminho_pdf = os.path.splitext(caminho_docx)[0] + ".pdf"
        doc = word.Documents.Open(caminho_docx, ReadOnly=True)
        try:
            doc.ExportAsFixedFormat(
                OutputFileName=caminho_pdf,
                ExportFormat=WD_FORMATO_PDF,
                OpenAfterExport=False,
                OptimizeFor=WD_OTIMIZA_IMPRESSAO,
                Range=WD_DOC_INTEIRO,
                Item=WD_SEM_MARCACAO,
                IncludeDocProps=True,
                KeepIRM=True,
                # indice de navegacao do PDF montado a partir dos titulos
                CreateBookmarks=WD_MARCADORES_TITULOS,
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        finally:
            doc.Close(False)
        tam = f"{os.path.getsize(caminho_pdf):,}".replace(",", ".")
        print(f"OK: {os.path.basename(caminho_pdf)}  ({tam} bytes)")
finally:
    word.Quit()
