from flask import Flask, render_template, request, jsonify
import re
import random
import smtplib
import requests
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# =========================
# BANCO
# =========================
def conectar():
    return sqlite3.connect("clientes.db")

def criar_tabela():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        cpf TEXT PRIMARY KEY,
        nome TEXT,
        celular TEXT,
        email TEXT,
        datahora TEXT
    )
    """)

    conn.commit()
    conn.close()

criar_tabela()

# =========================
# CONFIG
# =========================
codigos_gerados = {}

EMAIL_REMETENTE = "SEU_EMAIL@gmail.com"
EMAIL_SENHA_APP = "SUA_SENHA_APP"

SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PORTA = 587

ZAPI_INSTANCE = "3E0DA0C0399BB0821E57266509411D32"
ZAPI_TOKEN = "32B4B3104968DD6C13F5D8F0"
ZAPI_CLIENT_TOKEN = "Fb4455edcf75a45eaa7b58b1c7becb5a2S"

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

# =========================
# FUNÇÕES
# =========================
def so_numeros(t):
    return re.sub(r"\D", "", t or "")

def normalizar_telefone(t):
    t = so_numeros(t)
    if not t.startswith("55"):
        t = "55" + t
    return t

def cliente_ja_cadastrado(cpf):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT cpf FROM clientes WHERE cpf = ?", (cpf,))
    row = cur.fetchone()

    conn.close()
    return row is not None

def codigo_expirado(datahora_geracao):
    return datetime.now() > datahora_geracao + timedelta(minutes=5)

# =========================
# EMAIL
# =========================
def enviar_email(destinatario, codigo, nome):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario
        msg["Subject"] = "Folha10 Simples - Código"

        corpo = f"""
Olá {nome},

Recebemos uma solicitação de cadastro no Folha10 Simples.

Para continuar, utilize o código de confirmação abaixo:

{codigo}

Se você não solicitou este código, ignore esta mensagem.

Equipe do Folha10 Simples
"""

        msg.attach(MIMEText(corpo, "plain"))

        servidor = smtplib.SMTP(SMTP_SERVIDOR, SMTP_PORTA)
        servidor.starttls()
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        servidor.send_message(msg)
        servidor.quit()

        return True, ""

    except Exception as e:
        return False, str(e)

# =========================
# WHATSAPP
# =========================
def enviar_whatsapp(destinatario, codigo, nome):
    try:
        telefone = normalizar_telefone(destinatario)

        mensagem = (
            f"Olá {nome},\n\n"
            f"Recebemos uma solicitação de cadastro no Folha10 Simples.\n\n"
            f"Para continuar, utilize o código de confirmação abaixo:\n\n"
            f"{codigo}\n\n"
            f"Se você não solicitou este código, ignore esta mensagem.\n\n"
            f"Equipe do Folha10 Simples"
        )

        headers = {
            "Client-Token": ZAPI_CLIENT_TOKEN,
            "Content-Type": "application/json"
        }

        payload = {
            "phone": telefone,
            "message": mensagem
        }

        r = requests.post(ZAPI_URL, headers=headers, json=payload)

        if r.status_code not in (200, 201):
            return False, r.text

        return True, ""

    except Exception as e:
        return False, str(e)

# =========================
# ROTAS
# =========================
@app.route("/")
@app.route("/cadastro")
def cadastro():
    return render_template("Cadastro_Cliente.html")


@app.route("/validar", methods=["POST"])
def validar():
    data = request.get_json()

    cpf = so_numeros(data.get("cpf"))
    nome = (data.get("nome") or "").strip().lower()
    celular = data.get("celular")
    email = (data.get("email") or "").strip()
    canal = data.get("canal")

    if cpf == "":
        return jsonify({"ok": False, "campo": "cpf", "msg": "CPF / CNPJ não informado"})

    # Impedir cadastro duplicado
    if cliente_ja_cadastrado(cpf):
        return jsonify({
            "ok": False,
            "campo": "cpf",
            "msg": "Este cliente já está cadastrado"
        })

    codigo = str(random.randint(100000, 999999))

    codigos_gerados[cpf] = {
        "codigo": codigo,
        "nome": nome,
        "celular": celular,
        "email": email,
        "gerado_em": datetime.now(),
        "canal": canal
    }

    if canal == "email":
        ok, erro = enviar_email(email, codigo, nome)
        if not ok:
            return jsonify({"ok": False, "msg": erro})

        return jsonify({
            "ok": True,
            "msg": "Código enviado por e-mail"
        })

    if canal == "whatsapp":
        ok, erro = enviar_whatsapp(celular, codigo, nome)
        if not ok:
            print("ERRO WHATS:", erro)
            return jsonify({"ok": False, "msg": "Erro WhatsApp"})

        return jsonify({
            "ok": True,
            "msg": "Código enviado por WhatsApp"
        })

    return jsonify({"ok": False, "msg": "Canal inválido"})


@app.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.get_json()

    cpf = so_numeros(data.get("cpf"))
    codigo = (data.get("codigo") or "").strip()

    registro = codigos_gerados.get(cpf)

    if not registro:
        return jsonify({"ok": False, "campo": "codigo", "msg": "Código não encontrado"})

    # Expiração em 5 minutos
    if codigo_expirado(registro["gerado_em"]):
        del codigos_gerados[cpf]
        return jsonify({
            "ok": False,
            "campo": "codigo",
            "msg": "Código expirado. Solicite um novo código"
        })

    if registro["codigo"] != codigo:
        return jsonify({"ok": False, "campo": "codigo", "msg": "Código incorreto"})

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO clientes
    (cpf, nome, celular, email, datahora)
    VALUES (?, ?, ?, ?, datetime('now'))
    """, (
        cpf,
        registro["nome"],
        registro["celular"],
        registro["email"]
    ))

    conn.commit()
    conn.close()

    # remove o código após uso
    del codigos_gerados[cpf]

    return jsonify({"ok": True, "msg": "Cadastro realizado com sucesso"})


if __name__ == "__main__":
    app.run(debug=True)