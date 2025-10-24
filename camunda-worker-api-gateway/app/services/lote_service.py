"""
Serviço de gerenciamento de lotes de publicações
Implementa o processamento de lotes conforme BPMN
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bson import ObjectId

from pymongo import MongoClient, UpdateOne

from models.publicacao import (
    Lote,
    PublicacaoBronze,
    PublicacaoPrata,
    ProcessamentoLoteResponse,
)
from services.publicacao_service import PublicacaoService
from services.deduplicacao_service import DeduplicacaoService

logger = logging.getLogger(__name__)


class LoteService:
    """Serviço para gerenciamento de lotes de publicações"""

    def __init__(
        self,
        mongo_client: MongoClient,
        publicacao_service: PublicacaoService = None,
        deduplicacao_service: DeduplicacaoService = None,
        database_name: str = "worker_gateway",
    ):
        """
        Inicializa o serviço de lotes

        Args:
            mongo_client: Cliente MongoDB
            publicacao_service: Serviço de publicações
            deduplicacao_service: Serviço de deduplicação
            database_name: Nome do banco de dados
        """
        self.client = mongo_client
        self.db = mongo_client[database_name]

        # Coleções
        self.col_lotes = self.db["lotes"]
        self.col_publicacoes_bronze = self.db["publicacoes_bronze"]
        self.col_publicacoes_prata = self.db["publicacoes_prata"]
        self.col_execucoes = self.db["execucoes"]
        self.col_hashes = self.db["hashes"]

        # Serviços
        self.publicacao_service = publicacao_service or PublicacaoService()
        self.deduplicacao_service = deduplicacao_service or DeduplicacaoService(
            mongo_client, database_name
        )

    def criar_lote(
        self,
        execucao_id: str,
        publicacoes: List[Dict[str, Any]],
        cod_grupo: int = 5,
        data_inicial: str = None,
        data_final: str = None,
    ) -> str:
        """
        Cria um novo lote de publicações

        Args:
            execucao_id: ID da execução
            publicacoes: Lista de publicações do lote
            cod_grupo: Código do grupo
            data_inicial: Data inicial da busca
            data_final: Data final da busca

        Returns:
            str: ID do lote criado
        """
        try:
            logger.info(f"Criando lote com {len(publicacoes)} publicações")

            # Cria documento do lote
            lote = Lote(
                execucao_id=execucao_id,
                total_publicacoes=len(publicacoes),
                cod_grupo=cod_grupo,
                data_inicial=data_inicial,
                data_final=data_final,
                status="pendente",
                timestamp_criacao=datetime.now(),
            )

            # Insere lote
            result_lote = self.col_lotes.insert_one(lote.dict())
            lote_id = str(result_lote.inserted_id)

            logger.info(f"Lote criado: {lote_id}")

            # Salva publicações bronze
            if publicacoes:
                self._salvar_publicacoes_bronze(lote_id, publicacoes)

            return lote_id

        except Exception as e:
            logger.error(f"Erro ao criar lote: {e}")
            raise

    def _salvar_publicacoes_bronze(
        self, lote_id: str, publicacoes: List[Dict[str, Any]]
    ):
        """
        Salva publicações na tabela bronze

        Args:
            lote_id: ID do lote
            publicacoes: Lista de publicações
        """
        try:
            documentos_bronze = []

            for pub_data in publicacoes:
                # Cria publicação bronze
                pub_bronze = PublicacaoBronze(
                    lote_id=lote_id,
                    cod_publicacao=pub_data.get("cod_publicacao"),
                    numero_processo=pub_data.get("numero_processo"),
                    data_publicacao=pub_data.get("data_publicacao"),
                    texto_publicacao=pub_data.get("texto_publicacao"),
                    fonte=pub_data.get("fonte", "dw"),
                    tribunal=pub_data.get("tribunal", "tjmg"),
                    instancia=pub_data.get("instancia", "1"),
                    descricao_diario=pub_data.get("descricao_diario"),
                    uf_publicacao=pub_data.get("uf_publicacao"),
                    # Novos campos
                    ano_publicacao=pub_data.get("ano_publicacao"),
                    edicao_diario=pub_data.get("edicao_diario"),
                    pagina_inicial=pub_data.get("pagina_inicial"),
                    pagina_final=pub_data.get("pagina_final"),
                    data_divulgacao=pub_data.get("data_divulgacao"),
                    data_cadastro=pub_data.get("data_cadastro"),
                    cidade_publicacao=pub_data.get("cidade_publicacao"),
                    orgao_descricao=pub_data.get("orgao_descricao"),
                    vara_descricao=pub_data.get("vara_descricao"),
                    despacho_publicacao=pub_data.get("despacho_publicacao"),
                    processo_publicacao=pub_data.get("processo_publicacao"),
                    publicacao_corrigida=pub_data.get("publicacao_corrigida"),
                    cod_vinculo=pub_data.get("cod_vinculo"),
                    nome_vinculo=pub_data.get("nome_vinculo"),
                    oab_numero=pub_data.get("oab_numero"),
                    oab_estado=pub_data.get("oab_estado"),
                    diario_sigla_wj=pub_data.get("diario_sigla_wj"),
                    anexo=pub_data.get("anexo"),
                    cod_integracao=pub_data.get("cod_integracao"),
                    publicacao_exportada=pub_data.get("publicacao_exportada"),
                    cod_grupo=pub_data.get("cod_grupo"),
                    status="nova",
                )

                documentos_bronze.append(pub_bronze.dict())

            # Insere em batch
            if documentos_bronze:
                result = self.col_publicacoes_bronze.insert_many(documentos_bronze)
                logger.info(f"✅ {len(result.inserted_ids)} publicações bronze salvas")

                # Atualiza lote com IDs das publicações
                self.col_lotes.update_one(
                    {"_id": ObjectId(lote_id)},
                    {
                        "$set": {
                            "publicacoes_ids": [str(id) for id in result.inserted_ids]
                        }
                    },
                )

        except Exception as e:
            logger.error(f"Erro ao salvar publicações bronze: {e}")
            raise

    def buscar_lote_por_id(self, lote_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um lote por ID

        Args:
            lote_id: ID do lote

        Returns:
            dict: Dados do lote com publicações
        """
        try:
            # Busca lote
            lote = self.col_lotes.find_one({"_id": ObjectId(lote_id)})

            if not lote:
                logger.warning(f"Lote {lote_id} não encontrado")
                return None

            # Busca publicações do lote
            publicacoes = list(self.col_publicacoes_bronze.find({"lote_id": lote_id}))

            lote["publicacoes"] = publicacoes
            lote["_id"] = str(lote["_id"])

            return lote

        except Exception as e:
            logger.error(f"Erro ao buscar lote {lote_id}: {e}")
            return None

    def processar_lote(
        self,
        lote_id: str,
        processar_em_paralelo: bool = True,
        max_paralelo: int = 10,
        continuar_em_erro: bool = True,
        executar_classificacao: bool = True,
        executar_deduplicacao: bool = True,
    ) -> ProcessamentoLoteResponse:
        """
        Processa todas as publicações de um lote

        Fluxo:
        1. Busca publicações bronze do lote
        2. Para cada publicação:
           - Higieniza (Bronze → Prata)
           - Verifica duplicatas
           - Classifica
           - Salva resultado
        3. Atualiza estatísticas do lote

        Args:
            lote_id: ID do lote
            processar_em_paralelo: Se deve processar em paralelo
            max_paralelo: Máximo de threads paralelas
            continuar_em_erro: Se deve continuar em caso de erro
            executar_classificacao: Se deve classificar
            executar_deduplicacao: Se deve verificar duplicatas

        Returns:
            ProcessamentoLoteResponse: Resultado do processamento
        """
        timestamp_inicio = datetime.now()
        logger.info(f"🚀 Iniciando processamento do lote {lote_id}")

        try:
            # Atualiza status do lote
            self.col_lotes.update_one(
                {"_id": ObjectId(lote_id)},
                {
                    "$set": {
                        "status": "processando",
                        "timestamp_inicio_processamento": timestamp_inicio,
                    }
                },
            )

            # Busca publicações bronze do lote
            publicacoes_bronze = list(
                self.col_publicacoes_bronze.find(
                    {"lote_id": lote_id, "status": {"$ne": "processada"}}
                )
            )

            if not publicacoes_bronze:
                logger.info("Nenhuma publicação pendente no lote")
                return self._criar_resposta_vazia(lote_id, timestamp_inicio)

            logger.info(f"📦 {len(publicacoes_bronze)} publicações a processar")

            # Processa publicações
            if processar_em_paralelo and len(publicacoes_bronze) > 1:
                resultados = self._processar_paralelo(
                    publicacoes_bronze,
                    max_paralelo,
                    continuar_em_erro,
                    executar_classificacao,
                    executar_deduplicacao,
                )
            else:
                resultados = self._processar_sequencial(
                    publicacoes_bronze,
                    continuar_em_erro,
                    executar_classificacao,
                    executar_deduplicacao,
                )

            # Atualiza estatísticas do lote
            timestamp_fim = datetime.now()
            self._atualizar_estatisticas_lote(lote_id, resultados, timestamp_fim)

            # Cria resposta
            return self._criar_resposta_processamento(
                lote_id, timestamp_inicio, timestamp_fim, publicacoes_bronze, resultados
            )

        except Exception as e:
            logger.error(f"❌ Erro no processamento do lote: {e}")

            # Atualiza status de erro
            self.col_lotes.update_one(
                {"_id": ObjectId(lote_id)},
                {"$set": {"status": "erro", "erro_mensagem": str(e)}},
            )

            raise

    def _processar_publicacao(
        self,
        pub_bronze_doc: Dict[str, Any],
        executar_classificacao: bool,
        executar_deduplicacao: bool,
    ) -> Dict[str, Any]:
        """
        Processa uma publicação individual

        Args:
            pub_bronze_doc: Documento da publicação bronze
            executar_classificacao: Se deve classificar
            executar_deduplicacao: Se deve verificar duplicatas

        Returns:
            dict: Resultado do processamento
        """
        try:
            # Converte para modelo
            pub_bronze = PublicacaoBronze(**pub_bronze_doc)

            # 1. Higieniza publicação
            pub_prata = self.publicacao_service.higienizar_publicacao(pub_bronze)

            # 2. Verifica duplicatas
            if executar_deduplicacao:
                resultado_dedup = self.deduplicacao_service.verificar_duplicata(
                    pub_prata
                )
                pub_prata.status = resultado_dedup.status_recomendado
                pub_prata.score_similaridade = resultado_dedup.score_similaridade
                pub_prata.publicacoes_similares = resultado_dedup.publicacoes_similares

            # 3. Classifica publicação
            if executar_classificacao:
                tipo, confianca = self.publicacao_service.identificar_tipo_publicacao(
                    pub_prata.texto_limpo
                )
                urgente, prazo = self.publicacao_service.calcular_urgencia(
                    pub_prata.texto_limpo, tipo
                )
                entidades = self.publicacao_service.extrair_entidades(
                    pub_prata.texto_limpo
                )

                pub_prata.classificacao = {
                    "tipo": tipo,
                    "urgente": urgente,
                    "prazo_dias": prazo,
                    "confianca": confianca,
                    "entidades": entidades,
                }

            # 4. Salva publicação prata
            result_prata = self.col_publicacoes_prata.insert_one(pub_prata.dict())

            # 5. Registra hash se não for duplicata
            if pub_prata.status != "repetida":
                self.deduplicacao_service.registrar_hash(pub_prata)

            # 6. Atualiza status da publicação bronze
            self.col_publicacoes_bronze.update_one(
                {"_id": pub_bronze_doc["_id"]}, {"$set": {"status": "processada"}}
            )

            return {
                "success": True,
                "publicacao_bronze_id": str(pub_bronze_doc["_id"]),
                "publicacao_prata_id": str(result_prata.inserted_id),
                "status": pub_prata.status,
                "score": pub_prata.score_similaridade,
            }

        except Exception as e:
            logger.error(
                f"Erro ao processar publicação {pub_bronze_doc.get('cod_publicacao')}: {e}"
            )
            return {
                "success": False,
                "publicacao_bronze_id": str(pub_bronze_doc["_id"]),
                "erro": str(e),
            }

    def _processar_paralelo(
        self,
        publicacoes: List[Dict[str, Any]],
        max_paralelo: int,
        continuar_em_erro: bool,
        executar_classificacao: bool,
        executar_deduplicacao: bool,
    ) -> List[Dict[str, Any]]:
        """Processa publicações em paralelo"""
        resultados = []

        with ThreadPoolExecutor(max_workers=max_paralelo) as executor:
            futures = {
                executor.submit(
                    self._processar_publicacao,
                    pub,
                    executar_classificacao,
                    executar_deduplicacao,
                ): pub
                for pub in publicacoes
            }

            for future in as_completed(futures):
                try:
                    resultado = future.result()
                    resultados.append(resultado)
                except Exception as e:
                    if not continuar_em_erro:
                        raise
                    logger.error(f"Erro em processamento paralelo: {e}")
                    resultados.append({"success": False, "erro": str(e)})

        return resultados

    def _processar_sequencial(
        self,
        publicacoes: List[Dict[str, Any]],
        continuar_em_erro: bool,
        executar_classificacao: bool,
        executar_deduplicacao: bool,
    ) -> List[Dict[str, Any]]:
        """Processa publicações sequencialmente"""
        resultados = []

        for pub in publicacoes:
            try:
                resultado = self._processar_publicacao(
                    pub, executar_classificacao, executar_deduplicacao
                )
                resultados.append(resultado)
            except Exception as e:
                if not continuar_em_erro:
                    raise
                logger.error(f"Erro em processamento sequencial: {e}")
                resultados.append(
                    {
                        "success": False,
                        "publicacao_bronze_id": str(pub["_id"]),
                        "erro": str(e),
                    }
                )

        return resultados

    def _atualizar_estatisticas_lote(
        self, lote_id: str, resultados: List[Dict[str, Any]], timestamp_fim: datetime
    ):
        """Atualiza estatísticas do lote após processamento"""

        # Calcula estatísticas
        total_sucesso = sum(1 for r in resultados if r.get("success"))
        total_erro = len(resultados) - total_sucesso

        # Conta por status
        status_count = {}
        for r in resultados:
            if r.get("success"):
                status = r.get("status", "desconhecido")
                status_count[status] = status_count.get(status, 0) + 1

        # Atualiza lote
        self.col_lotes.update_one(
            {"_id": ObjectId(lote_id)},
            {
                "$set": {
                    "status": (
                        "processado" if total_erro == 0 else "processado_com_erros"
                    ),
                    "timestamp_fim_processamento": timestamp_fim,
                    "estatisticas": {
                        "total": len(resultados),
                        "processadas": total_sucesso,
                        "erros": total_erro,
                        "por_status": status_count,
                    },
                }
            },
        )

    def _criar_resposta_processamento(
        self,
        lote_id: str,
        timestamp_inicio: datetime,
        timestamp_fim: datetime,
        publicacoes_bronze: List[Dict[str, Any]],
        resultados: List[Dict[str, Any]],
    ) -> ProcessamentoLoteResponse:
        """Cria resposta do processamento"""

        # Estatísticas
        total_sucesso = sum(1 for r in resultados if r.get("success"))
        total_erro = len(resultados) - total_sucesso

        # Estatísticas por status
        estatisticas_status = {}
        publicacoes_prata_ids = []
        erros = []

        for r in resultados:
            if r.get("success"):
                status = r.get("status", "desconhecido")
                estatisticas_status[status] = estatisticas_status.get(status, 0) + 1
                if r.get("publicacao_prata_id"):
                    publicacoes_prata_ids.append(r["publicacao_prata_id"])
            else:
                erros.append(
                    {
                        "publicacao_id": r.get("publicacao_bronze_id"),
                        "erro": r.get("erro"),
                    }
                )

        return ProcessamentoLoteResponse(
            lote_id=lote_id,
            timestamp_inicio=timestamp_inicio,
            timestamp_fim=timestamp_fim,
            duracao_segundos=(timestamp_fim - timestamp_inicio).total_seconds(),
            total_publicacoes=len(publicacoes_bronze),
            processadas_sucesso=total_sucesso,
            processadas_erro=total_erro,
            estatisticas_status=estatisticas_status,
            erros=erros,
            publicacoes_prata_ids=publicacoes_prata_ids,
        )

    def _criar_resposta_vazia(
        self, lote_id: str, timestamp_inicio: datetime
    ) -> ProcessamentoLoteResponse:
        """Cria resposta vazia quando não há publicações"""
        timestamp_fim = datetime.now()

        return ProcessamentoLoteResponse(
            lote_id=lote_id,
            timestamp_inicio=timestamp_inicio,
            timestamp_fim=timestamp_fim,
            duracao_segundos=(timestamp_fim - timestamp_inicio).total_seconds(),
            total_publicacoes=0,
            processadas_sucesso=0,
            processadas_erro=0,
            estatisticas_status={},
            erros=[],
            publicacoes_prata_ids=[],
        )
