#!/usr/bin/env python3
"""
CPJ API Worker - Worker Unificado para API CPJ-3C
Gerencia todos os 21 endpoints da API em um único worker
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from common.cpj_auth_manager import CPJAuthManager
from camunda.external_task.external_task import ExternalTask

from handlers import (
    AuthHandlers, PessoasHandlers, ProcessosHandlers,
    PublicacoesHandlers, PedidosHandlers, EnvolvidosHandlers,
    TramitacaoHandlers, DocumentosHandlers
)

logger = logging.getLogger(__name__)


class CPJAPIWorker(BaseWorker):
    """Worker Unificado para API CPJ-3C - 22 tópicos, 21 endpoints"""

    def __init__(self):
        super().__init__(
            worker_id="cpj-api-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth(),
        )

        # Configurações CPJ
        cpj_base_url = os.getenv("CPJ_API_BASE_URL", "https://ip:porta/api/v2")
        cpj_user = os.getenv("CPJ_API_USER", "1")
        cpj_pass = os.getenv("CPJ_API_PASSWORD", "abc")

        # Gerenciador de autenticação
        self.cpj_auth = CPJAuthManager(cpj_base_url, cpj_user, cpj_pass)

        # Inicializar handlers
        self.auth = AuthHandlers(self, self.cpj_auth)
        self.pessoas = PessoasHandlers(self)
        self.processos = ProcessosHandlers(self)
        self.publicacoes = PublicacoesHandlers(self)
        self.pedidos = PedidosHandlers(self)
        self.envolvidos = EnvolvidosHandlers(self)
        self.tramitacao = TramitacaoHandlers(self)
        self.documentos = DocumentosHandlers(self)

        # Subscribe a todos os tópicos
        self.subscribe_multiple({
            # Autenticação
            Topics.CPJ_LOGIN: self.auth.handle_login,
            Topics.CPJ_REFRESH_TOKEN: self.auth.handle_refresh_token,
            
            # Publicações
            Topics.CPJ_BUSCAR_PUBLICACOES_NAO_VINCULADAS: self.publicacoes.handle_buscar_publicacoes,
            Topics.CPJ_ATUALIZAR_PUBLICACAO: self.publicacoes.handle_atualizar_publicacao,
            
            # Pessoas
            Topics.CPJ_CONSULTAR_PESSOA: self.pessoas.handle_consultar_pessoa,
            Topics.CPJ_CADASTRAR_PESSOA: self.pessoas.handle_cadastrar_pessoa,
            Topics.CPJ_ATUALIZAR_PESSOA: self.pessoas.handle_atualizar_pessoa,
            
            # Processos
            Topics.CPJ_CONSULTAR_PROCESSOS: self.processos.handle_consultar_processos,
            Topics.CPJ_CADASTRAR_PROCESSO: self.processos.handle_cadastrar_processo,
            Topics.CPJ_ATUALIZAR_PROCESSO: self.processos.handle_atualizar_processo,
            
            # Pedidos
            Topics.CPJ_CONSULTAR_PEDIDOS: self.pedidos.handle_consultar_pedidos,
            Topics.CPJ_CADASTRAR_PEDIDO: self.pedidos.handle_cadastrar_pedido,
            Topics.CPJ_ATUALIZAR_PEDIDO: self.pedidos.handle_atualizar_pedido,
            
            # Envolvidos
            Topics.CPJ_CONSULTAR_ENVOLVIDOS: self.envolvidos.handle_consultar_envolvidos,
            Topics.CPJ_CADASTRAR_ENVOLVIDO: self.envolvidos.handle_cadastrar_envolvido,
            Topics.CPJ_ATUALIZAR_ENVOLVIDO: self.envolvidos.handle_atualizar_envolvido,
            
            # Tramitação
            Topics.CPJ_CADASTRAR_ANDAMENTO: self.tramitacao.handle_cadastrar_andamento,
            Topics.CPJ_CADASTRAR_TAREFA: self.tramitacao.handle_cadastrar_tarefa,
            Topics.CPJ_ATUALIZAR_TAREFA: self.tramitacao.handle_atualizar_tarefa,
            
            # Documentos
            Topics.CPJ_CONSULTAR_DOCUMENTOS: self.documentos.handle_consultar_documentos,
            Topics.CPJ_BAIXAR_DOCUMENTO: self.documentos.handle_baixar_documento,
            Topics.CPJ_CADASTRAR_DOCUMENTO: self.documentos.handle_cadastrar_documento,
        })

        self.logger.info("🔍 CPJAPIWorker iniciado - 22 tópicos CPJ-3C")


def main():
    try:
        log_level = getattr(logging, WorkerConfig.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        logger.info("🚀 Iniciando CPJAPIWorker...")
        WorkerConfig.validate_config()
        
        worker = CPJAPIWorker()
        logger.info("✅ Worker iniciado - Monitorando 22 tópicos")
        
        worker.start()

    except KeyboardInterrupt:
        logger.info("⏹️  Worker interrompido")
    except Exception as e:
        logger.error(f"💥 Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
