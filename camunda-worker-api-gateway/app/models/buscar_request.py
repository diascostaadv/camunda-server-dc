"""
Modelos para requisições de busca de publicações
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator


class BuscarPublicacoesRequest(BaseModel):
    """Modelo para requisição de busca de publicações"""
    
    # Parâmetros de busca
    cod_grupo: int = Field(default=5, description="Código do grupo para busca")
    data_inicial: Optional[str] = Field(None, description="Data inicial para busca (YYYY-MM-DD)")
    data_final: Optional[str] = Field(None, description="Data final para busca (YYYY-MM-DD)")
    
    # Configurações de processamento
    limite_publicacoes: int = Field(default=50, ge=1, le=1000, description="Limite de publicações a processar")
    timeout_soap: int = Field(default=90, ge=30, le=300, description="Timeout para chamadas SOAP em segundos")
    max_retries: int = Field(default=3, ge=1, le=10, description="Máximo de tentativas em caso de erro")
    
    # Configurações do processo Camunda
    process_key: str = Field(default="processar_movimentacao_judicial", description="Chave do processo a iniciar")
    usar_business_key: bool = Field(default=True, description="Se deve usar business key nas instâncias")
    
    # Filtros opcionais
    filtrar_duplicatas: bool = Field(default=True, description="Se deve filtrar publicações duplicadas")
    apenas_nao_exportadas: bool = Field(default=True, description="Se deve buscar apenas não exportadas")
    
    @field_validator('data_inicial', 'data_final')
    def validar_formato_data(cls, v):
        """Valida formato das datas"""
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Data deve estar no formato YYYY-MM-DD")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return self.model_dump(exclude_none=True)


class PublicacaoProcessingResult(BaseModel):
    """Resultado do processamento de uma publicação individual"""
    
    cod_publicacao: int = Field(..., description="Código da publicação")
    numero_processo: Optional[str] = Field(None, description="Número do processo judicial")
    status: Literal["success", "error", "skipped"] = Field(..., description="Status do processamento")
    instance_id: Optional[str] = Field(None, description="ID da instância do processo criada")
    business_key: Optional[str] = Field(None, description="Business key utilizada")
    error_message: Optional[str] = Field(None, description="Mensagem de erro, se houver")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp do processamento")


class BuscarPublicacoesResponse(BaseModel):
    """Resposta da busca de publicações"""
    
    # Informações da execução
    timestamp_inicio: datetime = Field(..., description="Timestamp do início da busca")
    timestamp_fim: datetime = Field(..., description="Timestamp do fim da busca")
    duracao_segundos: float = Field(..., description="Duração total em segundos")
    
    # Estatísticas da busca SOAP
    total_encontradas: int = Field(..., description="Total de publicações encontradas na API SOAP")
    total_processadas: int = Field(..., description="Total de publicações que tentaram ser processadas")
    total_filtradas: int = Field(..., description="Total de publicações filtradas/ignoradas")
    
    # Estatísticas do processamento Camunda
    instancias_criadas: int = Field(..., description="Número de instâncias de processo criadas")
    instancias_com_erro: int = Field(..., description="Número de instâncias que falharam")
    instancias_ignoradas: int = Field(..., description="Número de publicações ignoradas")
    
    # Taxa de sucesso
    taxa_sucesso: float = Field(..., description="Taxa de sucesso (0.0 a 1.0)")
    
    # Detalhes dos processamentos
    resultados_detalhados: List[PublicacaoProcessingResult] = Field(default_factory=list, 
                                                                   description="Resultados detalhados por publicação")
    
    # Informações da configuração utilizada
    configuracao_utilizada: Dict[str, Any] = Field(default_factory=dict, 
                                                   description="Configuração que foi utilizada na busca")
    
    # Erros gerais
    erros_gerais: List[str] = Field(default_factory=list, description="Erros gerais durante a execução")
    
    # Estatísticas adicionais
    publicacoes_por_tribunal: Dict[str, int] = Field(default_factory=dict, 
                                                    description="Contagem de publicações por tribunal")
    publicacoes_por_fonte: Dict[str, int] = Field(default_factory=dict,
                                                 description="Contagem de publicações por fonte")
    
    @property
    def sucesso_geral(self) -> bool:
        """Indica se a operação foi bem-sucedida de forma geral"""
        return len(self.erros_gerais) == 0 and self.taxa_sucesso >= 0.8
    
    @property
    def resumo_textual(self) -> str:
        """Retorna resumo textual dos resultados"""
        return (
            f"Busca concluída em {self.duracao_segundos:.2f}s: "
            f"{self.total_encontradas} encontradas, "
            f"{self.instancias_criadas} processadas com sucesso, "
            f"{self.instancias_com_erro} com erro. "
            f"Taxa de sucesso: {self.taxa_sucesso:.1%}"
        )


class BuscarPublicacoesStatus(BaseModel):
    """Status atual de uma operação de busca em andamento"""
    
    operacao_id: str = Field(..., description="ID único da operação")
    status: Literal["running", "completed", "error", "cancelled"] = Field(..., description="Status atual")
    timestamp_inicio: datetime = Field(..., description="Quando a operação iniciou")
    timestamp_ultima_atualizacao: datetime = Field(default_factory=datetime.now, description="Última atualização")
    
    # Progresso
    total_esperado: Optional[int] = Field(None, description="Total de itens esperados para processar")
    total_processado: int = Field(default=0, description="Total de itens já processados")
    progresso_percentual: Optional[float] = Field(None, description="Progresso em percentual (0.0 a 1.0)")
    
    # Estatísticas em tempo real
    sucessos: int = Field(default=0, description="Número de sucessos até agora")
    erros: int = Field(default=0, description="Número de erros até agora")
    
    # Informações adicionais
    etapa_atual: str = Field(default="Iniciando", description="Etapa atual da operação")
    mensagem_status: str = Field(default="", description="Mensagem descritiva do status")
    
    # Resultado final (quando completo)
    resultado_final: Optional[BuscarPublicacoesResponse] = Field(None, description="Resultado final quando completado")
    
    def atualizar_progresso(self, processados: int, sucessos: int, erros: int, 
                           etapa: str = None, mensagem: str = None):
        """Atualiza o progresso da operação"""
        self.total_processado = processados
        self.sucessos = sucessos
        self.erros = erros
        self.timestamp_ultima_atualizacao = datetime.now()
        
        if etapa:
            self.etapa_atual = etapa
        if mensagem:
            self.mensagem_status = mensagem
            
        if self.total_esperado and self.total_esperado > 0:
            self.progresso_percentual = min(1.0, self.total_processado / self.total_esperado)


class TaskDataRequest(BaseModel):
    """Modelo para dados de tarefa recebidos do Camunda worker"""
    
    task_id: str = Field(..., description="ID da tarefa")
    process_instance_id: str = Field(..., description="ID da instância do processo")
    business_key: Optional[str] = Field(None, description="Business key da instância")
    
    # Variáveis da tarefa (parâmetros de busca)
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variáveis da tarefa")
    
    # Metadados
    topic_name: str = Field(..., description="Nome do tópico")
    worker_id: str = Field(..., description="ID do worker que enviou")
    
    def get_buscar_request(self) -> BuscarPublicacoesRequest:
        """Converte variáveis da tarefa para BuscarPublicacoesRequest"""
        # Extrair parâmetros das variáveis
        params = {}
        
        if 'cod_grupo' in self.variables:
            params['cod_grupo'] = self.variables['cod_grupo']
        if 'data_inicial' in self.variables:
            params['data_inicial'] = self.variables['data_inicial']
        if 'data_final' in self.variables:
            params['data_final'] = self.variables['data_final']
        if 'limite_publicacoes' in self.variables:
            params['limite_publicacoes'] = self.variables['limite_publicacoes']
            
        return BuscarPublicacoesRequest(**params)


class PublicacaoParaProcessamento(BaseModel):
    """Modelo para publicação convertida para processamento"""
    
    # Dados obrigatórios para MovimentacaoJudicial
    numero_processo: str = Field(..., description="Número do processo judicial")
    data_publicacao: str = Field(..., description="Data de publicação no formato dd/mm/yyyy")
    texto_publicacao: str = Field(..., description="Texto integral da movimentação")
    fonte: Literal["dw", "manual", "escavador"] = Field(..., description="Fonte da movimentação")
    tribunal: str = Field(..., description="Tribunal origem")
    instancia: str = Field(..., description="Instância judicial")
    
    # Metadados da API SOAP
    cod_publicacao: int = Field(..., description="Código original da publicação")
    descricao_diario: Optional[str] = Field(None, description="Descrição do diário")
    uf_publicacao: Optional[str] = Field(None, description="UF da publicação")
    
    def to_movimentacao_dict(self) -> Dict[str, Any]:
        """Converte para formato MovimentacaoJudicial"""
        return {
            "numero_processo": self.numero_processo,
            "data_publicacao": self.data_publicacao,
            "texto_publicacao": self.texto_publicacao,
            "fonte": self.fonte,
            "tribunal": self.tribunal,
            "instancia": self.instancia
        }
        
        
        
        # execucao = {
        #     "_id": str, 
        #     "data_inicio": datetime, 
        #     "data_fim": Optional[datetime], 
        #     "status": Literal["running", "completed", "error", "cancelled"],
        #     "total_encontradas": int,
        # }
        
        # publicacao = {
        #     "_id_execucao": str,
        #     "numero_processo": str,
        #     "data_publicacao": str,
        #     "texto_publicacao": str,
        #     "fonte": str,
        #     "tribunal": str,
        #     "instancia": str,
        #     "cod_publicacao": int,
        # }
    
    @classmethod
    def from_soap_publicacao(cls, publicacao, fonte: str = "dw") -> "PublicacaoParaProcessamento":
        """
        Cria instância a partir de objeto Publicacao da API SOAP
        
        Args:
            publicacao: Objeto Publicacao da API SOAP
            fonte: Fonte a ser atribuída (default: "dw")
        """
        # Processar tribunal
        tribunal = "tjmg"  # Padrão
        if hasattr(publicacao, 'descricao_diario') and publicacao.descricao_diario:
            tribunal = publicacao.descricao_diario.lower().replace(" ", "").replace("-", "")
        
        # Processar número do processo
        numero_processo = publicacao.numero_processo or f"PROCESSO-{publicacao.cod_publicacao}"
        
        # Processar texto
        texto_publicacao = (
            publicacao.texto_publicacao or 
            publicacao.despacho_publicacao or 
            publicacao.processo_publicacao or 
            f"Publicação código {publicacao.cod_publicacao}"
        )
        
        return cls(
            numero_processo=numero_processo,
            data_publicacao=publicacao.data_publicacao or "01/01/2024",
            texto_publicacao=texto_publicacao,
            fonte=fonte,
            tribunal=tribunal,
            instancia="1",  # Padrão
            cod_publicacao=publicacao.cod_publicacao,
            descricao_diario=publicacao.descricao_diario,
            uf_publicacao=publicacao.uf_publicacao
        )