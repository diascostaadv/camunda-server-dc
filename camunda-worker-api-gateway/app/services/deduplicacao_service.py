"""
Serviço de deduplicação de publicações com hash e fuzzy matching
Implementa a lógica de verificação de duplicatas conforme BPMN
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import Levenshtein

from pymongo import MongoClient
from bson import ObjectId

from models.publicacao import (
    PublicacaoPrata,
    ResultadoDeduplicacao,
    HashDeduplicacao
)

logger = logging.getLogger(__name__)


class DeduplicacaoService:
    """Serviço para deduplicação de publicações"""
    
    def __init__(self, mongo_client: MongoClient, database_name: str = "camunda_publicacoes"):
        """
        Inicializa o serviço de deduplicação
        
        Args:
            mongo_client: Cliente MongoDB
            database_name: Nome do banco de dados
        """
        self.client = mongo_client
        self.db = mongo_client[database_name]
        
        # Coleções
        self.col_hashes = self.db['hashes']
        self.col_publicacoes_prata = self.db['publicacoes_prata']
        self.col_publicacoes_bronze = self.db['publicacoes_bronze']
        
        # Configurações de similaridade
        self.score_minimo_duplicata = 90.0  # Score mínimo para considerar duplicata exata
        self.score_minimo_similar = 70.0    # Score mínimo para considerar similar
        self.janela_temporal_dias = 30      # Janela temporal para buscar publicações
    
    def verificar_duplicata(
        self, 
        publicacao: PublicacaoPrata,
        score_minimo: float = None
    ) -> ResultadoDeduplicacao:
        """
        Verifica se uma publicação é duplicata
        
        Fluxo conforme BPMN:
        1. Buscar hash no banco
        2. Se encontrou → repetida (score=100)
        3. Se não encontrou → buscar por número de processo
        4. Se não tem publicações do processo → nova_publicacao_inedita (score=0)
        5. Se tem publicações → calcular similaridade → identidade_duvidosa (score variável)
        
        Args:
            publicacao: Publicação prata a verificar
            score_minimo: Score mínimo personalizado
            
        Returns:
            ResultadoDeduplicacao: Resultado da verificação
        """
        try:
            logger.info(f"Verificando duplicata para hash {publicacao.hash_unica[:16]}...")
            
            # 1. Verificar hash exata
            hash_existente = self._buscar_hash_exata(publicacao.hash_unica)
            
            if hash_existente:
                # Hash encontrada - é duplicata exata
                logger.info(f"✅ Hash exata encontrada - publicação repetida")
                return self._criar_resultado_duplicata_exata(
                    publicacao,
                    hash_existente
                )
            
            # 2. Buscar publicações do mesmo processo
            publicacoes_processo = self._buscar_publicacoes_processo(
                publicacao.numero_processo_limpo,
                publicacao.data_publicacao
            )
            
            if not publicacoes_processo:
                # Nenhuma publicação do processo - é inédita
                logger.info(f"✅ Nenhuma publicação encontrada para o processo - publicação inédita")
                return self._criar_resultado_inedita(publicacao)
            
            # 3. Calcular similaridade com publicações existentes
            logger.info(f"Calculando similaridade com {len(publicacoes_processo)} publicações do processo")
            
            resultado_similaridade = self._calcular_similaridade_multipla(
                publicacao,
                publicacoes_processo,
                score_minimo or self.score_minimo_similar
            )
            
            return resultado_similaridade
            
        except Exception as e:
            logger.error(f"Erro na verificação de duplicata: {e}")
            raise
    
    def _buscar_hash_exata(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Busca hash exata no banco
        
        Args:
            hash_value: Valor da hash
            
        Returns:
            dict: Documento da hash se encontrado
        """
        return self.col_hashes.find_one({'hash_value': hash_value})
    
    def _buscar_publicacoes_processo(
        self,
        numero_processo: str,
        data_publicacao: datetime
    ) -> List[Dict[str, Any]]:
        """
        Busca publicações do mesmo processo
        
        Args:
            numero_processo: Número do processo limpo
            data_publicacao: Data da publicação
            
        Returns:
            list: Lista de publicações encontradas
        """
        # Define janela temporal
        data_inicio = data_publicacao - timedelta(days=self.janela_temporal_dias)
        data_fim = data_publicacao + timedelta(days=self.janela_temporal_dias)
        
        # Busca publicações
        query = {
            'numero_processo_limpo': numero_processo,
            'data_publicacao': {
                '$gte': data_inicio,
                '$lte': data_fim
            }
        }
        
        publicacoes = list(self.col_publicacoes_prata.find(query))
        logger.debug(f"Encontradas {len(publicacoes)} publicações para o processo {numero_processo}")
        
        return publicacoes
    
    def _calcular_similaridade_multipla(
        self,
        publicacao: PublicacaoPrata,
        publicacoes_existentes: List[Dict[str, Any]],
        score_minimo: float
    ) -> ResultadoDeduplicacao:
        """
        Calcula similaridade com múltiplas publicações
        
        Args:
            publicacao: Publicação a verificar
            publicacoes_existentes: Lista de publicações existentes
            score_minimo: Score mínimo para considerar similar
            
        Returns:
            ResultadoDeduplicacao: Resultado da análise
        """
        publicacoes_similares = []
        maior_score = 0.0
        publicacao_mais_similar = None
        
        for pub_existente in publicacoes_existentes:
            # Calcula score de similaridade
            score = self._calcular_score_fuzzy(
                publicacao.texto_limpo,
                pub_existente.get('texto_limpo', '')
            )
            
            if score >= score_minimo:
                publicacoes_similares.append({
                    'publicacao_id': str(pub_existente['_id']),
                    'score': score,
                    'data_publicacao': pub_existente['data_publicacao'],
                    'numero_processo': pub_existente.get('numero_processo_limpo', pub_existente.get('numero_processo')),
                    'tribunal': pub_existente.get('tribunal'),
                    'status': pub_existente.get('status'),
                    'hash_unica': pub_existente.get('hash_unica')
                })
                
                if score > maior_score:
                    maior_score = score
                    publicacao_mais_similar = pub_existente
        
        # Determina status baseado no score
        if maior_score >= self.score_minimo_duplicata:
            status = "repetida"
            justificativa = f"Publicação com similaridade de {maior_score:.1f}% encontrada"
        elif maior_score >= self.score_minimo_similar:
            status = "identidade_duvidosa"
            justificativa = f"Publicações similares encontradas (maior score: {maior_score:.1f}%)"
        else:
            status = "nova_publicacao_inedita"
            justificativa = "Publicação com baixa similaridade às existentes"
        
        # Ordena publicações similares por score
        publicacoes_similares.sort(key=lambda x: x['score'], reverse=True)
        
        return ResultadoDeduplicacao(
            publicacao_id=str(publicacao.publicacao_bronze_id),
            eh_duplicata=maior_score >= self.score_minimo_duplicata,
            hash_unica=publicacao.hash_unica,
            publicacao_original_id=str(publicacao_mais_similar['_id']) if publicacao_mais_similar else None,
            score_similaridade=maior_score,
            publicacoes_similares=publicacoes_similares[:10],  # Top 10 similares
            status_recomendado=status,
            justificativa=justificativa,
            timestamp_analise=datetime.now()
        )
    
    def _calcular_score_fuzzy(self, texto1: str, texto2: str) -> float:
        """
        Calcula score de similaridade entre dois textos usando fuzzy matching
        
        Usa combinação de algoritmos:
        - Levenshtein distance
        - SequenceMatcher
        - Jaccard similarity
        
        Args:
            texto1: Primeiro texto
            texto2: Segundo texto
            
        Returns:
            float: Score de similaridade (0-100)
        """
        if not texto1 or not texto2:
            return 0.0
        
        # Limita tamanho para performance
        texto1_truncado = texto1[:5000]
        texto2_truncado = texto2[:5000]
        
        scores = []
        
        # 1. Levenshtein ratio (mais preciso)
        try:
            levenshtein_ratio = Levenshtein.ratio(texto1_truncado, texto2_truncado)
            scores.append(levenshtein_ratio)
        except Exception as e:
            logger.warning(f"Erro no cálculo Levenshtein: {e}")
        
        # 2. SequenceMatcher (built-in Python)
        sequence_ratio = SequenceMatcher(None, texto1_truncado, texto2_truncado).ratio()
        scores.append(sequence_ratio)
        
        # 3. Jaccard similarity (baseado em palavras)
        palavras1 = set(texto1_truncado.split())
        palavras2 = set(texto2_truncado.split())
        
        if palavras1 or palavras2:
            intersecao = palavras1.intersection(palavras2)
            uniao = palavras1.union(palavras2)
            jaccard = len(intersecao) / len(uniao) if uniao else 0
            scores.append(jaccard)
        
        # Calcula média ponderada dos scores
        if scores:
            # Peso maior para Levenshtein se disponível
            if len(scores) == 3:
                score_final = (scores[0] * 0.5 + scores[1] * 0.3 + scores[2] * 0.2)
            else:
                score_final = sum(scores) / len(scores)
        else:
            score_final = 0.0
        
        return score_final * 100  # Converte para percentual
    
    def _criar_resultado_duplicata_exata(
        self,
        publicacao: PublicacaoPrata,
        hash_doc: Dict[str, Any]
    ) -> ResultadoDeduplicacao:
        """
        Cria resultado para duplicata exata
        
        Args:
            publicacao: Publicação verificada
            hash_doc: Documento da hash encontrada
            
        Returns:
            ResultadoDeduplicacao: Resultado
        """
        # Buscar todas as publicações com a mesma hash
        publicacoes_com_mesma_hash = list(self.col_hashes.find({
            'hash_value': publicacao.hash_unica
        }))
        
        # Criar lista de publicações similares com todas as correspondências
        publicacoes_similares = []
        for doc in publicacoes_com_mesma_hash:
            # Buscar informações adicionais da publicação prata se necessário
            pub_prata = self.col_publicacoes_prata.find_one({
                '_id': ObjectId(doc['publicacao_prata_id'])
            })
            
            similar_info = {
                'publicacao_id': str(doc['publicacao_prata_id']),
                'score': 100.0,
                'data_publicacao': doc.get('data_publicacao'),
                'numero_processo': doc.get('numero_processo')
            }
            
            # Adicionar informações adicionais se a publicação prata foi encontrada
            if pub_prata:
                similar_info['status'] = pub_prata.get('status')
                similar_info['tribunal'] = pub_prata.get('tribunal')
                
            publicacoes_similares.append(similar_info)
        
        # Ordenar por data de publicação (mais recente primeiro)
        publicacoes_similares.sort(
            key=lambda x: x.get('data_publicacao', datetime.min), 
            reverse=True
        )
        
        return ResultadoDeduplicacao(
            publicacao_id=str(publicacao.publicacao_bronze_id),
            eh_duplicata=True,
            hash_unica=publicacao.hash_unica,
            publicacao_original_id=str(hash_doc['publicacao_prata_id']),
            score_similaridade=100.0,
            publicacoes_similares=publicacoes_similares,
            status_recomendado="repetida",
            justificativa=f"Hash exata encontrada - {len(publicacoes_similares)} publicação(ões) duplicada(s)",
            timestamp_analise=datetime.now()
        )
    
    def _criar_resultado_inedita(self, publicacao: PublicacaoPrata) -> ResultadoDeduplicacao:
        """
        Cria resultado para publicação inédita
        
        Args:
            publicacao: Publicação verificada
            
        Returns:
            ResultadoDeduplicacao: Resultado
        """
        return ResultadoDeduplicacao(
            publicacao_id=str(publicacao.publicacao_bronze_id),
            eh_duplicata=False,
            hash_unica=publicacao.hash_unica,
            publicacao_original_id=None,
            score_similaridade=0.0,
            publicacoes_similares=[],
            status_recomendado="nova_publicacao_inedita",
            justificativa="Nenhuma publicação similar encontrada para este processo",
            timestamp_analise=datetime.now()
        )
    
    def registrar_hash(self, publicacao: PublicacaoPrata) -> str:
        """
        Registra hash de uma publicação no índice
        
        Args:
            publicacao: Publicação com hash a registrar
            
        Returns:
            str: ID do documento inserido
        """
        try:
            hash_doc = HashDeduplicacao(
                hash_value=publicacao.hash_unica,
                publicacao_prata_id=publicacao.publicacao_bronze_id,
                numero_processo=publicacao.numero_processo_limpo,
                data_publicacao=publicacao.data_publicacao,
                timestamp_criacao=datetime.now()
            )
            
            result = self.col_hashes.insert_one(hash_doc.dict())
            logger.info(f"Hash registrada: {publicacao.hash_unica[:16]}...")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Erro ao registrar hash: {e}")
            raise
    
    def buscar_publicacoes_similares(
        self,
        texto: str,
        limite: int = 10,
        score_minimo: float = 70.0
    ) -> List[Dict[str, Any]]:
        """
        Busca publicações similares baseado em texto
        
        Args:
            texto: Texto para busca
            limite: Número máximo de resultados
            score_minimo: Score mínimo de similaridade
            
        Returns:
            list: Lista de publicações similares
        """
        try:
            # Busca usando índice de texto
            publicacoes = self.col_publicacoes_prata.find(
                {'$text': {'$search': texto[:1000]}},
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})]).limit(limite * 2)
            
            # Calcula score fuzzy para refinamento
            resultados = []
            for pub in publicacoes:
                score_fuzzy = self._calcular_score_fuzzy(
                    texto,
                    pub.get('texto_limpo', '')
                )
                
                if score_fuzzy >= score_minimo:
                    pub['score_similaridade'] = score_fuzzy
                    resultados.append(pub)
            
            # Ordena por score e limita
            resultados.sort(key=lambda x: x['score_similaridade'], reverse=True)
            
            return resultados[:limite]
            
        except Exception as e:
            logger.error(f"Erro na busca de publicações similares: {e}")
            return []
    
    def atualizar_status_duplicata(
        self,
        publicacao_id: str,
        status: str,
        score: float,
        publicacoes_similares: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Atualiza status de duplicata de uma publicação
        
        Args:
            publicacao_id: ID da publicação
            status: Novo status
            score: Score de similaridade
            publicacoes_similares: Lista de publicações similares
            
        Returns:
            bool: True se atualizado com sucesso
        """
        try:
            update_doc = {
                '$set': {
                    'status': status,
                    'score_similaridade': score,
                    'timestamp_verificacao': datetime.now()
                }
            }
            
            if publicacoes_similares:
                update_doc['$set']['publicacoes_similares'] = publicacoes_similares
            
            result = self.col_publicacoes_prata.update_one(
                {'_id': ObjectId(publicacao_id)},
                update_doc
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status de duplicata: {e}")
            return False