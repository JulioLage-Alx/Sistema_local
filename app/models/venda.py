"""
Modelo Venda - Gerenciamento de vendas a crediário
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.utils.constants import (
    STATUS_VENDA, DIAS_VENCIMENTO_PADRAO, VALOR_MINIMO_VENDA
)


class Venda(db.Model):
    """Modelo para vendas do açougue"""
    
    __tablename__ = 'vendas'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer, 
        db.ForeignKey('clientes.id', ondelete='RESTRICT'), 
        nullable=False,
        index=True
    )
    
    # Datas
    data_venda = db.Column(
        db.Date, 
        nullable=False, 
        default=date.today,
        index=True
    )
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    data_pagamento = db.Column(db.Date, nullable=True, index=True)
    
    # Valores
    subtotal = db.Column(
        db.Numeric(10, 2), 
        nullable=False, 
        default=0
    )
    total = db.Column(
        db.Numeric(10, 2), 
        nullable=False, 
        default=0,
        index=True
    )
    
    # Status e controle
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default=STATUS_VENDA['ABERTA'],
        index=True
    )
    
    # Campos para notas de restante
    eh_restante = db.Column(
        db.Boolean, 
        nullable=False, 
        default=False,
        index=True
    )
    pagamento_multiplo_id = db.Column(
        db.Integer,
        db.ForeignKey('pagamentos_multiplos.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Controle
    data_criacao = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    data_atualizacao = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    itens = db.relationship(
        'ItemVenda', 
        backref='venda', 
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ItemVenda.id'
    )
    
    pagamentos = db.relationship(
        'Pagamento',
        backref='venda',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Pagamento.data_pagamento.desc()'
    )
    
    # Relacionamento com pagamento múltiplo (para notas de restante)
    pagamento_multiplo_origem = db.relationship(
        'PagamentoMultiplo',
        foreign_keys=[pagamento_multiplo_id],
        backref='vendas_restante'
    )
    
    def __repr__(self):
        return f'<Venda #{self.id} - {self.cliente.nome if self.cliente else "Cliente N/A"}>'
    
    def __str__(self):
        return f"Venda #{self.id} - {self.total}"
    
    @property
    def valor_pago(self):
        """Valor total já pago desta venda"""
        total = self.pagamentos.with_entities(
            func.sum(db.text('pagamentos.valor'))
        ).scalar()
        
        return Decimal(str(total or 0))
    
    @property
    def valor_restante(self):
        """Valor restante a ser pago"""
        return self.total - self.valor_pago
    
    @property
    def esta_paga(self):
        """Verifica se a venda está completamente paga"""
        return self.valor_restante <= 0
    
    @property
    def esta_vencida(self):
        """Verifica se a venda está vencida"""
        if self.status == STATUS_VENDA['PAGA']:
            return False
        
        return date.today() > self.data_vencimento
    
    @property
    def dias_atraso(self):
        """Número de dias em atraso"""
        if not self.esta_vencida:
            return 0
        
        return (date.today() - self.data_vencimento).days
    
    @property
    def status_display(self):
        """Status formatado para exibição"""
        from app.utils.constants import STATUS_VENDA_LABELS
        return STATUS_VENDA_LABELS.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Cor do status para exibição"""
        from app.utils.constants import STATUS_VENDA_COLORS
        
        if self.esta_vencida and self.status == STATUS_VENDA['ABERTA']:
            return 'danger'
        
        return STATUS_VENDA_COLORS.get(self.status, 'secondary')
    
    @property
    def descricao_restante(self):
        """Descrição para notas de restante"""
        if not self.eh_restante:
            return None
        
        if self.pagamento_multiplo_origem:
            detalhes = self.pagamento_multiplo_origem.detalhes
            notas_ids = [str(d.venda_id) for d in detalhes]
            data_pagamento = self.pagamento_multiplo_origem.data_pagamento
            
            return {
                'notas_ids': notas_ids,
                'data_pagamento': data_pagamento,
                'valor_total_notas': self.pagamento_multiplo_origem.valor_total_notas,
                'valor_pago': self.pagamento_multiplo_origem.valor_pago
            }
        
        return None
    
    def calcular_totais(self):
        """Recalcular subtotal e total baseado nos itens"""
        subtotal = self.itens.with_entities(
            func.sum(db.text('itens_venda.subtotal'))
        ).scalar() or 0
        
        self.subtotal = Decimal(str(subtotal))
        self.total = self.subtotal  # Sem desconto por enquanto
    
    def adicionar_item(self, descricao, quantidade, valor_unitario):
        """Adicionar item à venda"""
        from app.models.item_venda import ItemVenda
        
        item = ItemVenda(
            descricao=descricao,
            quantidade=Decimal(str(quantidade)),
            valor_unitario=Decimal(str(valor_unitario))
        )
        item.calcular_subtotal()
        
        self.itens.append(item)
        self.calcular_totais()
        
        return item
    
    def registrar_pagamento(self, valor, forma_pagamento, valor_recebido=None, observacoes=None):
        """Registrar pagamento para esta venda"""
        from app.models.pagamento import Pagamento
        
        # Validar valor
        valor_decimal = Decimal(str(valor))
        if valor_decimal <= 0:
            raise ValueError("Valor do pagamento deve ser positivo")
        
        if valor_decimal > self.valor_restante:
            raise ValueError("Valor do pagamento maior que o valor restante")
        
        # Criar pagamento
        pagamento = Pagamento(
            valor=valor_decimal,
            forma_pagamento=forma_pagamento,
            valor_recebido=Decimal(str(valor_recebido)) if valor_recebido else None,
            data_pagamento=date.today(),
            observacoes=observacoes
        )
        
        self.pagamentos.append(pagamento)
        
        # Atualizar status se necessário
        if self.esta_paga:
            self.status = STATUS_VENDA['PAGA']
            self.data_pagamento = date.today()
        
        return pagamento
    
    def atualizar_status(self):
        """Atualizar status baseado no pagamento"""
        if self.esta_paga:
            self.status = STATUS_VENDA['PAGA']
            if not self.data_pagamento:
                self.data_pagamento = date.today()
        elif self.esta_vencida:
            self.status = STATUS_VENDA['VENCIDA']
        else:
            self.status = STATUS_VENDA['ABERTA']
    
    def gerar_data_vencimento(self, dias=None):
        """Gerar data de vencimento baseada na data da venda"""
        if dias is None:
            dias = DIAS_VENCIMENTO_PADRAO
        
        self.data_vencimento = self.data_venda + timedelta(days=dias)
    
    def to_dict(self, include_itens=True, include_pagamentos=False):
        """Converter para dicionário"""
        data = {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome if self.cliente else None,
            'data_venda': self.data_venda.isoformat() if self.data_venda else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'subtotal': float(self.subtotal),
            'total': float(self.total),
            'valor_pago': float(self.valor_pago),
            'valor_restante': float(self.valor_restante),
            'status': self.status,
            'status_display': self.status_display,
            'status_color': self.status_color,
            'esta_paga': self.esta_paga,
            'esta_vencida': self.esta_vencida,
            'dias_atraso': self.dias_atraso,
            'eh_restante': self.eh_restante,
            'observacoes': self.observacoes
        }
        
        if include_itens:
            data['itens'] = [item.to_dict() for item in self.itens]
        
        if include_pagamentos:
            data['pagamentos'] = [pag.to_dict() for pag in self.pagamentos]
        
        if self.eh_restante:
            data['descricao_restante'] = self.descricao_restante
        
        return data
    
    @staticmethod
    def buscar_por_periodo(data_inicio, data_fim, cliente_id=None, status=None):
        """Buscar vendas por período"""
        query = Venda.query.filter(
            Venda.data_venda >= data_inicio,
            Venda.data_venda <= data_fim
        )
        
        if cliente_id:
            query = query.filter(Venda.cliente_id == cliente_id)
        
        if status:
            query = query.filter(Venda.status == status)
        
        return query.order_by(Venda.data_venda.desc())
    
    @staticmethod
    def vendas_vencidas(dias_atraso=None):
        """Listar vendas vencidas"""
        data_limite = date.today()
        
        if dias_atraso:
            data_limite = date.today() - timedelta(days=dias_atraso)
        
        return Venda.query.filter(
            Venda.status == STATUS_VENDA['ABERTA'],
            Venda.data_vencimento < data_limite
        ).order_by(Venda.data_vencimento)
    
    @staticmethod
    def vendas_hoje():
        """Vendas realizadas hoje"""
        return Venda.query.filter(
            Venda.data_venda == date.today()
        ).order_by(Venda.data_criacao.desc())
    
    @staticmethod
    def total_vendas_periodo(data_inicio, data_fim, apenas_pagas=False):
        """Total de vendas em um período"""
        query = Venda.query.filter(
            Venda.data_venda >= data_inicio,
            Venda.data_venda <= data_fim
        )
        
        if apenas_pagas:
            query = query.filter(Venda.status == STATUS_VENDA['PAGA'])
        
        total = query.with_entities(
            func.sum(Venda.total)
        ).scalar()
        
        return Decimal(str(total or 0))
    
    def validate(self):
        """Validar dados da venda"""
        errors = []
        
        # Validar cliente
        if not self.cliente_id:
            errors.append("Cliente é obrigatório")
        
        # Validar valor mínimo
        if self.total < VALOR_MINIMO_VENDA:
            errors.append(f"Valor mínimo da venda: R$ {VALOR_MINIMO_VENDA}")
        
        # Validar data de vencimento
        if self.data_vencimento and self.data_vencimento < self.data_venda:
            errors.append("Data de vencimento não pode ser anterior à data da venda")
        
        # Validar itens
        if self.itens.count() == 0:
            errors.append("Venda deve ter pelo menos um item")
        
        return errors
    
    def before_update(self):
        """Hook executado antes de atualizar"""
        self.data_atualizacao = datetime.utcnow()
        self.atualizar_status()


# Eventos SQLAlchemy
from sqlalchemy import event

@event.listens_for(Venda, 'before_update')
def venda_before_update(mapper, connection, target):
    """Executado antes de atualizar venda"""
    target.before_update()

@event.listens_for(Venda, 'before_insert')
def venda_before_insert(mapper, connection, target):
    """Executado antes de inserir venda"""
    # Gerar data de vencimento se não informada
    if not target.data_vencimento:
        target.gerar_data_vencimento()