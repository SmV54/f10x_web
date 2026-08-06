# -*- coding: utf-8 -*-
"""ETAPA 2 - le a ficha de TODAS as empresas do diretorio e separa as
administradoras de condominio.

As fichas saem do sitemap de perfis (14 mil e poucas empresas, todas as
categorias). Varrer tudo sai mais barato e mais completo do que passar cidade
por cidade: a listagem por cidade so mostra as 20 primeiras de cada pagina.

Cada ficha traz um bloco JSON-LD (nome, telefone, cidade/UF, site) e o campo
"ServiceTypes" com as categorias que a propria empresa declarou.

FILTRO: so entra quem declara "Administradoras de condominios". Quem declara
varias categorias (ex.: uma fabricante de geradores que tambem se cadastrou
como administradora) so passa se o nome ou a descricao confirmarem o ramo —
senao a campanha bate na porta errada.

Retoma de onde parou: _adm_vistos.json guarda o que ja foi lido.

Saida: Comercial\\_adm_fichas.json
"""
import os, re, sys, json, time, threading, html, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding="utf-8")

BASE    = os.path.dirname(os.path.abspath(__file__))
SLUGS   = os.path.join(BASE, "Comercial", "_adm_slugs.json")
# --todas: guarda TODA empresa do diretorio (qualquer categoria), para a leva
# de "pequenas empresas". Sem a flag, so o ramo condominial.
TODAS   = "--todas" in sys.argv
SAIDA   = os.path.join(BASE, "Comercial",
                       "_todas_fichas.json" if TODAS else "_adm_fichas.json")
VISTOS  = os.path.join(BASE, "Comercial",
                       "_todas_vistos.json" if TODAS else "_adm_vistos.json")
SITEMAP = "https://cdn.coteibem.com.br/sitemap/sitemap-company-profile.xml"
FICHA   = "https://coteibem.sindiconet.com.br/fornecedor/"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
THREADS = 12

# Categorias do diretorio que interessam a campanha (comparadas sem acento)
CATEGORIAS = ("administradoras de condominios", "sindicos profissionais")
RE_RAMO = re.compile(r"condom[ií]nio|condominial|s[ií]ndic|predial|administra[cç][aã]o de bens|"
                     r"gest[aã]o condominial|imobili", re.I)


def _sem_acento(t):
    t = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()

ses = requests.Session()
ses.headers.update(UA)
_ad = requests.adapters.HTTPAdapter(pool_connections=THREADS, pool_maxsize=THREADS)
ses.mount("https://", _ad)
ses.mount("http://", _ad)

trava = threading.Lock()
fichas, vistos = {}, set()
contador = {"lidas": 0, "erros": 0, "fora": 0}


def pegar(url, tentativas=2):
    for _ in range(tentativas):
        try:
            r = ses.get(url, timeout=25, verify=False)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return ""
        except Exception:
            pass
        time.sleep(1.0)
    return ""


def bloco_ld(txt):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', txt, re.S):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("telephone") is not None:
            return d
    return {}


def servicos(txt):
    # o bloco vem escapado dentro de uma string JS: \"ServiceTypes\":[\"...\"]
    limpo = txt.replace('\\"', '"')
    m = re.search(r'"ServiceTypes"\s*:\s*\[(.*?)\]', limpo, re.S)
    if not m:
        return []
    return [html.unescape(s) for s in re.findall(r'"(.*?)"', m.group(1))]


def descricao(txt):
    m = re.search(r'<meta name="description" content="(.*?)"', txt, re.S)
    return html.unescape(m.group(1))[:400] if m else ""


def salvar():
    json.dump(fichas, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(sorted(vistos), open(VISTOS, "w", encoding="utf-8"))


def uma_ficha(slug):
    txt = pegar(FICHA + slug)
    if not txt:
        with trava:
            contador["erros"] += 1
        return
    ld   = bloco_ld(txt)
    cats = servicos(txt)
    nome = html.unescape(str(ld.get("name") or "")).strip()
    desc = descricao(txt)

    # exata: "Curso para sindicos profissionais" nao vale como sindico
    achadas = [c for c in cats if _sem_acento(c) in CATEGORIAS]
    dentro = bool(achadas)
    if dentro and len(cats) > len(achadas) and not RE_RAMO.search(nome + " " + desc):
        dentro = False
    if TODAS:
        dentro = bool(nome)          # na varredura geral entra todo mundo

    end = ld.get("address") or {}
    with trava:
        contador["lidas"] += 1
        vistos.add(slug)
        if not dentro:
            contador["fora"] += 1
        else:
            fichas[slug] = {
                "slug": slug,
                "nome": nome,
                "telefone": str(ld.get("telephone") or "").strip(),
                "cidade": str(end.get("addressLocality") or "").strip(),
                "uf": str(end.get("addressRegion") or "").strip(),
                "site": str(ld.get("sameAs") or "").strip(),
                "categorias": cats,
                "categoria_alvo": achadas,
                "descricao": desc,
                "fonte": FICHA + slug,
            }
        if contador["lidas"] % 500 == 0:
            print(f"  {contador['lidas']} lidas | {len(fichas)} administradoras | "
                  f"{contador['fora']} fora | {contador['erros']} erros", flush=True)
            salvar()


def main():
    # retomada
    for arq, alvo in ((SAIDA, fichas), (VISTOS, vistos)):
        if os.path.exists(arq):
            try:
                d = json.load(open(arq, encoding="utf-8"))
                alvo.update(d)
            except Exception:
                pass
    if fichas or vistos:
        print(f"retomando: {len(fichas)} administradoras, {len(vistos)} fichas ja lidas", flush=True)

    print("baixando sitemap de fichas...", flush=True)
    xml = pegar(SITEMAP)
    slugs = {u.rstrip("/").split("/")[-1] for u in re.findall(r"<loc>(.*?)</loc>", xml)}
    if os.path.exists(SLUGS):                       # o que a etapa 1 ja tinha achado
        slugs |= set(json.load(open(SLUGS, encoding="utf-8")).keys())
    slugs -= vistos
    slugs = sorted(slugs)
    if "--teste" in sys.argv:
        slugs = slugs[:60]
    print(f"fichas a ler: {len(slugs)}", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        list(as_completed([ex.submit(uma_ficha, s) for s in slugs]))

    salvar()
    print(f"\nFIM em {(time.time()-t0)/60:.1f} min")
    print(f"  lidas nesta rodada: {contador['lidas']}")
    print(f"  administradoras    : {len(fichas)}")
    print(f"  fora da categoria  : {contador['fora']}")
    print(f"  erros              : {contador['erros']}")
    print("gravado:", SAIDA)


if __name__ == "__main__":
    main()
