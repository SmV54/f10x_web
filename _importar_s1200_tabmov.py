# -*- coding: utf-8 -*-
"""
Importa a ficha financeira do eSocial (ZIPs baixados do portal) para o
tab_mov e o tab_total de uma empresa, usando a planilha de-para de rubricas.

Serve para empresa que veio de outro sistema: o histórico da ficha financeira
é o que dá as médias de férias, 13º e rescisão; o tab_total dá as bases do
seguro-desemprego, do dissídio e da ficha.

Uso:
    python _importar_s1200_tabmov.py --cliente 73 --empresa 79 --depara "C:\\...\\De-para ... - F10.xlsx"
    python _importar_s1200_tabmov.py ... --gravar

Sem --gravar é SIMULAÇÃO: não grava nada, mostra o resumo por folha e salva a
prévia em C:\\XMLeSocial\\Planilhas\\Previa_S1200_tabmov.xlsx. A tela
(Descompactar XML, Etapa 4) usa as mesmas funções: simular() e gravar().

A planilha: aba com "de-para" no nome (a "(todas)" primeiro); coluna A = código
da rubrica no eSocial; a coluna de título "Folha10" (sem ela, a O) = verba do
Folha10 (4 dígitos), NÃO IMPORTAR ou TAB_TOTAL (informativa: base/FGTS, que
não vira verba — o Folha10 só tem provento e desconto).

tab_mov (lote 1200, origem 'M'), com a NOSSA verba:
  - S-1200: anulado por S-3000 não entra; retificado substitui o original;
    apuração anual (13º) e verba de uso só no 13º → '1', folha AAAA12;
    verba de uso só em férias (0041/0042/0045/0046/0103) → 'F'; o resto → 'N';
  - S-2299 (a rescisão não tem S-1200): as verbasResc do período → 'R', folha
    = mês do desligamento;
  - qtd em horas × 100 (037FOLH e 404FOLH vêm em horas.minutos).

tab_total (controle 1200), uma linha por matrícula/folha/tipo:
  - proventos, descontos e líquido: soma do tab_mov importado pelo tipo da verba;
  - base e valor do INSS: S-5001 (o que o eSocial apurou); base e valor do FGTS:
    S-5003, inteiros na 'N'. Férias ('F') ficam só com as verbas de férias e o
    INSS da verba 0103, sem base; a 'N' leva o INSS do mês menos o 0103.
    Mês com rescisão: tudo na 'R';
  - base do IRRF: rubricas informativas de natureza 9903 do próprio S-1200
    (o S-5002 é por data de pagamento, não por competência);
  - salário: vrSalFx do S-2200/S-2206 vigente no fim do mês.

Só entram folhas ANTES da primeira folha que a empresa já tem no Folha10 (tab_mov
de outra origem ou tab_total de outro controle). Rodar de novo apaga o que o
lote 1200 / controle 1200 gravou na empresa e grava outra vez.
"""
import os, re, sys, ssl, argparse, tempfile, unicodedata
from collections import defaultdict, Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import _descompactar_xml_esocial as DX

LOTE = 1200
CONTROLE_TOT = 1200
# A tab_mov só aceita C/M/F/A (check constraint tab_mov_origem_check; o "I"
# quebrou a gravação em 30/10/2026). M = lançamento: o recálculo só apaga as
# verbas C. O que identifica esta importação é o LOTE.
ORIGEM = "M"
QTD_HORAS_MIN = {"037FOLH", "404FOLH"}       # quantidade em horas.minutos
VERBA_INSS_FERIAS = 103
PREVIA = r"C:\XMLeSocial\Planilhas\Previa_S1200_tabmov.xlsx"

RE_TAG = lambda t: re.compile(rf"<{t}>([^<]*)</{t}>")
R_PER, R_CPF, R_IND, R_RETIF = RE_TAG("perApur"), RE_TAG("cpfTrab"), RE_TAG("indApuracao"), RE_TAG("indRetif")
R_REC = RE_TAG("nrRecibo")


def _g(rx, txt, padrao=""):
    if isinstance(rx, str):
        rx = RE_TAG(rx)
    m = rx.search(txt)
    return m.group(1).strip() if m else padrao


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")


def _cent(v):
    return int(round(float(v or 0) * 100))


# ── planilha ─────────────────────────────────────────────────────────────
def ler_depara(caminho):
    """(mapa {cod: verba}, fora {cod}, info {cod}, pend {cod: motivo}, aba)."""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    abas = [w for w in wb.worksheets if "de-para" in w.title.lower()]
    ws = (next((w for w in abas if "todas" in w.title.lower()), None)
          or (abas[0] if abas else wb.worksheets[0]))
    mapa, fora, info, pend = {}, set(), set(), {}
    col = 14
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            cab = [_sem_acento(x).strip().lower() for x in (r or [])]
            if "folha10" in cab:
                col = cab.index("folha10")
            continue
        if not r or not r[0] or not str(r[0]).strip():
            continue
        cod = str(r[0]).strip()
        v = str(r[col] or "").strip() if len(r) > col else ""
        vu = _sem_acento(v).upper()
        if re.fullmatch(r"\d{1,4}", v) and v != "9999":
            mapa[cod] = int(v)
        elif "IMPORTAR" in vu and vu.startswith("N"):
            fora.add(cod)
        elif vu.replace(" ", "_") == "TAB_TOTAL":
            info.add(cod)
        else:
            pend[cod] = v or "sem verba"
    return mapa, fora, info, pend, ws.title


# ── XMLs ─────────────────────────────────────────────────────────────────
def _eventos(origem, layout, zips=None):
    """[(nome, texto, recibo)] de um layout, sem repetir arquivo."""
    vistos, out = set(), []
    for z in (zips or DX.listar_zips(origem)):
        for nome, dados in DX.iter_xmls(os.path.join(origem, z)):
            if not nome or not nome.endswith(f".{layout}.xml") or nome in vistos:
                continue
            vistos.add(nome)
            out.append((nome, dados.decode("utf-8", "ignore"), DX.recibo_proprio(dados)))
    return out


def _so_validos(eventos, anulados):
    """Tira o anulado por S-3000 e o original que uma retificação substituiu."""
    subst = {e["substitui"] for e, _ in eventos if e["retif"] and e["substitui"]}
    return [(e, it) for e, it in eventos if e["recibo"] not in anulados and e["recibo"] not in subst]


def ler_s1200(origem, anulados=None, zips=None):
    """[(ev, itens)] dos S-1200 válidos: sem os anulados e sem os retificados."""
    zips = zips or DX.listar_zips(origem)
    if anulados is None:
        anulados = DX.recibos_excluidos(origem, zips)
    eventos = []
    for nome, t, rec in _eventos(origem, "S-1200", zips):
        ide = re.search(r"<ideEvento>(.*?)</ideEvento>", t, re.S)
        ide = ide.group(1) if ide else ""
        ev = {"arquivo": nome, "recibo": rec, "retif": _g(R_RETIF, ide) == "2",
              "substitui": _g(R_REC, ide), "per": _g(R_PER, ide), "ind": _g(R_IND, ide, "1"),
              "cpf": _g(R_CPF, t), "matr_es": _g("matricula", t), "layout": "S-1200"}
        itens = []
        for dm in re.findall(r"<dmDev>(.*?)</dmDev>", t, re.S):
            ide_dm = _g("ideDmDev", dm)
            for it in re.findall(r"<itensRemun>(.*?)</itensRemun>", dm, re.S):
                itens.append({"dm": ide_dm, "cod": _g("codRubr", it),
                              "qtd": float(_g("qtdRubr", it, "0") or 0),
                              "vr": float(_g("vrRubr", it, "0") or 0)})
        eventos.append((ev, itens))
    validos = _so_validos(eventos, anulados)
    return validos, len(eventos), len(eventos) - len(validos)


def ler_s2299(origem, anulados, zips=None):
    """[(ev, itens)] dos S-2299 válidos, só as verbas do período (infoPerApur)."""
    eventos = []
    for nome, t, rec in _eventos(origem, "S-2299", zips):
        ide = re.search(r"<ideEvento>(.*?)</ideEvento>", t, re.S)
        ide = ide.group(1) if ide else ""
        dt = _g("dtDeslig", t)
        ev = {"arquivo": nome, "recibo": rec, "retif": _g(R_RETIF, ide) == "2",
              "substitui": _g(R_REC, ide), "per": dt[:7], "ind": "1", "dt": dt,
              "cpf": _g(R_CPF, t), "matr_es": _g("matricula", t), "layout": "S-2299"}
        itens = []
        for dm in re.findall(r"<dmDev>(.*?)</dmDev>", t, re.S):
            ap = re.search(r"<infoPerApur>(.*?)</infoPerApur>", dm, re.S)
            for it in re.findall(r"<detVerbas>(.*?)</detVerbas>", ap.group(1) if ap else "", re.S):
                itens.append({"dm": _g("ideDmDev", dm), "cod": _g("codRubr", it),
                              "qtd": float(_g("qtdRubr", it, "0") or 0),
                              "vr": float(_g("vrRubr", it, "0") or 0)})
        eventos.append((ev, itens))
    return _so_validos(eventos, anulados)


def ler_rubricas_s1010(origem, zips=None):
    """{codRubr: {'tp', 'nat', 'dsc'}} da definição mais recente."""
    rub = {}
    for _, t, _ in _eventos(origem, "S-1010", zips):
        cod, ini, dsc = _g("codRubr", t), _g("iniValid", t), _g("dscRubr", t)
        if cod and dsc and (cod not in rub or ini >= rub[cod]["ini"]):
            rub[cod] = {"tp": _g("tpRubr", t), "nat": _g("natRubr", t), "dsc": dsc, "ini": ini}
    return rub


def ler_totalizadores(origem, recibos_validos, zips=None):
    """S-5001 e S-5003 dos eventos válidos.

    {(cpf, perApur, indApuracao): {'inss_base0','inss_base13','inss_desc0','inss_desc13',
                                   'fgts_base','fgts_dep','fgts_base13','fgts_dep13'}}
    O totalizador aponta o evento de origem no nrRecArqBase; o que vem de
    S-1200 retificado ou anulado fica de fora por aí.
    """
    tot = defaultdict(lambda: defaultdict(int))
    for _, t, _ in _eventos(origem, "S-5001", zips):
        if _g("nrRecArqBase", t) not in recibos_validos:
            continue
        k = (_g(R_CPF, t), _g(R_PER, t), _g(R_IND, t, "1"))
        for b in re.findall(r"<infoBaseCS>(.*?)</infoBaseCS>", t, re.S):
            i13, tpv, v = _g("ind13", b), _g("tpValor", b), _cent(_g("valor", b, "0"))
            sufixo = "13" if i13 == "1" else "0"
            if tpv == "11":
                tot[k]["inss_base" + sufixo] += v
            elif tpv == "21":
                tot[k]["inss_desc" + sufixo] += v
    for _, t, _ in _eventos(origem, "S-5003", zips):
        if _g("nrRecArqBase", t) not in recibos_validos:
            continue
        k = (_g(R_CPF, t), _g(R_PER, t), _g(R_IND, t, "1"))
        for b in re.findall(r"<basePerApur>(.*?)</basePerApur>", t, re.S):
            tpv = _g("tpValor", b)
            sufixo = "13" if tpv in ("12", "22") else ""
            tot[k]["fgts_base" + sufixo] += _cent(_g("remFGTS", b, "0"))
            tot[k]["fgts_dep" + sufixo] += _cent(_g("dpsFGTS", b, "0"))
    return tot


def ler_salarios(origem, anulados, zips=None):
    """{cpf: [(AAAA-MM-DD, centavos)]} do S-2200 (admissão) e S-2206 (alteração)."""
    sal = defaultdict(list)
    for lay, tag_dt in (("S-2200", "dtAdm"), ("S-2206", "dtAlteracao")):
        for _, t, rec in _eventos(origem, lay, zips):
            if rec in anulados:
                continue
            v, dt = _g("vrSalFx", t), _g(tag_dt, t)
            if v and dt:
                sal[_g(R_CPF, t)].append((dt, _cent(v)))
    return {c: sorted(l) for c, l in sal.items()}


def _sal_no_mes(lista, folha):
    fim = f"{str(folha)[:4]}-{str(folha)[4:6]}-31"
    ok = [v for d, v in (lista or []) if d <= fim]
    return ok[-1] if ok else 0


def _horas(cod, q):
    if cod in QTD_HORAS_MIN:
        h = int(q)
        return h + round((q - h) * 100) / 60
    return q


# ── montagem ─────────────────────────────────────────────────────────────
def _norm_matr(m):
    """Matrícula do eSocial sem zeros à esquerda ('00020000036' = '20000036')."""
    return str(m or "").strip().lstrip("0")


def montar(validos, mapa, fora, info, pend, mat_por_cpf, rinfo, r1010, mat_por_es=None):
    """Soma por (mat, folha, tipo, verba) e separa o que ficou de fora.

    Devolve (soma, irrf, faltou_cpf, pend_uso, fora_uso, info_uso, tipo_mes):
      irrf      {(mat, folha, tipo): centavos} — base do IRRF (natureza 9903);
      tipo_mes  {(mat, AAAAMM): {'N','F','R','1'}} — para o tab_total.
    """
    soma = defaultdict(lambda: [0.0, 0.0])
    irrf = defaultdict(int)
    faltou_cpf, fora_uso, info_uso = Counter(), Counter(), Counter()
    # pend_uso[(cod, motivo da tela)] = {'n', 'vr', 'pers', 'func', 'cliente'}; 'cliente' é o
    # texto do PDF que vai para o cliente (sem o jeito interno de falar)
    pend_uso = defaultdict(lambda: {"n": 0, "vr": 0.0, "pers": set(), "func": set(), "cliente": ""})

    def _pend(cod, motivo, cliente, ev, it, mat):
        d = pend_uso[(cod, motivo)]
        d["n"] += 1
        d["vr"] += it["vr"]
        d["pers"].add(ev["per"])
        d["func"].add(mat)
        d["cliente"] = cliente
    tipo_mes = defaultdict(set)
    for ev, itens in validos:
        # A matrícula do eSocial não é a nossa: liga pela tab_cad.matricula_es
        # (com o mesmo CPF — readmitido tem duas), e só sem ela pelo CPF.
        par = (mat_por_es or {}).get(_norm_matr(ev.get("matr_es")))
        mat = par[0] if par and par[1] == ev["cpf"] else mat_por_cpf.get(ev["cpf"])
        if not mat:
            faltou_cpf[ev["cpf"]] += 1
            continue
        anual = ev["ind"] == "2" or len(ev["per"]) == 4
        ano, mes = ev["per"][:4], (ev["per"][5:7] if len(ev["per"]) >= 7 else "12")
        resc = ev["layout"] == "S-2299"
        for it in itens:
            cod = it["cod"]
            if cod in fora:
                fora_uso[cod] += 1
                continue
            if cod in info:
                info_uso[cod] += 1
                if (r1010.get(cod) or {}).get("nat") == "9903":
                    dsc = _sem_acento((r1010.get(cod) or {}).get("dsc", "")).upper()
                    if resc:
                        k = (mat, int(ano + mes), "R")
                    elif anual or "13" in dsc:
                        k = (mat, int(ano + "12"), "1")
                    elif "FERIAS" in dsc:
                        k = (mat, int(ano + mes), "F")
                    else:
                        k = (mat, int(ano + mes), "N")
                    irrf[k] += _cent(it["vr"])
                continue
            verba = mapa.get(cod)
            if verba is None:
                if cod in pend:
                    _pend(cod, pend[cod], "Falta informar a verba do Folha10 (ou “NÃO IMPORTAR”).", ev, it, mat)
                else:
                    _pend(cod, "não está na planilha", "A rubrica não está na planilha. Inclua a linha com a "
                          "verba do Folha10 (ou “NÃO IMPORTAR”).", ev, it, mat)
                continue
            ri = rinfo.get(verba)
            if not ri:
                _pend(cod, f"verba {verba:04d} não existe no Folha10",
                      f"A verba {verba:04d} informada não existe no Folha10. Confira o código.", ev, it, mat)
                continue
            tp_es = {"1": "1", "2": "2"}.get((r1010.get(cod) or {}).get("tp", ""))
            if tp_es and tp_es != ri["tp"]:
                es_txt = "provento" if tp_es == "1" else "desconto"
                f10_txt = "provento" if ri["tp"] == "1" else "desconto"
                _pend(cod, f"no eSocial é {es_txt}; a verba {verba:04d} é {f10_txt}",
                      f"No eSocial esta rubrica é {es_txt.upper()}, mas a verba {verba:04d} "
                      f"({ri['dsc'].strip()}) é {f10_txt.upper()}. Informe uma verba de {es_txt}.", ev, it, mat)
                continue
            if resc:
                folha, tipo = int(ano + mes), "R"
            elif anual or ri["uso"] == "1":
                folha, tipo = int(ano + "12"), "1"
            elif ri["uso"] == "F":
                folha, tipo = int(ano + mes), "F"
            else:
                folha, tipo = int(ano + mes), "N"
            k = (mat, folha, tipo, verba)
            soma[k][0] += _horas(cod, it["qtd"])
            soma[k][1] += it["vr"]
            tipo_mes[(mat, folha)].add(tipo)
    return soma, irrf, faltou_cpf, pend_uso, fora_uso, info_uso, tipo_mes


def montar_total(id_cliente, id_empresa, soma, irrf, tot, cpf_por_mat, sal, rinfo, teto, filial):
    """Linhas do tab_total (ver a docstring do módulo)."""
    g = defaultdict(lambda: defaultdict(int))     # (mat, folha, tipo) -> campos
    for (mat, folha, tipo, verba), (_, v) in soma.items():
        ri, vc = rinfo[verba], _cent(v)
        d = g[(mat, folha, tipo)]
        d["prov" if ri["tp"] == "1" else "desc"] += vc
        if tipo == "F" and verba == VERBA_INSS_FERIAS:
            d["inss_desc"] += vc
    for k, v in irrf.items():
        g[k]["irrf"] += v

    tipos = defaultdict(set)
    for mat, folha, tipo in list(g):
        tipos[(mat, folha)].add(tipo)
    for mat, cpf in cpf_por_mat.items():
        for (c, per, ind), t in tot.items():
            if c != cpf:
                continue
            if ind == "2" or len(per) == 4:
                d = g[(mat, int(per[:4] + "12"), "1")]
                d["inss_base"] += t["inss_base13"]
                d["inss_desc"] += t["inss_desc13"]
                continue
            folha = int(per[:4] + per[5:7])
            ts = tipos.get((mat, folha), set())
            if "R" in ts:
                d = g[(mat, folha, "R")]
                d["inss_base"] += t["inss_base0"]
                d["inss_desc"] += t["inss_desc0"] + t["inss_desc13"]
                d["fgts_base"] += t["fgts_base"] + t["fgts_base13"]
                d["fgts"] += t["fgts_dep"] + t["fgts_dep13"]
                continue
            # Base do mês inteira na 'N' (o seguro-desemprego só lê a N). A 'F'
            # fica só com as verbas de férias e o INSS 0103, sem base: o sistema
            # antigo pagava férias adiantadas e descontava na folha (verba 0051),
            # então as verbas de férias passavam da base do mês e a N zerava.
            f = g.get((mat, folha, "F"), {})
            d = g[(mat, folha, "N")]
            d["inss_base"] += t["inss_base0"]
            d["inss_desc"] += t["inss_desc0"] - f.get("inss_desc", 0)
            d["fgts_base"] += t["fgts_base"]
            d["fgts"] += t["fgts_dep"]
            if t["fgts_base13"] or t["fgts_dep13"]:
                d13 = g[(mat, int(per[:4] + "12"), "1")]
                d13["fgts_base"] += t["fgts_base13"]
                d13["fgts"] += t["fgts_dep13"]
            if t["inss_base13"] or t["inss_desc13"]:
                # 13º dentro da folha do mês (sem ser rescisão): vai para a '1'
                d13 = g[(mat, int(per[:4] + "12"), "1")]
                d13["inss_base"] += t["inss_base13"]
                d13["inss_desc"] += t["inss_desc13"]

    linhas = []
    for (mat, folha, tipo), d in sorted(g.items()):
        if not any(d.get(c) for c in ("prov", "desc", "inss_base", "fgts_base", "irrf")):
            continue
        base = max(0, d["inss_base"])
        tt = teto(folha)
        linhas.append({
            "id_cliente": id_cliente, "id_empresa": id_empresa, "situacao": "A",
            "matricula": mat, "folha": folha, "folha_tipo": tipo, "filial": filial.get(mat, ""),
            "valor_base_inss_semlimite": base,
            "valor_base_inss_comlimite": min(base, tt) if tt else base,
            "valor_inss_retido": max(0, d["inss_desc"]),
            "valor_base_fgts": max(0, d["fgts_base"]), "valor_fgts": max(0, d["fgts"]),
            "valor_irrf_basetotal": d["irrf"], "valor_irrf_basetabela": d["irrf"],
            "valor_irrf_dependentes": 0, "qtd_irrf_dependentes": 0,
            "valor_salario": _sal_no_mes(sal.get(cpf_por_mat.get(mat)), folha),
            "valor_total_proventos": d["prov"], "valor_total_descontos": d["desc"],
            "valor_liquido": d["prov"] - d["desc"],
            "os": 0, "controle": CONTROLE_TOT,
        })
    return linhas


# ── banco ────────────────────────────────────────────────────────────────
def _supabase():
    caminho = os.path.join(tempfile.gettempdir(), "folha10_ca.pem")
    with open(caminho, "w", encoding="utf-8") as f:
        import certifi
        f.write(open(certifi.where(), encoding="utf-8").read())
        for loja in ("ROOT", "CA"):
            for der, enc, _ in ssl.enum_certificates(loja):
                if enc == "x509_asn":
                    f.write(ssl.DER_cert_to_PEM_cert(der))
    os.environ["SSL_CERT_FILE"] = caminho
    os.environ["REQUESTS_CA_BUNDLE"] = caminho
    import app
    return app


def _rubricas(app, id_cliente):
    """{verba: {'tp', 'uso', 'f_cp', 'f_fgts', 'dsc'}} — sistema + cliente."""
    out = {}
    for cli in (0, id_cliente):
        for r in app._diss_todos(app.supabase.table("tab_rubrica")
                                 .select("cod_rubr, dsc_rubr, tp_rubr, tipo_uso, tpf_inc_cp, tpf_inc_fgts")
                                 .eq("id_cliente", cli)):
            out[int(r["cod_rubr"])] = {"tp": str(r.get("tp_rubr") or "1"),
                                       "uso": str(r.get("tipo_uso") or "").strip(),
                                       "f_cp": str(r.get("tpf_inc_cp") or ""),
                                       "f_fgts": str(r.get("tpf_inc_fgts") or ""),
                                       "dsc": r.get("dsc_rubr") or ""}
    return out


def _primeira_folha_f10(app, id_empresa):
    """Primeira folha que a empresa já tem no Folha10 (fora desta importação)."""
    sb, ini = app.supabase, []
    r = (sb.table("tab_mov").select("folha").eq("id_empresa", id_empresa).neq("lote", LOTE)
         .order("folha").limit(1).execute().data)
    if r:
        ini.append(int(r[0]["folha"]))
    r = (sb.table("tab_total").select("folha").eq("id_empresa", id_empresa).neq("controle", CONTROLE_TOT)
         .order("folha").limit(1).execute().data)
    if r:
        ini.append(int(r[0]["folha"]))
    return min(ini) if ini else 0


def simular(app, id_cliente, id_empresa, depara, origem=DX.ORIGEM, progresso=None):
    """Monta tudo sem gravar. Devolve um dicionário com o resumo e as linhas."""
    prog = progresso or (lambda p, e: None)
    sb = app.supabase
    emp = (sb.table("tab_empresa").select("id_empresa, razaosocial, cnpj")
           .eq("id_empresa", id_empresa).eq("id_cliente", id_cliente).execute().data)
    if not emp:
        return {"ok": False, "msg": f"Empresa {id_empresa} não é do cliente {id_cliente}."}
    if not os.path.isfile(depara):
        return {"ok": False, "msg": f"Planilha de-para não encontrada: {depara}"}
    cad = app._diss_todos(sb.table("tab_cad").select("matricula, cpf, nome, filial, matricula_es")
                          .eq("id_empresa", id_empresa).eq("id_cliente", id_cliente))
    mat_por_cpf = {str(c["cpf"]).zfill(11): int(c["matricula"]) for c in cad}
    mat_por_es = {_norm_matr(c.get("matricula_es")): (int(c["matricula"]), str(c["cpf"]).zfill(11))
                  for c in cad if _norm_matr(c.get("matricula_es"))}
    cpf_por_mat = {m: c for c, m in mat_por_cpf.items()}
    nome = {int(c["matricula"]): c["nome"] for c in cad}
    filial = {int(c["matricula"]): str(c.get("filial") or "") for c in cad}

    prog(5, "lendo a planilha de-para…")
    mapa, fora, info, pend, aba = ler_depara(depara)
    rinfo = _rubricas(app, id_cliente)
    zips = DX.listar_zips(origem)
    prog(10, "lendo os S-3000 (exclusões)…")
    anulados = DX.recibos_excluidos(origem, zips)
    prog(25, "lendo os S-1010…")
    r1010 = ler_rubricas_s1010(origem, zips)
    prog(35, "lendo os S-1200…")
    v1200, n_ev, n_tirados = ler_s1200(origem, anulados, zips)
    prog(55, "lendo os S-2299…")
    v2299 = ler_s2299(origem, anulados, zips)
    prog(65, "lendo os totalizadores S-5001/S-5003…")
    recibos = {e["recibo"] for e, _ in v1200 + v2299}
    tot = ler_totalizadores(origem, recibos, zips)
    prog(85, "lendo os salários (S-2200/S-2206)…")
    sal = ler_salarios(origem, anulados, zips)

    prog(90, "montando…")
    soma, irrf, faltou_cpf, pend_uso, fora_uso, info_uso, _ = montar(
        v1200 + v2299, mapa, fora, info, pend, mat_por_cpf, rinfo, r1010, mat_por_es)

    corte = _primeira_folha_f10(app, id_empresa)
    def teto(folha, _c={}):
        if folha not in _c:
            tb = app._get_tabela_legais(folha) or {}
            lims = [int(tb.get(f"inss{i}_limite") or 0) for i in range(1, 7)]
            lims = [x for x in lims if x]
            _c[folha] = lims[-1] if lims else 0
        return _c[folha]
    linhas_tot = montar_total(id_cliente, id_empresa, soma, irrf, tot, cpf_por_mat, sal, rinfo, teto, filial)

    linhas_mov = [{"id_cliente": id_cliente, "id_empresa": id_empresa, "situacao": "A",
                   "matricula": mat, "folha": folha, "folha_tipo": tipo, "complemento": 0,
                   "cod_verba": verba, "qtd": int(round(q * 100)), "valor": int(round(v * 100)),
                   "lote": LOTE, "origem": ORIGEM, "controle": 0, "os": 0}
                  for (mat, folha, tipo, verba), (q, v) in sorted(soma.items())]
    pulou = sorted({l["folha"] for l in linhas_mov + linhas_tot if corte and l["folha"] >= corte})
    if corte:
        linhas_mov = [l for l in linhas_mov if l["folha"] < corte]
        linhas_tot = [l for l in linhas_tot if l["folha"] < corte]

    por_folha = defaultdict(lambda: {"linhas": 0, "prov": 0, "desc": 0, "func": set(),
                                     "inss": 0, "fgts": 0})
    for l in linhas_mov:
        pf = por_folha[(l["folha"], l["folha_tipo"])]
        pf["linhas"] += 1
        pf["func"].add(l["matricula"])
        pf["prov" if rinfo[l["cod_verba"]]["tp"] == "1" else "desc"] += l["valor"]
    for l in linhas_tot:
        pf = por_folha[(l["folha"], l["folha_tipo"])]
        pf["inss"] += l["valor_inss_retido"]
        pf["fgts"] += l["valor_fgts"]
    folhas = [{"folha": f, "tipo": t, "linhas": d["linhas"], "func": len(d["func"]),
               "prov": d["prov"], "desc": d["desc"], "inss": d["inss"], "fgts": d["fgts"]}
              for (f, t), d in sorted(por_folha.items())]
    def _periodo(pers):
        f = lambda p: f"{p[5:7]}/{p[:4]}" if len(p) >= 7 else f"13º/{p[:4]}"
        ps = sorted(pers, key=lambda p: p if len(p) >= 7 else p + "-12")
        return "" if not ps else (f(ps[0]) if len(ps) == 1 else f"{f(ps[0])} a {f(ps[-1])}")
    pendentes = [{"cod": c, "motivo": m, "vezes": d["n"], "dsc": (r1010.get(c) or {}).get("dsc", ""),
                  "tipo": (r1010.get(c) or {}).get("tp", ""), "valor": _cent(d["vr"]),
                  "periodo": _periodo(d["pers"]), "func": len(d["func"]), "cliente": d["cliente"]}
                 for (c, m), d in sorted(pend_uso.items(), key=lambda x: -x[1]["n"])]
    return {"ok": True, "empresa": emp[0]["razaosocial"], "cnpj": emp[0].get("cnpj") or "",
            "funcionarios": len(cad),
            "planilha": os.path.basename(depara), "aba": aba,
            "depara": {"com_verba": len(mapa), "nao_importar": len(fora), "tab_total": len(info),
                       "pendentes": len(pend)},
            "s1200": n_ev, "s1200_fora": n_tirados, "s1200_validos": len(v1200), "s2299": len(v2299),
            "cpf_sem_func": sorted(faltou_cpf), "pendentes": pendentes, "folhas": folhas,
            "corte": corte, "folhas_puladas": pulou,
            "linhas_mov": linhas_mov, "linhas_tot": linhas_tot, "nome": nome,
            "total_prov": sum(f["prov"] for f in folhas), "total_desc": sum(f["desc"] for f in folhas)}


def salvar_previa(res, caminho=PREVIA):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumo por folha"
    ws.append(["Folha", "Tipo", "Funcionários", "Linhas tab_mov", "Proventos", "Descontos",
               "INSS (tab_total)", "FGTS (tab_total)"])
    for f in res["folhas"]:
        ws.append([f["folha"], f["tipo"], f["func"], f["linhas"], f["prov"] / 100, f["desc"] / 100,
                   f["inss"] / 100, f["fgts"] / 100])
    ws = wb.create_sheet("tab_mov")
    ws.append(["Matrícula", "Nome", "Folha", "Tipo", "Verba", "Qtd", "Valor (R$)"])
    for l in res["linhas_mov"]:
        ws.append([l["matricula"], res["nome"].get(l["matricula"], ""), l["folha"], l["folha_tipo"],
                   l["cod_verba"], l["qtd"] / 100, l["valor"] / 100])
    ws = wb.create_sheet("tab_total")
    cols = ["valor_salario", "valor_total_proventos", "valor_total_descontos", "valor_liquido",
            "valor_base_inss_semlimite", "valor_base_inss_comlimite", "valor_inss_retido",
            "valor_base_fgts", "valor_fgts", "valor_irrf_basetabela"]
    ws.append(["Matrícula", "Nome", "Folha", "Tipo"] + cols)
    for l in res["linhas_tot"]:
        ws.append([l["matricula"], res["nome"].get(l["matricula"], ""), l["folha"], l["folha_tipo"]]
                  + [l[c] / 100 for c in cols])
    ws = wb.create_sheet("Pendentes")
    ws.append(["Código eSocial", "Descrição", "Vezes", "Motivo"])
    for p in res["pendentes"]:
        ws.append([p["cod"], p["dsc"], p["vezes"], p["motivo"]])
    wb.save(caminho)
    return caminho


def pdf_criticas(res, destino):
    """PDF para mandar ao cliente: o que impede a importação, rubrica por rubrica.

    Escrito para o cliente — sem caminho local, sem nome de tabela nem de
    sistema interno. destino: caminho do arquivo ou um BytesIO.
    """
    from datetime import datetime
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    AZ = colors.HexColor("#1E3A5F")
    s_tit = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, textColor=AZ, spaceAfter=4)
    s_sub = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"))
    s_txt = ParagraphStyle("x", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#334155"),
                           spaceAfter=4)
    s_res = ParagraphStyle("r", parent=s_sub, fontSize=9.5, leading=12, textColor=colors.black, spaceBefore=4,
                           spaceAfter=6)
    s_c = ParagraphStyle("c", fontName="Helvetica", fontSize=7.5, leading=9)
    s_cb = ParagraphStyle("cb", parent=s_c, fontName="Helvetica-Bold")
    W = landscape(A4)[0] - 3 * cm
    cnpj = re.sub(r"\D", "", res.get("cnpj") or "")
    if len(cnpj) == 14:
        cnpj = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    brl = lambda c: ("R$ " + f"{c / 100:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")
    TP = {"1": "Provento", "2": "Desconto", "3": "Informativa", "4": "Informativa dedutora"}
    esc = lambda t: str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    pend = res.get("pendentes") or []

    el = [Paragraph("IMPORTAÇÃO DA FICHA FINANCEIRA — PENDÊNCIAS DA PLANILHA DE-PARA", s_tit),
          Paragraph(f"Empresa: <b>{esc(res.get('empresa') or '—')}</b>" + (f" — CNPJ {cnpj}" if cnpj else "") + "<br/>"
                    f"Planilha: <b>{esc(res.get('planilha'))}</b> (aba “{esc(res.get('aba'))}”)<br/>"
                    f"Conferência de {datetime.now().strftime('%d/%m/%Y')}.", s_sub),
          Spacer(1, 6),
          Paragraph("Para trazer o histórico das folhas do eSocial para o Folha10, cada rubrica usada nas folhas "
                    "e nas rescisões precisa estar na planilha de-para, dizendo para qual verba do Folha10 ela vai "
                    "(ou “NÃO IMPORTAR”). Enquanto houver pendência, a importação não é feita.", s_txt)]
    if not pend:
        el.append(Paragraph("<font color='#166534'><b>Nenhuma pendência.</b></font> A planilha está pronta "
                            "para a importação.", s_res))
    else:
        el.append(Paragraph(f"<font color='#B91C1C'><b>{len(pend)} rubrica(s) com pendência.</b></font> "
                            "Corrija na planilha e devolva para importarmos.", s_res))
        rows = [[Paragraph(h, s_cb) for h in ("Rubrica", "Descrição no eSocial", "Tipo", "Período", "Func.",
                                              "Valor total", "O que fazer")]]
        for p in pend:
            rows.append([Paragraph(esc(x), s_cb if j == 0 else s_c) for j, x in enumerate(
                [p["cod"], p["dsc"], TP.get(p.get("tipo"), p.get("tipo") or ""), p.get("periodo", ""),
                 p.get("func", ""), brl(p.get("valor") or 0), p.get("cliente") or p["motivo"]])])
        t = Table(rows, colWidths=[x * W for x in (.1, .22, .08, .12, .05, .1, .33)], repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FB")),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        el.append(t)

    def rodape(c, d):
        c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(1.5 * cm, 0.8 * cm, "Folha10-Simples · Importação da ficha financeira do eSocial")
        c.drawRightString(landscape(A4)[0] - 1.5 * cm, 0.8 * cm, f"Página {d.page}"); c.restoreState()

    SimpleDocTemplate(destino, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                      topMargin=1.3 * cm, bottomMargin=1.3 * cm,
                      title="Pendências da planilha de-para").build(el, onFirstPage=rodape, onLaterPages=rodape)
    return destino


def gravar(app, id_cliente, id_empresa, res, cpf_usuario="", progresso=None):
    """Grava o que simular() montou. Recusa se houver pendência.
    progresso(pct, etapa) é chamado a cada lote de 500 linhas (a barra da tela)."""
    prog = progresso or (lambda p, e: None)
    if res.get("pendentes") or res.get("cpf_sem_func"):
        return {"ok": False, "msg": "Há códigos pendentes ou CPF sem funcionário — corrija a planilha antes."}
    sb = app.supabase

    def _limpar():
        sb.table("tab_mov").delete().eq("id_empresa", id_empresa).eq("id_cliente", id_cliente).eq("lote", LOTE).execute()
        sb.table("tab_total").delete().eq("id_empresa", id_empresa).eq("id_cliente", id_cliente) \
            .eq("controle", CONTROLE_TOT).execute()

    prog(2, "apagando a importação anterior…")
    _limpar()
    # Cada insert de 500 é tudo-ou-nada, mas a gravação inteira não: se um lote
    # falhar no meio (constraint do banco, rede), desfaz o que já entrou para não
    # ficar ficha pela metade — quem olha a empresa não teria como saber.
    total = len(res["linhas_mov"]) + len(res["linhas_tot"]) or 1
    feitas = 0
    try:
        for tab, linhas in (("tab_mov", res["linhas_mov"]), ("tab_total", res["linhas_tot"])):
            for i in range(0, len(linhas), 500):
                lote = linhas[i:i + 500]
                prog(5 + 90 * feitas // total, f"gravando {tab}: {i + len(lote)} de {len(linhas)} linhas…")
                sb.table(tab).insert(lote).execute()
                feitas += len(lote)
    except Exception as e:
        prog(97, "erro — desfazendo o que entrou…")
        try:
            _limpar()
            desfeito = "nada ficou gravado"
        except Exception as e2:
            desfeito = f"ATENÇÃO: não deu para desfazer ({str(e2)[:80]}) — rode a gravação de novo"
        return {"ok": False, "msg": f"Erro ao gravar ({desfeito}): {str(e)[:300]}"}
    prog(97, "gravando o log…")
    obs = (f"eSocial S-1200/S-2299 -> lote {LOTE}: tab_mov {len(res['linhas_mov'])}, "
           f"tab_total {len(res['linhas_tot'])}, {len(res['folhas'])} folhas, "
           f"planilha {res['planilha']}")[:300]
    try:
        sb.table("tab_log").insert({
            "id_cliente": id_cliente, "id_empresa": id_empresa, "cpf_usuario": cpf_usuario,
            "menu": "IMP-S1200", "matricula": 0, "observacao": obs,
            "data_hora_grava": app._agora_brasilia().strftime("%Y%m%d %H%M"),
        }).execute()
    except Exception as e:
        print(f"(log não gravado: {e})")
    return {"ok": True, "mov": len(res["linhas_mov"]), "tot": len(res["linhas_tot"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", type=int, required=True)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--depara", required=True)
    ap.add_argument("--origem", default=DX.ORIGEM)
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()

    app = _supabase()
    res = simular(app, a.cliente, a.empresa, a.depara, a.origem,
                  progresso=lambda p, e: print(f"  {p:>3}% {e}"))
    if not res["ok"]:
        sys.exit(res["msg"])
    brl = lambda c: f"{c / 100:>14,.2f}"
    print(f"\nEmpresa {a.empresa} - {res['empresa']}  ({res['funcionarios']} funcionários)")
    print(f"Planilha {res['planilha']} (aba {res['aba']}): {res['depara']}")
    print(f"S-1200: {res['s1200']} | fora (anulado/retificado): {res['s1200_fora']} | "
          f"válidos: {res['s1200_validos']} | S-2299 válidos: {res['s2299']}")
    if res["cpf_sem_func"]:
        print(f"CPF sem funcionário: {len(res['cpf_sem_func'])}")
    if res["pendentes"]:
        print("\nPENDENTES (bloqueiam a gravação):")
        for p in res["pendentes"]:
            print(f"  {p['cod']:<16} {p['vezes']:>4}x  {p['dsc'][:35]:<35}  {p['motivo']}")
    print("\nFolha   Tipo Func Linhas      Proventos      Descontos           INSS           FGTS")
    for f in res["folhas"]:
        print(f"{f['folha']}  {f['tipo']:^4} {f['func']:>4} {f['linhas']:>6} {brl(f['prov'])} {brl(f['desc'])} "
              f"{brl(f['inss'])} {brl(f['fgts'])}")
    print(f"tab_mov: {len(res['linhas_mov'])} linhas | tab_total: {len(res['linhas_tot'])} linhas"
          + (f" | folhas a partir de {res['corte']} ficam de fora (já são do Folha10)" if res["corte"] else ""))
    try:
        print(f"Prévia: {salvar_previa(res)}")
    except Exception as e:
        print(f"(não deu para salvar a prévia: {e})")
    if not a.gravar:
        print("\nSIMULAÇÃO - nada foi gravado. Use --gravar para gravar.")
        return
    r = gravar(app, a.cliente, a.empresa, res)
    print(r)


if __name__ == "__main__":
    main()
