"""
Validador de Número CNJ
Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
"""

import re


def validar_numero_cnj(numero_cnj: str) -> bool:
    """
    Valida número de processo no padrão CNJ

    Args:
        numero_cnj: Número do processo (formato CNJ)

    Returns:
        True se válido, False caso contrário

    Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
    - NNNNNNN: Número sequencial (7 dígitos)
    - DD: Dígito verificador (2 dígitos)
    - AAAA: Ano (4 dígitos)
    - J: Justiça (1 dígito)
    - TR: Tribunal (2 dígitos)
    - OOOO: Origem (4 dígitos)
    """
    if not numero_cnj:
        return False

    # Padrão CNJ
    pattern = r'^\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}$'

    if not re.match(pattern, numero_cnj):
        return False

    # Extrair componentes
    parts = numero_cnj.replace('-', '.').split('.')

    if len(parts) != 6:
        return False

    numero_sequencial = parts[0]
    digito_verificador = parts[1]
    ano = parts[2]
    justica = parts[3]
    tribunal = parts[4]
    origem = parts[5]

    # Validar dígito verificador (algoritmo CNJ)
    try:
        # Concatenar componentes sem dígito verificador
        concatenado = f"{origem}{ano}{justica}{tribunal}{numero_sequencial}"

        # Calcular resto da divisão por 97
        resto = int(concatenado) % 97
        digito_calculado = 98 - resto

        # Comparar com dígito fornecido
        return int(digito_verificador) == digito_calculado

    except ValueError:
        return False
