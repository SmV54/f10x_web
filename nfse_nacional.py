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
        # Ordem exigida pelo XSD (TCInfoPessoa): CNPJ/CPF → CAEPF → IM → xNome
        #                                        → end → fone → email
        if d.get("tom_im"):
            E(toma, "IM", so_digitos(d["tom_im"])[:15])
        E(toma, "xNome", _txt(d.get("tom_nome") or "TOMADOR"))
        # Endereço do tomador: enviado SEMPRE que o cadastro tem os dados completos.
        # (Antes só ia com ISS retido — obrigatório, senão E0237 — ou tomador CPF;
        # para CNPJ não-retido era omitido e o endereço não aparecia na NFS-e nem
        # no DANFSe.) O cMun vem do CEP (ViaCEP), então município e CEP são
        # coerentes entre si, o que evita a rejeição E0240.
        # xLgr, nro e xBairro são obrigatórios dentro de <end> (XSD TCEndereco):
        # sem qualquer um deles o grupo inteiro é omitido.
        _tem_end = all(d.get(k) for k in ("tom_lgr", "tom_nro", "tom_bairro", "tom_ibge", "tom_cep"))
        if _tem_end:
            end = E(toma, "end")
            endnac = E(end, "endNac")
            E(endnac, "cMun", so_digitos(d["tom_ibge"]).zfill(7))
            E(endnac, "CEP", so_digitos(d["tom_cep"]).zfill(8))
            E(end, "xLgr", _txt(d["tom_lgr"]))
            E(end, "nro", _txt(d["tom_nro"]))
            if d.get("tom_cpl"):
                E(end, "xCpl", _txt(d["tom_cpl"]))
            E(end, "xBairro", _txt(d["tom_bairro"]))
        _fone = so_digitos(d.get("tom_fone"))
        if 6 <= len(_fone) <= 20:                 # TSTelefone: [0-9]{6,20}
            E(toma, "fone", _fone)
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


def _fmt_fone(v):
    """(81) 3117-7150 / (81) 91234-5678. Devolve como veio se não for 10/11 díg."""
    d = so_digitos(v)
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    return str(v or "")


def _fmt_chave(c):
    d = re.sub(r"\D", "", str(c or ""))
    return " ".join(d[i:i+4] for i in range(0, len(d), 4))


def gerar_danfse_pdf(nfse_xml_str, chave="", tom_mun="", tom_end=None,
                     tom_im="", tom_fone=""):
    """Gera o DANFSE (PDF auxiliar) a partir do XML da NFS-e. Retorna bytes do PDF.

    tom_mun: "CIDADE - UF" do tomador (o XML só traz o código IBGE do município).
             Em branco, o quadro do tomador mostra o próprio código.
    tom_end: endereço do tomador vindo do CADASTRO, usado SÓ quando o XML não tem
             o grupo <end> (notas emitidas antes de o endereço passar a ser enviado
             sempre). Dict com lgr/nro/cpl/bairro/cep. É o mesmo que o portal
             nacional faz no DANFSe dele: completa o tomador pelo CNPJ.
    tom_im / tom_fone: inscrição municipal e telefone do tomador vindos do
             cadastro (a TabCLI_NF não tem esses campos; hoje é regra fixa por
             cliente no app.py). Prevalecem sobre o que está no XML, para o
             mesmo cliente sair igual nas notas novas e nas antigas."""
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
    t_cmun = g(f"{dps}/{{}}toma/{{}}end/{{}}endNac/{{}}cMun")
    # Nota antiga, sem <end> no XML: completa pelo cadastro (ver docstring).
    if not t_lgr and tom_end:
        t_lgr = tom_end.get("lgr") or ""
        t_nro = tom_end.get("nro") or ""
        t_cpl = tom_end.get("cpl") or ""
        t_bai = tom_end.get("bairro") or ""
        t_cep = t_cep or tom_end.get("cep") or ""
    t_mail = g(f"{dps}/{{}}toma/{{}}email")
    desc   = g(f"{dps}/{{}}serv/{{}}cServ/{{}}xDescServ")
    ctribnac = g(f"{dps}/{{}}serv/{{}}cServ/{{}}cTribNac")
    # OBS: <valores> fica sob infDPS (irmão de <serv>), não dentro de <serv>.
    vserv  = g(f"{dps}/{{}}valores/{{}}vServPrest/{{}}vServ")
    vliq   = g(f"{inf}/{{}}valores/{{}}vLiq") or vserv
    ret    = g(f"{dps}/{{}}valores/{{}}trib/{{}}tribMun/{{}}tpRetISSQN")
    paliq  = g(f"{dps}/{{}}valores/{{}}trib/{{}}tribMun/{{}}pAliq")
    ptribsn = g(f"{dps}/{{}}valores/{{}}trib/{{}}totTrib/{{}}pTotTribSN")

    # ISSQN apurado a partir da alíquota informada no DPS (sem deduções → BC = vServ).
    def _num(s):
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return 0.0
    _bc_iss  = _num(vserv)
    _paliq_f = _num(paliq)
    _iss_val = round(_bc_iss * _paliq_f / 100.0, 2)
    _tem_aliq = bool(paliq) and _paliq_f > 0
    _aliq_txt = (f"{_paliq_f:.2f}".replace(".", ",") + "%") if _tem_aliq else "-"
    _bc_txt   = _fmt_brl(_bc_iss) if _tem_aliq else "-"
    _iss_txt  = _fmt_brl(_iss_val) if _tem_aliq else "-"
    # ISS retido (tpRetISSQN=2 tomador, 3 intermediário) → valor destacado como retido.
    _iss_ret_txt = _fmt_brl(_iss_val) if (_tem_aliq and str(ret) in ("2", "3")) else "-"

    def dt(s):
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]} {s[11:16]}" if len(s) >= 16 else s
    def comp(s):
        return f"{s[5:7]}/{s[0:4]}" if len(s) >= 7 else s

    # ── campos adicionais para o layout oficial DANFSe v1.0 ──
    ndps     = g(f"{dps}/{{}}nDPS")
    serie    = g(f"{dps}/{{}}serie")
    dhemidps = g(f"{dps}/{{}}dhEmi")
    e_fone   = g(f"{inf}/{{}}emit/{{}}fone")
    ctribmun = g(f"{dps}/{{}}serv/{{}}cServ/{{}}cTribMun")
    xtribmun = g(f"{inf}/{{}}xTribMun") or xtrib
    cnbs     = g(f"{dps}/{{}}serv/{{}}cServ/{{}}cNBS")
    loc_prest = g(f"{inf}/{{}}xLocPrestacao") or loc_emi
    t_im     = tom_im or g(f"{dps}/{{}}toma/{{}}IM")
    t_fone   = tom_fone or g(f"{dps}/{{}}toma/{{}}fone")
    opsimp   = g(f"{dps}/{{}}prest/{{}}regTrib/{{}}opSimpNac")
    regapsn  = g(f"{dps}/{{}}prest/{{}}regTrib/{{}}regApTribSN")
    regesp   = g(f"{dps}/{{}}prest/{{}}regTrib/{{}}regEspTrib")
    tribissqn = g(f"{dps}/{{}}valores/{{}}trib/{{}}tribMun/{{}}tribISSQN")

    from xml.sax.saxutils import escape as _xesc
    def esc(x):
        return _xesc(str(x if x not in (None, "") else "-"))
    def dtsec(s):    # data + hora com segundos
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]} {s[11:19]}" if len(s) >= 19 else dt(s)
    def data(s):     # só data dd/mm/aaaa
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}" if len(s) >= 10 else s
    def ctrib(c):    # 010301 -> 01.03.01
        c = re.sub(r"\D", "", c or "")
        return ".".join([c[0:2], c[2:4], c[4:6]]) if len(c) >= 6 else c

    OPSIMP = {"1": "Não Optante",
              "2": "Optante - Microempreendedor Individual (MEI)",
              "3": "Optante - Microempresa ou Empresa de Pequeno Porte (ME/EPP)"}
    REGAP  = {"1": "Regime de apuração dos tributos federais e municipal pelo Simples Nacional",
              "2": "Regime de apuração dos tributos federais pelo SN e ISSQN por fora do SN",
              "3": "Emitente da NFS-e não optante pelo Simples Nacional"}
    REGESP = {"0": "Nenhum", "1": "Ato Cooperado", "2": "Estimativa",
              "3": "Microempresa Municipal", "4": "Notário ou Registrador",
              "5": "Profissional Autônomo", "6": "Sociedade de Profissionais"}
    TRIBISS = {"1": "Operação Tributável", "2": "Exportação de Serviço",
               "3": "Não Incidência", "4": "Imunidade",
               "5": "Exigibilidade Suspensa por Decisão Judicial",
               "6": "Exigibilidade Suspensa por Processo Administrativo"}
    RETISS = {"1": "Não Retido", "2": "Retido pelo Tomador", "3": "Retido pelo Intermediário"}

    ss = getSampleStyleSheet()
    pFld  = ParagraphStyle('fld', parent=ss['Normal'], fontSize=7.5, leading=8.5)
    pSec  = ParagraphStyle('sec', parent=ss['Normal'], fontSize=8.5, fontName='Helvetica-Bold', leading=10)
    pSecC = ParagraphStyle('secc', parent=pSec, alignment=1)
    pTit  = ParagraphStyle('tit', parent=ss['Normal'], fontSize=11, fontName='Helvetica-Bold', alignment=1, leading=13)
    pSub  = ParagraphStyle('sub', parent=ss['Normal'], fontSize=8, alignment=1, leading=10)
    pOrg  = ParagraphStyle('org', parent=ss['Normal'], fontSize=7.5, leading=9, alignment=2)
    pLogo = ParagraphStyle('logo', parent=ss['Normal'], fontSize=22, fontName='Helvetica-Bold', leading=22)
    pLogoSub = ParagraphStyle('logosub', parent=ss['Normal'], fontSize=5.6, leading=6.6, textColor=colors.HexColor('#0b7d3e'))
    pQR   = ParagraphStyle('qr', parent=ss['Normal'], fontSize=5.8, leading=6.8, alignment=1, textColor=colors.HexColor('#333333'))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=8*mm, bottomMargin=8*mm, title=f"NFSe {numero}")
    el = []
    W = 182 * mm
    LINE = colors.black

    def fld(label, value):
        if label:
            return Paragraph(f"<font size=6.5 color='#444444'><b>{esc(label)}</b></font><br/>"
                             f"<font size=8>{esc(value)}</font>", pFld)
        return Paragraph(f"<font size=8>{esc(value)}</font>", pFld)

    def secbar(txt, centered=False):
        t = Table([[Paragraph(esc(txt), pSecC if centered else pSec)]], colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#d9d9d9')),
            ('BOX',(0,0),(-1,-1),0.5,LINE),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),1.5)]))
        return t

    def block(titulo, rows, centered=False):
        el.append(secbar(titulo, centered))
        for r in rows:
            cells = [fld(l, v) for (l, v) in r]
            n = len(cells)
            t = Table([cells], colWidths=[W / n] * n)
            t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                ('BOX',(0,0),(-1,-1),0.5,LINE),
                ('INNERGRID',(0,0),(-1,-1),0.3,colors.HexColor('#bfbfbf')),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('TOPPADDING',(0,0),(-1,-1),1.6),('BOTTOMPADDING',(0,0),(-1,-1),1.6)]))
            el.append(t)

    # QR Code — consulta pública oficial da NFS-e pela chave (gov.br)
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    chave_d = re.sub(r"\D", "", str(chave or ""))
    url_consulta = f"https://www.nfse.gov.br/consultapublica?tpc=1&chNFSe={chave_d}"
    _qr = QrCodeWidget(url_consulta, barLevel='M')
    _b = _qr.getBounds(); _qw = _b[2] - _b[0]; _qh = _b[3] - _b[1]
    _SZ = 24 * mm
    qr_draw = Drawing(_SZ, _SZ, transform=[_SZ / _qw, 0, 0, _SZ / _qh, 0, 0])
    qr_draw.add(_qr)

    # ── Cabeçalho: logo (texto) · título · órgão emissor ──
    logo_cell = Table([[Paragraph("NFS<font color='#0b7d3e'>e</font>", pLogo)],
                       [Paragraph("Nota Fiscal de<br/>Serviço eletrônica", pLogoSub)]],
                      colWidths=[38*mm])
    logo_cell.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    tit_cell = Table([[Paragraph("DANFSe v1.0", pTit)],
                      [Paragraph("Documento Auxiliar da NFS-e", pSub)]], colWidths=[100*mm])
    _mail_org = "faleconosco@recife.pe.gov.br" if "recife" in loc_emi.lower() else ""
    org_cell = Paragraph(f"<b>Prefeitura do {esc(loc_emi)}</b><br/>Secretaria de Finanças"
                         + (f"<br/>{_mail_org}" if _mail_org else ""), pOrg)
    hdr = Table([[logo_cell, tit_cell, org_cell]], colWidths=[40*mm, 100*mm, 42*mm])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('BOX',(0,0),(-1,-1),0.8,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    el.append(hdr)

    # ── Identificação: chave + números (esq.) · QR (dir.) ──
    idgrid = Table([
        [fld("Número da NFS-e", numero), fld("Competência da NFS-e", data(dcompet)),
         fld("Data e Hora da emissão da NFS-e", dtsec(dhproc))],
        [fld("Número da DPS", ndps), fld("Série da DPS", serie),
         fld("Data e Hora da emissão da DPS", dtsec(dhemidps))],
    ], colWidths=[34*mm, 40*mm, 62*mm])
    idgrid.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    left_col = Table([[Paragraph("<font size=6.5 color='#444444'><b>Chave de Acesso da NFS-e</b></font><br/>"
                                 f"<font face='Courier' size=8.5>{esc(chave_d)}</font>", pFld)],
                      [idgrid]], colWidths=[136*mm])
    left_col.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(0,0),3),('BOTTOMPADDING',(0,0),(0,0),3),
        ('LINEBELOW',(0,0),(0,0),0.3,colors.HexColor('#bfbfbf')),
        ('TOPPADDING',(0,1),(0,1),0),('BOTTOMPADDING',(0,1),(0,1),0)]))
    qr_col = Table([[qr_draw],
                    [Paragraph("A autenticidade desta NFS-e pode ser verificada pela leitura deste "
                               "código QR ou pela consulta da chave de acesso no portal nacional da NFS-e", pQR)]],
                   colWidths=[46*mm])
    qr_col.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(0,0),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    ident = Table([[left_col, qr_col]], colWidths=[136*mm, 46*mm])
    ident.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BOX',(0,0),(-1,-1),0.8,LINE),('LINEBEFORE',(1,0),(1,0),0.5,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    el.append(ident)

    # ── Emitente / Prestador ──
    e_end = f"{e_lgr}, {e_nro}" + (f", {e_cpl}" if e_cpl else "") + (f", {e_bai}" if e_bai else "")
    block("EMITENTE DA NFS-e — Prestador do Serviço", [
        [("CNPJ / CPF / NIF", _fmt_doc(e_cnpj)), ("Inscrição Municipal", e_im),
         ("Telefone", _fmt_fone(e_fone) if e_fone else "-")],
        [("Nome / Nome Empresarial", e_nome)],
        [("E-mail", e_mail)],
        [("Endereço", e_end)],
        [("Município", f"{loc_emi} - {e_uf}"), ("CEP", _fmt_cep(e_cep))],
        [("Simples Nacional na Data de Competência", OPSIMP.get(opsimp, "-")),
         ("Regime de Apuração Tributária pelo SN", REGAP.get(regapsn, "-"))],
    ])

    # ── Tomador ──
    t_end = (f"{t_lgr}, {t_nro}" + (f", {t_cpl}" if t_cpl else "") + (f", {t_bai}" if t_bai else "")) \
            if t_lgr else "-"
    block("TOMADOR DO SERVIÇO", [
        [("CNPJ / CPF / NIF", _fmt_doc(t_doc)), ("Inscrição Municipal", t_im or "-"),
         ("Telefone", _fmt_fone(t_fone) if t_fone else "-")],
        [("Nome / Nome Empresarial", t_nome or "-")],
        [("E-mail", t_mail or "-")],
        [("Endereço", t_end)],
        [("Município", (tom_mun or t_cmun or "-")), ("CEP", _fmt_cep(t_cep) if t_cep else "-")],
    ])

    # ── Intermediário (ausente) ──
    el.append(secbar("INTERMEDIÁRIO DO SERVIÇO NÃO IDENTIFICADO NA NFS-e", centered=True))

    # ── Serviço prestado ──
    block("SERVIÇO PRESTADO", [
        [("Código de Tributação Nacional", f"{ctrib(ctribnac)} - {xtrib}"),
         ("Código de Tributação Municipal", f"{ctribmun} - {xtribmun}"),
         ("Local da Prestação", f"{loc_prest} - {e_uf}"),
         ("País da Prestação", "-")],
        [("Descrição do Serviço", desc)],
    ])

    # ── Tributação Municipal ──
    block("TRIBUTAÇÃO MUNICIPAL", [
        [("Tributação do ISSQN", TRIBISS.get(tribissqn, "-")),
         ("País Resultado da Prestação do Serviço", "-"),
         ("Município de Incidência do ISSQN", f"{loc_inc} - {e_uf}" if loc_inc else "-"),
         ("Regime Especial de Tributação", REGESP.get(regesp, "-"))],
        [("Tipo de Imunidade", "-"), ("Suspensão da Exigibilidade do ISSQN", "Não"),
         ("Número Processo Suspensão", "-"), ("Benefício Municipal", "-")],
        [("Valor do Serviço", _fmt_brl(vserv)), ("Desconto Incondicionado", "-"),
         ("Total Deduções/Reduções", "-"), ("Cálculo do BM", "-")],
        [("BC ISSQN", _bc_txt), ("Alíquota Aplicada", _aliq_txt),
         ("Retenção do ISSQN", RETISS.get(ret, "-")), ("ISSQN Apurado", _iss_txt)],
    ])

    # ── Tributação Federal ──
    block("TRIBUTAÇÃO FEDERAL", [
        [("IRRF", "-"), ("Contribuição Previdenciária - Retida", "-"),
         ("Contribuições Sociais - Retidas", "-"), ("Descrição Contrib. Sociais - Retidas", "-")],
        [("PIS - Débito Apuração Própria", "-"), ("COFINS - Débito Apuração Própria", "-")],
    ])

    # ── Valor Total da NFS-e ──
    block("VALOR TOTAL DA NFS-E", [
        [("Valor do Serviço", _fmt_brl(vserv)), ("Desconto Condicionado", "-"),
         ("Desconto Incondicionado", "-"), ("ISSQN Retido", _iss_ret_txt)],
        [("Total das Retenções Federais", "-"), ("PIS/COFINS - Débito Apur. Própria", "-"),
         ("Valor Líquido da NFS-e", _fmt_brl(vliq))],
    ])

    # ── Totais aproximados dos tributos ──
    block("TOTAIS APROXIMADOS DOS TRIBUTOS", [
        [("Federais", "-"), ("Estaduais", "-"), ("Municipais", "-")],
    ])

    # ── Informações complementares ──
    block("INFORMAÇÕES COMPLEMENTARES", [
        [("", f"NBS: {cnbs}" if cnbs else "-")],
    ])

    doc.build(el)
    return buf.getvalue()
