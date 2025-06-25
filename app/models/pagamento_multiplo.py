"""
Modelo PagamentoMultiplo - Pagamentos de múltiplas vendas em uma operação
"""

from datetime import datetime, date
from decimal import Decimal
from app import db
from app.utils.constants import FORMAS_PAGAMENTO, STATUS_VENDA


class PagamentoMultiplo(db.Model):
    """Modelo para pagamentos múltiplos (várias vendas de uma vez)"""
    
    __tablename__ = 'pagamentos_multiplos'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer, 
        db.ForeignKey('clientes.id', ondelete='RESTRICT'), 
        nullable=False,
        index=True
    )
    
    # Valores do pagamento múltiplo
    valor_total_notas = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    valor_pago = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    valor_restante = db.Column(
        db.Numeric(10, 2), 
        nullable=False,
        default=0
    )
    
    # Dados do pagamento
    forma_pagamento = db.Column(
        db.String(20), 
        nullable=False,
        default=FORMAS_PAGAMENTO['DINHEIRO']
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
    
    # Relacionamentos
    cliente = db.relationship('Cliente', backref='pagamentos_multiplos')
    
    detalhes = db.relationship(
        'PagamentoMultiploDetalhe',
        backref='pagamento_multiplo',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<PagamentoMultiplo R$ {self.valor_pago} - {self.cliente.nome if self.cliente else "Cliente N/A"}>'
    
    def __str__(self):
        return f"Pagamento Múltiplo R$ {self.valor_pago} - {self.data_pagamento}"
    
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
    def tem_restante(self):
        """Verifica se sobrou valor restante"""
        return self.valor_restante > 0
    
    @property
    def notas_pagas(self):
        """Lista das vendas que foram pagas"""
        return [detalhe.venda for detalhe in self.detalhes if detalhe.venda]
    
    @property
    def notas_ids(self):
        """IDs das notas que foram pagas"""
        return [detalhe.venda_id for detalhe in self.detalhes]
    
    def calcular_troco(self):
        """Calcular troco para pagamentos em dinheiro"""
        if self.eh_dinheiro and self.valor_recebido:
            troco = Decimal(str(self.valor_recebido)) - Decimal(str(self.valor_pago))
            self.troco = max(troco, Decimal('0.00'))
        else:
            self.troco = Decimal('0.00')
        
        return self.troco
    
    def calcular_valores(self):
        """Calcular valor restante baseado no total e valor pago"""
        self.valor_restante = self.valor_total_notas - self.valor_pago
        
        if self.valor_restante < 0:
            self.valor_restante = Decimal('0.00')
    
    def adicionar_venda(self, venda, valor_pago_venda=None):
        """Adicionar venda ao pagamento múltiplo"""
        if valor_pago_venda is None:
            valor_pago_venda = venda.valor_restante
        
        detalhe = PagamentoMultiploDetalhe(
            venda_id=venda.id,
            valor_original=venda.total,
            valor_pago=Decimal(str(valor_pago_venda))
        )
        
        self.detalhes.append(detalhe)
        return detalhe
    
    def processar_pagamento(self):
        """Processar o pagamento múltiplo"""
        from app.models.venda import Venda
        from app.models.item_venda import ItemVenda
        
        # Processar cada venda
        for detalhe in self.detalhes:
            venda = detalhe.venda
            if not venda:
                continue
            
            # Criar pagamento individual para a venda
            pagamento = venda.registrar_pagamento(
                valor=detalhe.valor_pago,
                forma_pagamento=self.forma_pagamento,
                valor_recebido=None,  # Não se aplica em pagamento múltiplo
                observacoes=f"Pagamento múltiplo #{self.id}"
            )
        
        # Criar nota de restante se necessário
        if self.tem_restante:
            venda_restante = Venda(
                cliente_id=self.cliente_id,
                data_venda=self.data_pagamento,
                eh_restante=True,
                pagamento_multiplo_id=self.id,
                observacoes=f"Restante do pagamento múltiplo #{self.id}"
            )
            
            # Gerar data de vencimento
            venda_restante.gerar_data_vencimento()
            
            # Adicionar item de restante
            item_restante = ItemVenda.criar_item_restante(
                valor_restante=self.valor_restante,
                notas_ids=self.notas_ids,
                data_pagamento=self.data_pagamento
            )
            
            venda_restante.itens.append(item_restante)
            venda_restante.calcular_totais()
            
            # Salvar venda de restante
            db.session.add(venda_restante)
            
            return venda_restante
        
        return None
    
    def gerar_comprovante_dados(self):
        """Gerar dados para impressão do comprovante"""
        dados = {
            'pagamento_multiplo_id': self.id,
            'cliente_nome': self.cliente.nome if self.cliente else 'Cliente não identificado',
            'data_pagamento': self.data_pagamento,
            'valor_total_notas': self.valor_total_notas,
            'valor_pago': self.valor_pago,
            'valor_restante': self.valor_restante,
            'forma_pagamento': self.forma_pagamento_display,
            'tem_restante': self.tem_restante,
            'notas_pagas': []
        }
        
        # Adicionar dados específicos do dinheiro
        if self.eh_dinheiro:
            dados.update({
                'valor_recebido': self.valor_recebido,
                'troco': self.troco
            })
        
        # Adicionar detalhes das notas pagas
        for detalhe in self.detalhes:
            if detalhe.venda:
                dados['notas_pagas'].append({
                    'venda_id': detalhe.venda_id,
                    'valor_original': float(detalhe.valor_original),
                    'valor_pago': float(detalhe.valor_pago),
                    'data_venda': detalhe.venda.data_venda.isoformat()
                })
        
        return dados
    
    def to_dict(self, include_detalhes=True):
        """Converter para dicionário"""
        from app.utils.helpers import format_currency
        
        data = {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome if self.cliente else None,
            'valor_total_notas': float(self.valor_total_notas),
            'valor_pago': float(self.valor_pago),
            'valor_restante': float(self.valor_restante),
            'forma_pagamento': self.forma_pagamento,
            'forma_pagamento_display': self.forma_pagamento_display,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'observacoes': self.observacoes,
            'eh_dinheiro': self.eh_dinheiro,
            'tem_restante': self.tem_restante,
            'notas_ids': self.notas_ids
        }
        
        # Adicionar campos específicos do dinheiro
        if self.eh_dinheiro:
            data.update({
                'valor_recebido': float(self.valor_recebido) if self.valor_recebido else None,
                'troco': float(self.troco) if self.troco else None
            })
        
        # Incluir detalhes se solicitado
        if include_detalhes:
            data['detalhes'] = [detalhe.to_dict() for detalhe in self.detalhes]
        
        return data
    
    def validate(self):
        """Validar dados do pagamento múltiplo"""
        errors = []
        
        # Validar valores
        if not self.valor_total_notas or self.valor_total_notas <= 0:
            errors.append("Valor total das notas deve ser maior que zero")
        
        if not self.valor_pago or self.valor_pago <= 0:
            errors.append("Valor pago deve ser maior que zero")
        
        if self.valor_pago > self.valor_total_notas:
            errors.append("Valor pago não pode ser maior que o valor total das notas")
        
        # Validar forma de pagamento
        if self.forma_pagamento not in FORMAS_PAGAMENTO.values():
            errors.append("Forma de pagamento inválida")
        
        # Validações específicas para dinheiro
        if self.eh_dinheiro:
            if self.valor_recebido and self.valor_recebido < self.valor_pago:
                errors.append("Valor recebido não pode ser menor que o valor pago")
        
        # Validar se tem detalhes
        if self.detalhes.count() == 0:
            errors.append("Pagamento múltiplo deve ter pelo menos uma venda")
        
        return errors
    
    def before_insert(self):
        """Hook executado antes de inserir"""
        self.calcular_valores()
        if self.eh_dinheiro:
            self.calcular_troco()
    
    def before_update(self):
        """Hook executado antes de atualizar"""
        self.calcular_valores()
        if self.eh_dinheiro:
            self.calcular_troco()


class PagamentoMultiploDetalhe(db.Model):
    """Modelo para detalhes do pagamento múltiplo (vendas incluídas)"""
    
    __tablename__ = 'pagamentos_multiplos_detalhes'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    pagamento_multiplo_id = db.Column(
        db.Integer, 
        db.ForeignKey('pagamentos_multiplos.id', ondelete='CASCADE'), 
        nullable=False
    )
    venda_id = db.Column(
        db.Integer, 
        db.ForeignKey('vendas.id', ondelete='CASCADE'), 
        nullable=False
    )
    
    # Valores
    valor_original = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    valor_pago = db.Column(
        db.Numeric(10, 2), 
        nullable=False
    )
    
    # Relacionamentos
    venda = db.relationship('Venda')
    
    def __repr__(self):
        return f'<PagamentoMultiploDetalhe Venda #{self.venda_id} - R$ {self.valor_pago}>'
    
    @property
    def valor_restante_na_venda(self):
        """Valor que restou na venda após este pagamento"""
        return self.valor_original - self.valor_pago
    
    @property
    def pagou_total(self):
        """Verifica se pagou o valor total da venda"""
        return self.valor_pago >= self.valor_original
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'pagamento_multiplo_id': self.pagamento_multiplo_id,
            'venda_id': self.venda_id,
            'valor_original': float(self.valor_original),
            'valor_pago': float(self.valor_pago),
            'valor_restante_na_venda': float(self.valor_restante_na_venda),
            'pagou_total': self.pagou_total,
            'venda': self.venda.to_dict(include_itens=False) if self.venda else None
        }


# Eventos SQLAlchemy
from sqlalchemy import event

@event.listens_for(PagamentoMultiplo, 'before_insert')
def pagamento_multiplo_before_insert(mapper, connection, target):
    """Executado antes de inserir pagamento múltiplo"""
    target.before_insert()

@event.listens_for(PagamentoMultiplo, 'before_update')
def pagamento_multiplo_before_update(mapper, connection, target):
    """Executado antes de atualizar pagamento múltiplo"""
    target.before_update()