"""
Serviço de tratamento e higienização de publicações judiciais
Implementa o processo de transformação Bronze → Prata conforme BPMN
"""

import re
import unicodedata
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from models.publicacao import PublicacaoBronze, PublicacaoPrata
from services.hash_generator import gerar_hash_unica

logger = logging.getLogger(__name__)


class PublicacaoService:
    """Serviço para tratamento e higienização de publicações"""
    
    def __init__(self):
        # Padrões de limpeza
        self.cabecalhos_fornecedor = [
            r"^DIÁRIO.*?JUSTIÇA.*?\n+",
            r"^TRIBUNAL.*?\n+",
            r"^PODER JUDICIÁRIO.*?\n+",
            r"^Diário Eletrônico.*?\n+",
            r"^DJe.*?\d{2}/\d{2}/\d{4}.*?\n+",
        ]
        
        # Padrões de número de processo
        self.regex_numero_processo = re.compile(
            r'\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}'
        )
        
    def higienizar_publicacao(self, publicacao_bronze: PublicacaoBronze) -> PublicacaoPrata:
        """
        Higieniza uma publicação bronze transformando em prata
        
        Etapas conforme BPMN:
        1. Normalizar espaços
        2. Remover acentos
        3. Remover caracteres especiais
        4. Converter para minúsculas
        5. Remover cabeçalhos de fornecedor
        6. Tratar datas
        7. Gerar hash única
        
        Args:
            publicacao_bronze: Publicação bronze a ser higienizada
            
        Returns:
            PublicacaoPrata: Publicação higienizada
        """
        try:
            logger.info(f"Iniciando higienização da publicação {publicacao_bronze.cod_publicacao}")
            
            # 1. Higienizar texto
            texto_limpo = self._higienizar_texto(publicacao_bronze.texto_publicacao)
            
            # 2. Limpar número do processo
            numero_processo_limpo = self._limpar_numero_processo(publicacao_bronze.numero_processo)
            
            # 3. Processar data
            data_publicacao_processada = self._processar_data(publicacao_bronze.data_publicacao)
            
            # 4. Gerar hash única (com texto original para garantir unicidade)
            hash_unica = gerar_hash_unica(
                numero_processo=publicacao_bronze.numero_processo,
                data_publicacao=publicacao_bronze.data_publicacao,
                texto_original=publicacao_bronze.texto_publicacao
            )
            
            # 5. Gerar hash alternativa (com texto limpo para comparações)
            hash_alternativa = gerar_hash_unica(
                numero_processo=numero_processo_limpo,
                data_publicacao=publicacao_bronze.data_publicacao,
                texto_original=texto_limpo
            )
            
            # 6. Criar publicação prata
            publicacao_prata = PublicacaoPrata(
                publicacao_bronze_id=str(publicacao_bronze.cod_publicacao),
                hash_unica=hash_unica,
                hash_alternativa=hash_alternativa,
                numero_processo=publicacao_bronze.numero_processo,
                numero_processo_limpo=numero_processo_limpo,
                data_publicacao=data_publicacao_processada,
                data_publicacao_original=publicacao_bronze.data_publicacao,
                texto_limpo=texto_limpo,
                texto_original=publicacao_bronze.texto_publicacao,
                fonte=publicacao_bronze.fonte,
                tribunal=publicacao_bronze.tribunal.lower(),
                instancia=publicacao_bronze.instancia,
                status="nova_publicacao_inedita",  # Status inicial
                score_similaridade=0.0,
                timestamp_processamento=datetime.now()
            )
            
            logger.info(f"✅ Publicação {publicacao_bronze.cod_publicacao} higienizada com sucesso")
            return publicacao_prata
            
        except Exception as e:
            logger.error(f"Erro ao higienizar publicação {publicacao_bronze.cod_publicacao}: {e}")
            raise
    
    def _higienizar_texto(self, texto: str) -> str:
        """
        Higieniza o texto da publicação
        
        Etapas:
        1. Remove cabeçalhos de fornecedor
        2. Normaliza espaços
        3. Remove acentos
        4. Remove caracteres especiais
        5. Converte para minúsculas
        6. Remove espaços nas extremidades
        
        Args:
            texto: Texto original
            
        Returns:
            str: Texto higienizado
        """
        if not texto:
            return ""
        
        texto_limpo = texto
        
        # 1. Remove cabeçalhos de fornecedor
        for padrao in self.cabecalhos_fornecedor:
            texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE | re.MULTILINE)
        
        # 2. Normaliza quebras de linha múltiplas
        texto_limpo = re.sub(r'\n{3,}', '\n\n', texto_limpo)
        
        # 3. Remove acentos
        texto_limpo = self._remover_acentos(texto_limpo)
        
        # 4. Remove caracteres especiais mantendo pontuação básica
        texto_limpo = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\/]', ' ', texto_limpo)
        
        # 5. Normaliza espaços múltiplos
        texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
        
        # 6. Converte para minúsculas
        texto_limpo = texto_limpo.lower()
        
        # 7. Remove espaços nas extremidades
        texto_limpo = texto_limpo.strip()
        
        return texto_limpo
    
    def _remover_acentos(self, texto: str) -> str:
        """
        Remove acentos do texto
        
        Args:
            texto: Texto com acentos
            
        Returns:
            str: Texto sem acentos
        """
        # Normaliza para NFD (decompõe caracteres)
        nfd = unicodedata.normalize('NFD', texto)
        
        # Remove marcas diacríticas
        sem_acentos = ''.join(
            char for char in nfd 
            if unicodedata.category(char) != 'Mn'
        )
        
        return sem_acentos
    
    def _limpar_numero_processo(self, numero_processo: str) -> str:
        """
        Limpa e normaliza número do processo
        
        Args:
            numero_processo: Número original
            
        Returns:
            str: Número limpo e padronizado
        """
        if not numero_processo:
            return ""
        
        # Remove caracteres não numéricos exceto hífen e ponto
        numero_limpo = re.sub(r'[^\d\-\.]', '', numero_processo)
        
        # Tenta extrair padrão CNJ se existir
        match = self.regex_numero_processo.search(numero_processo)
        if match:
            numero_limpo = match.group(0)
        
        # Remove espaços e converte para minúsculas
        numero_limpo = numero_limpo.strip().lower()
        
        return numero_limpo
    
    def _processar_data(self, data_str: str) -> datetime:
        """
        Processa string de data para datetime
        
        Args:
            data_str: Data em formato string
            
        Returns:
            datetime: Data processada
        """
        if not data_str:
            return datetime.now()
        
        # Lista de formatos possíveis
        formatos = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d/%m/%y',
            '%d-%m-%y',
            '%d.%m.%Y',
            '%d.%m.%y'
        ]
        
        for formato in formatos:
            try:
                return datetime.strptime(data_str.strip(), formato)
            except ValueError:
                continue
        
        # Se nenhum formato funcionou, tenta extrair números
        numeros = re.findall(r'\d+', data_str)
        if len(numeros) >= 3:
            try:
                dia = int(numeros[0])
                mes = int(numeros[1])
                ano = int(numeros[2])
                
                # Ajusta ano de 2 dígitos
                if ano < 100:
                    ano = 2000 + ano if ano < 50 else 1900 + ano
                
                return datetime(ano, mes, dia)
            except (ValueError, IndexError):
                pass
        
        # Fallback para data atual
        logger.warning(f"Não foi possível processar data: {data_str}. Usando data atual.")
        return datetime.now()
    
    def extrair_entidades(self, texto: str) -> Dict[str, Any]:
        """
        Extrai entidades do texto (partes, advogados, etc)
        
        Args:
            texto: Texto para análise
            
        Returns:
            dict: Entidades extraídas
        """
        entidades = {
            'partes': [],
            'advogados': [],
            'numeros_processo': [],
            'valores': [],
            'datas': []
        }
        
        # Extrai números de processo
        processos = self.regex_numero_processo.findall(texto)
        entidades['numeros_processo'] = list(set(processos))
        
        # Extrai advogados (OAB)
        padrao_oab = re.compile(r'OAB[/\s]+(\w+)[/\s]+(\d+)', re.IGNORECASE)
        advogados = padrao_oab.findall(texto)
        entidades['advogados'] = [f"OAB/{uf}/{num}" for uf, num in advogados]
        
        # Extrai valores monetários
        padrao_valor = re.compile(r'R\$\s*[\d\.,]+', re.IGNORECASE)
        valores = padrao_valor.findall(texto)
        entidades['valores'] = valores
        
        # Extrai datas
        padrao_data = re.compile(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}')
        datas = padrao_data.findall(texto)
        entidades['datas'] = list(set(datas))
        
        # Extrai possíveis nomes de partes (heurística simples)
        # Busca por padrões como "Autor: NOME" ou "Réu: NOME"
        padrao_partes = re.compile(
            r'(?:autor|reu|requerente|requerido|exequente|executado|impetrante|impetrado)'
            r'[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|,|;|\.)',
            re.IGNORECASE
        )
        partes = padrao_partes.findall(texto)
        entidades['partes'] = [p.strip() for p in partes if len(p.strip()) > 3]
        
        return entidades
    
    def identificar_tipo_publicacao(self, texto: str) -> Tuple[str, float]:
        """
        Identifica o tipo de publicação baseado no texto
        
        Args:
            texto: Texto da publicação
            
        Returns:
            tuple: (tipo, confiança)
        """
        texto_lower = texto.lower()
        
        # Dicionário de palavras-chave por tipo
        tipos_padroes = {
            'sentenca': ['sentenca', 'julgo procedente', 'julgo improcedente', 'extingo o processo'],
            'decisao_interlocutoria': ['decisao interlocutoria', 'defiro', 'indefiro', 'decido'],
            'despacho': ['despacho', 'vista', 'manifeste-se', 'diga'],
            'intimacao': ['intimacao', 'intimado', 'intimo', 'fica intimado'],
            'citacao': ['citacao', 'citado', 'cite-se', 'fica citado'],
            'publicacao_edital': ['edital', 'prazo de', 'publicar'],
            'audiencia': ['audiencia', 'designo audiencia', 'comparecimento']
        }
        
        scores = {}
        for tipo, palavras in tipos_padroes.items():
            score = sum(1 for palavra in palavras if palavra in texto_lower)
            if score > 0:
                scores[tipo] = score
        
        if scores:
            # Retorna o tipo com maior score
            tipo_identificado = max(scores, key=scores.get)
            # Calcula confiança baseada no número de matches
            confianca = min(scores[tipo_identificado] / 3.0, 1.0)
            return tipo_identificado, confianca
        
        return 'outros', 0.5
    
    def calcular_urgencia(self, texto: str, tipo: str) -> Tuple[bool, Optional[int]]:
        """
        Calcula se a publicação é urgente e o prazo em dias
        
        Args:
            texto: Texto da publicação
            tipo: Tipo da publicação
            
        Returns:
            tuple: (é_urgente, prazo_dias)
        """
        texto_lower = texto.lower()
        
        # Palavras que indicam urgência
        palavras_urgencia = [
            'urgente', 'urgencia', 'prazo fatal', 'improrrogavel',
            'prazo de 24 horas', 'prazo de 48 horas', 'imediato'
        ]
        
        eh_urgente = any(palavra in texto_lower for palavra in palavras_urgencia)
        
        # Tenta extrair prazo
        prazo_dias = None
        
        # Busca por padrões de prazo
        padrao_prazo = re.compile(r'prazo de (\d+) dias?', re.IGNORECASE)
        match = padrao_prazo.search(texto)
        if match:
            prazo_dias = int(match.group(1))
            if prazo_dias <= 5:
                eh_urgente = True
        
        # Prazos específicos por tipo
        if tipo == 'citacao' and not prazo_dias:
            prazo_dias = 15  # Prazo padrão para contestação
        elif tipo == 'intimacao' and not prazo_dias:
            prazo_dias = 5  # Prazo padrão para manifestação
        
        return eh_urgente, prazo_dias