# -*- coding: utf-8 -*-
"""
Importa os valores do S-1200 (ZIPs baixados do portal do eSocial) para o
tab_mov de uma empresa, usando a planilha de-para de rubricas.

Serve para empresa que veio de outro sistema: o histórico da ficha financeira
é o que dá as médias de férias, 13º e rescisão.

Uso:
    python _importar_s1200_tabmov.py --cliente 73 --empresa 79 --depara "C:\\...\\analise F10.xlsx"
    python _importar_s1200_tabmov.py ... --gravar

Sem --gravar é SIMULAÇÃO: não grava nada, mostra o resumo por folha e salva a
prévia em C:\\XMLeSocial\\Planilhas\\Previa_S1200_tabmov.xlsx.

A planilha: coluna A = código da rubrica no eSocial, coluna O = verba do
Folha10 (4 dígitos) ou NÃO IMPORTAR / CRIAR / DECIDIR. Código sem verba fica
de fora e aparece no resumo; com --gravar ele só segue se vier também
--ignorar-pendentes.

O que entra:
  - S-1200 anulado por S-3000 não entra;
  - S-1200 retificado (indRetif=2) substitui o original — o original sai;
  - folha_tipo: 0011 (13º) e indApuracao=2 → '1', folha AAAA12;
    férias (0041/0042/0045/0046) → 'F'; o resto → 'N';
  - valores somados por matrícula/folha/tipo/verba; qtd em horas × 100
    (037FOLH e 404FOLH vêm em horas.minutos e são convertidas).

Tudo vai com lote = LOTE e origem 'I'. Rodar de novo apaga o que esse lote
gravou na empresa e grava outra vez. Se a empresa já tiver tab_mov de outra
origem, não grava nada.
"""
import os, re, sys, ssl, argparse, tempfile
from collections import defaultdict, Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import _descompactar_xml_esocial as DX

LOTE = 1200
ORIGEM = "I"
QTD_HORAS_MIN = {"037FOLH", "404FOLH"}       # quantidade em horas.minutos
VERBAS_FERIAS = {41, 42, 45, 46}
VERBA_13 = 11
PREVIA = r"C:\XMLeSocial\Planilhas\Previa_S1200_tabmov.xlsx"

RE_TAG = lambda t: re.compile(rf"<{t}>([^<]*)</{t}>")
R_PER, R_CPF, R_IND, R_RETIF = RE_TAG("perApur"), RE_TAG("cpfTrab"), RE_TAG("indApuracao"), RE_TAG("indRetif")


def _g(rx, txt, padrao=""):
    m = rx.search(txt)
    return m.group(1).strip() if m else padrao


def ler_depara(caminho):
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    ws = wb["De-para (usadas)"]
    mapa, fora, pend = {}, set(), {}
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not r or not r[0]:
            continue
        cod = str(r[0]).strip()
        v = str(r[14] or "").strip() if len(r) > 14 else ""
        if re.fullmatch(r"\d{1,4}", v):
            mapa[cod] = int(v)
        elif v.upper().startswith("N") and "IMPORTAR" in v.upper():
            fora.add(cod)
        else:
            pend[cod] = v or "sem verba"
    return mapa, fora, pend


def ler_s1200(origem):
    """[(ev, itens)] dos S-1200 válidos: sem os anulados e sem os retificados."""
    zips = DX.listar_zips(origem)
    anulados = DX.recibos_excluidos(origem, zips)
    eventos, vistos = [], set()
    for z in zips:
        for nome, dados in DX.iter_xmls(os.path.join(origem, z)):
            if not nome or not nome.endswith(".S-1200.xml") or nome in vistos:
                continue
            vistos.add(nome)
            t = dados.decode("utf-8", "ignore")
            ide = re.search(r"<ideEvento>(.*?)</ideEvento>", t, re.S)
            ide = ide.group(1) if ide else ""
            ev = {"arquivo": nome, "recibo": DX.recibo_proprio(dados),
                  "retif": _g(R_RETIF, ide) == "2", "substitui": _g(RE_TAG("nrRecibo"), ide),
                  "per": _g(R_PER, ide), "ind": _g(R_IND, ide, "1"), "cpf": _g(R_CPF, t)}
            itens = []
            for dm in re.findall(r"<dmDev>(.*?)</dmDev>", t, re.S):
                ide_dm = _g(RE_TAG("ideDmDev"), dm)
                for it in re.findall(r"<itensRemun>(.*?)</itensRemun>", dm, re.S):
                    itens.append({"dm": ide_dm, "cod": _g(RE_TAG("codRubr"), it),
                                  "qtd": float(_g(RE_TAG("qtdRubr"), it, "0") or 0),
                                  "vr": float(_g(RE_TAG("vrRubr"), it, "0") or 0)})
            eventos.append((ev, itens))
    substituidos = {ev["substitui"] for ev, _ in eventos if ev["retif"] and ev["substitui"]}
    validos = [(ev, it) for ev, it in eventos
               if ev["recibo"] not in anulados and ev["recibo"] not in substituidos]
    return validos, len(eventos), len(eventos) - len(validos)


def _horas(cod, q):
    if cod in QTD_HORAS_MIN:
        h = int(q)
        return h + round((q - h) * 100) / 60
    return q


def montar(validos, mapa, fora, pend, mat_por_cpf):
    soma = defaultdict(lambda: [0.0, 0.0])          # (mat, folha, tipo, verba) -> [qtd, valor]
    faltou_cpf, pend_uso, fora_uso = Counter(), Counter(), Counter()
    for ev, itens in validos:
        mat = mat_por_cpf.get(ev["cpf"])
        if not mat:
            faltou_cpf[ev["cpf"]] += 1
            continue
        anual = ev["ind"] == "2" or len(ev["per"]) == 4
        ano, mes = ev["per"][:4], (ev["per"][5:7] if len(ev["per"]) >= 7 else "12")
        for it in itens:
            cod = it["cod"]
            if cod in fora:
                fora_uso[cod] += 1
                continue
            verba = mapa.get(cod)
            if verba is None:
                pend_uso[(cod, pend.get(cod, "não está na planilha"))] += 1
                continue
            if anual or verba == VERBA_13:
                folha, tipo = int(ano + "12"), "1"
            else:
                folha = int(ano + mes)
                tipo = "F" if verba in VERBAS_FERIAS else "N"
            k = (mat, folha, tipo, verba)
            soma[k][0] += _horas(cod, it["qtd"])
            soma[k][1] += it["vr"]
    return soma, faltou_cpf, pend_uso, fora_uso


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", type=int, required=True)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--depara", required=True)
    ap.add_argument("--origem", default=DX.ORIGEM)
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--ignorar-pendentes", action="store_true")
    a = ap.parse_args()

    app = _supabase()
    sb = app.supabase
    emp = (sb.table("tab_empresa").select("id_empresa, razaosocial")
           .eq("id_empresa", a.empresa).eq("id_cliente", a.cliente).execute().data)
    if not emp:
        sys.exit(f"Empresa {a.empresa} não é do cliente {a.cliente}.")
    cad = app._diss_todos(sb.table("tab_cad").select("matricula, cpf, nome")
                          .eq("id_empresa", a.empresa).eq("id_cliente", a.cliente))
    mat_por_cpf = {str(c["cpf"]).zfill(11): int(c["matricula"]) for c in cad}
    nome = {int(c["matricula"]): c["nome"] for c in cad}

    mapa, fora, pend = ler_depara(a.depara)
    validos, n_ev, n_tirados = ler_s1200(a.origem)
    soma, faltou_cpf, pend_uso, fora_uso = montar(validos, mapa, fora, pend, mat_por_cpf)

    print(f"Empresa {a.empresa} - {emp[0]['razaosocial']}  ({len(cad)} funcionários)")
    print(f"S-1200 nos ZIPs: {n_ev}  | anulados/retificados fora: {n_tirados}  | válidos: {len(validos)}")
    print(f"De-para: {len(mapa)} com verba, {len(fora)} não importar, {len(pend)} pendentes")
    if faltou_cpf:
        print(f"\nCPF sem funcionário na empresa ({len(faltou_cpf)}): " + ", ".join(sorted(faltou_cpf)))
    if pend_uso:
        print("\nPENDENTES (ficaram de fora):")
        for (cod, motivo), n in sorted(pend_uso.items(), key=lambda x: -x[1]):
            print(f"  {cod:<16} {n:>4}x  {motivo}")

    por_folha = defaultdict(lambda: [0, 0.0])
    for (mat, folha, tipo, verba), (q, v) in soma.items():
        por_folha[(folha, tipo)][0] += 1
        por_folha[(folha, tipo)][1] += v
    print("\nFolha   Tipo  Linhas     Valor (R$)")
    for (folha, tipo), (n, v) in sorted(por_folha.items()):
        print(f"{folha}  {tipo:^4}  {n:>6}  {v:>14,.2f}")
    print(f"Total de linhas: {len(soma)}")

    linhas = [{"id_cliente": a.cliente, "id_empresa": a.empresa, "situacao": "A",
               "matricula": mat, "folha": folha, "folha_tipo": tipo, "complemento": 0,
               "cod_verba": verba, "qtd": int(round(q * 100)), "valor": int(round(v * 100)),
               "lote": LOTE, "origem": ORIGEM, "controle": 0, "os": 0}
              for (mat, folha, tipo, verba), (q, v) in sorted(soma.items())]

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Previa tab_mov"
        ws.append(["Matrícula", "Nome", "Folha", "Tipo", "Verba", "Qtd", "Valor (R$)"])
        for l in linhas:
            ws.append([l["matricula"], nome.get(l["matricula"], ""), l["folha"], l["folha_tipo"],
                       l["cod_verba"], l["qtd"] / 100, l["valor"] / 100])
        ws2 = wb.create_sheet("Pendentes")
        ws2.append(["Código eSocial", "Vezes", "Situação na planilha"])
        for (cod, motivo), n in sorted(pend_uso.items(), key=lambda x: -x[1]):
            ws2.append([cod, n, motivo])
        wb.save(PREVIA)
        print(f"\nPrévia: {PREVIA}")
    except Exception as e:
        print(f"(não deu para salvar a prévia: {e})")

    if not a.gravar:
        print("\nSIMULAÇÃO - nada foi gravado. Use --gravar para gravar.")
        return
    if pend_uso and not a.ignorar_pendentes:
        sys.exit("\nHá códigos pendentes: complete a planilha ou use --ignorar-pendentes.")
    outros = (sb.table("tab_mov").select("id", count="exact")
              .eq("id_empresa", a.empresa).neq("lote", LOTE).limit(1).execute().count)
    if outros:
        sys.exit(f"\nA empresa já tem {outros} linha(s) no tab_mov de outra origem - nada gravado.")
    sb.table("tab_mov").delete().eq("id_empresa", a.empresa).eq("lote", LOTE).execute()
    for i in range(0, len(linhas), 500):
        sb.table("tab_mov").insert(linhas[i:i + 500]).execute()
    total = sum(l["valor"] for l in linhas) / 100
    try:
        sb.table("tab_log").insert({
            "id_cliente": a.cliente, "id_empresa": a.empresa, "cpf_usuario": "",
            "menu": "IMP-S1200", "matricula": 0,
            "observacao": (f"S-1200 -> tab_mov lote {LOTE}: {len(linhas)} linhas, "
                           f"{len(por_folha)} folhas, R$ {total:,.2f}")[:300],
            "data_hora_grava": app._agora_brasilia().strftime("%Y%m%d %H%M"),
        }).execute()
    except Exception as e:
        print(f"(log não gravado: {e})")
    print(f"\nGRAVADO: {len(linhas)} linhas no tab_mov (lote {LOTE}).")


if __name__ == "__main__":
    main()
