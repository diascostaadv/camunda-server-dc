"""
Validador de Datas
"""

from datetime import datetime
from typing import Optional


def validar_data(data_str: str, formato: str = "%Y-%m-%d") -> bool:
    """
    Valida se string é uma data válida

    Args:
        data_str: String da data
        formato: Formato esperado (default: YYYY-MM-DD)

    Returns:
        True se válida, False caso contrário
    """
    if not data_str:
        return False

    try:
        datetime.strptime(data_str, formato)
        return True
    except ValueError:
        return False


def validar_data_nao_futura(data_str: str, formato: str = "%Y-%m-%d") -> bool:
    """
    Valida se data não é futura

    Args:
        data_str: String da data
        formato: Formato esperado

    Returns:
        True se não for futura, False caso contrário
    """
    if not validar_data(data_str, formato):
        return False

    try:
        data = datetime.strptime(data_str, formato)
        return data <= datetime.now()
    except ValueError:
        return False


def validar_intervalo_datas(
    data_inicial: str,
    data_final: str,
    formato: str = "%Y-%m-%d"
) -> bool:
    """
    Valida se data_final >= data_inicial

    Args:
        data_inicial: Data inicial
        data_final: Data final
        formato: Formato esperado

    Returns:
        True se intervalo válido, False caso contrário
    """
    if not validar_data(data_inicial, formato) or not validar_data(data_final, formato):
        return False

    try:
        dt_inicial = datetime.strptime(data_inicial, formato)
        dt_final = datetime.strptime(data_final, formato)
        return dt_final >= dt_inicial
    except ValueError:
        return False
