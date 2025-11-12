"""
Modelos Pydantic para o fluxo de publicações judiciais
Implementa as estruturas Bronze/Prata conforme BPMN
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


class PublicacaoBronze(BaseModel):
    """
    Modelo para publicações brutas (tabela bronze)
    Dados como vieram da fonte original sem tratamento

    NOTA: Este modelo é mantido apenas para documentação.
    Na prática, os dados bronze são salvos diretamente como dicionários
    sem validação Pydantic para máxima flexibilidade com campos dinâmicos da Webjur.
    """

    lote_id: str = Field(..., description="ID do lote de busca")
    cod_publicacao: int = Field(..., description="Código único da publicação na fonte")
    numero_processo: str = Field(..., description="Número do processo judicial")
    data_publicacao: str = Field(
        ..., description="Data de publicação (formato original)"
    )
    texto_publicacao: str = Field(..., description="Texto integral da publicação")
    fonte: Literal["dw", "manual", "escavador"] = Field(
        ..., description="Fonte da publicação"
    )
    tribunal: str = Field(..., description="Tribunal de origem")
    instancia: str = Field(..., description="Instância judicial")
    descricao_diario: Optional[str] = Field(
        None, description="Descrição do diário oficial"
    )
    uf_publicacao: Optional[str] = Field(None, description="UF da publicação")
    timestamp_insercao: datetime = Field(
        default_factory=datetime.now, description="Timestamp de inserção"
    )
    status: Literal["nova", "processada", "repetida", "erro"] = Field(
        default="nova", description="Status do processamento"
    )

    # Campos adicionais da API WebJur
    ano_publicacao: Optional[int] = Field(None, description="Ano da publicação")
    edicao_diario: Optional[int] = Field(None, description="Edição do diário")
    pagina_inicial: Optional[int] = Field(None, description="Página inicial")
    pagina_final: Optional[int] = Field(None, description="Página final")
    data_divulgacao: Optional[str] = Field(None, description="Data de divulgação")
    data_cadastro: Optional[str] = Field(None, description="Data de cadastro")
    cidade_publicacao: Optional[str] = Field(None, description="Cidade da publicação")
    orgao_descricao: Optional[str] = Field(None, description="Descrição do órgão")
    vara_descricao: Optional[str] = Field(None, description="Descrição da vara")
    despacho_publicacao: Optional[str] = Field(
        None, description="Despacho da publicação"
    )
    processo_publicacao: Optional[str] = Field(
        None, description="Processo da publicação"
    )
    publicacao_corrigida: Optional[int] = Field(None, description="Flag de correção")
    cod_vinculo: Optional[int] = Field(None, description="Código do vínculo")
    nome_vinculo: Optional[str] = Field(None, description="Nome do vínculo")
    oab_numero: Optional[int] = Field(None, description="Número OAB")
    oab_estado: Optional[str] = Field(None, description="Estado OAB")
    diario_sigla_wj: Optional[str] = Field(None, description="Sigla do diário WebJur")
    anexo: Optional[str] = Field(None, description="Anexo da publicação")
    cod_integracao: Optional[str] = Field(None, description="Código de integração")
    publicacao_exportada: Optional[int] = Field(None, description="Flag de exportação")
    cod_grupo: Optional[int] = Field(None, description="Código do grupo")

    # Campos de controle de exportação (nosso sistema)
    marcada_exportada_webjur: Optional[bool] = Field(
        default=False, description="Flag indicando se foi marcada como exportada via setPublicacoes()"
    )
    timestamp_marcacao_exportada: Optional[datetime] = Field(
        None, description="Timestamp de quando foi marcada como exportada"
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class PublicacaoPrata(BaseModel):
    """
    Modelo para publicações higienizadas (tabela prata)
    Dados tratados, limpos e enriquecidos
    """

    publicacao_bronze_id: str = Field(
        ..., description="ID da publicação bronze original"
    )
    hash_unica: str = Field(..., description="Hash SHA256 única para deduplicação")
    hash_alternativa: Optional[str] = Field(
        None, description="Hash alternativa com texto limpo"
    )

    # Dados principais higienizados
    numero_processo: str = Field(..., description="Número do processo original")
    numero_processo_limpo: str = Field(
        ..., description="Número do processo normalizado"
    )
    data_publicacao: datetime = Field(..., description="Data de publicação parseada")
    data_publicacao_original: str = Field(
        ..., description="Data de publicação formato original"
    )
    texto_limpo: str = Field(..., description="Texto higienizado e normalizado")
    texto_original: str = Field(..., description="Texto original para referência")

    # Metadados
    fonte: Literal["dw", "manual", "escavador"] = Field(
        ..., description="Fonte da publicação"
    )
    tribunal: str = Field(..., description="Tribunal de origem")
    instancia: str = Field(..., description="Instância judicial")

    # Status e classificação
    status: Literal[
        "nova_publicacao_inedita", "identidade_duvidosa", "repetida", "apto_a_agenda"
    ] = Field(..., description="Status após deduplicação")

    score_similaridade: float = Field(
        0.0, ge=0.0, le=100.0, description="Score de similaridade (0-100)"
    )

    # Publicações similares encontradas
    publicacoes_similares: List[Dict[str, Any]] = Field(
        default_factory=list, description="Lista de publicações similares com scores"
    )

    # Classificação
    classificacao: Optional[Dict[str, Any]] = Field(
        None, description="Classificação da publicação"
    )

    # Controle
    timestamp_processamento: datetime = Field(
        default_factory=datetime.now, description="Timestamp do processamento"
    )
    camunda_instance_id: Optional[str] = Field(
        None, description="ID da instância no Camunda"
    )

    @field_validator("score_similaridade")
    def validar_score(cls, v):
        """Valida o score de similaridade"""
        if v < 0 or v > 100:
            raise ValueError("Score deve estar entre 0 e 100")
        return v

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class Lote(BaseModel):
    """
    Modelo para lote de publicações
    Agrupa publicações de uma busca específica
    """

    execucao_id: str = Field(..., description="ID da execução que gerou o lote")
    timestamp_criacao: datetime = Field(
        default_factory=datetime.now, description="Timestamp de criação"
    )
    total_publicacoes: int = Field(..., description="Total de publicações no lote")
    cod_grupo: int = Field(..., description="Código do grupo de busca")
    data_inicial: Optional[str] = Field(None, description="Data inicial da busca")
    data_final: Optional[str] = Field(None, description="Data final da busca")
    status: Literal["pendente", "processando", "processado", "erro"] = Field(
        default="pendente", description="Status do processamento do lote"
    )
    publicacoes_ids: List[str] = Field(
        default_factory=list, description="IDs das publicações do lote"
    )
    estatisticas: Dict[str, int] = Field(
        default_factory=lambda: {
            "total": 0,
            "processadas": 0,
            "repetidas": 0,
            "novas": 0,
            "erros": 0,
        },
        description="Estatísticas do processamento",
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class HashDeduplicacao(BaseModel):
    """
    Modelo para índice de hashes
    Usado para deduplicação rápida
    """

    hash_value: str = Field(..., description="Valor da hash SHA256")
    publicacao_prata_id: str = Field(..., description="ID da publicação prata")
    numero_processo: str = Field(
        ..., description="Número do processo para referência rápida"
    )
    data_publicacao: datetime = Field(..., description="Data da publicação")
    timestamp_criacao: datetime = Field(
        default_factory=datetime.now, description="Timestamp de criação"
    )

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class ClassificacaoPublicacao(BaseModel):
    """
    Modelo para classificação de publicações
    Define tipo, urgência e outras características
    """

    tipo: Literal[
        "sentenca",
        "decisao_interlocutoria",
        "despacho",
        "intimacao",
        "citacao",
        "publicacao_edital",
        "audiencia",
        "outros",
    ] = Field(..., description="Tipo principal da publicação")

    subtipo: Optional[str] = Field(None, description="Subtipo específico")
    urgente: bool = Field(False, description="Se é urgente")
    prazo_dias: Optional[int] = Field(None, description="Prazo em dias se aplicável")

    # Entidades extraídas
    partes_mencionadas: List[str] = Field(
        default_factory=list, description="Partes mencionadas no texto"
    )
    advogados_mencionados: List[str] = Field(
        default_factory=list, description="Advogados mencionados"
    )

    # Análise de conteúdo
    palavras_chave: List[str] = Field(
        default_factory=list, description="Palavras-chave identificadas"
    )
    sentimento: Literal["positivo", "negativo", "neutro"] = Field(
        default="neutro", description="Análise de sentimento"
    )

    # Confiança da classificação
    confianca: float = Field(
        0.0, ge=0.0, le=1.0, description="Nível de confiança (0-1)"
    )

    @field_validator("confianca")
    def validar_confianca(cls, v):
        """Valida o nível de confiança"""
        if v < 0 or v > 1:
            raise ValueError("Confiança deve estar entre 0 e 1")
        return v


class ResultadoDeduplicacao(BaseModel):
    """
    Modelo para resultado do processo de deduplicação
    """

    publicacao_id: str = Field(..., description="ID da publicação analisada")
    eh_duplicata: bool = Field(..., description="Se é duplicata")
    hash_unica: str = Field(..., description="Hash gerada")

    # Se for duplicata
    publicacao_original_id: Optional[str] = Field(
        None, description="ID da publicação original se duplicata"
    )
    score_similaridade: float = Field(0.0, description="Score de similaridade")

    # Publicações similares encontradas
    publicacoes_similares: List[Dict[str, Any]] = Field(
        default_factory=list, description="Lista de publicações similares"
    )

    # Status resultante
    status_recomendado: Literal[
        "nova_publicacao_inedita", "identidade_duvidosa", "repetida", "apto_a_agenda"
    ] = Field(..., description="Status recomendado")

    justificativa: str = Field(..., description="Justificativa da decisão")
    timestamp_analise: datetime = Field(
        default_factory=datetime.now, description="Timestamp da análise"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProcessamentoPublicacaoRequest(BaseModel):
    """
    Request para processar uma publicação individual
    """

    publicacao_bronze_id: str = Field(
        ..., description="ID da publicação bronze a processar"
    )
    executar_classificacao: bool = Field(
        True, description="Se deve executar classificação"
    )
    executar_deduplicacao: bool = Field(
        True, description="Se deve executar deduplicação"
    )
    iniciar_processo_camunda: bool = Field(
        False, description="Se deve iniciar processo no Camunda"
    )

    # Parâmetros opcionais
    score_minimo_similaridade: float = Field(
        80.0, ge=0.0, le=100.0, description="Score mínimo para considerar duplicata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "publicacao_bronze_id": "65a1b2c3d4e5f6a7b8c9d0e1",
                    "executar_classificacao": True,
                    "executar_deduplicacao": True,
                    "iniciar_processo_camunda": False,
                    "score_minimo_similaridade": 85.0
                }
            ]
        }
    }


class ProcessamentoLoteRequest(BaseModel):
    """
    Request para processar um lote de publicações
    """

    lote_id: str = Field(..., description="ID do lote a processar")
    processar_em_paralelo: bool = Field(
        True, description="Se deve processar em paralelo"
    )
    max_paralelo: int = Field(
        10, ge=1, le=50, description="Máximo de processamentos paralelos"
    )
    continuar_em_erro: bool = Field(
        True, description="Se deve continuar processando em caso de erro"
    )

    # Configurações de processamento
    executar_classificacao: bool = Field(
        True, description="Se deve executar classificação"
    )
    executar_deduplicacao: bool = Field(
        True, description="Se deve executar deduplicação"
    )
    iniciar_processos_camunda: bool = Field(
        False, description="Se deve iniciar processos no Camunda"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "lote_id": "lote_20240115_001",
                    "processar_em_paralelo": True,
                    "max_paralelo": 10,
                    "continuar_em_erro": True,
                    "executar_classificacao": True,
                    "executar_deduplicacao": True,
                    "iniciar_processos_camunda": False
                }
            ]
        }
    }


class ProcessamentoLoteResponse(BaseModel):
    """
    Response do processamento de lote
    """

    lote_id: str = Field(..., description="ID do lote processado")
    timestamp_inicio: datetime = Field(..., description="Timestamp de início")
    timestamp_fim: datetime = Field(..., description="Timestamp de fim")
    duracao_segundos: float = Field(..., description="Duração em segundos")

    # Estatísticas
    total_publicacoes: int = Field(..., description="Total de publicações no lote")
    processadas_sucesso: int = Field(
        ..., description="Publicações processadas com sucesso"
    )
    processadas_erro: int = Field(..., description="Publicações com erro")

    # Detalhamento por status
    estatisticas_status: Dict[str, int] = Field(
        default_factory=dict, description="Contagem por status"
    )

    # Erros encontrados
    erros: List[Dict[str, Any]] = Field(
        default_factory=list, description="Lista de erros encontrados"
    )

    # IDs das publicações prata criadas
    publicacoes_prata_ids: List[str] = Field(
        default_factory=list, description="IDs das publicações prata criadas"
    )

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "json_schema_extra": {
            "examples": [
                {
                    "lote_id": "lote_20240115_001",
                    "timestamp_inicio": "2024-01-15T10:00:00Z",
                    "timestamp_fim": "2024-01-15T10:05:30Z",
                    "duracao_segundos": 330.5,
                    "total_publicacoes": 25,
                    "processadas_sucesso": 23,
                    "processadas_erro": 2,
                    "estatisticas_status": {
                        "nova_publicacao_inedita": 20,
                        "repetida": 3,
                        "identidade_duvidosa": 0,
                        "erro": 2
                    },
                    "erros": [
                        {
                            "publicacao_bronze_id": "65a1b2c3d4e5f6a7b8c9d0e1",
                            "erro": "Falha ao classificar: timeout na API N8N"
                        }
                    ],
                    "publicacoes_prata_ids": [
                        "65a1b2c3d4e5f6a7b8c9d0e2",
                        "65a1b2c3d4e5f6a7b8c9d0e3"
                    ]
                }
            ]
        }
    }
