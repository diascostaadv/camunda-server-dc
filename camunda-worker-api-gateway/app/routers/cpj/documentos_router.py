"""
Router para operações de Documentos CPJ-3C
Endpoints: Consultar, Baixar, Cadastrar documento
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from services.cpj_service import CPJService
from io import BytesIO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cpj/documentos", tags=["CPJ - Documentos"])


class CadastrarDocumentoRequest(BaseModel):
    path: str = Field(..., description="Nome do arquivo")
    texto: str = Field(..., description="Descrição do documento")
    interno: bool = Field(default=False, description="Se documento é interno")
    versao: str = Field(default="v1", description="Versão do documento")
    id_tipo_documento: Optional[int] = Field(None, description="Tipo do documento")
    file_64: Optional[str] = Field(
        None, description="Arquivo em base64 (max 32KB)"
    )
    file_link: Optional[str] = Field(None, description="Link público do arquivo")
    file_token: Optional[str] = Field(
        None, description="Token para autenticação no link"
    )


@router.post("/consultar/{origem}/{id_origem}")
async def consultar_documentos(origem: str, id_origem: int) -> Dict[str, Any]:
    """
    Consulta documentos por módulo de origem (Seção 4.19)

    **Parâmetros**:
    - origem: Módulo do sistema (ex: 'processo', 'pessoa', 'pedido')
    - id_origem: Código do recurso (PJ, código pessoa, etc)

    **Returns**:
    - documentos: Lista de documentos com metadados
    """
    try:
        logger.info(f"🔍 Consultando documentos - origem: {origem}, id: {id_origem}")

        cpj_service = CPJService()
        documentos = await cpj_service.consultar_documentos(origem, id_origem)

        logger.info(f"✅ Encontrados {len(documentos)} documentos")
        return {"success": True, "total": len(documentos), "documentos": documentos}

    except Exception as e:
        logger.error(f"❌ Erro ao consultar documentos: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar documentos: {str(e)}"
        )


@router.get("/baixar/{id_ged}")
async def baixar_documento(id_ged: int):
    """
    Baixa documento pelo ID GED (Seção 4.20)

    **Returns**:
    - Filestream do arquivo (binary)
    """
    try:
        logger.info(f"📥 Baixando documento GED {id_ged}")

        cpj_service = CPJService()
        content = await cpj_service.baixar_documento(id_ged)

        if content is None:
            raise HTTPException(
                status_code=404, detail=f"Documento {id_ged} não encontrado"
            )

        logger.info(f"✅ Documento {id_ged} baixado - {len(content)} bytes")

        # Retornar como stream
        return StreamingResponse(
            BytesIO(content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=documento_{id_ged}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao baixar documento: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao baixar documento: {str(e)}"
        )


@router.post("/cadastrar/{origem}/{id_origem}")
async def cadastrar_documento(
    origem: str, id_origem: int, request: CadastrarDocumentoRequest
) -> Dict[str, Any]:
    """
    Cadastra novo documento (Seção 4.21)

    **Formas de envio**:
    - file_64: Arquivo em base64 (max 32KB)
    - file_link + file_token: Link público com token de acesso

    **Restrição**: Tamanho máximo 32KB para base64
    """
    try:
        logger.info(f"➕ Cadastrando documento - origem: {origem}, id: {id_origem}")

        # Validar que pelo menos uma forma de envio foi fornecida
        if not request.file_64 and not request.file_link:
            raise HTTPException(
                status_code=400,
                detail="Deve fornecer file_64 ou file_link para upload",
            )

        cpj_service = CPJService()
        result = await cpj_service.cadastrar_documento(
            origem, id_origem, request.dict(exclude_none=True)
        )

        if result.get("success"):
            logger.info("✅ Documento cadastrado com sucesso")
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Erro ao cadastrar documento"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao cadastrar documento: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao cadastrar documento: {str(e)}"
        )
