"""
Handlers para CPJ API Worker
Organiza handlers por módulo funcional
"""

from .auth_handlers import AuthHandlers
from .pessoas_handlers import PessoasHandlers
from .processos_handlers import ProcessosHandlers
from .publicacoes_handlers import PublicacoesHandlers
from .pedidos_handlers import PedidosHandlers
from .envolvidos_handlers import EnvolvidosHandlers
from .tramitacao_handlers import TramitacaoHandlers
from .documentos_handlers import DocumentosHandlers

__all__ = [
    "AuthHandlers",
    "PessoasHandlers",
    "ProcessosHandlers",
    "PublicacoesHandlers",
    "PedidosHandlers",
    "EnvolvidosHandlers",
    "TramitacaoHandlers",
    "DocumentosHandlers",
]
