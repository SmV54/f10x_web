from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
import random

from database.conexao import conectar
from services.validacoes import (
    validar_cpf_cnpj,
    validar_nome,
    validar_celular,
    validar_email_minimo,
    somente_numeros
)

cliente_bp = Blueprint("cliente", __name__)

meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# armazenamento simples em memória para teste
# depois vamos trocar por sessão ou tabela temporária
codigo_teste_atual = ""
codigo_teste_expira = None


@cliente_bp.route("/")
def home():
    hoje = datetime.now()
    mes = meses[hoje.month - 1]
    ano = hoje.year

    return render_template(
        "cadastro_cliente.html",
        mes_atual=mes,
        ano_atual=ano,
        mensagem="",
        mensagem_tipo="",
        codigo_teste="",
        cpf_cnpj="",
        nome="",
        celular="",
        email="",
        qtd_empresas="1",
        qtd_funcionarios="10"
    )


@cliente_bp.route("/cadastro-cliente", methods=["GET", "POST"])
def cadastro_cliente():
    global codigo_teste_atual, codigo_teste_expira

    hoje = datetime.now()
    mes = meses[hoje.month - 1]
    ano = hoje.year

    mensagem = ""
    mensagem_tipo = ""
    codigo_teste = ""

    cpf_cnpj = ""
    nome = ""
    celular = ""
    email = ""
    qtd_empresas = "1"
    qtd_funcionarios = "10"

    if request.method == "POST":
        acao = request.form.get("acao", "")

        cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
        nome = request.form.get("nome", "").strip()
        celular = request.form.get("celular", "").strip()
        email = request.form.get("email", "").strip().lower()
        qtd_empresas = request.form.get("qtd_empresas", "1").strip()
        qtd_funcionarios = request.form.get("qtd_funcionarios", "10").strip()

        erros = []

        if not validar_cpf_cnpj(cpf_cnpj):
            erros.append("CPF/CNPJ inválido.")

        if not validar_nome(nome):
            erros.append("Nome deve ter no mínimo 10 caracteres e conter apenas letras e espaços.")

        if not validar_celular(celular):
            erros.append("Celular inválido. Informe DDD + número com 10 ou 11 dígitos.")

        if not validar_email_minimo(email):
            erros.append("Email inválido.")

        try:
            if int(qtd_empresas) < 1:
                erros.append("Quantidade de empresas deve ser maior que zero.")
        except ValueError:
            erros.append("Quantidade de empresas inválida.")

        try:
            if int(qtd_funcionarios) < 1:
                erros.append("Quantidade de funcionários deve ser maior que zero.")
        except ValueError:
            erros.append("Quantidade de funcionários inválida.")

        if acao == "enviar_codigo":
            if erros:
                mensagem = " ".join(erros)
                mensagem_tipo = "erro"
            else:
                codigo_teste_atual = str(random.randint(100000, 999999))
                codigo_teste_expira = datetime.now() + timedelta(minutes=10)

                mensagem = "Código gerado com sucesso em modo teste."
                mensagem_tipo = "sucesso"
                codigo_teste = codigo_teste_atual

        elif acao == "criar_cadastro":
            if erros:
                mensagem = " ".join(erros)
                mensagem_tipo = "erro"
            else:
                datalimite = f"{hoje.year}{str(hoje.month).zfill(2)}"

                try:
                    conn = conectar()
                    cur = conn.cursor()

                    cur.execute(
                        "select 1 from public.tab_cliente where cpf_cnpj = %s",
                        (somente_numeros(cpf_cnpj),)
                    )

                    existe = cur.fetchone()

                    if existe:
                        mensagem = "CPF/CNPJ já cadastrado."
                        mensagem_tipo = "erro"
                    else:
                        cur.execute(
                            """
                            insert into public.tab_cliente
                            (
                                cpf_cnpj,
                                nome,
                                celular,
                                email,
                                qtdempresas,
                                qtdfuncionarios,
                                datalimite
                            )
                            values (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                somente_numeros(cpf_cnpj),
                                nome,
                                somente_numeros(celular),
                                email,
                                int(qtd_empresas),
                                int(qtd_funcionarios),
                                datalimite
                            )
                        )

                        conn.commit()

                        mensagem = "Cadastro realizado com sucesso."
                        mensagem_tipo = "sucesso"

                        cpf_cnpj = ""
                        nome = ""
                        celular = ""
                        email = ""
                        qtd_empresas = "1"
                        qtd_funcionarios = "10"

                    cur.close()
                    conn.close()

                except Exception as e:
                    mensagem = f"Erro ao gravar: {str(e)}"
                    mensagem_tipo = "erro"

    return render_template(
        "cadastro_cliente.html",
        mes_atual=mes,
        ano_atual=ano,
        mensagem=mensagem,
        mensagem_tipo=mensagem_tipo,
        codigo_teste=codigo_teste,
        cpf_cnpj=cpf_cnpj,
        nome=nome,
        celular=celular,
        email=email,
        qtd_empresas=qtd_empresas,
        qtd_funcionarios=qtd_funcionarios
    )