"""
Movimentação Judicial Models
Schema para processamento de movimentações judiciais
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class MovimentacaoJudicial(BaseModel):
    """Modelo para movimentações judiciais"""
    
    # Campos de entrada obrigatórios
    numero_processo: str = Field(..., description="Número do processo judicial")
    data_publicacao: str = Field(..., description="Data de publicação no formato dd/mm/yyyy")
    texto_publicacao: str = Field(..., description="Texto integral da movimentação")
    fonte: Literal["dw", "manual", "escavador"] = Field(..., description="Fonte da movimentação")
    tribunal: str = Field(..., description="Tribunal origem (ex: tjmg)")
    instancia: str = Field(..., description="Instância judicial")
    
    # Campos processados (Passo 1)
    texto_publicacao_limpo: Optional[str] = Field(None, description="Texto sanitizado")
    data_publicacao_parsed: Optional[datetime] = Field(None, description="Data convertida para datetime")
    hash_unica: Optional[str] = Field(None, description="Hash única para detecção de duplicatas")
    timestamp_processamento: Optional[datetime] = Field(None, description="Timestamp do processamento")
    status_processamento: str = Field("pending", description="Status atual do processamento")
    
    # Metadata adicional
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadados do processamento")
    
    @field_validator('fonte')
    def validar_fonte(cls, v):
        """Valida se a fonte é um dos valores permitidos"""
        if v not in ["dw", "manual", "escavador"]:
            raise ValueError("Fonte deve ser 'dw', 'manual' ou 'escavador'")
        return v
    
    @field_validator('data_publicacao')
    def validar_formato_data(cls, v):
        """Validação básica do formato de data"""
        if not v or len(v) != 10:
            raise ValueError("Data deve estar no formato dd/mm/yyyy")
        
        parts = v.split('/')
        if len(parts) != 3:
            raise ValueError("Data deve estar no formato dd/mm/yyyy")
        
        try:
            day, month, year = map(int, parts)
            if not (1 <= day <= 31):
                raise ValueError("Dia deve estar entre 1 e 31")
            if not (1 <= month <= 12):
                raise ValueError("Mês deve estar entre 1 e 12")
            if not (1900 <= year <= 2100):
                raise ValueError("Ano deve estar entre 1900 e 2100")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Data deve conter apenas números no formato dd/mm/yyyy")
            raise e
        
        return v
    
    @field_validator('instancia')
    def validar_instancia(cls, v):
        """Valida se instância é numérica"""
        if not v.isdigit():
            raise ValueError("Instância deve ser numérica")
        return v
    
    @field_validator('numero_processo')
    def validar_numero_processo(cls, v):
        """Valida se número do processo não está vazio"""
        if not v or not v.strip():
            raise ValueError("Número do processo é obrigatório")
        return v.strip()
    
    @field_validator('texto_publicacao')
    def validar_texto_publicacao(cls, v):
        """Valida se texto não está vazio"""
        if not v or not v.strip():
            raise ValueError("Texto da publicação é obrigatório")
        return v.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para dicionário"""
        return self.dict(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MovimentacaoJudicial":
        """Cria instância a partir de dicionário"""
        return cls(**data)


class MovimentacaoProcessingResult(BaseModel):
    """Resultado do processamento de uma movimentação"""
    
    success: bool = Field(..., description="Se o processamento foi bem-sucedido")
    movimentacao: Optional[MovimentacaoJudicial] = Field(None, description="Movimentação processada")
    error_message: Optional[str] = Field(None, description="Mensagem de erro, se houver")
    processing_steps: list = Field(default_factory=list, description="Passos executados no processamento")
    
    def add_step(self, step: str):
        """Adiciona um passo ao processamento"""
        timestamp = datetime.utcnow().isoformat()
        self.processing_steps.append(f"{timestamp}: {step}")


class MovimentacaoQuery(BaseModel):
    """Parâmetros para consulta de movimentações"""
    
    numero_processo: Optional[str] = None
    tribunal: Optional[str] = None
    fonte: Optional[Literal["dw", "manual", "escavador"]] = None
    status_processamento: Optional[str] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class MovimentacaoStatistics(BaseModel):
    """Estatísticas de processamento de movimentações"""
    
    total_movimentacoes: int = 0
    por_status: Dict[str, int] = Field(default_factory=dict)
    por_fonte: Dict[str, int] = Field(default_factory=dict)
    por_tribunal: Dict[str, int] = Field(default_factory=dict)
    taxa_sucesso: float = 0.0
    tempo_medio_processamento: Optional[float] = None