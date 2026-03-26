from flask import Flask, render_template, request, jsonify
import re
import os
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
# FUNÇÕES BÁSICAS
# =========================
def so_numeros(t):
    return re.sub(r"\D", "", t or "")

def normalizar_telefone(t):
    t = so_numeros(t)
    if not t.startswith("55"):
        t = "55" + t
    return t

def cliente_ja_cadastrado(documento):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT cpf FROM clientes WHERE cpf = ?", (documento,))
    row = cur.fetchone()

    conn.close()
    return row is not None

def codigo_expirado(datahora_geracao):
    return datetime.now() > datahora_geracao + timedelta(minutes=5)

# =========================
# VALIDAÇÕES
# =========================
def validar_cpf(cpf):
    cpf = so_numeros(cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False

    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False

    return True

def validar_cnpj(cnpj):
    cnpj = so_numeros(cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma = 0
    for i in range(12):
        soma += int(cnpj[i]) * pesos1[i]
    resto = soma % 11
    dig1 = 0 if resto < 2 else 11 - resto
    if dig1 != int(cnpj[12]):
        return False

    soma = 0
    for i in range(13):
        soma += int(cnpj[i]) * pesos2[i]
    resto = soma % 11
    dig2 = 0 if resto < 2 else 11 - resto
    if dig2 != int(cnpj[13]):
        return False

    return True

def validar_cpf_cnpj(documento):
    documento = so_numeros(documento)

    if documento == "":
        return False, "CPF / CNPJ não informado", ""

    if len(documento) == 11:
        if not validar_cpf(documento):
            return False, "CPF inválido", ""
        return True, "", "CPF"

    if len(documento) == 14:
        if not validar_cnpj(documento):
            return False, "CNPJ inválido", ""
        return True, "", "CNPJ"

    return False, "CPF deve ter 11 dígitos ou CNPJ 14 dígitos", ""

def validar_nome(nome):
    nome_original = (nome or "").strip()
    nome_limpo = re.sub(r"[^A-Za-zÀ-ÿ\s]", "", nome_original)
    nome_sem_espacos = re.sub(r"\s", "", nome_limpo)

    if nome_original == "":
        return False, "Nome não informado"

    if nome_limpo != nome_original:
        return False, "Nome deve conter apenas letras e espaços"

    if len(nome_sem_espacos) < 10:
        return False, "Nome deve ter no mínimo 10 letras"

    return True, ""

def validar_celular(celular):
    numero = so_numeros(celular)

    if numero == "":
        return False, "Celular não informado"

    # Aceita:
    # 11 dígitos = DDD + 9 dígitos
    # 13 dígitos = 55 + DDD + 9 dígitos
    if len(numero) == 13 and numero.startswith("55"):
        numero = numero[2:]

    if len(numero) != 11:
        return False, "Celular deve ter DDD + 9 dígitos"

    ddd = numero[:2]
    nono = numero[2]
    restante = numero[3:]

    if not ddd.isdigit():
        return False, "DDD inválido"

    if int(ddd) < 11 or int(ddd) > 99:
        return False, "DDD inválido"

    if nono != "9":
        return False, "Celular deve ter 9 dígitos após o DDD, iniciando com 9"

    if not restante.isdigit():
        return False, "Celular inválido"

    return True, ""

def validar_email(email):
    email = (email or "").strip()

    if email == "":
        return False, "E-mail não informado"

    padrao = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(padrao, email):
        return False, "E-mail inválido"

    return True, ""

def validar_canal(canal):
    canal = (canal or "").strip().lower()
    if canal not in ("email", "whatsapp"):
        return False, "Canal inválido"
    return True, ""

def validar_tudo(documento, nome, celular, email, canal, verificar_duplicidade=True):
    erros = {}

    ok_doc, msg_doc, tipo_doc = validar_cpf_cnpj(documento)
    if not ok_doc:
        erros["cpf"] = msg_doc

    ok_nome, msg_nome = validar_nome(nome)
    if not ok_nome:
        erros["nome"] = msg_nome

    ok_cel, msg_cel = validar_celular(celular)
    if not ok_cel:
        erros["celular"] = msg_cel

    ok_email, msg_email = validar_email(email)
    if not ok_email:
        erros["email"] = msg_email

    ok_canal, msg_canal = validar_canal(canal)
    if not ok_canal:
        erros["canal"] = msg_canal

    documento_limpo = so_numeros(documento)
    if verificar_duplicidade and ok_doc:
        if cliente_ja_cadastrado(documento_limpo):
            erros["cpf"] = "Este cliente já está cadastrado"

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "tipo_documento": tipo_doc,
        "documento_limpo": documento_limpo
    }

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

        r = requests.post(ZAPI_URL, headers=headers, json=payload, timeout=30)

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

@app.route("/prevalidar", methods=["POST"])
def prevalidar():
    data = request.get_json() or {}

    documento = data.get("cpf")
    nome = data.get("nome")
    celular = data.get("celular")
    email = data.get("email")
    canal = data.get("canal")

    resultado = validar_tudo(
        documento=documento,
        nome=nome,
        celular=celular,
        email=email,
        canal=canal,
        verificar_duplicidade=True
    )

    return jsonify({
        "ok": resultado["ok"],
        "erros": resultado["erros"],
        "tipo_documento": resultado["tipo_documento"],
        "habilita_enviar_codigo": resultado["ok"]
    })

@app.route("/validar", methods=["POST"])
def validar():
    data = request.get_json() or {}

    documento = data.get("cpf")
    nome = (data.get("nome") or "").strip()
    celular = (data.get("celular") or "").strip()
    email = (data.get("email") or "").strip()
    canal = (data.get("canal") or "").strip().lower()

    resultado = validar_tudo(
        documento=documento,
        nome=nome,
        celular=celular,
        email=email,
        canal=canal,
        verificar_duplicidade=True
    )

    if not resultado["ok"]:
        return jsonify({
            "ok": False,
            "msg": "Existem campos inválidos",
            "erros": resultado["erros"]
        })

    documento_limpo = resultado["documento_limpo"]
    codigo = str(random.randint(100000, 999999))

    codigos_gerados[documento_limpo] = {
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
            return jsonify({"ok": False, "msg": f"Erro ao enviar e-mail: {erro}"})

        return jsonify({
            "ok": True,
            "msg": "Código enviado por e-mail"
        })

    if canal == "whatsapp":
        ok, erro = enviar_whatsapp(celular, codigo, nome)
        if not ok:
            return jsonify({"ok": False, "msg": f"Erro ao enviar WhatsApp: {erro}"})

        return jsonify({
            "ok": True,
            "msg": "Código enviado por WhatsApp"
        })

    return jsonify({"ok": False, "msg": "Canal inválido"})

@app.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.get_json() or {}

    documento = so_numeros(data.get("cpf"))
    codigo = (data.get("codigo") or "").strip()

    if documento == "":
        return jsonify({"ok": False, "campo": "cpf", "msg": "CPF / CNPJ não informado"})

    if codigo == "":
        return jsonify({"ok": False, "campo": "codigo", "msg": "Código não informado"})

    registro = codigos_gerados.get(documento)

    if not registro:
        return jsonify({"ok": False, "campo": "codigo", "msg": "Código não encontrado"})

    if codigo_expirado(registro["gerado_em"]):
        del codigos_gerados[documento]
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
        documento,
        registro["nome"],
        registro["celular"],
        registro["email"]
    ))

    conn.commit()
    conn.close()

    del codigos_gerados[documento]

    return jsonify({"ok": True, "msg": "Cadastro realizado com sucesso"})

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta, debug=True)