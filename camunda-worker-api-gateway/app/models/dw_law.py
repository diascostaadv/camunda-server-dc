"""
Modelos Pydantic para integração DW LAW e-Protocol
Estruturas de dados para consulta processual
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from bson import ObjectId


# ==================== MODELS DE INSERÇÃO/EXCLUSÃO ====================

class ProcessoDWLawInput(BaseModel):
    """
    Modelo para entrada de processo (inserção)
    """
    numero_processo: str = Field(..., description="Número do processo CNJ")
    other_info_client1: Optional[str] = Field(
        None, description="Campo extra 1 para controle do cliente"
    )
    other_info_client2: Optional[str] = Field(
        None, description="Campo extra 2 para controle do cliente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "numero_processo": "0012205-60.2015.5.15.0077",
                "other_info_client1": "CÓDIGO_INTERNO_123",
                "other_info_client2": "PASTA_456"
            }
        }


class ProcessoDWLaw(BaseModel):
    """
    Modelo para processo DW LAW armazenado no MongoDB
    """
    chave_projeto: str = Field(..., description="Chave única do projeto DW LAW")
    numero_processo: str = Field(..., description="Número do processo CNJ")
    chave_de_pesquisa: Optional[str] = Field(
        None, description="Chave de pesquisa retornada pelo DW LAW"
    )
    tribunal: Optional[str] = Field(None, description="Tribunal")
    sistema: Optional[str] = Field(None, description="Sistema (PJE, ESAJ, etc)")
    instancia: Optional[str] = Field(None, description="Instância")

    # Campos de controle do cliente
    other_info_client1: Optional[str] = Field(None, description="Info cliente 1")
    other_info_client2: Optional[str] = Field(None, description="Info cliente 2")

    # Controle de status
    status: Literal["inserido", "consultando", "consultado", "erro", "excluido"] = Field(
        default="inserido", description="Status do processo"
    )

    # Timestamps
    timestamp_insercao: datetime = Field(
        default_factory=datetime.now, description="Timestamp de inserção"
    )
    timestamp_ultima_consulta: Optional[datetime] = Field(
        None, description="Timestamp da última consulta"
    )

    # Camunda
    camunda_instance_id: Optional[str] = Field(
        None, description="ID da instância no Camunda"
    )
    camunda_business_key: Optional[str] = Field(
        None, description="Business key no Camunda"
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


# ==================== MODELS DE CONSULTA ====================

class RepresentanteDWLaw(BaseModel):
    """Representante de uma parte"""
    nome: Optional[str] = None
    tipo: Optional[str] = None
    numero_oab: Optional[str] = None
    uf_oab: Optional[str] = None
    cpf: Optional[str] = None


class PoloDWLaw(BaseModel):
    """Polo processual (parte)"""
    nome: Optional[str] = None
    classificacao: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    tipo_polo: Optional[str] = Field(None, description="A=Ativo, P=Passivo, I=Indefinido, O=Outros")
    representantes: List[RepresentanteDWLaw] = Field(default_factory=list)


class ArquivoMovimentacaoDWLaw(BaseModel):
    """Arquivo de movimentação processual"""
    nome_arquivo: Optional[str] = None
    link_arquivo: Optional[str] = None


class MovimentacaoDWLaw(BaseModel):
    """Movimentação processual"""
    data_movimentacao: Optional[str] = None
    descricao: Optional[str] = None
    arquivos: List[ArquivoMovimentacaoDWLaw] = Field(default_factory=list)


class AudienciaDWLaw(BaseModel):
    """Audiência processual"""
    data_audiencia: Optional[str] = None
    hora_audiencia: Optional[str] = None
    modalidade: Optional[str] = None
    situacao: Optional[str] = None
    tipo: Optional[str] = None
    sala_local: Optional[str] = None
    url_ata: Optional[str] = None


class ConsultaProcessoDWLaw(BaseModel):
    """
    Modelo completo para resultado de consulta processual DW LAW
    Armazena dados retornados pela API
    """
    # Metadados da consulta
    chave_de_pesquisa: str = Field(..., description="Chave de pesquisa DW LAW")
    chave_projeto: str = Field(..., description="Chave do projeto")
    status_pesquisa: str = Field(..., description="S=Sucesso, A=Alerta, R=RPA, E=Em análise")
    descricao_status_pesquisa: str = Field(..., description="Descrição do status")
    tipo_consulta: str = Field(default="CONS", description="Tipo de consulta")

    # Dados do processo
    numero_processo: str = Field(..., description="Número do processo CNJ")
    classe_judicial: Optional[str] = None
    assunto: Optional[str] = None
    jurisdicao: Optional[str] = None
    uf: Optional[str] = None
    valor: Optional[str] = Field(None, description="Valor da causa")

    # Flags
    segredo_justica: Optional[str] = Field(None, description="S=Sim, N=Não")
    citacao: Optional[str] = Field(None, description="S=Sim, N=Não, E=Extinto, P=Possível, X=Sigiloso")
    indicio_citacao: Optional[str] = Field(None, description="Indício da citação com data e texto")
    justica_gratuita: Optional[str] = Field(None, description="S=Sim, N=Não")
    tutela_liminar: Optional[str] = Field(None, description="S=Sim, N=Não")
    arquivado: Optional[str] = Field(None, description="S=Sim, N=Não")

    # Informações adicionais
    prioridade: Optional[str] = None
    orgao_julgador: Optional[str] = None
    cargo_judicial: Optional[str] = None
    competencia: Optional[str] = None
    outras_info: Optional[str] = None
    link_arquivo: Optional[str] = Field(None, description="Link da inicial")

    # Sistema
    sistema: Optional[str] = Field(None, description="PJE, ESAJ, etc")
    instancia: Optional[str] = None
    tribunal: Optional[str] = None
    juiz: Optional[str] = None
    nome_projeto: Optional[str] = None

    # Datas
    data_distribuicao: Optional[str] = None
    ultima_distribuicao: Optional[str] = None
    ultima_atualizacao: Optional[str] = None
    data_sla: Optional[str] = None

    # Processos relacionados
    processos_desdobramento: Optional[str] = Field(
        None, description="Processos vinculados"
    )

    # Estruturas complexas
    polos: List[PoloDWLaw] = Field(default_factory=list)
    movimentacoes: List[MovimentacaoDWLaw] = Field(default_factory=list)
    audiencias: List[AudienciaDWLaw] = Field(default_factory=list)

    # Controle
    timestamp_consulta: datetime = Field(
        default_factory=datetime.now, description="Timestamp da consulta"
    )
    camunda_instance_id: Optional[str] = Field(
        None, description="ID da instância no Camunda"
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


# ==================== MODELS DE CALLBACK ====================

class CallbackDWLaw(BaseModel):
    """
    Modelo para callback recebido do DW LAW
    Salva o payload completo recebido via webhook
    """
    # Payload completo conforme enviado pelo DW LAW
    payload_completo: Dict[str, Any] = Field(..., description="Payload completo do callback")

    # Campos principais extraídos
    chave_de_pesquisa: str = Field(..., description="Chave de pesquisa")
    numero_processo: str = Field(..., description="Número do processo")
    status_pesquisa: str = Field(..., description="Status da pesquisa")
    descricao_status_pesquisa: str = Field(..., description="Descrição do status")

    # Controle
    timestamp_recebimento: datetime = Field(
        default_factory=datetime.now, description="Timestamp de recebimento"
    )
    processado: bool = Field(default=False, description="Se foi processado")
    timestamp_processamento: Optional[datetime] = Field(
        None, description="Timestamp do processamento"
    )

    # Mensagem Camunda enviada
    mensagem_camunda_enviada: bool = Field(
        default=False, description="Se mensagem foi enviada ao Camunda"
    )
    camunda_business_key: Optional[str] = Field(
        None, description="Business key usado na mensagem Camunda"
    )
    mensagem_camunda_resultado: Optional[Dict[str, Any]] = Field(
        None, description="Resultado do envio da mensagem"
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


# ==================== REQUEST/RESPONSE MODELS ====================

class InserirProcessosRequest(BaseModel):
    """Request para inserir processos"""
    chave_projeto: str = Field(..., description="Chave única do projeto DW LAW")
    processos: List[ProcessoDWLawInput] = Field(..., description="Lista de processos")
    camunda_instance_id: Optional[str] = Field(None, description="ID da instância Camunda")
    camunda_business_key: Optional[str] = Field(None, description="Business key Camunda")


class ExcluirProcessosRequest(BaseModel):
    """Request para excluir processos"""
    chave_projeto: str = Field(..., description="Chave única do projeto DW LAW")
    lista_de_processos: List[Dict[str, str]] = Field(
        ..., description="Lista com numero_processo"
    )


class ConsultarProcessoRequest(BaseModel):
    """Request para consultar processo"""
    chave_de_pesquisa: str = Field(..., description="Chave de pesquisa DW LAW")
    camunda_instance_id: Optional[str] = Field(None, description="ID da instância Camunda")


class DWLawResponse(BaseModel):
    """Response padrão para operações DW LAW"""
    success: bool = Field(..., description="Se operação foi bem-sucedida")
    data: Optional[Dict[str, Any]] = Field(None, description="Dados retornados")
    error: Optional[str] = Field(None, description="Código de erro")
    message: Optional[str] = Field(None, description="Mensagem descritiva")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
