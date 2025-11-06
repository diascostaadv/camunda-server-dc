"""
Routers para integração com API CPJ-3C
Organizado por categoria de endpoints
"""

from .publicacoes_router import router as publicacoes_router
from .pessoas_router import router as pessoas_router
from .processos_router import router as processos_router
from .pedidos_router import router as pedidos_router
from .envolvidos_router import router as envolvidos_router
from .tramitacao_router import router as tramitacao_router
from .documentos_router import router as documentos_router

__all__ = [
    "publicacoes_router",
    "pessoas_router",
    "processos_router",
    "pedidos_router",
    "envolvidos_router",
    "tramitacao_router",
    "documentos_router",
]
