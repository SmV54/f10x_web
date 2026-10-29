# -*- coding: utf-8 -*-
"""
Confere a planilha de-para de rubricas de uma importação contra as rubricas
que a empresa mandou ao eSocial (S-1010) nos ZIPs do portal.

Cada importação tem a sua planilha de-para (código da rubrica no eSocial →
verba do Folha10). Antes de importar o S-1200 é preciso saber se a planilha
cobre todas as rubricas: a que ficar de fora tem o valor perdido na
importação, sem aviso.

Uso:
    python _conferir_depara_s1010.py --depara "C:\\...\\De-para rubricas.xlsx"
    python _conferir_depara_s1010.py --depara ... --origem C:\\XMLeSocial\\XMLzip --aba "De-para (usadas)"

A planilha: a aba (padrão: a primeira com "de-para" no nome; senão a
primeira) traz o código da rubrica do eSocial na coluna A, a partir da
linha 2. Só a coluna A é lida — o resto da planilha é livre.

Sai um PDF (padrão em C:\\XMLeSocial\\Planilhas) com:
  1. rubricas do S-1010 que NÃO estão na planilha e têm valor nos S-1200
     (essas se perdem na importação);
  2. rubricas do S-1010 fora da planilha e sem uso em S-1200 (não afetam);
  3. códigos da planilha que não existem em nenhum S-1010 (digitação errada
     ou rubrica de outra empresa).
Não grava nada no banco.
"""
import os, re, sys, argparse
from collections import defaultdict

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import _descompactar_xml_esocial as DX
import _importar_s1200_tabmov as I

TIPO = {"1": "Provento", "2": "Desconto", "3": "Informativa", "4": "Informativa dedutora"}


def _g(tag, t):
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", t)
    return m.group(1).strip() if m else ""


def ler_planilha(caminho, aba=""):
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    if aba:
        ws = wb[aba]
    else:
        ws = next((w for w in wb.worksheets if "de-para" in w.title.lower()), wb.worksheets[0])
    cods = {}
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not r or r[0] is None or not str(r[0]).strip():
            continue
        cods[str(r[0]).strip()] = i + 1
    return ws.title, cods


def ler_s1010(origem):
    """{codRubr: definição mais recente (iniValid maior)}; exclusão marca 'excluida'."""
    rub = {}
    for z in DX.listar_zips(origem):
        for nome, dados in DX.iter_xmls(os.path.join(origem, z)):
            if not nome or ".S-1010." not in nome:
                continue
            t = dados.decode("utf-8", "ignore")
            cod = _g("codRubr", t)
            if not cod:
                continue
            d = {"cod": cod, "tab": _g("ideTabRubr", t), "dsc": _g("dscRubr", t),
                 "tipo": TIPO.get(_g("tpRubr", t), _g("tpRubr", t)), "nat": _g("natRubr", t),
                 "inss": _g("codIncCP", t), "irrf": _g("codIncIRRF", t), "fgts": _g("codIncFGTS", t),
                 "ini": _g("iniValid", t), "excluida": "<exclusao>" in t}
            ant = rub.get(cod)
            if d["excluida"] and ant:
                ant["excluida"] = True
                continue
            if not ant or d["ini"] >= ant["ini"]:
                if ant and not d["dsc"]:
                    continue
                rub[cod] = d
    return rub


def nome_empresa(cnpj):
    """Razao social pelo CNPJ (raiz ou completo) em tab_empresa — so leitura.
    O S-1000 nao traz o nome; sem conexao, o relatorio sai so com o CNPJ."""
    raiz = re.sub(r"\D", "", cnpj or "")[:8]
    if len(raiz) != 8:
        return ""
    try:
        app = I._supabase()
        rows = (app.supabase.table("tab_empresa").select("id_empresa, razaosocial, cnpj")
                .like("cnpj", raiz + "%").execute().data or [])
        return " / ".join(f"{int(r['id_empresa']):04d} - {(r.get('razaosocial') or '').strip()}" for r in rows)
    except Exception as e:
        print(f"(nome da empresa nao lido: {str(e)[:80]})")
        return ""


def uso_s1200(origem):
    uso = defaultdict(lambda: {"n": 0, "vr": 0.0, "pers": set(), "cpfs": set()})
    validos, _, _ = I.ler_s1200(origem)
    for ev, itens in validos:
        for it in itens:
            u = uso[it["cod"]]
            u["n"] += 1; u["vr"] += it["vr"]; u["pers"].add(ev["per"]); u["cpfs"].add(ev["cpf"])
    return uso, len(validos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depara", required=True)
    ap.add_argument("--aba", default="")
    ap.add_argument("--origem", default=DX.ORIGEM)
    ap.add_argument("--saida", default="")
    a = ap.parse_args()

    aba, plan = ler_planilha(a.depara, a.aba)
    rub = ler_s1010(a.origem)
    uso, n_ev = uso_s1200(a.origem)
    emp = DX.identificar_empresa(a.origem)
    cnpj = (emp.get("empresas") or [{}])[0].get("cnpj_fmt", "")
    empresa = nome_empresa((emp.get("empresas") or [{}])[0].get("cnpj", ""))

    # rubrica usada em S-1200 mas sem S-1010 nos ZIPs tambem conta
    todos = set(rub) | set(uso)
    fora = sorted(c for c in todos if c not in plan)
    fora_usadas = [c for c in fora if c in uso]
    fora_sem_uso = [c for c in fora if c not in uso]
    plan_sem_s1010 = sorted(c for c in plan if c not in rub and c not in uso)

    def per_fmt(p):
        return f"{p[5:7]}/{p[:4]}" if len(p) >= 7 else f"13º/{p[:4]}"

    def periodo(pers):
        ps = sorted(pers)
        return "" if not ps else (per_fmt(ps[0]) if len(ps) == 1 else f"{per_fmt(ps[0])} a {per_fmt(ps[-1])}")

    def brl(v):
        return ("R$ " + f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    AZ, VERM = colors.HexColor("#1E3A5F"), colors.HexColor("#B91C1C")
    s_tit = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, textColor=AZ, spaceAfter=4)
    s_sub = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"))
    s_sec = ParagraphStyle("g", fontName="Helvetica-Bold", fontSize=10.5, textColor=AZ, spaceBefore=12, spaceAfter=3)
    s_txt = ParagraphStyle("x", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#334155"), spaceAfter=3)
    s_c = ParagraphStyle("c", fontName="Helvetica", fontSize=7.5, leading=9)
    s_cb = ParagraphStyle("cb", parent=s_c, fontName="Helvetica-Bold")
    W = landscape(A4)[0] - 3 * cm

    def tabela(cods, com_uso):
        cab = ["Código", "Descrição", "Tipo", "Natureza", "INSS/IRRF/FGTS", "Válida desde"]
        cw = [.09, .33, .09, .07, .11, .09]
        if com_uso:
            cab += ["Lanç.", "Func.", "Período", "Total"]
            cw = [.08, .26, .08, .06, .1, .08, .05, .05, .12, .12]
        rows = [[Paragraph(h, s_cb) for h in cab]]
        for c in cods:
            r = rub.get(c) or {}
            dsc = r.get("dsc") or "(sem S-1010 nos ZIPs)"
            if r.get("excluida"):
                dsc += " — excluída no S-1010"
            lin = [c, dsc, r.get("tipo", ""), r.get("nat", ""),
                   f"{r.get('inss', '')} / {r.get('irrf', '')} / {r.get('fgts', '')}" if r else "",
                   (r.get("ini") or "")[5:7] + "/" + (r.get("ini") or "")[:4] if r.get("ini") else ""]
            if com_uso:
                u = uso[c]
                lin += [str(u["n"]), str(len(u["cpfs"])), periodo(u["pers"]), brl(u["vr"])]
            rows.append([Paragraph(str(x), s_cb if j == 0 else s_c) for j, x in enumerate(lin)])
        t = Table(rows, colWidths=[x * W for x in cw], repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FB")),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return t

    def nada(txt):
        return Paragraph(f"<font color='#166534'><b>Nenhuma.</b></font> {txt}", s_txt)

    el = [Paragraph("CONFERÊNCIA DA PLANILHA DE-PARA × RUBRICAS DO eSOCIAL (S-1010)", s_tit),
          Paragraph(f"Empresa: <b>{empresa or '(não cadastrada no Folha10)'}</b> — CNPJ {cnpj or '—'}<br/>"
                    f"Planilha: <b>{os.path.basename(a.depara)}</b> — aba “{aba}”, {len(plan)} código(s)<br/>"
                    f"ZIPs: {a.origem} — {len(rub)} rubrica(s) no S-1010, {n_ev} S-1200 válido(s) "
                    "(sem os anulados por S-3000 e sem os originais retificados)", s_sub),
          Spacer(1, 4)]
    tot_perdido = sum(uso[c]["vr"] for c in fora_usadas)
    el.append(Paragraph(
        f"<b>Resultado:</b> {len(fora_usadas)} rubrica(s) com valor no S-1200 fora da planilha"
        + (f" (<font color='#B91C1C'><b>{brl(tot_perdido)}</b></font> que ficariam de fora da importação)" if fora_usadas else "")
        + f"; {len(fora_sem_uso)} fora da planilha sem uso; {len(plan_sem_s1010)} código(s) da planilha sem S-1010.",
        ParagraphStyle("r", parent=s_sub, fontSize=9.5, textColor=colors.black)))

    el.append(Paragraph("1. Fora da planilha e COM valor nos S-1200 — incluir antes de importar", s_sec))
    el.append(Paragraph("O valor destas rubricas não entra no movimento se a planilha não disser para qual verba vai "
                        "(ou que não deve ser importada).", s_txt))
    el.append(tabela(fora_usadas, True) if fora_usadas else nada("Todas as rubricas com valor estão na planilha."))

    el.append(Paragraph("2. Fora da planilha e SEM uso nos S-1200 — não afetam a importação", s_sec))
    el.append(Paragraph("Estão cadastradas no S-1010, mas nenhum S-1200 dos ZIPs tem valor nelas. Podem ficar fora; "
                        "inclua se quiser a planilha completa.", s_txt))
    el.append(tabela(fora_sem_uso, False) if fora_sem_uso else nada("Todas as rubricas do S-1010 estão na planilha."))

    el.append(Paragraph("3. Na planilha mas sem S-1010 nem S-1200 nos ZIPs — conferir o código", s_sec))
    el.append(Paragraph("Pode ser erro de digitação (zero a mais, letra trocada) ou rubrica de outra empresa.", s_txt))
    if plan_sem_s1010:
        rows = [[Paragraph(h, s_cb) for h in ("Código na planilha", "Linha")]] + \
               [[Paragraph(c, s_cb), Paragraph(str(plan[c]), s_c)] for c in plan_sem_s1010]
        t = Table(rows, colWidths=[.2 * W, .1 * W], repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FB")),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1"))]))
        el.append(t)
    else:
        el.append(nada("Todo código da planilha existe nos ZIPs."))

    def rodape(c, d):
        c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(1.5 * cm, 0.8 * cm, "Folha10-Simples · Conferência de-para × S-1010")
        c.drawRightString(landscape(A4)[0] - 1.5 * cm, 0.8 * cm, f"Página {d.page}"); c.restoreState()

    saida = a.saida or os.path.join(DX.PLANILHAS, "Conferencia_DePara_S1010_"
                                    + re.sub(r"\W+", "_", os.path.splitext(os.path.basename(a.depara))[0]).strip("_") + ".pdf")
    SimpleDocTemplate(saida, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                      topMargin=1.3 * cm, bottomMargin=1.3 * cm).build(el, onFirstPage=rodape, onLaterPages=rodape)
    print(f"Planilha: {len(plan)} códigos (aba {aba}) | S-1010: {len(rub)} | S-1200 válidos: {n_ev}")
    print(f"Fora da planilha com uso: {len(fora_usadas)} ({brl(tot_perdido)}) | sem uso: {len(fora_sem_uso)} | "
          f"planilha sem S-1010: {len(plan_sem_s1010)}")
    for c in fora_usadas:
        print(f"  {c:<12} {uso[c]['n']:>4}x {brl(uso[c]['vr']):>14}  {(rub.get(c) or {}).get('dsc', '')}")
    print(saida)


if __name__ == "__main__":
    main()
