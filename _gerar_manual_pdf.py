# -*- coding: utf-8 -*-
"""Exporta o Manual de Regras (.docx) para PDF.

Usa o proprio Word instalado na maquina, pelo COM. Assim o PDF sai identico ao
documento — mesmas quebras, mesmas tabelas — em vez de ser um segundo desenho
do mesmo conteudo, que sairia desalinhado do .docx a cada edicao.

Rodar sempre DEPOIS do _gerar_manual.py. E rotina local (precisa do Word).
"""
import os
import sys

PASTA = r"C:\folha10-simples\manual"
DOCX  = os.path.join(PASTA, "Manual_de_Regras_Folha10_Simples.docx")
PDF   = os.path.join(PASTA, "Manual_de_Regras_Folha10_Simples.pdf")

WD_FORMATO_PDF = 17          # wdExportFormatPDF
WD_OTIMIZA_IMPRESSAO = 0     # wdExportOptimizeForPrint
WD_DOC_INTEIRO = 0           # wdExportAllDocument
WD_SEM_MARCACAO = 0          # wdExportDocumentContent
WD_MARCADORES_TITULOS = 1    # wdExportCreateHeadingBookmarks

if not os.path.exists(DOCX):
    sys.exit(f"Nao achei o .docx. Rode antes: python _gerar_manual.py\n  {DOCX}")

import win32com.client as win32

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    doc = word.Documents.Open(DOCX, ReadOnly=True)
    try:
        doc.ExportAsFixedFormat(
            OutputFileName=PDF,
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
finally:
    word.Quit()

print("OK:", PDF, f"({os.path.getsize(PDF):,} bytes)".replace(",", "."))
