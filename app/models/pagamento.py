"""
Modelo Pagamento - Pagamentos individuais de vendas
"""

from datetime import datetime, date
from decimal import Decimal
from app import db
from app.utils.constants import FORMAS_PAGAMENTO


class Pagamento(db.Model):
    """Modelo para pagamentos de vendas individuais"""
    
    __tablename__ = 'pagamentos'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, 
        db.ForeignKey('vendas.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Dados do pagamento
    valor = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    forma_pagamento = db.Column(
        db.String(20), 
        nullable=False,
        default=FORMAS_PAGAMENTO['DINHEIRO'],
        index=True
    )
    
    # Campos específicos para pagamento em dinheiro
    valor_recebido = db.Column(
        db.Numeric(10, 2), 
        nullable=True
    )
    troco = db.Column(
        db.Numeric(10, 2), 
        nullable=True,
        default=0
    )
    
    # Controle
    data_pagamento = db.Column(
        db.Date, 
        nullable=False, 
        default=date.today,
        index=True
    )
    data_criacao = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    observacoes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Pagamento R$ {self.valor} - {self.forma_pagamento}>'
    
    def __str__(self):
        return f"R$ {self.valor} - {self.forma_pagamento_display}"
    
    @property
    def forma_pagamento_display(self):
        """Forma de pagamento formatada para exibição"""
        from app.utils.constants import FORMAS_PAGAMENTO_LABELS
        return FORMAS_PAGAMENTO_LABELS.get(self.forma_pagamento, self.forma_pagamento)
    
    @property
    def eh_dinheiro(self):
        """Verifica se o pagamento é em dinheiro"""
        return self.forma_pagamento == FORMAS_PAGAMENTO['DINHEIRO']
    
    @property
    def valor_formatado(self):
        """Valor formatado para exibição"""
        from app.utils.helpers import format_currency
        return format_currency(self.valor)
    
    @property
    def valor_recebido_formatado(self):
        """Valor recebido formatado para exibição"""
        from app.utils.helpers import format_currency
        return format_currency(self.valor_recebido) if self.valor_recebido else None
    
    @property
    def troco_formatado(self):
        """Troco formatado para exibição"""
        from app.utils.helpers import format_currency
        return format_currency(self.troco) if self.troco else None
    
    def calcular_troco(self):
        """Calcular troco para pagamentos em dinheiro"""
        if self.eh_dinheiro and self.valor_recebido:
            troco = Decimal(str(self.valor_recebido)) - Decimal(str(self.valor))
            self.troco = max(troco, Decimal('0.00'))
        else:
            self.troco = Decimal('0.00')
        
        return self.troco
    
    def gerar_comprovante_dados(self):
        """Gerar dados para impressão do comprovante"""
        dados = {
            'venda_id': self.venda_id,
            'data_pagamento': self.data_pagamento,
            'valor': self.valor,
            'forma_pagamento': self.forma_pagamento_display,
            'cliente_nome': self.venda.cliente.nome if self.venda and self.venda.cliente else 'Cliente não identificado'
        }
        
        # Adicionar dados específicos do dinheiro
        if self.eh_dinheiro:
            dados.update({
                'valor_recebido': self.valor_recebido,
                'troco': self.troco,
                'valor_recebido_formatado': self.valor_recebido_formatado,
                'troco_formatado': self.troco_formatado
            })
        
        # Adicionar itens da venda
        if self.venda:
            dados['venda'] = self.venda.to_dict(include_itens=True)
        
        return dados
    
    def to_dict(self):
        """Converter para dicionário"""
        data = {
            'id': self.id,
            'venda_id': self.venda_id,
            'valor': float(self.valor),
            'valor_formatado': self.valor_formatado,
            'forma_pagamento': self.forma_pagamento,
            'forma_pagamento_display': self.forma_pagamento_display,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'observacoes': self.observacoes,
            'eh_dinheiro': self.eh_dinheiro
        }
        
        # Adicionar campos específicos do dinheiro
        if self.eh_dinheiro:
            data.update({
                'valor_recebido': float(self.valor_recebido) if self.valor_recebido else None,
                'troco': float(self.troco) if self.troco else None,
                'valor_recebido_formatado': self.valor_recebido_formatado,
                'troco_formatado': self.troco_formatado
            })
        
        return data
    
    @staticmethod
    def buscar_por_periodo(data_inicio, data_fim, forma_pagamento=None):
        """Buscar pagamentos por período"""
        query = Pagamento.query.filter(
            Pagamento.data_pagamento >= data_inicio,
            Pagamento.data_pagamento <= data_fim
        )
        
        if forma_pagamento:
            query = query.filter(Pagamento.forma_pagamento == forma_pagamento)
        
        return query.order_by(Pagamento.data_pagamento.desc())
    
    @staticmethod
    def total_por_forma_pagamento(data_inicio, data_fim):
        """Total de pagamentos por forma de pagamento"""
        from sqlalchemy import func
        
        return db.session.query(
            Pagamento.forma_pagamento,
            func.sum(Pagamento.valor).label('total'),
            func.count(Pagamento.id).label('quantidade')
        ).filter(
            Pagamento.data_pagamento >= data_inicio,
            Pagamento.data_pagamento <= data_fim
        ).group_by(Pagamento.forma_pagamento).all()
    
    def validate(self):
        """Validar dados do pagamento"""
        errors = []
        
        # Validar valor
        if not self.valor or self.valor <= 0:
            errors.append("Valor do pagamento deve ser maior que zero")
        
        # Validar forma de pagamento
        if self.forma_pagamento not in FORMAS_PAGAMENTO.values():
            errors.append("Forma de pagamento inválida")
        
        # Validações específicas para dinheiro
        if self.eh_dinheiro:
            if self.valor_recebido and self.valor_recebido < self.valor:
                errors.append("Valor recebido não pode ser menor que o valor do pagamento")
        
        # Validar se o pagamento não excede o valor da venda
        if self.venda:
            valor_restante = self.venda.valor_restante
            if self.valor > valor_restante:
                errors.append(f"Valor do pagamento (R$ {self.valor}) maior que o valor restante (R$ {valor_restante})")
        
        return errors
    
    def before_insert(self):
        """Hook executado antes de inserir"""
        if self.eh_dinheiro:
            self.calcular_troco()
    
    def before_update(self):
        """Hook executado antes de atualizar"""
        if self.eh_dinheiro:
            self.calcular_troco()


# Eventos SQLAlchemy
from sqlalchemy import event

@event.listens_for(Pagamento, 'before_insert')
def pagamento_before_insert(mapper, connection, target):
    """Executado antes de inserir pagamento"""
    target.before_insert()

@event.listens_for(Pagamento, 'before_update')
def pagamento_before_update(mapper, connection, target):
    """Executado antes de atualizar pagamento"""
    target.before_update()

@event.listens_for(Pagamento, 'after_insert')
def pagamento_after_insert(mapper, connection, target):
    """Executado após inserir pagamento - atualizar status da venda"""
    if target.venda:
        target.venda.atualizar_status()