"""
Módulo de modelos da aplicação
Importa todos os modelos para facilitar o uso
"""

from .cliente import Cliente
from .venda import Venda
from .item_venda import ItemVenda
from .pagamento import Pagamento
from .pagamento_multiplo import PagamentoMultiplo, PagamentoMultiploDetalhe

# Lista de todos os modelos para facilitar importação
__all__ = [
    'Cliente',
    'Venda', 
    'ItemVenda',
    'Pagamento',
    'PagamentoMultiplo',
    'PagamentoMultiploDetalhe'
]

# Função para criar todas as tabelas
def create_all_tables(db):
    """Criar todas as tabelas do banco de dados"""
    db.create_all()

# Função para dropar todas as tabelas
def drop_all_tables(db):
    """Dropar todas as tabelas do banco de dados"""
    db.drop_all()