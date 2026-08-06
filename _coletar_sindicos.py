# -*- coding: utf-8 -*-
"""
Coleta telefones de sindicos profissionais a partir dos sites das proprias
empresas e grava em Comercial\\_coleta_sindicos.csv.

REGRA: so entra numero que aparece LITERALMENTE no HTML da pagina. Nada de
numero deduzido ou completado — nesta campanha um numero errado significa
mensagem promocional para um estranho.

Prioridade das evidencias, da mais forte para a mais fraca:
  1. link wa.me / api.whatsapp.com  -> WhatsApp confirmado pelo proprio site
  2. link tel:                       -> telefone declarado pelo site
  3. texto no formato (DD) 9XXXX-XXXX

Uso:
    python _coletar_sindicos.py urls.txt
"""
import os, re, sys, csv, html
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE  = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(BASE, "Comercial", "_coleta_sindicos.csv")
UA    = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

RE_WA    = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|web\.whatsapp\.com/send\?phone=)(\+?\d{10,15})", re.I)
RE_TEL   = re.compile(r"tel:(\+?[\d\s().-]{8,20})", re.I)
# (?<!\d) e (?!\d) sao obrigatorios: sem eles a busca acha "telefone" dentro
# de qualquer sequencia longa de digitos. Um nome de arquivo de imagem
# (image_1765997345198-pop-irae.webp) virou o celular (65) 99734-5198 de um
# desconhecido em Mato Grosso no site de uma administradora de Sao Paulo.
RE_TEXTO = re.compile(r"(?<!\d)\(?(\d{2})\)?[\s.\-]?(9[\s.]?\d{4})[\s.\-]?(\d{4})(?!\d)")
RE_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
RE_TAGS  = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)


def so_numeros(t):
    return re.sub(r"\D", "", t or "")


def normalizar(bruto):
    """Devolve o celular no formato 55DD9XXXXXXXX, ou "" se nao for celular."""
    t = so_numeros(bruto)
    if t.startswith("55") and len(t) in (12, 13):
        t = t[2:]
    if len(t) != 11 or t[2] != "9":
        return ""                      # fixo, incompleto ou fora do padrao
    if t[:2] not in DDDS:
        return ""
    # Depois do 9 inicial, celular brasileiro comeca em 6, 7, 8 ou 9.
    # Sem esta checagem entram mascaras de formulario, como o (61) 90000-0000
    # que veio de um campo "digite seu telefone", e lixo de texto solto.
    if t[3] not in "6789":
        return ""
    if len(set(t[2:])) <= 2:           # 999999999, 988888888... nao existe
        return ""
    return "55" + t


DDDS = {
    "11","12","13","14","15","16","17","18","19","21","22","24","27","28",
    "31","32","33","34","35","37","38","41","42","43","44","45","46","47","48","49",
    "51","53","54","55","61","62","63","64","65","66","67","68","69",
    "71","73","74","75","77","79","81","82","83","84","85","86","87","88","89",
    "91","92","93","94","95","96","97","98","99",
}


def titulo_da_pagina(txt):
    m = RE_TITLE.search(txt)
    if not m:
        return ""
    t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    return t[:90]


def coletar(url):
    """Retorna lista de dicts com os achados desta pagina."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, verify=False)
        if r.status_code != 200:
            return [{"url": url, "erro": f"HTTP {r.status_code}"}]
        txt = r.text
    except Exception as e:
        return [{"url": url, "erro": str(e)[:90]}]

    nome = titulo_da_pagina(txt)
    limpo = RE_TAGS.sub(" ", txt)

    achados = {}          # telefone normalizado -> evidencia mais forte
    def registrar(tel_bruto, evidencia):
        tel = normalizar(tel_bruto)
        if not tel:
            return
        ordem = {"wa.me": 3, "tel:": 2, "texto": 1}
        if tel not in achados or ordem[evidencia] > ordem[achados[tel]]:
            achados[tel] = evidencia

    for m in RE_WA.finditer(txt):
        registrar(m.group(1), "wa.me")
    for m in RE_TEL.finditer(txt):
        registrar(m.group(1), "tel:")
    for m in RE_TEXTO.finditer(limpo):
        registrar("".join(m.groups()), "texto")

    if not achados:
        return [{"url": url, "nome": nome, "erro": "sem celular na pagina"}]
    return [{"url": url, "nome": nome, "telefone": tel, "evidencia": ev}
            for tel, ev in achados.items()]


def main():
    arq_urls = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "urls.txt")
    with open(arq_urls, encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    print(f"URLs a visitar: {len(urls)}", flush=True)
    linhas, erros = [], []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(coletar, u): u for u in urls}
        for fut in as_completed(futs):
            for item in fut.result():
                if item.get("erro"):
                    erros.append(item)
                    print(f"  -- {item['url']}  ::  {item['erro']}", flush=True)
                else:
                    linhas.append(item)
                    print(f"  OK {item['telefone']}  [{item['evidencia']}]  "
                          f"{item['nome'][:55]}", flush=True)

    # Um telefone so pode entrar uma vez, mesmo achado em sites diferentes
    vistos, unicas = set(), []
    for l in sorted(linhas, key=lambda x: {"wa.me": 0, "tel:": 1, "texto": 2}[x["evidencia"]]):
        if l["telefone"] in vistos:
            continue
        vistos.add(l["telefone"])
        unicas.append(l)

    novo = not os.path.exists(SAIDA)
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["nome", "telefone", "evidencia", "fonte"])
        for l in unicas:
            w.writerow([l["nome"], l["telefone"], l["evidencia"], l["url"]])

    print(f"\nPaginas com celular: {len(set(l['url'] for l in linhas))}")
    print(f"Telefones unicos   : {len(unicas)}")
    print(f"Paginas sem numero : {len(erros)}")
    print(f"Gravado em: {SAIDA}")


if __name__ == "__main__":
    main()
