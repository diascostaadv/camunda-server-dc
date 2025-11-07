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
    PublicacaoPrata,
    ProcessamentoLoteResponse,
)
from models.auditoria import StatusMarcacao
from services.publicacao_service import PublicacaoService
from services.deduplicacao_service import DeduplicacaoService
from services.auditoria_service import AuditoriaService
from services.intimation_service import IntimationService

logger = logging.getLogger(__name__)


class LoteService:
    """Serviço para gerenciamento de lotes de publicações"""

    def __init__(
        self,
        mongo_client: MongoClient,
        publicacao_service: PublicacaoService = None,
        deduplicacao_service: DeduplicacaoService = None,
        intimation_service: IntimationService = None,
        auditoria_service: AuditoriaService = None,
        database_name: str = "worker_gateway",
        marcar_automaticamente: bool = True,
    ):
        """
        Inicializa o serviço de lotes

        Args:
            mongo_client: Cliente MongoDB
            publicacao_service: Serviço de publicações
            deduplicacao_service: Serviço de deduplicação
            intimation_service: Serviço de marcação Webjur
            auditoria_service: Serviço de auditoria
            database_name: Nome do banco de dados
            marcar_automaticamente: Se deve marcar como exportada ao salvar
        """
        self.client = mongo_client
        self.db = mongo_client[database_name]
        self.marcar_automaticamente = marcar_automaticamente

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
        self.intimation_service = intimation_service
        self.auditoria_service = auditoria_service or AuditoriaService(
            mongo_client, database_name
        )

    def criar_lote(
        self,
        execucao_id: str,
        publicacoes: List[Dict[str, Any]],
        cod_grupo: int = 5,
        data_inicial: str = None,
        data_final: str = None,
        chunk_size: int = 200,
    ) -> str:
        """
        Cria um novo lote de publicações

        Args:
            execucao_id: ID da execução
            publicacoes: Lista de publicações do lote
            cod_grupo: Código do grupo
            data_inicial: Data inicial da busca
            data_final: Data final da busca
            chunk_size: Tamanho dos chunks para processamento (padrão: 200)

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
                self._salvar_publicacoes_bronze(lote_id, publicacoes, chunk_size)

            return lote_id

        except Exception as e:
            logger.error(f"Erro ao criar lote: {e}")
            raise

    def _salvar_publicacoes_bronze(
        self, lote_id: str, publicacoes: List[Dict[str, Any]], chunk_size: int = 200
    ):
        """
        Salva publicações na tabela bronze em chunks

        Salva dados da Webjur diretamente como dicionários sem validação Pydantic
        para máxima flexibilidade com campos dinâmicos.

        Processa em chunks para evitar problemas de memória e timeouts com volumes grandes.

        Args:
            lote_id: ID do lote
            publicacoes: Lista de publicações
            chunk_size: Tamanho dos chunks para processamento (padrão: 200)
        """
        try:
            total_publicacoes = len(publicacoes)
            all_inserted_ids = []

            # Processa em chunks
            num_chunks = (total_publicacoes + chunk_size - 1) // chunk_size

            if num_chunks > 1:
                logger.info(
                    f"📦 Processando {total_publicacoes} publicações em {num_chunks} chunks de até {chunk_size}"
                )

            for i in range(0, total_publicacoes, chunk_size):
                chunk = publicacoes[i : i + chunk_size]
                chunk_num = (i // chunk_size) + 1

                documentos_bronze = []
                for pub_data in chunk:
                    # Adiciona campos de controle essenciais
                    documento_bronze = {
                        **pub_data,  # Mantém todos os campos originais da Webjur
                        "lote_id": lote_id,
                        "timestamp_insercao": datetime.now(),
                        "status": "nova",
                    }
                    documentos_bronze.append(documento_bronze)

                # Insere chunk em batch
                if documentos_bronze:
                    result = self.col_publicacoes_bronze.insert_many(documentos_bronze)
                    all_inserted_ids.extend(result.inserted_ids)

                    if num_chunks > 1:
                        logger.info(
                            f"✅ Chunk {chunk_num}/{num_chunks}: {len(result.inserted_ids)} publicações salvas"
                        )

            # Log final
            logger.info(f"✅ Total: {len(all_inserted_ids)} publicações bronze salvas")

            # Atualiza lote com IDs das publicações
            self.col_lotes.update_one(
                {"_id": ObjectId(lote_id)},
                {"$set": {"publicacoes_ids": [str(id) for id in all_inserted_ids]}},
            )

            # NOVO: Marcar automaticamente como exportadas se habilitado
            if self.marcar_automaticamente and self.intimation_service:
                logger.info("🏷️ Marcação automática habilitada - iniciando processo...")
                self._marcar_publicacoes_automaticamente(
                    lote_id=lote_id,
                    publicacoes=publicacoes,
                    publicacoes_ids=all_inserted_ids,
                )

        except Exception as e:
            logger.error(f"Erro ao salvar publicações bronze: {e}")
            raise

    def _marcar_publicacoes_automaticamente(
        self,
        lote_id: str,
        publicacoes: List[Dict[str, Any]],
        publicacoes_ids: List[ObjectId],
    ):
        """
        Marca publicações como exportadas imediatamente após salvar

        Para cada publicação:
        1. Cria log de auditoria
        2. Tenta marcar no Webjur
        3. Atualiza MongoDB se sucesso
        4. Registra resultado no log de auditoria

        Args:
            lote_id: ID do lote
            publicacoes: Lista de publicações
            publicacoes_ids: IDs gerados no MongoDB
        """
        try:
            # Extrair códigos de publicação para marcação em lote
            codigos_publicacao = []
            publicacao_map = {}  # Mapeia cod_publicacao -> dados completos

            for i, pub_data in enumerate(publicacoes):
                cod_pub = pub_data.get("cod_publicacao")
                if cod_pub:
                    codigos_publicacao.append(cod_pub)
                    publicacao_map[cod_pub] = {
                        "dados": pub_data,
                        "mongodb_id": str(publicacoes_ids[i]),
                        "index": i,
                    }

            if not codigos_publicacao:
                logger.warning("Nenhum código de publicação válido para marcar")
                return

            total_para_marcar = len(codigos_publicacao)
            logger.info(
                f"📊 Iniciando marcação automática de {total_para_marcar} publicações do lote {lote_id}"
            )

            # Criar logs de auditoria para todas
            logs_map = {}  # cod_publicacao -> log_id
            for cod_pub in codigos_publicacao:
                pub_info = publicacao_map[cod_pub]
                try:
                    log_id = self.auditoria_service.iniciar_log_marcacao(
                        cod_publicacao=cod_pub,
                        lote_id=lote_id,
                        publicacao_bronze_id=pub_info["mongodb_id"],
                        snapshot_publicacao=pub_info["dados"],
                        contexto={"metadata": {"marcacao_automatica": True}},
                    )
                    logs_map[cod_pub] = log_id
                except Exception as e:
                    logger.error(f"Erro ao criar log para {cod_pub}: {e}")

            # Tentar marcar todas no Webjur em lote (mais eficiente)
            inicio = time.time()
            try:
                sucesso_webjur = self.intimation_service.set_publicacoes(codigos_publicacao)
                duracao_ms = (time.time() - inicio) * 1000

                if sucesso_webjur:
                    logger.info(
                        f"✅ Marcação Webjur bem-sucedida para {total_para_marcar} publicações em {duracao_ms:.2f}ms"
                    )

                    # Atualizar MongoDB em lote
                    bulk_updates = []
                    for cod_pub in codigos_publicacao:
                        bulk_updates.append(
                            UpdateOne(
                                {"cod_publicacao": cod_pub, "lote_id": lote_id},
                                {
                                    "$set": {
                                        "marcada_exportada_webjur": True,
                                        "timestamp_marcacao_exportada": datetime.now(),
                                        "marcacao_automatica": True,
                                    }
                                },
                            )
                        )

                    if bulk_updates:
                        result = self.col_publicacoes_bronze.bulk_write(bulk_updates)
                        logger.info(
                            f"💾 MongoDB atualizado: {result.modified_count} documentos"
                        )

                    # Registrar sucesso nos logs de auditoria
                    for cod_pub in codigos_publicacao:
                        if cod_pub in logs_map:
                            self.auditoria_service.marcar_como_sucesso(
                                log_id=logs_map[cod_pub],
                                duracao_ms=duracao_ms / total_para_marcar,
                                detalhes={
                                    "marcacao_em_lote": True,
                                    "total_no_lote": total_para_marcar,
                                },
                            )

                else:
                    logger.error(
                        f"❌ Falha na marcação Webjur para {total_para_marcar} publicações"
                    )

                    # Registrar falha nos logs
                    for cod_pub in codigos_publicacao:
                        if cod_pub in logs_map:
                            self.auditoria_service.marcar_como_falha(
                                log_id=logs_map[cod_pub],
                                status=StatusMarcacao.FALHA_WEBJUR,
                                mensagem_erro="Falha na chamada setPublicacoes() do Webjur",
                                duracao_ms=duracao_ms / total_para_marcar,
                                detalhes={
                                    "marcacao_em_lote": True,
                                    "total_no_lote": total_para_marcar,
                                },
                            )

            except Exception as e:
                logger.error(f"💥 Erro ao marcar publicações no Webjur: {e}")
                duracao_ms = (time.time() - inicio) * 1000

                # Registrar erro nos logs
                for cod_pub in codigos_publicacao:
                    if cod_pub in logs_map:
                        self.auditoria_service.marcar_como_falha(
                            log_id=logs_map[cod_pub],
                            status=StatusMarcacao.ERRO_INTERNO,
                            mensagem_erro=str(e),
                            duracao_ms=duracao_ms / total_para_marcar,
                            detalhes={
                                "marcacao_em_lote": True,
                                "total_no_lote": total_para_marcar,
                                "exception_type": type(e).__name__,
                            },
                        )

        except Exception as e:
            logger.error(f"💥 Erro fatal na marcação automática: {e}")
            # Não propaga exceção para não bloquear o salvamento

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
            # Trabalha diretamente com dicionário (sem validação Pydantic)
            # 1. Higieniza publicação
            pub_prata = self.publicacao_service.higienizar_publicacao(pub_bronze_doc)

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
