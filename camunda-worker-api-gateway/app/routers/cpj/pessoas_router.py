"""
Router para operações de Pessoas CPJ-3C
Endpoints: Consultar, Cadastrar, Atualizar pessoa
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cpj/pessoas", tags=["CPJ - Pessoas"])


# ==================== MODELS ====================


class ConsultarPessoaRequest(BaseModel):
    """Request para consultar pessoa"""

    filter: Dict[str, Any] = Field(..., description="Filtros de busca")
    sort: str = Field(default="nome", description="Campo para ordenação")


class CadastrarPessoaRequest(BaseModel):
    """Request para cadastrar pessoa"""

    nome: str = Field(..., description="Nome da pessoa")
    categoria: int = Field(..., description="Categoria da pessoa")
    fisica_juridica: int = Field(
        ..., description="1=Física, 2=Jurídica", ge=1, le=2
    )
    cpf_cnpj: Optional[str] = Field(None, description="CPF ou CNPJ")
    rgie: Optional[str] = Field(None, description="RG/IE")
    email: Optional[str] = Field(None, description="E-mail")
    telefone: Optional[str] = Field(None, description="Telefone")
    celular: Optional[str] = Field(None, description="Celular")
    enderecos: Optional[List[Dict[str, Any]]] = Field(None, description="Endereços")
    # Campos adicionais conforme documentação CPJ...


class AtualizarPessoaRequest(BaseModel):
    """Request para atualizar pessoa"""

    update_data_hora: str = Field(..., description="Data/hora do registro (ISO)")
    update_usuario: int = Field(..., description="ID do usuário atualizando")
    categoria: Optional[int] = None
    fisica_juridica: Optional[int] = Field(None, ge=1, le=2)
    email: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    enderecos: Optional[List[Dict[str, Any]]] = None
    # Campos atualizáveis conforme doc CPJ...


# ==================== ENDPOINTS ====================


@router.post("/consultar")
async def consultar_pessoa(request: ConsultarPessoaRequest) -> Dict[str, Any]:
    """
    Consulta pessoas com filtros (Seção 4.4 da API CPJ)

    **Filtros suportados**:
    - codigo: Código da pessoa
    - cpf_cnpj: CPF ou CNPJ
    - nome: Nome (pode usar like)
    - email: E-mail

    **Returns**:
    - pessoas: Lista de pessoas encontradas
    - total: Total encontrado
    """
    try:
        logger.info(f"🔍 Consultando pessoas - Filtros: {list(request.filter.keys())}")

        cpj_service = CPJService()
        pessoas = await cpj_service.consultar_pessoa(
            filters=request.filter, sort=request.sort
        )

        logger.info(f"✅ Encontradas {len(pessoas)} pessoas")

        return {"success": True, "total": len(pessoas), "pessoas": pessoas}

    except Exception as e:
        logger.error(f"❌ Erro ao consultar pessoa: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar pessoa: {str(e)}"
        )


@router.post("/cadastrar")
async def cadastrar_pessoa(request: CadastrarPessoaRequest) -> Dict[str, Any]:
    """
    Cadastra nova pessoa (Seção 4.5 da API CPJ)

    **Campos obrigatórios**:
    - nome
    - categoria
    - fisica_juridica (1=Física, 2=Jurídica)

    **Returns**:
    - codigo: Código da pessoa cadastrada
    """
    try:
        logger.info(f"➕ Cadastrando pessoa: {request.nome}")

        cpj_service = CPJService()
        result = await cpj_service.cadastrar_pessoa(request.dict(exclude_none=True))

        if result.get("success"):
            logger.info(f"✅ Pessoa cadastrada - Código: {result.get('codigo')}")
            return result
        else:
            raise HTTPException(
                status_code=400, detail=result.get("message", "Erro ao cadastrar pessoa")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao cadastrar pessoa: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao cadastrar pessoa: {str(e)}"
        )


@router.post("/atualizar/{codigo}")
async def atualizar_pessoa(
    codigo: int, request: AtualizarPessoaRequest
) -> Dict[str, Any]:
    """
    Atualiza pessoa existente (Seção 4.6 da API CPJ)

    **Restrições**:
    - Não pode estar em situação "Bloqueado ERP"
    - CPF/CNPJ só pode ser alterado se estiver vazio
    - Nome não pode ser alterado
    - Informações bancárias não podem ser alteradas

    **Returns**:
    - success: Se atualização foi bem-sucedida
    """
    try:
        logger.info(f"✏️ Atualizando pessoa {codigo}")

        cpj_service = CPJService()
        result = await cpj_service.atualizar_pessoa(
            codigo, request.dict(exclude_none=True)
        )

        if result.get("success"):
            logger.info(f"✅ Pessoa {codigo} atualizada com sucesso")
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Erro ao atualizar pessoa"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar pessoa {codigo}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao atualizar pessoa: {str(e)}"
        )
