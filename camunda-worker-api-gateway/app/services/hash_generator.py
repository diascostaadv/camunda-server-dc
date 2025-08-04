"""
Hash Generator Service
Serviço para geração de hash única para detecção de duplicatas em movimentações judiciais
"""

import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HashGenerator:
    """Gerador de hash única para movimentações judiciais"""
    
    def __init__(self):
        # Algoritmo de hash padrão (SHA256 para maior confiabilidade)
        self._algorithm = 'sha256'
        
    def gerar_hash_unica(
        self, 
        numero_processo: str, 
        data_publicacao: str, 
        texto_original: str,
        tribunal: str,
        encoding: str = 'utf-8'
    ) -> str:
        """
        Gera hash única baseada nos campos principais da movimentação
        
        Args:
            numero_processo: Número do processo judicial
            data_publicacao: Data de publicação (formato original)
            texto_original: Texto original da movimentação
            tribunal: Tribunal de origem
            encoding: Codificação para bytes (padrão: utf-8)
            
        Returns:
            str: Hash SHA256 em formato hexadecimal
            
        Raises:
            ValueError: Se algum campo obrigatório estiver vazio
        """
        # Validações
        if not numero_processo or not numero_processo.strip():
            raise ValueError("Número do processo é obrigatório para hash")
        
        if not data_publicacao or not data_publicacao.strip():
            raise ValueError("Data de publicação é obrigatória para hash")
        
        if not texto_original or not texto_original.strip():
            raise ValueError("Texto original é obrigatório para hash")
        
        if not tribunal or not tribunal.strip():
            raise ValueError("Tribunal é obrigatório para hash")
        
        try:
            logger.debug(f"Gerando hash para processo {numero_processo}")
            
            # Normaliza os campos (remove espaços extras, converte para lowercase)
            numero_normalizado = numero_processo.strip().lower()
            data_normalizada = data_publicacao.strip()
            texto_normalizado = texto_original.strip()
            tribunal_normalizado = tribunal.strip().lower()
            
            # Constrói a string para hash com separadores consistentes
            hash_input = self._construir_string_hash(
                numero_normalizado,
                data_normalizada, 
                texto_normalizado,
                tribunal_normalizado
            )
            
            # Gera hash
            hash_obj = hashlib.new(self._algorithm)
            hash_obj.update(hash_input.encode(encoding))
            hash_result = hash_obj.hexdigest()
            
            logger.debug(f"Hash gerada com sucesso: {hash_result[:16]}...")
            return hash_result
            
        except Exception as e:
            logger.error(f"Erro ao gerar hash: {str(e)}")
            raise
    
    def _construir_string_hash(
        self, 
        numero_processo: str,
        data_publicacao: str,
        texto_original: str,
        tribunal: str
    ) -> str:
        """
        Constrói string padronizada para geração de hash
        
        Args:
            numero_processo: Número do processo normalizado
            data_publicacao: Data de publicação
            texto_original: Texto original da movimentação
            tribunal: Tribunal normalizado
            
        Returns:
            str: String padronizada para hash
        """
        # Usa separador único e consistente
        separador = "|#|"
        
        # Constrói string no formato: processo|#|data|#|texto|#|tribunal
        hash_string = separador.join([
            numero_processo,
            data_publicacao,
            texto_original,
            tribunal
        ])
        
        return hash_string
    
    def verificar_hash_existente(self, hash_nova: str, hashes_existentes: list) -> bool:
        """
        Verifica se a hash já existe na lista fornecida
        
        Args:
            hash_nova: Hash recém-gerada
            hashes_existentes: Lista de hashes existentes
            
        Returns:
            bool: True se a hash já existe
        """
        if not hash_nova or not hashes_existentes:
            return False
        
        return hash_nova in hashes_existentes
    
    def gerar_hash_alternativa(
        self,
        numero_processo: str,
        data_publicacao: str,
        texto_limpo: str,  # Usando texto limpo ao invés do original
        tribunal: str,
        encoding: str = 'utf-8'
    ) -> str:
        """
        Gera hash alternativa usando texto limpo (para comparações adicionais)
        
        Args:
            numero_processo: Número do processo judicial
            data_publicacao: Data de publicação
            texto_limpo: Texto limpo/sanitizado
            tribunal: Tribunal de origem
            encoding: Codificação para bytes
            
        Returns:
            str: Hash SHA256 alternativa
        """
        try:
            logger.debug("Gerando hash alternativa com texto limpo")
            
            # Normaliza campos
            numero_normalizado = numero_processo.strip().lower()
            data_normalizada = data_publicacao.strip()
            texto_normalizado = texto_limpo.strip().lower()
            tribunal_normalizado = tribunal.strip().lower()
            
            # Constrói string para hash alternativa
            hash_input = self._construir_string_hash(
                numero_normalizado,
                data_normalizada,
                texto_normalizado,
                tribunal_normalizado
            )
            
            # Adiciona prefixo para diferençar da hash principal
            hash_input = "ALT:" + hash_input
            
            # Gera hash
            hash_obj = hashlib.new(self._algorithm)
            hash_obj.update(hash_input.encode(encoding))
            hash_result = hash_obj.hexdigest()
            
            logger.debug(f"Hash alternativa gerada: {hash_result[:16]}...")
            return hash_result
            
        except Exception as e:
            logger.error(f"Erro ao gerar hash alternativa: {str(e)}")
            raise
    
    def obter_informacoes_hash(self, hash_value: str) -> Dict[str, Any]:
        """
        Obtém informações sobre uma hash
        
        Args:
            hash_value: Valor da hash
            
        Returns:
            dict: Informações sobre a hash
        """
        try:
            informacoes = {
                'hash': hash_value,
                'algoritmo': self._algorithm,
                'tamanho': len(hash_value),
                'eh_valida': self._validar_hash_format(hash_value),
                'timestamp_analise': datetime.utcnow().isoformat(),
                'prefixo': hash_value[:8] if hash_value else None,
                'sufixo': hash_value[-8:] if hash_value else None,
            }
            
            # Verifica se é hash alternativa
            if len(hash_value) == 64:  # SHA256 tem 64 caracteres hex
                informacoes['tipo'] = 'sha256'
            else:
                informacoes['tipo'] = 'desconhecido'
            
            return informacoes
            
        except Exception as e:
            return {
                'hash': hash_value,
                'erro': str(e),
                'eh_valida': False
            }
    
    def _validar_hash_format(self, hash_value: str) -> bool:
        """
        Valida se a hash está no formato correto
        
        Args:
            hash_value: Valor da hash
            
        Returns:
            bool: True se válida
        """
        if not hash_value:
            return False
        
        # SHA256 deve ter 64 caracteres hexadecimais
        if len(hash_value) != 64:
            return False
        
        # Verifica se todos são caracteres hexadecimais
        try:
            int(hash_value, 16)
            return True
        except ValueError:
            return False
    
    def comparar_hashes(self, hash1: str, hash2: str) -> Dict[str, Any]:
        """
        Compara duas hashes e retorna informações
        
        Args:
            hash1: Primeira hash
            hash2: Segunda hash
            
        Returns:
            dict: Resultado da comparação
        """
        resultado = {
            'sao_iguais': hash1 == hash2,
            'hash1_valida': self._validar_hash_format(hash1),
            'hash2_valida': self._validar_hash_format(hash2),
            'timestamp_comparacao': datetime.utcnow().isoformat()
        }
        
        if resultado['hash1_valida'] and resultado['hash2_valida']:
            resultado['diferenca_caracteres'] = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
            resultado['prefixos_iguais'] = hash1[:8] == hash2[:8]
            resultado['sufixos_iguais'] = hash1[-8:] == hash2[-8:]
        
        return resultado
    
    def gerar_hash_rapida(self, texto: str) -> str:
        """
        Gera hash rápida para propósitos de debugging/logging
        
        Args:
            texto: Texto para hash
            
        Returns:
            str: Hash MD5 (mais rápida, menos segura)
        """
        try:
            return hashlib.md5(texto.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Erro ao gerar hash rápida: {str(e)}")
            return "erro_hash"


# Instância global do gerador
hash_generator = HashGenerator()


def gerar_hash_unica(
    numero_processo: str,
    data_publicacao: str, 
    texto_original: str,
    tribunal: str
) -> str:
    """
    Função de conveniência para geração de hash única
    
    Args:
        numero_processo: Número do processo judicial
        data_publicacao: Data de publicação
        texto_original: Texto original da movimentação
        tribunal: Tribunal de origem
        
    Returns:
        str: Hash SHA256 única
    """
    return hash_generator.gerar_hash_unica(
        numero_processo, data_publicacao, texto_original, tribunal
    )


def verificar_duplicata(hash_nova: str, hashes_existentes: list) -> bool:
    """
    Função de conveniência para verificação de duplicatas
    
    Args:
        hash_nova: Hash recém-gerada
        hashes_existentes: Lista de hashes existentes
        
    Returns:
        bool: True se é duplicata
    """
    return hash_generator.verificar_hash_existente(hash_nova, hashes_existentes)


def obter_informacoes_hash(hash_value: str) -> Dict[str, Any]:
    """
    Função de conveniência para obter informações da hash
    
    Args:
        hash_value: Valor da hash
        
    Returns:
        dict: Informações sobre a hash
    """
    return hash_generator.obter_informacoes_hash(hash_value)