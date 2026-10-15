# -*- coding: utf-8 -*-
"""Roda o Folha10 AQUI na máquina, ligado ao Supabase real.

    python rodar_local.py        ->  http://127.0.0.1:5000

Por que não basta "python app.py": o Avast desta máquina intercepta o TLS e o
Python não confia no certificado dele. Sem isso toda consulta ao banco quebra
— e o login diz "CPF não cadastrado" (cliente_ja_cadastrado devolve False
quando a consulta falha). Este script junta as raízes do Windows num pacote
temporário e aponta o Python para ele — só neste processo, sem mudar nada na
máquina. No Render não precisa. Mesmo esquema do C:\\NF10\\rodar_local.py.
"""
import os
import ssl
import tempfile

import certifi

caminho = os.path.join(tempfile.gettempdir(), "folha10_ca.pem")
with open(caminho, "w", encoding="utf-8") as f:
    f.write(open(certifi.where(), encoding="utf-8").read())
    for loja in ("ROOT", "CA"):
        for der, enc, _ in ssl.enum_certificates(loja):
            if enc == "x509_asn":
                f.write(ssl.DER_cert_to_PEM_cert(der))
os.environ["SSL_CERT_FILE"] = caminho
os.environ["REQUESTS_CA_BUNDLE"] = caminho

import app  # noqa: E402

if __name__ == "__main__":
    # Igual ao "python app.py" (debug=True), mas sem o recarregador: ele
    # reinicia o processo e o pacote de certificados ja' esta' no ambiente,
    # entao funcionaria - porem duplica a carga do app.py (78 mil linhas).
    app.app.run(port=int(os.environ.get("PORT", 5000)), debug=True, use_reloader=False)
