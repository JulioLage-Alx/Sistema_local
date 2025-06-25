"""
Módulo de Services da aplicação
Contém toda a lógica de negócio do sistema
"""

from .venda_service import VendaService
from .pagamento_service import PagamentoService

# Lista de todos os services para facilitar importação
__all__ = [
    'VendaService',
    'PagamentoService'
]

# Instâncias globais dos services (singleton pattern)
venda_service = VendaService()
pagamento_service = PagamentoService()