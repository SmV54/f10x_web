import re


def somente_numeros(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def validar_cpf(cpf: str) -> bool:
    cpf = somente_numeros(cpf)

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


def validar_cnpj(cnpj: str) -> bool:
    cnpj = somente_numeros(cnpj)

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


def validar_cpf_cnpj(valor: str) -> bool:
    numero = somente_numeros(valor)

    if len(numero) == 11:
        return validar_cpf(numero)

    if len(numero) == 14:
        return validar_cnpj(numero)

    return False


def validar_nome(nome: str) -> bool:
    nome = (nome or "").strip()

    if len(nome) < 10:
        return False

    # aceita letras, espaços e acentos
    padrao = r"^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$"
    return re.fullmatch(padrao, nome) is not None


def validar_celular(celular: str) -> bool:
    celular = somente_numeros(celular)

    # aceita 10 ou 11 dígitos
    if len(celular) not in (10, 11):
        return False

    ddd = int(celular[:2])

    # DDDs válidos no Brasil: 11 a 99
    if ddd < 11 or ddd > 99:
        return False

    return True


def validar_email_minimo(email: str) -> bool:
    email = (email or "").strip().lower()

    if len(email) < 6:
        return False

    if "@" not in email or "." not in email:
        return False

    if email.startswith("@") or email.endswith("@"):
        return False

    if email.startswith(".") or email.endswith("."):
        return False

    if " " in email:
        return False

    return True   