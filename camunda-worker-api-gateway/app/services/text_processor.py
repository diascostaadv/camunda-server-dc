"""
Text Processor Service
Serviço para limpeza e sanitização de texto de movimentações judiciais
"""

import re
import unicodedata
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TextProcessor:
    """Processador de texto para movimentações judiciais"""
    
    def __init__(self):
        # Padrões regex para limpeza
        self._whitespace_pattern = re.compile(r'\s+')
        self._special_chars_pattern = re.compile(r'[^\w\s]', re.UNICODE)
        self._numeric_pattern = re.compile(r'\d')
        
    def limpar_texto_publicacao(self, texto_original: str) -> str:
        """
        Limpa e sanitiza o texto da publicação
        
        Args:
            texto_original: Texto original da movimentação
            
        Returns:
            str: Texto limpo e sanitizado
            
        Raises:
            ValueError: Se o texto estiver vazio ou None
        """
        if not texto_original:
            raise ValueError("Texto original não pode estar vazio")
        
        try:
            logger.debug(f"Iniciando limpeza de texto: {len(texto_original)} caracteres")
            
            # 1. Remove quebras de linha e normaliza espaços
            texto = self._normalizar_espacos(texto_original)
            
            # 2. Remove acentos e caracteres especiais
            texto = self._remover_acentos(texto)
            
            # 3. Remove caracteres especiais (mantém números e letras)
            texto = self._remover_caracteres_especiais(texto)
            
            # 4. Converte para minúsculas
            texto = texto.lower()
            
            # 5. Normalização final de espaços
            texto = self._normalizar_espacos(texto)
            
            # 6. Remove espaços do início e fim
            texto = texto.strip()
            
            if not texto:
                raise ValueError("Texto resultou vazio após limpeza")
            
            logger.debug(f"Limpeza concluída: {len(texto)} caracteres")
            return texto
            
        except Exception as e:
            logger.error(f"Erro na limpeza de texto: {str(e)}")
            raise
    
    def _normalizar_espacos(self, texto: str) -> str:
        """
        Normaliza espaços em branco, quebras de linha e tabs
        
        Args:
            texto: Texto a ser normalizado
            
        Returns:
            str: Texto com espaços normalizados
        """
        # Remove quebras de linha, tabs e múltiplos espaços
        texto = re.sub(r'[\n\r\t]+', ' ', texto)
        texto = self._whitespace_pattern.sub(' ', texto)
        return texto
    
    def _remover_acentos(self, texto: str) -> str:
        """
        Remove acentos e caracteres diacríticos
        
        Args:
            texto: Texto com acentos
            
        Returns:
            str: Texto sem acentos
        """
        # Normaliza para NFD (decomposed form) e remove marcas diacríticas
        texto_nfd = unicodedata.normalize('NFD', texto)
        texto_sem_acentos = ''.join(
            char for char in texto_nfd 
            if unicodedata.category(char) != 'Mn'
        )
        return texto_sem_acentos
    
    def _remover_caracteres_especiais(self, texto: str) -> str:
        """
        Remove caracteres especiais, mantendo apenas letras, números e espaços
        
        Args:
            texto: Texto com caracteres especiais
            
        Returns:
            str: Texto apenas com letras, números e espaços
        """
        # Remove tudo exceto letras, números e espaços
        texto_limpo = re.sub(r'[^\w\s]', ' ', texto, flags=re.UNICODE)
        return texto_limpo
    
    def extrair_informacoes_basicas(self, texto_original: str) -> dict:
        """
        Extrai informações básicas do texto para análise
        
        Args:
            texto_original: Texto original da movimentação
            
        Returns:
            dict: Informações extraídas do texto
        """
        try:
            informacoes = {
                'tamanho_original': len(texto_original),
                'linhas': len(texto_original.split('\n')),
                'palavras': len(texto_original.split()),
                'tem_numeros': bool(self._numeric_pattern.search(texto_original)),
                'tem_caracteres_especiais': bool(self._special_chars_pattern.search(texto_original)),
            }
            
            # Texto limpo para comparação
            texto_limpo = self.limpar_texto_publicacao(texto_original)
            informacoes.update({
                'tamanho_limpo': len(texto_limpo),
                'palavras_limpas': len(texto_limpo.split()),
                'reducao_tamanho': len(texto_original) - len(texto_limpo),
                'percentual_reducao': round((len(texto_original) - len(texto_limpo)) / len(texto_original) * 100, 2)
            })
            
            return informacoes
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações básicas: {str(e)}")
            return {}
    
    def validar_texto_limpo(self, texto_limpo: str, texto_original: str) -> dict:
        """
        Valida se o texto limpo está adequado
        
        Args:
            texto_limpo: Texto após limpeza
            texto_original: Texto original
            
        Returns:
            dict: Resultado da validação
        """
        validacao = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Verifica se não ficou vazio
            if not texto_limpo or not texto_limpo.strip():
                validacao['is_valid'] = False
                validacao['errors'].append("Texto ficou vazio após limpeza")
                return validacao
            
            # Verifica redução excessiva
            reducao = (len(texto_original) - len(texto_limpo)) / len(texto_original) * 100
            if reducao > 80:
                validacao['warnings'].append(f"Redução excessiva de texto: {reducao:.1f}%")
            
            # Verifica se ainda tem conteúdo significativo
            palavras = len(texto_limpo.split())
            if palavras < 3:
                validacao['warnings'].append(f"Poucas palavras após limpeza: {palavras}")
            
            # Verifica caracteres inválidos remanescentes
            if re.search(r'[^\w\s]', texto_limpo):
                validacao['warnings'].append("Ainda há caracteres especiais no texto limpo")
            
        except Exception as e:
            validacao['is_valid'] = False
            validacao['errors'].append(f"Erro na validação: {str(e)}")
        
        return validacao


# Instância global do processador
text_processor = TextProcessor()


def limpar_texto_publicacao(texto_original: str) -> str:
    """
    Função de conveniência para limpeza de texto
    
    Args:
        texto_original: Texto original da movimentação
        
    Returns:
        str: Texto limpo e sanitizado
    """
    return text_processor.limpar_texto_publicacao(texto_original)


def extrair_informacoes_texto(texto_original: str) -> dict:
    """
    Função de conveniência para extração de informações
    
    Args:
        texto_original: Texto original da movimentação
        
    Returns:
        dict: Informações extraídas do texto
    """
    return text_processor.extrair_informacoes_basicas(texto_original)


def validar_texto_processado(texto_limpo: str, texto_original: str) -> dict:
    """
    Função de conveniência para validação
    
    Args:
        texto_limpo: Texto após limpeza
        texto_original: Texto original
        
    Returns:
        dict: Resultado da validação
    """
    return text_processor.validar_texto_limpo(texto_limpo, texto_original)