# -*- coding: utf-8 -*-
"""ETAPA 4 - visita o site da propria administradora atras do WhatsApp.

Reaproveita a funcao coletar() de _coletar_sindicos.py (mesma regra: so entra
numero que aparece LITERALMENTE no HTML) e grava em
Comercial\\_coleta_adm_sites.csv.

Os sites saem do campo "sameAs" das fichas (etapa 2) e de listas de associadas
(arquivos Comercial\\_adm_sites_*.txt).

Uso: python _adm_4_sites.py [--teste]
"""
import os, re, sys, csv, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _coletar_sindicos import coletar          # mesma regra de coleta

FICHAS = os.path.join(BASE, "Comercial", "_adm_fichas.json")
SAIDA  = os.path.join(BASE, "Comercial", "_coleta_adm_sites.csv")
THREADS = 8


def normalizar_url(bruto):
    u = (bruto or "").strip()
    if not u or u in ("-", "#"):
        return ""
    u = u.split(" ")[0].strip().rstrip("/")
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith("http"):
        u = "https://" + u
    m = re.match(r"https?://[^/]+", u)
    if not m:
        return ""
    dom = m.group(0)
    # fora: redes sociais e agregadores - o alvo e o site da empresa
    # ueniweb fica de fora: a plataforma injeta widgets com telefone de OUTRAS
    # empresas na mesma pagina (deu numero de 5 estados diferentes na campanha
    # de sindicos), entao nao da para confiar no numero achado ali.
    if re.search(r"(facebook|instagram|linkedin|youtube|twitter|x\.com|wa\.me|whatsapp|"
                 r"google|bit\.ly|linktr\.ee|blogspot|wordpress\.com|webnode|ueniweb|"
                 r"sindiconet|coteibem|papocondominial|b2bfy|econodata|apontador|"
                 r"telelistas|guiamais|solutudo)", dom, re.I):
        return ""
    return u if len(u) < 120 else dom


def reunir_urls():
    urls = set()
    if os.path.exists(FICHAS):
        for f in json.load(open(FICHAS, encoding="utf-8")).values():
            u = normalizar_url(f.get("site"))
            if u:
                urls.add(u)
    for nome in os.listdir(os.path.join(BASE, "Comercial")):
        if nome.startswith("_adm_sites_") and nome.endswith(".txt"):
            for l in open(os.path.join(BASE, "Comercial", nome), encoding="utf-8"):
                u = normalizar_url(l)
                if u:
                    urls.add(u)
    return sorted(urls)


# Onde o WhatsApp costuma estar quando a home nao mostra
PAGINAS_CONTATO = ["/contato", "/contato/", "/fale-conosco", "/contato.php",
                   "/contato.html", "/quem-somos"]


def rodada(urls, rotulo):
    """Visita a lista e devolve (linhas, urls_sem_numero, erros)."""
    linhas, sem, erro = [], [], 0
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futs = {ex.submit(coletar, u): u for u in urls}
        for i, fut in enumerate(as_completed(futs), 1):
            for item in fut.result():
                if item.get("erro"):
                    if "sem celular" in item["erro"]:
                        sem.append(item["url"])
                    else:
                        erro += 1
                else:
                    linhas.append(item)
            if i % 100 == 0:
                print(f"  [{rotulo}] {i}/{len(urls)} | {len(linhas)} numeros | "
                      f"{len(sem)} sem celular | {erro} erros", flush=True)
    return linhas, sem, erro


def main():
    urls = reunir_urls()
    if "--teste" in sys.argv:
        urls = urls[:30]
    print(f"sites a visitar: {len(urls)}", flush=True)

    t0 = time.time()
    linhas, sem_home, erro = rodada(urls, "home")

    # 2a rodada: so nos sites que nao mostraram celular na home
    alvos = []
    for u in sem_home:
        base = re.match(r"https?://[^/]+", u)
        if base:
            alvos += [base.group(0) + p for p in PAGINAS_CONTATO]
    print(f"\n2a rodada (paginas de contato): {len(alvos)} enderecos", flush=True)
    linhas2, sem2, erro2 = rodada(alvos, "contato")
    linhas += linhas2
    sem, erro = len(sem_home), erro + erro2

    novo = not os.path.exists(SAIDA)
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["nome", "telefone", "evidencia", "fonte"])
        for l in linhas:
            w.writerow([l["nome"], l["telefone"], l["evidencia"], l["url"]])

    print(f"\nFIM em {(time.time()-t0)/60:.1f} min")
    print(f"  numeros achados : {len(linhas)}")
    print(f"  sites sem celular: {sem}")
    print(f"  sites com erro   : {erro}")
    print("gravado:", SAIDA)


if __name__ == "__main__":
    main()
