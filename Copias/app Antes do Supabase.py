from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "folha10_simples_chave_local_2026")
app.permanent_session_lifetime = timedelta(days=30)

# =========================
# CONFIG LOGIN
# =========================
TEMPO_BLOQUEIO_MINUTOS = 3
MAX_TENTATIVAS_LOGIN = 3

# =========================
# BANCO
# =========================
def conectar():
    conn = sqlite3.connect("clientes.db")
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        cpf TEXT PRIMARY KEY,
        nome TEXT,
        celular TEXT,
        email TEXT,
        senha TEXT,
        tentativas_login INTEGER DEFAULT 0,
        bloqueado_ate TEXT,
        datahora TEXT
    )
    """)

    conn.commit()
    conn.close()

def ajustar_tabela_clientes():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(clientes)")
    colunas = [row["name"] for row in cur.fetchall()]

    if "senha" not in colunas:
        cur.execute("ALTER TABLE clientes ADD COLUMN senha TEXT")

    if "tentativas_login" not in colunas:
        cur.execute("ALTER TABLE clientes ADD COLUMN tentativas_login INTEGER DEFAULT 0")

    if "bloqueado_ate" not in colunas:
        cur.execute("ALTER TABLE clientes ADD COLUMN bloqueado_ate TEXT")

    conn.commit()
    conn.close()

criar_tabela()
ajustar_tabela_clientes()

# =========================
# CONFIG GERAL
# =========================
codigos_gerados = {}

EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE", "SEU_EMAIL@gmail.com")
EMAIL_SENHA_APP = os.environ.get("EMAIL_SENHA_APP", "SUA_SENHA_APP")

SMTP_SERVIDOR = os.environ.get("SMTP_SERVIDOR", "smtp.gmail.com")
SMTP_PORTA = int(os.environ.get("SMTP_PORTA", "587"))

ZAPI_INSTANCE = os.environ.get("ZAPI_INSTANCE", "3E0DA0C0399BB0821E57266509411D32")
ZAPI_TOKEN = os.environ.get("ZAPI_TOKEN", "32B4B3104968DD6C13F5D8F0")
ZAPI_CLIENT_TOKEN = os.environ.get("ZAPI_CLIENT_TOKEN", "Fb4455edcf75a45eaa7b58b1c7becb5a2S")

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

def parse_datahora(texto):
    if not texto:
        return None

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except:
            pass

    return None

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

def validar_cpf_cnpj(documento):
    documento = so_numeros(documento)

    if documento == "":
        return False, "CPF não informado", ""

    if len(documento) != 11:
        return False, "CPF deve ter 11 dígitos", ""

    if not validar_cpf(documento):
        return False, "CPF inválido", ""

    return True, "", "CPF"

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
        return False, "Celular deve iniciar com 9 após o DDD"

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

def validar_senha_6_digitos(senha):
    senha = (senha or "").strip()
    if not re.fullmatch(r"\d{6}", senha):
        return False, "Senha deve ter exatamente 6 dígitos"
    return True, ""

def validar_senha_confirmacao(senha, senha2):
    erros = {}

    ok_senha, msg_senha = validar_senha_6_digitos(senha)
    if not ok_senha:
        erros["senha"] = msg_senha

    if (senha or "").strip() != (senha2 or "").strip():
        erros["senha2"] = "Confirmação da senha não confere"

    return {
        "ok": len(erros) == 0,
        "erros": erros
    }

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
# LOGIN
# =========================
def cliente_por_cpf(cpf):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT cpf, nome, celular, email, senha, tentativas_login, bloqueado_ate, datahora
        FROM clientes
        WHERE cpf = ?
    """, (cpf,))
    row = cur.fetchone()
    conn.close()
    return row

def limpar_bloqueio_login(cpf):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE clientes
        SET tentativas_login = 0, bloqueado_ate = NULL
        WHERE cpf = ?
    """, (cpf,))
    conn.commit()
    conn.close()

def segundos_restantes_bloqueio(row_cliente):
    if row_cliente is None:
        return 0

    bloqueado_ate = parse_datahora(row_cliente["bloqueado_ate"])
    if bloqueado_ate is None:
        return 0

    delta = int((bloqueado_ate - datetime.now()).total_seconds())

    if delta <= 0:
        limpar_bloqueio_login(row_cliente["cpf"])
        return 0

    return delta

def cliente_bloqueado(row_cliente):
    segundos = segundos_restantes_bloqueio(row_cliente)
    return segundos > 0, segundos

def registrar_tentativa_login_invalida(cpf):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT tentativas_login
        FROM clientes
        WHERE cpf = ?
    """, (cpf,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return

    tentativas = row["tentativas_login"] or 0
    tentativas += 1

    bloqueado_ate = None
    if tentativas >= MAX_TENTATIVAS_LOGIN:
        bloqueado_ate = (datetime.now() + timedelta(minutes=TEMPO_BLOQUEIO_MINUTOS)).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        UPDATE clientes
        SET tentativas_login = ?, bloqueado_ate = ?
        WHERE cpf = ?
    """, (tentativas, bloqueado_ate, cpf))

    conn.commit()
    conn.close()

def efetuar_login(cpf, nome, manter):
    session.clear()
    session["cpf"] = cpf
    session["nome"] = nome
    session["logado"] = True
    session.permanent = bool(manter)

# =========================
# ROTAS DE TELA
# =========================
@app.route("/")
@app.route("/cadastro")
def cadastro():
    return render_template("Cadastro_Cliente.html")

@app.route("/login")
def login():
    return render_template("F10_Login.html")

@app.route("/painel")
def painel():
    if not session.get("logado"):
        return redirect(url_for("login"))

    nome = session.get("nome", "")

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Folha10 Simples - Painel</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background:#f4f6f8;
                margin:0;
                padding:40px;
            }}
            .box {{
                max-width:700px;
                margin:auto;
                background:#fff;
                padding:30px;
                border-radius:14px;
                box-shadow:0 10px 30px rgba(0,0,0,0.08);
            }}
            a {{
                color:#1d4ed8;
                text-decoration:none;
                font-weight:bold;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>Folha10 Simples</h2>
            <p>Login realizado com sucesso.</p>
            <p>Bem-vindo: <strong>{nome}</strong></p>
            <p><a href="/logout">Sair</a></p>
        </div>
    </body>
    </html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
# ROTAS CADASTRO
# =========================
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
    nome = (data.get("nome") or "").strip().lower()
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

@app.route("/validar_codigo_cadastro", methods=["POST"])
def validar_codigo_cadastro():
    data = request.get_json() or {}

    documento = so_numeros(data.get("cpf"))
    codigo = (data.get("codigo") or "").strip()

    if documento == "":
        return jsonify({"ok": False, "campo": "cpf", "msg": "CPF não informado"})

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

    return jsonify({
        "ok": True,
        "msg": "Código validado com sucesso"
    })

@app.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.get_json() or {}

    documento = so_numeros(data.get("cpf"))
    codigo = (data.get("codigo") or "").strip()
    senha = (data.get("senha") or "").strip()
    senha2 = (data.get("senha2") or "").strip()

    if documento == "":
        return jsonify({"ok": False, "campo": "cpf", "msg": "CPF não informado"})

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

    resultado_senha = validar_senha_confirmacao(senha, senha2)
    if not resultado_senha["ok"]:
        return jsonify({
            "ok": False,
            "msg": "Senha inválida",
            "erros": resultado_senha["erros"]
        })

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO clientes
    (cpf, nome, celular, email, senha, tentativas_login, bloqueado_ate, datahora)
    VALUES (?, ?, ?, ?, ?, 0, NULL, datetime('now'))
    """, (
        documento,
        registro["nome"],
        registro["celular"],
        registro["email"],
        senha
    ))

    conn.commit()
    conn.close()

    del codigos_gerados[documento]

    return jsonify({
        "ok": True,
        "msg": "Cadastro realizado com sucesso",
        "redirect_login": "/login"
    })

# =========================
# ROTAS LOGIN
# =========================
@app.route("/fazer_login", methods=["POST"])
def fazer_login():
    data = request.get_json() or {}

    cpf = so_numeros(data.get("cpf"))
    senha = (data.get("senha") or "").strip()
    manter = bool(data.get("manter"))

    if not validar_cpf(cpf):
        return jsonify({"ok": False, "msg": "Dados inválidos"})

    ok_senha, _ = validar_senha_6_digitos(senha)
    if not ok_senha:
        return jsonify({"ok": False, "msg": "Dados inválidos"})

    row = cliente_por_cpf(cpf)

    if row is None:
        return jsonify({"ok": False, "msg": "Dados inválidos"})

    bloqueado, segundos = cliente_bloqueado(row)
    if bloqueado:
        return jsonify({
            "ok": False,
            "bloqueado": True,
            "segundos_restantes": segundos,
            "msg": "Login bloqueado temporariamente."
        })

    senha_banco = (row["senha"] or "").strip()

    if senha_banco != senha:
        registrar_tentativa_login_invalida(cpf)

        row_atualizado = cliente_por_cpf(cpf)
        bloqueado_agora, segundos = cliente_bloqueado(row_atualizado)

        if bloqueado_agora:
            return jsonify({
                "ok": False,
                "bloqueado": True,
                "segundos_restantes": segundos,
                "msg": "Login bloqueado temporariamente."
            })

        return jsonify({"ok": False, "msg": "Dados inválidos"})

    limpar_bloqueio_login(cpf)
    efetuar_login(cpf, row["nome"], manter)

    return jsonify({
        "ok": True,
        "msg": "Login realizado com sucesso",
        "redirect": "/painel"
    })

# =========================
# ROTA AUXILIAR
# =========================
@app.route("/dados_cliente/<cpf>")
def dados_cliente(cpf):
    documento = so_numeros(cpf)
    row = cliente_por_cpf(documento)

    if row is None:
        return jsonify({"ok": False, "msg": "Cliente não encontrado"})

    return jsonify({
        "ok": True,
        "cpf": row["cpf"],
        "nome": row["nome"],
        "celular": row["celular"],
        "email": row["email"],
        "datahora": row["datahora"]
    })

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta, debug=True)