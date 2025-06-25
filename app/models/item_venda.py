"""
Modelo ItemVenda - Itens das vendas
"""

from datetime import datetime, date
from decimal import Decimal
from app import db
from app.utils.constants import VALOR_MINIMO_VENDA


class ItemVenda(db.Model):
    """Modelo para itens das vendas"""
    
    __tablename__ = 'itens_venda'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, 
        db.ForeignKey('vendas.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Dados do item
    descricao = db.Column(
        db.String(255), 
        nullable=False
    )
    quantidade = db.Column(
        db.Numeric(10, 3), 
        nullable=False
    )
    valor_unitario = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    subtotal = db.Column(
        db.Numeric(10, 2), 
        nullable=False,
        default=0
    )
    
    # Controle
    data_criacao = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    # Relacionamentos
    venda = db.relationship('Venda', back_populates='itens')
    
    def __repr__(self):
        return f'<ItemVenda {self.descricao} - Qtd: {self.quantidade} - Valor: R$ {self.valor_unitario}>'
    
    def __str__(self):
        return f"{self.descricao} - {self.quantidade} x R$ {self.valor_unitario:.2f}"
    
    @property
    def descricao_formatada(self):
        """Descrição formatada para exibição"""
        if len(self.descricao) > 50:
            return f"{self.descricao[:47]}..."
        return self.descricao
    
    @property
    def quantidade_formatada(self):
        """Quantidade formatada (remove zeros desnecessários)"""
        # Remove zeros à direita após a vírgula
        quantidade_str = f"{self.quantidade:.3f}".rstrip('0').rstrip('.')
        return quantidade_str
    
    @property
    def valor_unitario_formatado(self):
        """Valor unitário formatado como moeda"""
        from app.utils.helpers import format_currency
        return format_currency(self.valor_unitario)
    
    @property
    def subtotal_formatado(self):
        """Subtotal formatado como moeda"""
        from app.utils.helpers import format_currency
        return format_currency(self.subtotal)
    
    @property
    def eh_item_restante(self):
        """Verificar se é um item de restante"""
        return self.descricao.lower().startswith('saldo restante')
    
    def calcular_subtotal(self):
        """Calcular e atualizar subtotal do item"""
        if self.quantidade and self.valor_unitario:
            self.subtotal = self.quantidade * self.valor_unitario
        else:
            self.subtotal = Decimal('0.00')
        
        return self.subtotal
    
    def atualizar_valores(self, quantidade: float = None, valor_unitario: float = None):
        """
        Atualizar quantidade e/ou valor unitário e recalcular subtotal
        
        Args:
            quantidade: Nova quantidade (opcional)
            valor_unitario: Novo valor unitário (opcional)
        """
        if quantidade is not None:
            self.quantidade = Decimal(str(quantidade))
        
        if valor_unitario is not None:
            self.valor_unitario = Decimal(str(valor_unitario))
        
        self.calcular_subtotal()
    
    def validar(self):
        """
        Validar dados do item
        
        Returns:
            Lista de erros encontrados
        """
        erros = []
        
        # Validar descrição
        if not self.descricao or len(self.descricao.strip()) < 2:
            erros.append("Descrição deve ter pelo menos 2 caracteres")
        
        if len(self.descricao) > 255:
            erros.append("Descrição muito longa (máximo 255 caracteres)")
        
        # Validar quantidade
        if not self.quantidade or self.quantidade <= 0:
            erros.append("Quantidade deve ser maior que zero")
        
        if self.quantidade > 9999.999:
            erros.append("Quantidade muito alta (máximo 9999.999)")
        
        # Validar valor unitário
        if not self.valor_unitario or self.valor_unitario < VALOR_MINIMO_VENDA:
            erros.append(f"Valor unitário deve ser maior que R$ {VALOR_MINIMO_VENDA:.2f}")
        
        if self.valor_unitario > 99999.99:
            erros.append("Valor unitário muito alto (máximo R$ 99.999,99)")
        
        # Validar subtotal calculado
        subtotal_calculado = self.quantidade * self.valor_unitario if self.quantidade and self.valor_unitario else 0
        if abs(float(self.subtotal) - float(subtotal_calculado)) > 0.01:
            erros.append("Subtotal incorreto")
        
        return erros
    
    @staticmethod
    def criar_item_restante(valor_restante: Decimal, notas_ids: list, data_pagamento: date) -> 'ItemVenda':
        """
        Criar item de restante para pagamento múltiplo
        
        Args:
            valor_restante: Valor do restante
            notas_ids: Lista de IDs das notas originais
            data_pagamento: Data do pagamento original
            
        Returns:
            ItemVenda de restante
        """
        # Formatar descrição do item de restante
        if len(notas_ids) <= 3:
            notas_str = ", ".join([f"#{nota_id}" for nota_id in notas_ids])
        else:
            primeiras_notas = ", ".join([f"#{nota_id}" for nota_id in notas_ids[:2]])
            notas_str = f"{primeiras_notas} e mais {len(notas_ids) - 2} nota(s)"
        
        descricao = f"Saldo restante das notas {notas_str}"
        
        # Truncar descrição se muito longa
        if len(descricao) > 250:
            descricao = f"Saldo restante das notas #{notas_ids[0]} e mais {len(notas_ids) - 1} nota(s)"
        
        # Criar item
        item = ItemVenda(
            descricao=descricao,
            quantidade=Decimal('1.00'),
            valor_unitario=valor_restante
        )
        
        item.calcular_subtotal()
        
        return item
    
    @staticmethod
    def criar_item_simples(descricao: str, quantidade: float, valor_unitario: float) -> 'ItemVenda':
        """
        Criar item simples com validação
        
        Args:
            descricao: Descrição do item
            quantidade: Quantidade
            valor_unitario: Valor unitário
            
        Returns:
            ItemVenda criado
            
        Raises:
            ValueError: Se dados são inválidos
        """
        # Validações básicas
        if not descricao or len(descricao.strip()) < 2:
            raise ValueError("Descrição deve ter pelo menos 2 caracteres")
        
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        
        if valor_unitario <= 0:
            raise ValueError("Valor unitário deve ser maior que zero")
        
        # Criar item
        item = ItemVenda(
            descricao=descricao.strip(),
            quantidade=Decimal(str(quantidade)),
            valor_unitario=Decimal(str(valor_unitario))
        )
        
        item.calcular_subtotal()
        
        # Validar item criado
        erros = item.validar()
        if erros:
            raise ValueError(f"Erro na validação: {'; '.join(erros)}")
        
        return item
    
    def duplicar(self) -> 'ItemVenda':
        """
        Criar cópia do item (sem venda_id)
        
        Returns:
            Novo ItemVenda idêntico
        """
        item_copia = ItemVenda(
            descricao=self.descricao,
            quantidade=self.quantidade,
            valor_unitario=self.valor_unitario
        )
        
        item_copia.calcular_subtotal()
        
        return item_copia
    
    def to_dict(self):
        """
        Converter item para dicionário
        
        Returns:
            Dict com dados do item
        """
        return {
            'id': self.id,
            'venda_id': self.venda_id,
            'descricao': self.descricao,
            'descricao_formatada': self.descricao_formatada,
            'quantidade': float(self.quantidade),
            'quantidade_formatada': self.quantidade_formatada,
            'valor_unitario': float(self.valor_unitario),
            'valor_unitario_formatado': self.valor_unitario_formatado,
            'subtotal': float(self.subtotal),
            'subtotal_formatado': self.subtotal_formatado,
            'eh_item_restante': self.eh_item_restante,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None
        }
    
    @staticmethod
    def from_dict(dados: dict) -> 'ItemVenda':
        """
        Criar ItemVenda a partir de dicionário
        
        Args:
            dados: Dicionário com dados do item
            
        Returns:
            ItemVenda criado
        """
        item = ItemVenda(
            descricao=dados.get('descricao', ''),
            quantidade=Decimal(str(dados.get('quantidade', 0))),
            valor_unitario=Decimal(str(dados.get('valor_unitario', 0)))
        )
        
        if 'venda_id' in dados:
            item.venda_id = dados['venda_id']
        
        item.calcular_subtotal()
        
        return item
    
    def before_insert(self):
        """Hook executado antes de inserir no banco"""
        self.calcular_subtotal()
    
    def before_update(self):
        """Hook executado antes de atualizar no banco"""
        self.calcular_subtotal()


# Eventos SQLAlchemy
from sqlalchemy import event

@event.listens_for(ItemVenda, 'before_insert')
def item_venda_before_insert(mapper, connection, target):
    """Executado antes de inserir item"""
    target.before_insert()

@event.listens_for(ItemVenda, 'before_update')
def item_venda_before_update(mapper, connection, target):
    """Executado antes de atualizar item"""
    target.before_update()


# Funções auxiliares

def calcular_total_itens(itens: list) -> Decimal:
    """
    Calcular total de uma lista de itens
    
    Args:
        itens: Lista de ItemVenda
        
    Returns:
        Total calculado
    """
    total = Decimal('0.00')
    
    for item in itens:
        if isinstance(item, ItemVenda):
            total += item.subtotal
        elif isinstance(item, dict):
            quantidade = Decimal(str(item.get('quantidade', 0)))
            valor_unitario = Decimal(str(item.get('valor_unitario', 0)))
            total += quantidade * valor_unitario
    
    return total


def validar_lista_itens(itens: list) -> tuple:
    """
    Validar lista de itens
    
    Args:
        itens: Lista de itens (dict ou ItemVenda)
        
    Returns:
        Tuple[valido, erros, total]
    """
    erros = []
    total = Decimal('0.00')
    
    if not itens:
        erros.append("Lista de itens está vazia")
        return False, erros, 0
    
    for i, item in enumerate(itens):
        try:
            if isinstance(item, dict):
                # Validar item como dicionário
                descricao = item.get('descricao', '').strip()
                quantidade = float(item.get('quantidade', 0))
                valor_unitario = float(item.get('valor_unitario', 0))
                
                if not descricao:
                    erros.append(f"Item {i+1}: Descrição é obrigatória")
                
                if quantidade <= 0:
                    erros.append(f"Item {i+1}: Quantidade deve ser maior que zero")
                
                if valor_unitario <= 0:
                    erros.append(f"Item {i+1}: Valor unitário deve ser maior que zero")
                
                if not erros:
                    total += Decimal(str(quantidade)) * Decimal(str(valor_unitario))
                    
            elif isinstance(item, ItemVenda):
                # Validar ItemVenda
                item_erros = item.validar()
                if item_erros:
                    erros.extend([f"Item {i+1}: {erro}" for erro in item_erros])
                else:
                    total += item.subtotal
            else:
                erros.append(f"Item {i+1}: Tipo inválido")
                
        except Exception as e:
            erros.append(f"Item {i+1}: Erro na validação - {str(e)}")
    
    return len(erros) == 0, erros, float(total)


def agrupar_itens_por_descricao(itens: list) -> dict:
    """
    Agrupar itens por descrição (para relatórios)
    
    Args:
        itens: Lista de ItemVenda
        
    Returns:
        Dict agrupado por descrição
    """
    agrupados = {}
    
    for item in itens:
        if not isinstance(item, ItemVenda):
            continue
        
        descricao = item.descricao.lower().strip()
        
        if descricao not in agrupados:
            agrupados[descricao] = {
                'descricao': item.descricao,
                'quantidade_total': Decimal('0.00'),
                'valor_total': Decimal('0.00'),
                'itens_count': 0,
                'valor_medio': Decimal('0.00')
            }
        
        grupo = agrupados[descricao]
        grupo['quantidade_total'] += item.quantidade
        grupo['valor_total'] += item.subtotal
        grupo['itens_count'] += 1
        grupo['valor_medio'] = grupo['valor_total'] / grupo['quantidade_total']
    
    return agrupados


def obter_itens_mais_vendidos(limite: int = 10) -> list:
    """
    Obter itens mais vendidos
    
    Args:
        limite: Número máximo de itens a retornar
        
    Returns:
        Lista de itens mais vendidos
    """
    from sqlalchemy import func
    
    resultado = db.session.query(
        ItemVenda.descricao,
        func.sum(ItemVenda.quantidade).label('quantidade_total'),
        func.sum(ItemVenda.subtotal).label('valor_total'),
        func.count(ItemVenda.id).label('vendas_count')
    ).group_by(
        ItemVenda.descricao
    ).order_by(
        func.sum(ItemVenda.quantidade).desc()
    ).limit(limite).all()
    
    return [
        {
            'descricao': item.descricao,
            'quantidade_total': float(item.quantidade_total),
            'valor_total': float(item.valor_total),
            'vendas_count': item.vendas_count,
            'ticket_medio': float(item.valor_total / item.vendas_count) if item.vendas_count > 0 else 0
        }
        for item in resultado
    ]