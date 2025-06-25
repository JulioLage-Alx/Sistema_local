"""
Modelo ItemVenda - Itens de cada venda
"""

from decimal import Decimal, ROUND_HALF_UP
from app import db


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
    
    # Dados do item (digitação livre)
    descricao = db.Column(db.String(255), nullable=False)
    quantidade = db.Column(
        db.Numeric(10, 3), 
        nullable=False,
        default=1
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
    ordem = db.Column(db.Integer, nullable=False, default=1)
    
    def __repr__(self):
        return f'<ItemVenda {self.descricao} - {self.quantidade}x{self.valor_unitario}>'
    
    def __str__(self):
        return f"{self.descricao} - {self.quantidade} x R$ {self.valor_unitario}"
    
    def calcular_subtotal(self):
        """Calcular subtotal do item"""
        if self.quantidade and self.valor_unitario:
            subtotal = Decimal(str(self.quantidade)) * Decimal(str(self.valor_unitario))
            self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.subtotal = Decimal('0.00')
        
        return self.subtotal
    
    @property
    def quantidade_formatada(self):
        """Quantidade formatada para exibição"""
        if self.quantidade % 1 == 0:
            return f"{int(self.quantidade)}"
        else:
            return f"{self.quantidade:.3f}".rstrip('0').rstrip('.')
    
    @property
    def valor_unitario_formatado(self):
        """Valor unitário formatado"""
        from app.utils.helpers import format_currency
        return format_currency(self.valor_unitario)
    
    @property
    def subtotal_formatado(self):
        """Subtotal formatado"""
        from app.utils.helpers import format_currency
        return format_currency(self.subtotal)
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'venda_id': self.venda_id,
            'descricao': self.descricao,
            'quantidade': float(self.quantidade),
            'quantidade_formatada': self.quantidade_formatada,
            'valor_unitario': float(self.valor_unitario),
            'valor_unitario_formatado': self.valor_unitario_formatado,
            'subtotal': float(self.subtotal),
            'subtotal_formatado': self.subtotal_formatado,
            'ordem': self.ordem
        }
    
    @staticmethod
    def criar_item_restante(valor_restante, notas_ids, data_pagamento):
        """Criar item para nota de restante"""
        descricao = "Saldo restante das notas"
        
        item = ItemVenda(
            descricao=descricao,
            quantidade=Decimal('1'),
            valor_unitario=Decimal(str(valor_restante))
        )
        item.calcular_subtotal()
        
        return item
    
    def validate(self):
        """Validar dados do item"""
        errors = []
        
        # Validar descrição
        if not self.descricao or len(self.descricao.strip()) < 2:
            errors.append("Descrição deve ter pelo menos 2 caracteres")
        
        # Validar quantidade
        if not self.quantidade or self.quantidade <= 0:
            errors.append("Quantidade deve ser maior que zero")
        
        # Validar valor unitário
        if not self.valor_unitario or self.valor_unitario <= 0:
            errors.append("Valor unitário deve ser maior que zero")
        
        return errors
    
    def before_insert(self):
        """Hook executado antes de inserir"""
        self.calcular_subtotal()
    
    def before_update(self):
        """Hook executado antes de atualizar"""
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

@event.listens_for(ItemVenda, 'after_insert')
@event.listens_for(ItemVenda, 'after_update')
@event.listens_for(ItemVenda, 'after_delete')
def item_venda_after_change(mapper, connection, target):
    """Executado após mudanças no item - recalcular totais da venda"""
    if target.venda:
        target.venda.calcular_totais()