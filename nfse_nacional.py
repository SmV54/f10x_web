# -*- coding: utf-8 -*-
"""
NFS-e Nacional (padrão gov.br / Sefin Nacional) — geração e assinatura do DPS.

Módulo isolado e sem dependência de Flask/Supabase, para poder ser testado
sozinho. As rotas do app (app.py) fornecem os dados (emitente, tomador vindo
da TabCLI_NF, certificado A1 vindo de tab_empresa) e chamam estas funções.

Fluxo: montar_dps() -> assinar_dps() -> validar_xsd() -> compactar_gzip_b64()
       -> POST /nfse (feito no app.py, com mTLS).

Layout: DPS v1.01 (XSD oficial 20260209). Namespace do SPED/Fazenda.
"""
import os
import re
import gzip
import base64
from datetime import datetime, timezone, timedelta

NS_NFSE = "http://www.sped.fazenda.gov.br/nfse"
NS_DS   = "http://www.w3.org/2000/09/xmldsig#"

# Diretório dos XSDs oficiais (copiados para o projeto).
XSD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfse_schemas")

# Fuso de Brasília (UTC-3) — usado no dhEmi. Sem horário de verão (extinto).
TZ_BR = timezone(timedelta(hours=-3))


# ─────────────────────────────────────────────────────────────────────────
# Helpers de formatação
# ─────────────────────────────────────────────────────────────────────────
def so_digitos(v):
    return re.sub(r"\D", "", str(v or ""))


def _txt(v):
    """Normaliza texto para o XML (colapsa espaços; remove controles)."""
    s = str(v or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def dps_id(cloc_emi, cnpj_cpf_emit, serie, ndps):
    """Monta o atributo Id do infDPS: 'DPS' + 42 dígitos.
    Composição: cLocEmi(7) + tpInsc(1: 1=CPF,2=CNPJ) + inscFed(14) + serie(5) + nDPS(15).
    """
    ins = so_digitos(cnpj_cpf_emit)
    tp_insc = "2" if len(ins) == 14 else "1"      # 2=CNPJ, 1=CPF
    ins14 = ins.zfill(14)
    cloc = so_digitos(cloc_emi).zfill(7)
    serie5 = so_digitos(serie).zfill(5)
    ndps15 = so_digitos(ndps).zfill(15)
    corpo = f"{cloc}{tp_insc}{ins14}{serie5}{ndps15}"
    assert len(corpo) == 42, f"Id do DPS deve ter 42 dígitos, veio {len(corpo)}"
    return "DPS" + corpo


def competencia_iso(mmaaaa):
    """'MM/AAAA' (ou 'AAAA-MM') -> 'AAAA-MM-01' (primeiro dia da competência)."""
    s = so_digitos(mmaaaa)
    if len(s) == 6:                # MMAAAA
        mm, aaaa = s[:2], s[2:]
    elif len(s) == 8:              # AAAAMMDD -> pega AAAA-MM
        aaaa, mm = s[:4], s[4:6]
    else:
        raise ValueError(f"Competência inválida: {mmaaaa!r}")
    return f"{aaaa}-{mm}-01"


def valor_2casas(v):
    """Valor em reais (float/str) -> string com 2 casas e ponto: 549.0 -> '549.00'."""
    n = float(v)
    return f"{n:.2f}"


# ─────────────────────────────────────────────────────────────────────────
# Montagem do DPS
# ─────────────────────────────────────────────────────────────────────────
def montar_dps(d):
    """Monta o XML do DPS (sem assinatura) a partir do dict `d`.

    Campos esperados em `d`:
      ambiente        : 1 (produção) ou 2 (produção restrita/homologação)
      serie, ndps     : série e número do DPS
      dh_emi          : datetime (opcional; default agora em -03:00)
      competencia     : 'MM/AAAA'
      ver_aplic       : versão do aplicativo emissor
      # Emitente (prestador)
      emit_cnpj, emit_im, emit_nome, emit_email
      emit_op_simp_nac (default '3'), emit_reg_ap_sn (default '1'), emit_reg_esp (default '0')
      cloc_emi        : código IBGE do município emissor (7 díg.)
      # Serviço
      serv_ctribnac, serv_ctribmun (3 díg., opcional), serv_nbs (opcional)
      serv_desc       : discriminação
      serv_local      : IBGE local da prestação (default = cloc_emi)
      serv_aliquota   : '5.00' ou None (omite pAliq se None — Recife parametriza)
      # Valores / ISS
      valor           : valor do serviço em reais
      iss_retido      : bool (True=retido pelo tomador)
      # Tomador
      tom_cnpj_cpf, tom_nome, tom_email
      tom_ibge, tom_cep, tom_lgr, tom_nro, tom_cpl, tom_bairro   (endereço; opcional)
    Retorna: (xml_str, dps_id_str)
    """
    from lxml import etree

    def E(parent, tag, text=None):
        el = etree.SubElement(parent, f"{{{NS_NFSE}}}{tag}")
        if text is not None:
            el.text = str(text)
        return el

    iddps = dps_id(d["cloc_emi"], d["emit_cnpj"], d["serie"], d["ndps"])

    dh = d.get("dh_emi") or datetime.now(TZ_BR)
    if dh.tzinfo is None:
        dh = dh.replace(tzinfo=TZ_BR)
    dh_str = dh.strftime("%Y-%m-%dT%H:%M:%S%z")
    dh_str = dh_str[:-2] + ":" + dh_str[-2:]     # +/-HHMM -> +/-HH:MM

    root = etree.Element(f"{{{NS_NFSE}}}DPS", nsmap={None: NS_NFSE})
    root.set("versao", "1.00")
    inf = E(root, "infDPS")
    inf.set("Id", iddps)

    E(inf, "tpAmb", str(d["ambiente"]))
    E(inf, "dhEmi", dh_str)
    E(inf, "verAplic", _txt(d.get("ver_aplic", "Folha10"))[:20])
    E(inf, "serie", so_digitos(d["serie"]).lstrip("0") or "0")
    E(inf, "nDPS", so_digitos(d["ndps"]).lstrip("0") or "0")
    E(inf, "dCompet", competencia_iso(d["competencia"]))
    E(inf, "tpEmit", "1")                         # 1 = Prestador
    E(inf, "cLocEmi", so_digitos(d["cloc_emi"]).zfill(7))

    # ── Prestador ──
    prest = E(inf, "prest")
    E(prest, "CNPJ", so_digitos(d["emit_cnpj"]).zfill(14))
    if d.get("emit_im"):
        E(prest, "IM", so_digitos(d["emit_im"]))
    # xNome do prestador NÃO deve ser enviado quando o emitente é o próprio prestador
    # (tpEmit=1) — o sistema preenche pelo cadastro (erro E0121 se enviado).
    if d.get("emit_email"):
        E(prest, "email", _txt(d["emit_email"]))
    reg = E(prest, "regTrib")
    E(reg, "opSimpNac", str(d.get("emit_op_simp_nac", "3")))
    if str(d.get("emit_op_simp_nac", "3")) == "3" and d.get("emit_reg_ap_sn"):
        E(reg, "regApTribSN", str(d["emit_reg_ap_sn"]))
    E(reg, "regEspTrib", str(d.get("emit_reg_esp", "0")))

    # ── Tomador (opcional, mas enviamos quando há dados) ──
    tom_ins = so_digitos(d.get("tom_cnpj_cpf"))
    if tom_ins:
        toma = E(inf, "toma")
        if len(tom_ins) == 14:
            E(toma, "CNPJ", tom_ins)
        elif len(tom_ins) == 11:
            E(toma, "CPF", tom_ins)
        else:
            E(toma, "CNPJ", tom_ins.zfill(14))
        E(toma, "xNome", _txt(d.get("tom_nome") or "TOMADOR"))
        # Endereço do tomador:
        #  - ISS retido pelo tomador → obrigatório informar na DPS (senão E0237);
        #  - CPF → sem cadastro central, informamos;
        #  - CNPJ não-retido → omitimos (o Sistema Nacional completa pelo cadastro da
        #    Receita, evitando rejeição por CEP/município desatualizado, ex. E0240).
        _tem_end = all(d.get(k) for k in ("tom_lgr", "tom_nro", "tom_bairro", "tom_ibge", "tom_cep"))
        if _tem_end and (d.get("iss_retido") or len(tom_ins) == 11):
            end = E(toma, "end")
            endnac = E(end, "endNac")
            E(endnac, "cMun", so_digitos(d["tom_ibge"]).zfill(7))
            E(endnac, "CEP", so_digitos(d["tom_cep"]).zfill(8))
            E(end, "xLgr", _txt(d["tom_lgr"]))
            E(end, "nro", _txt(d["tom_nro"]))
            if d.get("tom_cpl"):
                E(end, "xCpl", _txt(d["tom_cpl"]))
            E(end, "xBairro", _txt(d["tom_bairro"]))
        if d.get("tom_email"):
            E(toma, "email", _txt(d["tom_email"]))

    # ── Serviço ──
    serv = E(inf, "serv")
    loc = E(serv, "locPrest")
    E(loc, "cLocPrestacao", so_digitos(d.get("serv_local") or d["cloc_emi"]).zfill(7))
    cserv = E(serv, "cServ")
    E(cserv, "cTribNac", so_digitos(d["serv_ctribnac"]).zfill(6))
    if d.get("serv_ctribmun"):
        E(cserv, "cTribMun", so_digitos(d["serv_ctribmun"]).zfill(3))
    E(cserv, "xDescServ", _txt(d["serv_desc"])[:2000])
    nbs = so_digitos(d.get("serv_nbs"))
    if len(nbs) == 9:                             # cNBS é opcional e exige 9 dígitos
        E(cserv, "cNBS", nbs)

    # ── Valores / Tributação ──
    valores = E(inf, "valores")
    vsp = E(valores, "vServPrest")
    E(vsp, "vServ", valor_2casas(d["valor"]))
    trib = E(valores, "trib")
    tribmun = E(trib, "tribMun")
    E(tribmun, "tribISSQN", "1")                  # 1 = operação tributável
    E(tribmun, "tpRetISSQN", "2" if d.get("iss_retido") else "1")  # 2=retido tomador,1=não
    if d.get("serv_aliquota"):
        E(tribmun, "pAliq", str(d["serv_aliquota"]))
    tottrib = E(trib, "totTrib")
    if str(d.get("emit_op_simp_nac", "3")) == "3":
        # ME/EPP (Simples): usar pTotTribSN (% da alíquota do SN); indTotTrib é proibido (E0712).
        E(tottrib, "pTotTribSN", str(d.get("emit_ptrib_sn", "0")))
    else:
        E(tottrib, "indTotTrib", "0")             # não informar valor estimado (Lei 12.741)

    xml = etree.tostring(root, encoding="unicode", xml_declaration=False)
    return xml, iddps


# ─────────────────────────────────────────────────────────────────────────
# Assinatura XMLDSig (Signature como filho de <DPS>, referência ao infDPS Id)
# ─────────────────────────────────────────────────────────────────────────
# NFS-e Nacional exige canonicalização EXCLUSIVA (xml-exc-c14n) — diferente da NF-e,
# que usa a inclusiva. Assinar com a inclusiva resulta em E0714 (erro na assinatura).
_C14N = "http://www.w3.org/2001/10/xml-exc-c14n#"


def assinar_dps(xml_str, pfx_bytes, senha):
    """Assina o DPS com o A1 (pfx), XMLDSig envelopada referenciando #<Id do infDPS>.

    A Signature é gerada SEM prefixo de namespace (namespace dsig como default),
    porque o Sefin Nacional rejeita qualquer prefixo (erro E1228). Por isso a
    assinatura é montada manualmente (lxml + cryptography) e o SignedInfo é
    canonicalizado JÁ dentro do documento (C14N 1.0 inclusive), garantindo que o
    SignatureValue confira na verificação do servidor.
    """
    import base64 as _b64
    from lxml import etree
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import pkcs12, Encoding

    sen = senha.encode() if isinstance(senha, str) else senha
    pk, cert, _chain = pkcs12.load_key_and_certificates(pfx_bytes, sen)

    root = etree.fromstring(xml_str.encode("utf-8"))
    inf = root.find(f"{{{NS_NFSE}}}infDPS")
    if inf is None:
        raise ValueError("infDPS não encontrado no DPS.")
    ref_id = inf.get("Id")

    def DS(tag):
        return f"{{{NS_DS}}}{tag}"

    # NFS-e Nacional segue o padrão ICP-Brasil de assinatura (NF-e): RSA-SHA1 + SHA1 + C14N 1.0.
    # 1. DigestValue = SHA1( C14N(infDPS) ) — enveloped: infDPS não tem Signature dentro.
    inf_c14n = etree.tostring(inf, method="c14n", exclusive=True, with_comments=False)
    dig = hashes.Hash(hashes.SHA1()); dig.update(inf_c14n)
    digest_b64 = _b64.b64encode(dig.finalize()).decode()

    # 2. Signature (namespace dsig como DEFAULT — sem prefixo)
    sig = etree.SubElement(root, DS("Signature"), nsmap={None: NS_DS})
    signed_info = etree.SubElement(sig, DS("SignedInfo"))
    etree.SubElement(signed_info, DS("CanonicalizationMethod")).set("Algorithm", _C14N)
    etree.SubElement(signed_info, DS("SignatureMethod")).set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")
    ref = etree.SubElement(signed_info, DS("Reference")); ref.set("URI", f"#{ref_id}")
    transforms = etree.SubElement(ref, DS("Transforms"))
    etree.SubElement(transforms, DS("Transform")).set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    etree.SubElement(transforms, DS("Transform")).set("Algorithm", _C14N)
    etree.SubElement(ref, DS("DigestMethod")).set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
    etree.SubElement(ref, DS("DigestValue")).text = digest_b64

    # 3. SignatureValue = sign( C14N(SignedInfo em contexto) )
    si_c14n = etree.tostring(signed_info, method="c14n", exclusive=True, with_comments=False)
    assinatura = pk.sign(si_c14n, padding.PKCS1v15(), hashes.SHA1())
    etree.SubElement(sig, DS("SignatureValue")).text = _b64.b64encode(assinatura).decode()

    # 4. KeyInfo / X509Certificate (DER em base64)
    key_info = etree.SubElement(sig, DS("KeyInfo"))
    x509 = etree.SubElement(key_info, DS("X509Data"))
    etree.SubElement(x509, DS("X509Certificate")).text = _b64.b64encode(
        cert.public_bytes(Encoding.DER)).decode()

    corpo = etree.tostring(root, encoding="unicode", xml_declaration=False)
    # Prólogo com encoding UTF-8 exigido pelo Sefin (erro E1229 sem ele);
    # a declaração não entra na canonicalização/digest, então é seguro prefixar aqui.
    return '<?xml version="1.0" encoding="UTF-8"?>' + corpo


# ─────────────────────────────────────────────────────────────────────────
# Validação contra o XSD oficial
# ─────────────────────────────────────────────────────────────────────────
def _xsd_sanitizado_dir(xsd_dir):
    """Cria (uma vez) uma cópia dos XSDs com os patterns corrigidos.
    Motivo: alguns patterns do XSD publicado usam '^...$' — no XML Schema do W3C
    o '^' e o '$' são caracteres LITERAIS (não âncoras), o que faz o libxml2
    rejeitar valores válidos (ex.: serie='1'). Removemos '^' inicial e '$' final
    do valor de cada <xs:pattern> (sem tocar em '^' dentro de classes [^...])."""
    import tempfile, glob, hashlib
    fixed = os.path.join(tempfile.gettempdir(), "nfse_xsd_fix")
    os.makedirs(fixed, exist_ok=True)
    pat = re.compile(r'(<xs:pattern\s+value=")([^"]*)("\s*/>)')

    def fix_val(m):
        v = m.group(2)
        if v.startswith("^"):
            v = v[1:]
        if v.endswith("$"):
            v = v[:-1]
        return m.group(1) + v + m.group(3)

    for src in glob.glob(os.path.join(xsd_dir, "*.xsd")):
        dst = os.path.join(fixed, os.path.basename(src))
        txt = open(src, "r", encoding="utf-8").read()
        new = pat.sub(fix_val, txt)
        # só reescreve se mudou ou destino não existe (evita I/O desnecessário)
        if (not os.path.exists(dst)) or open(dst, "r", encoding="utf-8").read() != new:
            open(dst, "w", encoding="utf-8").write(new)
    return fixed


def validar_xsd(xml_str, xsd_dir=None):
    """Valida o XML do DPS contra o DPS_v1.01.xsd. Retorna (ok:bool, erros:list[str])."""
    from lxml import etree
    xsd_dir = xsd_dir or XSD_DIR
    if not os.path.exists(os.path.join(xsd_dir, "DPS_v1.01.xsd")):
        return True, [f"(XSD não encontrado em {xsd_dir} — validação pulada)"]
    fixed = _xsd_sanitizado_dir(xsd_dir)
    schema = etree.XMLSchema(etree.parse(os.path.join(fixed, "DPS_v1.01.xsd")))
    doc = etree.fromstring(xml_str.encode("utf-8"))
    ok = schema.validate(doc)
    erros = [f"linha {e.line}: {e.message}" for e in schema.error_log]
    return bool(ok), erros


# ─────────────────────────────────────────────────────────────────────────
# Compactação para o corpo do POST
# ─────────────────────────────────────────────────────────────────────────
def compactar_gzip_b64(xml_str):
    """XML -> GZip -> Base64 (string), formato exigido pelo corpo do POST /nfse."""
    raw = xml_str.encode("utf-8")
    comp = gzip.compress(raw)
    return base64.b64encode(comp).decode("ascii")


# ─────────────────────────────────────────────────────────────────────────
# DANFSE — PDF auxiliar gerado a partir do XML da NFS-e
# ─────────────────────────────────────────────────────────────────────────
def _fmt_doc(d):
    d = re.sub(r"\D", "", str(d or ""))
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def _fmt_cep(c):
    d = re.sub(r"\D", "", str(c or ""))
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else (c or "")


def _fmt_brl(v):
    try:
        n = float(v)
    except Exception:
        return str(v or "")
    s = f"{n:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_chave(c):
    d = re.sub(r"\D", "", str(c or ""))
    return " ".join(d[i:i+4] for i in range(0, len(d), 4))


def gerar_danfse_pdf(nfse_xml_str, chave=""):
    """Gera o DANFSE (PDF auxiliar) a partir do XML da NFS-e. Retorna bytes do PDF."""
    from lxml import etree
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    NS = NS_NFSE
    root = etree.fromstring(nfse_xml_str.encode("utf-8")) \
        if isinstance(nfse_xml_str, str) else etree.fromstring(nfse_xml_str)

    def g(path):
        el = root.find(path.replace("{}", "{%s}" % NS))
        return (el.text or "").strip() if el is not None and el.text else ""

    inf = "{}infNFSe"
    numero  = g(f"{inf}/{{}}nNFSe")
    dhproc  = g(f"{inf}/{{}}dhProc")
    cstat   = g(f"{inf}/{{}}cStat")
    loc_emi = g(f"{inf}/{{}}xLocEmi")
    loc_inc = g(f"{inf}/{{}}xLocIncid")
    xtrib   = g(f"{inf}/{{}}xTribNac")
    # emitente/prestador
    e_nome = g(f"{inf}/{{}}emit/{{}}xNome")
    e_cnpj = g(f"{inf}/{{}}emit/{{}}CNPJ") or g(f"{inf}/{{}}emit/{{}}CPF")
    e_im   = g(f"{inf}/{{}}emit/{{}}IM")
    e_lgr  = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}xLgr")
    e_nro  = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}nro")
    e_cpl  = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}xCpl")
    e_bai  = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}xBairro")
    e_uf   = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}UF")
    e_cep  = g(f"{inf}/{{}}emit/{{}}enderNac/{{}}CEP")
    e_mail = g(f"{inf}/{{}}emit/{{}}email")
    # DPS (tomador, serviço, valores declarados)
    dps = f"{inf}/{{}}DPS/{{}}infDPS"
    dcompet = g(f"{dps}/{{}}dCompet")
    t_nome = g(f"{dps}/{{}}toma/{{}}xNome")
    t_cnpj = g(f"{dps}/{{}}toma/{{}}CNPJ")
    t_cpf  = g(f"{dps}/{{}}toma/{{}}CPF")
    t_doc  = t_cnpj or t_cpf
    t_lgr  = g(f"{dps}/{{}}toma/{{}}end/{{}}xLgr")
    t_nro  = g(f"{dps}/{{}}toma/{{}}end/{{}}nro")
    t_cpl  = g(f"{dps}/{{}}toma/{{}}end/{{}}xCpl")
    t_bai  = g(f"{dps}/{{}}toma/{{}}end/{{}}xBairro")
    t_cep  = g(f"{dps}/{{}}toma/{{}}end/{{}}endNac/{{}}CEP")
    t_mail = g(f"{dps}/{{}}toma/{{}}email")
    desc   = g(f"{dps}/{{}}serv/{{}}cServ/{{}}xDescServ")
    ctribnac = g(f"{dps}/{{}}serv/{{}}cServ/{{}}cTribNac")
    vserv  = g(f"{dps}/{{}}serv/{{}}valores/{{}}vServPrest/{{}}vServ")
    vliq   = g(f"{inf}/{{}}valores/{{}}vLiq") or vserv
    ret    = g(f"{dps}/{{}}serv/{{}}valores/{{}}trib/{{}}tribMun/{{}}tpRetISSQN")
    ptribsn = g(f"{dps}/{{}}serv/{{}}valores/{{}}trib/{{}}totTrib/{{}}pTotTribSN")

    def dt(s):
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]} {s[11:16]}" if len(s) >= 16 else s
    def comp(s):
        return f"{s[5:7]}/{s[0:4]}" if len(s) >= 7 else s

    ss = getSampleStyleSheet()
    pN = ParagraphStyle('n', parent=ss['Normal'], fontSize=8, leading=10)
    pB = ParagraphStyle('b', parent=pN, fontName='Helvetica-Bold')
    pSmall = ParagraphStyle('s', parent=pN, fontSize=7, leading=8.5, textColor=colors.HexColor('#475569'))
    pTitulo = ParagraphStyle('t', parent=ss['Normal'], fontSize=13, fontName='Helvetica-Bold')

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=12*mm, bottomMargin=12*mm,
                            title=f"NFSe {numero}")
    el = []
    AZUL = colors.HexColor('#1d4ed8'); CINZA = colors.HexColor('#f1f5f9')
    LINHA = colors.HexColor('#cbd5e1')

    # Cabeçalho
    cab = Table([[
        Paragraph("NOTA FISCAL DE SERVIÇOS ELETRÔNICA<br/><font size=8 color='#475569'>NFS-e — Padrão Nacional · DANFSE</font>", pTitulo),
        Paragraph(f"<b>Nº {numero}</b><br/>"
                  f"<font size=8>Competência: {comp(dcompet)}<br/>"
                  f"Emissão: {dt(dhproc)}<br/>"
                  f"Município: {loc_emi}</font>", pN),
    ]], colWidths=[112*mm, 70*mm])
    cab.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 1, AZUL),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    el.append(cab)
    el.append(Spacer(1, 3))
    # Chave de acesso
    ch = Table([[Paragraph("<b>CHAVE DE ACESSO</b>", pSmall)],
                [Paragraph(f"<font face='Courier' size=9>{_fmt_chave(chave)}</font>", pN)]],
               colWidths=[182*mm])
    ch.setStyle(TableStyle([('BOX',(0,0),(-1,-1),0.7,LINHA),('BACKGROUND',(0,0),(-1,-1),CINZA),
        ('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    el.append(ch); el.append(Spacer(1, 6))

    def bloco(titulo, linhas):
        dados = [[Paragraph(f"<b>{titulo}</b>", pSmall)]]
        for lab, val in linhas:
            dados.append([Paragraph(f"<b>{lab}:</b> {val}", pN) if lab else Paragraph(val, pN)])
        t = Table(dados, colWidths=[182*mm])
        t.setStyle(TableStyle([
            ('BOX',(0,0),(-1,-1),0.7,LINHA),
            ('BACKGROUND',(0,0),(0,0),colors.HexColor('#e2e8f0')),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),2.5),('BOTTOMPADDING',(0,0),(-1,-1),2.5),
            ('TOPPADDING',(0,0),(0,0),4),('BOTTOMPADDING',(0,0),(0,0),4),
        ]))
        return t

    e_end = f"{e_lgr}, {e_nro}" + (f" — {e_cpl}" if e_cpl else "") + \
            f" · {e_bai} · {loc_emi}/{e_uf} · CEP {_fmt_cep(e_cep)}"
    el.append(bloco("PRESTADOR DE SERVIÇOS", [
        ("Nome/Razão social", e_nome), ("CNPJ", _fmt_doc(e_cnpj) + f"    Inscr. Municipal: {e_im}"),
        ("Endereço", e_end), ("E-mail", e_mail),
    ]))
    el.append(Spacer(1, 5))
    t_end = (f"{t_lgr}, {t_nro}" + (f" — {t_cpl}" if t_cpl else "") +
             (f" · {t_bai}" if t_bai else "") + (f" · CEP {_fmt_cep(t_cep)}" if t_cep else "")) \
            if t_lgr else "(endereço não informado)"
    el.append(bloco("TOMADOR DE SERVIÇOS", [
        ("Nome/Razão social", t_nome or "—"),
        ("CPF/CNPJ", _fmt_doc(t_doc)),
        ("Endereço", t_end), ("E-mail", t_mail or "—"),
    ]))
    el.append(Spacer(1, 5))
    el.append(bloco("DISCRIMINAÇÃO DO SERVIÇO", [
        ("", f"<b>{ctribnac} — {xtrib}</b>" if xtrib else ctribnac),
        ("", desc),
    ]))
    el.append(Spacer(1, 5))

    ret_txt = {"1": "Não retido", "2": "Retido pelo tomador", "3": "Retido pelo intermediário"}.get(ret, "—")
    val = Table([
        [Paragraph("<b>Valor do serviço</b>", pN), Paragraph(_fmt_brl(vserv), pN),
         Paragraph("<b>Retenção do ISSQN</b>", pN), Paragraph(ret_txt, pN)],
        [Paragraph("<b>Trib. aprox. (Simples)</b>", pN), Paragraph(f"{ptribsn}%" if ptribsn else "—", pN),
         Paragraph("<b>VALOR LÍQUIDO</b>", pB), Paragraph(f"<b>{_fmt_brl(vliq)}</b>", pB)],
    ], colWidths=[38*mm, 53*mm, 38*mm, 53*mm])
    val.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.7,LINHA),('INNERGRID',(0,0),(-1,-1),0.4,LINHA),
        ('BACKGROUND',(2,1),(3,1),colors.HexColor('#dcfce7')),
        ('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
    ]))
    el.append(val)
    el.append(Spacer(1, 8))
    autoriz = "Autorizada" if cstat == "100" else f"Status {cstat}"
    el.append(Paragraph(
        f"<font size=7 color='#64748b'>Documento auxiliar da NFS-e ({autoriz}). "
        f"Consulte a validade pela chave de acesso no portal nacional "
        f"<b>www.nfse.gov.br</b>. Processado em {dt(dhproc)}.</font>", pSmall))

    doc.build(el)
    return buf.getvalue()
