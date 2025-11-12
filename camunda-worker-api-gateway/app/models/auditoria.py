"""
Modelos para log de auditoria de marcação de publicações
Registra todo o histórico de tentativas de marcação com detalhes completos
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class StatusMarcacao(str, Enum):
    """Status possíveis de uma tentativa de marcação"""

    PENDENTE = "pendente"  # Aguardando processamento
    SUCESSO = "sucesso"  # Marcada com sucesso
    FALHA_WEBJUR = "falha_webjur"  # Falha na API Webjur
    FALHA_MONGODB = "falha_mongodb"  # Falha ao atualizar MongoDB
    FALHA_TIMEOUT = "falha_timeout"  # Timeout na operação
    FALHA_VALIDACAO = "falha_validacao"  # Erro de validação
    ERRO_INTERNO = "erro_interno"  # Erro inesperado


class TentativaMarcacao(BaseModel):
    """Representa uma tentativa de marcação"""

    numero_tentativa: int = Field(..., description="Número da tentativa (1, 2, 3...)")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Quando a tentativa foi feita"
    )
    status: StatusMarcacao = Field(..., description="Status da tentativa")
    duracao_ms: Optional[float] = Field(
        None, description="Duração da tentativa em milissegundos"
    )
    mensagem_erro: Optional[str] = Field(None, description="Mensagem de erro se falhou")
    detalhes: Dict[str, Any] = Field(
        default_factory=dict, description="Detalhes adicionais da tentativa"
    )


class LogMarcacaoPublicacao(BaseModel):
    """
    Log completo de auditoria de marcação de publicação

    Registra todas as tentativas de marcar uma publicação como exportada,
    incluindo snapshot dos dados e contexto de execução.
    """

    # Identificação
    cod_publicacao: int = Field(..., description="Código da publicação no Webjur")
    lote_id: Optional[str] = Field(None, description="ID do lote que processou")
    execucao_id: Optional[str] = Field(
        None, description="ID da execução que originou"
    )
    publicacao_bronze_id: Optional[str] = Field(
        None, description="ID do documento no MongoDB (publicacoes_bronze)"
    )

    # Status atual
    status_atual: StatusMarcacao = Field(
        default=StatusMarcacao.PENDENTE, description="Status atual da marcação"
    )
    marcada_com_sucesso: bool = Field(
        default=False, description="Se foi marcada com sucesso no Webjur"
    )

    # Timestamps
    timestamp_primeira_tentativa: datetime = Field(
        default_factory=datetime.now, description="Quando foi a primeira tentativa"
    )
    timestamp_ultima_tentativa: Optional[datetime] = Field(
        None, description="Quando foi a última tentativa"
    )
    timestamp_sucesso: Optional[datetime] = Field(
        None, description="Quando foi marcada com sucesso"
    )

    # Tentativas
    total_tentativas: int = Field(default=1, description="Total de tentativas feitas")
    tentativas: List[TentativaMarcacao] = Field(
        default_factory=list, description="Histórico de todas as tentativas"
    )

    # Duração total
    duracao_total_ms: Optional[float] = Field(
        None, description="Duração total de todas as tentativas em ms"
    )

    # Contexto de execução
    worker_id: Optional[str] = Field(
        None, description="ID do worker que processou (se aplicável)"
    )
    task_id: Optional[str] = Field(
        None, description="ID da tarefa Camunda (se aplicável)"
    )
    process_instance_id: Optional[str] = Field(
        None, description="ID da instância do processo BPMN"
    )

    # Snapshot dos dados (para auditoria)
    snapshot_publicacao: Optional[Dict[str, Any]] = Field(
        None, description="Cópia dos dados da publicação no momento da marcação"
    )

    # Metadados
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados adicionais (versão, ambiente, etc.)",
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "examples": [
                {
                    "cod_publicacao": 123456,
                    "lote_id": "lote_20240115_001",
                    "execucao_id": "exec_abc123",
                    "publicacao_bronze_id": "65a1b2c3d4e5f6a7b8c9d0e1",
                    "status_atual": "sucesso",
                    "marcada_com_sucesso": True,
                    "timestamp_primeira_tentativa": "2024-01-15T10:00:00Z",
                    "timestamp_ultima_tentativa": "2024-01-15T10:00:05Z",
                    "timestamp_sucesso": "2024-01-15T10:00:05Z",
                    "total_tentativas": 1,
                    "tentativas": [
                        {
                            "numero_tentativa": 1,
                            "timestamp": "2024-01-15T10:00:00Z",
                            "status": "sucesso",
                            "duracao_ms": 1250.5,
                            "mensagem_erro": None,
                            "detalhes": {
                                "response_code": 200,
                                "webjur_response": "OK"
                            }
                        }
                    ],
                    "duracao_total_ms": 1250.5,
                    "worker_id": "marcar-publicacoes-worker-01",
                    "task_id": "task_xyz789",
                    "process_instance_id": "proc_inst_456",
                    "snapshot_publicacao": {
                        "numero_processo": "1234567-89.2024.8.13.0000",
                        "data_publicacao": "15/01/2024"
                    },
                    "metadata": {
                        "versao": "1.0.0",
                        "ambiente": "production"
                    }
                }
            ]
        }
    }


class ConsultaLogRequest(BaseModel):
    """Request para consultar logs de marcação"""

    cod_publicacao: Optional[int] = None
    lote_id: Optional[str] = None
    status: Optional[StatusMarcacao] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    apenas_falhas: bool = False
    limite: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ConsultaLogResponse(BaseModel):
    """Response com logs de marcação"""

    total_registros: int
    logs: List[LogMarcacaoPublicacao]
    estatisticas: Dict[str, Any] = Field(default_factory=dict)
