
import re


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cpf_valido(valor: str) -> bool:
    cpf = somente_digitos(valor)


    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11
        digito = 0 if digito == 10 else digito
        if digito != int(cpf[tamanho]):
            return False

    return True


def celular_valido(valor: str) -> bool:
    return len(somente_digitos(valor)) in (10, 11)
