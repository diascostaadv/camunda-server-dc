"""
Validador de CPF e CNPJ
"""

import re


def validar_cpf_cnpj(documento: str) -> bool:
    """
    Valida CPF ou CNPJ

    Args:
        documento: CPF ou CNPJ (com ou sem formatação)

    Returns:
        True se válido, False caso contrário
    """
    if not documento:
        return False

    # Remover formatação
    documento = re.sub(r'[^0-9]', '', documento)

    # Verificar tamanho
    if len(documento) == 11:
        return _validar_cpf(documento)
    elif len(documento) == 14:
        return _validar_cnpj(documento)
    else:
        return False


def _validar_cpf(cpf: str) -> bool:
    """Valida CPF"""
    # CPF deve ter 11 dígitos
    if len(cpf) != 11:
        return False

    # Verificar se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False

    # Calcular primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0

    # Calcular segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0

    # Verificar dígitos
    return cpf[-2:] == f"{digito1}{digito2}"


def _validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ"""
    # CNPJ deve ter 14 dígitos
    if len(cnpj) != 14:
        return False

    # Verificar se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False

    # Calcular primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0

    # Calcular segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0

    # Verificar dígitos
    return cnpj[-2:] == f"{digito1}{digito2}"
