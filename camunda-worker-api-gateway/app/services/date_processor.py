"""
Date Processor Service
Serviço para conversão e validação de datas de movimentações judiciais
"""

import logging
from datetime import datetime, date
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DateProcessor:
    """Processador de datas para movimentações judiciais"""
    
    def __init__(self):
        # Formatos de data suportados
        self._supported_formats = [
            "%d/%m/%Y",    # dd/mm/yyyy (formato principal)
            "%d-%m-%Y",    # dd-mm-yyyy
            "%d.%m.%Y",    # dd.mm.yyyy
        ]
        
    def converter_data_publicacao(self, data_str: str) -> datetime:
        """
        Converte string de data para datetime
        
        Args:
            data_str: Data em formato string (dd/mm/yyyy)
            
        Returns:
            datetime: Data convertida
            
        Raises:
            ValueError: Se a data estiver em formato inválido
        """
        if not data_str:
            raise ValueError("Data não pode estar vazia")
        
        data_str = data_str.strip()
        
        try:
            logger.debug(f"Convertendo data: {data_str}")
            
            # Tenta conversão com os formatos suportados
            for formato in self._supported_formats:
                try:
                    data_convertida = datetime.strptime(data_str, formato)
                    
                    # Validações adicionais
                    self._validar_data(data_convertida)
                    
                    logger.debug(f"Data convertida com sucesso: {data_convertida}")
                    return data_convertida
                    
                except ValueError:
                    continue
            
            # Se chegou aqui, não conseguiu converter com nenhum formato
            raise ValueError(f"Formato de data inválido: {data_str}. Use dd/mm/yyyy")
            
        except Exception as e:
            logger.error(f"Erro na conversão de data '{data_str}': {str(e)}")
            raise
    
    def _validar_data(self, data: datetime) -> None:
        """
        Valida se a data está dentro de limites razoáveis
        
        Args:
            data: Data a ser validada
            
        Raises:
            ValueError: Se a data estiver fora dos limites
        """
        hoje = datetime.now()
        ano_minimo = 1900
        ano_maximo = hoje.year + 1
        
        if data.year < ano_minimo:
            raise ValueError(f"Ano muito antigo: {data.year}. Mínimo: {ano_minimo}")
        
        if data.year > ano_maximo:
            raise ValueError(f"Ano muito recente: {data.year}. Máximo: {ano_maximo}")
        
        # Verifica se não é uma data futura muito distante
        if data > hoje.replace(year=hoje.year + 1):
            raise ValueError(f"Data muito no futuro: {data.strftime('%d/%m/%Y')}")
    
    def formatar_data_para_display(self, data: datetime, formato: str = "%d/%m/%Y") -> str:
        """
        Formata datetime para string de exibição
        
        Args:
            data: Data a ser formatada
            formato: Formato desejado (padrão: dd/mm/yyyy)
            
        Returns:
            str: Data formatada
        """
        try:
            return data.strftime(formato)
        except Exception as e:
            logger.error(f"Erro ao formatar data {data}: {str(e)}")
            return str(data)
    
    def obter_informacoes_data(self, data_str: str) -> dict:
        """
        Obtém informações sobre a data fornecida
        
        Args:
            data_str: Data em formato string
            
        Returns:
            dict: Informações sobre a data
        """
        try:
            data = self.converter_data_publicacao(data_str)
            hoje = datetime.now()
            
            informacoes = {
                'data_original': data_str,
                'data_convertida': data.isoformat(),
                'data_formatada': self.formatar_data_para_display(data),
                'ano': data.year,
                'mes': data.month,
                'dia': data.day,
                'dia_semana': data.strftime('%A'),
                'mes_nome': data.strftime('%B'),
                'trimestre': (data.month - 1) // 3 + 1,
                'eh_ano_bissexto': self._eh_ano_bissexto(data.year),
                'dias_desde_hoje': (data.date() - hoje.date()).days,
                'eh_passado': data.date() < hoje.date(),
                'eh_futuro': data.date() > hoje.date(),
                'eh_hoje': data.date() == hoje.date(),
            }
            
            return informacoes
            
        except Exception as e:
            return {
                'data_original': data_str,
                'erro': str(e),
                'valida': False
            }
    
    def _eh_ano_bissexto(self, ano: int) -> bool:
        """
        Verifica se o ano é bissexto
        
        Args:
            ano: Ano a ser verificado
            
        Returns:
            bool: True se for bissexto
        """
        return ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)
    
    def validar_formato_data(self, data_str: str) -> dict:
        """
        Valida o formato da data sem converter
        
        Args:
            data_str: Data em formato string
            
        Returns:
            dict: Resultado da validação
        """
        validacao = {
            'is_valid': True,
            'formato_detectado': None,
            'warnings': [],
            'errors': []
        }
        
        if not data_str:
            validacao['is_valid'] = False
            validacao['errors'].append("Data não pode estar vazia")
            return validacao
        
        data_str = data_str.strip()
        
        # Verifica formato básico
        if len(data_str) != 10:
            validacao['warnings'].append(f"Comprimento incomum: {len(data_str)} (esperado: 10)")
        
        # Tenta identificar o formato
        for formato in self._supported_formats:
            try:
                datetime.strptime(data_str, formato)
                validacao['formato_detectado'] = formato
                break
            except ValueError:
                continue
        
        if not validacao['formato_detectado']:
            validacao['is_valid'] = False
            validacao['errors'].append(f"Formato não reconhecido: {data_str}")
        
        return validacao
    
    def converter_para_iso(self, data_str: str) -> str:
        """
        Converte data para formato ISO (YYYY-MM-DD)
        
        Args:
            data_str: Data em formato dd/mm/yyyy
            
        Returns:
            str: Data em formato ISO
        """
        try:
            data = self.converter_data_publicacao(data_str)
            return data.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Erro ao converter para ISO: {str(e)}")
            raise
    
    def extrair_componentes_data(self, data_str: str) -> Tuple[int, int, int]:
        """
        Extrai componentes individuais da data
        
        Args:
            data_str: Data em formato string
            
        Returns:
            tuple: (dia, mês, ano)
        """
        try:
            data = self.converter_data_publicacao(data_str)
            return data.day, data.month, data.year
        except Exception as e:
            logger.error(f"Erro ao extrair componentes: {str(e)}")
            raise


# Instância global do processador
date_processor = DateProcessor()


def converter_data_publicacao(data_str: str) -> datetime:
    """
    Função de conveniência para conversão de data
    
    Args:
        data_str: Data em formato string (dd/mm/yyyy)
        
    Returns:
        datetime: Data convertida
    """
    return date_processor.converter_data_publicacao(data_str)


def validar_formato_data(data_str: str) -> dict:
    """
    Função de conveniência para validação de formato
    
    Args:
        data_str: Data em formato string
        
    Returns:
        dict: Resultado da validação
    """
    return date_processor.validar_formato_data(data_str)


def obter_informacoes_data(data_str: str) -> dict:
    """
    Função de conveniência para obter informações da data
    
    Args:
        data_str: Data em formato string
        
    Returns:
        dict: Informações sobre a data
    """
    return date_processor.obter_informacoes_data(data_str)


def converter_para_iso(data_str: str) -> str:
    """
    Função de conveniência para conversão ISO
    
    Args:
        data_str: Data em formato dd/mm/yyyy
        
    Returns:
        str: Data em formato ISO (YYYY-MM-DD)
    """
    return date_processor.converter_para_iso(data_str)