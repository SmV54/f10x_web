from flask import Flask, render_template, request

app = Flask(__name__)

# ================================
# ROTA PRINCIPAL (HOME)
# ================================
@app.route("/")
def home():
    return render_template("Cadastro_Cliente.html")


# ================================
# EXEMPLO DE ROTA PARA RECEBER DADOS
# ================================
@app.route("/salvar", methods=["POST"])
def salvar():
    # Exemplo de captura de dados do formulário
    cnpj_cpf = request.form.get("cnpj_cpf")
    nome = request.form.get("nome")
    celular = request.form.get("celular")
    email = request.form.get("email")

    print("Dados recebidos:")
    print(cnpj_cpf, nome, celular, email)

    return "Dados recebidos com sucesso!"


# ================================
# INICIALIZAÇÃO
# ================================
if __name__ == "__main__":
    app.run(debug=True)