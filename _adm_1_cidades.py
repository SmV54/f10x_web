# -*- coding: utf-8 -*-
"""ETAPA 1 - varre as paginas de cidade do diretorio (categoria Administradoras
de Condominios) e junta os slugs das fichas de empresa.

As URLs das cidades saem do proprio sitemap da categoria (robots.txt libera
/fornecedores). Cidade com pagina cheia (20 fichas) tem as paginas seguintes
visitadas ate acabar ou ate o limite de MAX_PAG.

Saida: Comercial\\_adm_slugs.json  {slug: [cidades onde apareceu]}
"""
import os, re, sys, json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding="utf-8")

BASE    = os.path.dirname(os.path.abspath(__file__))
SAIDA   = os.path.join(BASE, "Comercial", "_adm_slugs.json")
SITEMAP = "https://cdn.coteibem.com.br/sitemap/sitemap-company-directory-administradoras-condominios.xml"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
THREADS  = 12
MAX_PAG  = 4
POR_PAG  = 20

ses = requests.Session()
ses.headers.update(UA)
trava = threading.Lock()
slugs = {}
contador = {"cidades": 0, "erros": 0}


def pegar(url, tentativas=2):
    for i in range(tentativas):
        try:
            r = ses.get(url, timeout=25, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1.5)
    return ""


def slugs_da_pagina(txt):
    return set(re.findall(r"/fornecedor/([a-z0-9\-]+)", txt))


def uma_cidade(url):
    achados = set()
    for pag in range(1, MAX_PAG + 1):
        u = url if pag == 1 else f"{url}?page={pag}"
        txt = pegar(u)
        if not txt:
            with trava:
                contador["erros"] += 1
            break
        s = slugs_da_pagina(txt)
        achados |= s
        if len(s) < POR_PAG:
            break
    cidade = "/".join(url.split("/")[-2:])
    with trava:
        contador["cidades"] += 1
        for s in achados:
            slugs.setdefault(s, [])
            if cidade not in slugs[s]:
                slugs[s].append(cidade)
        if contador["cidades"] % 200 == 0:
            print(f"  {contador['cidades']} cidades | {len(slugs)} fichas | "
                  f"{contador['erros']} erros", flush=True)
            with open(SAIDA, "w", encoding="utf-8") as f:
                json.dump(slugs, f, ensure_ascii=False)
    return len(achados)


def main():
    # retomada: o que ja foi achado continua valendo
    if os.path.exists(SAIDA):
        try:
            slugs.update(json.load(open(SAIDA, encoding="utf-8")))
            print(f"retomando com {len(slugs)} fichas ja conhecidas", flush=True)
        except Exception:
            pass

    print("baixando sitemap...", flush=True)
    xml = pegar(SITEMAP)
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    print(f"cidades no sitemap: {len(urls)}", flush=True)

    inicio = 0
    for a in sys.argv:
        if a.startswith("--inicio="):
            inicio = int(a.split("=")[1])
    if inicio:
        urls = urls[inicio:]
        print(f"pulando as {inicio} primeiras (ja varridas)", flush=True)

    if "--teste" in sys.argv:
        urls = urls[:60]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        list(as_completed([ex.submit(uma_cidade, u) for u in urls]))

    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(slugs, f, ensure_ascii=False)
    print(f"\nFIM: {contador['cidades']} cidades em {(time.time()-t0)/60:.1f} min | "
          f"{len(slugs)} fichas distintas | {contador['erros']} erros")
    print("gravado:", SAIDA)


if __name__ == "__main__":
    main()
