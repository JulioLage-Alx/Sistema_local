"""
Modelo Cliente - Gerenciamento de clientes do açougue
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.utils.constants import LIMITE_CREDITO_PADRAO


class Cliente(db.Model):
    """Modelo para clientes do açougue"""
    
    __tablename__ = 'clientes'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    cpf = db.Column(db.String(14), unique=True, nullable=True, index=True)
    telefone = db.Column(db.String(15), nullable=True)
    endereco = db.Column(db.Text, nullable=True)
    
    # Configurações de crédito
    limite_credito = db.Column(
        db.Numeric(10, 2), 
        nullable=False, 
        default=LIMITE_CREDITO_PADRAO
    )
    
    # Controle
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    data_cadastro = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        index=True
    )
    data_atualizacao = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    vendas = db.relationship(
        'Venda', 
        backref='cliente', 
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<Cliente {self.nome}>'
    
    def __str__(self):
        return self.nome
    
    @property
    def vendas_em_aberto(self):
        """Vendas em aberto do cliente"""
        from app.models.venda import Venda
        return self.vendas.filter(Venda.status == 'aberta')
    
    @property
    def vendas_vencidas(self):
        """Vendas vencidas do cliente"""
        from app.models.venda import Venda
        from app.utils.constants import DIAS_INADIMPLENCIA
        from datetime import date, timedelta
        
        data_limite = date.today() - timedelta(days=DIAS_INADIMPLENCIA)
        
        return self.vendas.filter(
            Venda.status == 'aberta',
            Venda.data_vencimento < data_limite
        )
    
    @property
    def valor_total_em_aberto(self):
        """Valor total das vendas em aberto"""
        total = self.vendas_em_aberto.with_entities(
            func.sum(db.text('vendas.total'))
        ).scalar()
        
        return Decimal(str(total or 0))
    
    @property
    def valor_total_vencido(self):
        """Valor total das vendas vencidas"""
        total = self.vendas_vencidas.with_entities(
            func.sum(db.text('vendas.total'))
        ).scalar()
        
        return Decimal(str(total or 0))
    
    @property
    def credito_disponivel(self):
        """Crédito disponível para o cliente"""
        valor_usado = self.valor_total_em_aberto
        return self.limite_credito - valor_usado
    
    @property
    def esta_inadimplente(self):
        """Verifica se o cliente está inadimplente"""
        return self.vendas_vencidas.count() > 0
    
    @property
    def pode_comprar(self):
        """Verifica se o cliente pode fazer novas compras"""
        return (self.ativo and 
                self.credito_disponivel > 0 and 
                not self.esta_inadimplente)
    
    def historico_vendas(self, limit=None):
        """Histórico de vendas do cliente ordenado por data"""
        from app.models.venda import Venda
        
        query = self.vendas.order_by(Venda.data_venda.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query
    
    def total_compras_periodo(self, data_inicio, data_fim):
        """Total de compras em um período"""
        from app.models.venda import Venda
        
        total = self.vendas.filter(
            Venda.data_venda >= data_inicio,
            Venda.data_venda <= data_fim,
            Venda.status.in_(['paga', 'aberta'])
        ).with_entities(
            func.sum(Venda.total)
        ).scalar()
        
        return Decimal(str(total or 0))
    
    def verificar_limite_credito(self, valor_nova_compra):
        """Verificar se uma nova compra excede o limite"""
        valor_total_com_nova = self.valor_total_em_aberto + Decimal(str(valor_nova_compra))
        return valor_total_com_nova <= self.limite_credito
    
    def to_dict(self, include_vendas=False):
        """Converter para dicionário"""
        data = {
            'id': self.id,
            'nome': self.nome,
            'cpf': self.cpf,
            'telefone': self.telefone,
            'endereco': self.endereco,
            'limite_credito': float(self.limite_credito),
            'ativo': self.ativo,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'observacoes': self.observacoes,
            'valor_total_em_aberto': float(self.valor_total_em_aberto),
            'credito_disponivel': float(self.credito_disponivel),
            'esta_inadimplente': self.esta_inadimplente,
            'pode_comprar': self.pode_comprar
        }
        
        if include_vendas:
            data['vendas'] = [venda.to_dict() for venda in self.historico_vendas(10)]
        
        return data
    
    @staticmethod
    def buscar(termo, apenas_ativos=True):
        """Buscar clientes por nome, CPF ou telefone"""
        query = Cliente.query
        
        if apenas_ativos:
            query = query.filter(Cliente.ativo == True)
        
        if termo:
            # Remover formatação para busca
            termo_limpo = ''.join(filter(str.isalnum, termo))
            
            query = query.filter(
                db.or_(
                    Cliente.nome.ilike(f'%{termo}%'),
                    func.replace(func.replace(func.replace(
                        Cliente.cpf, '.', ''), '-', ''), ' ', ''
                    ).ilike(f'%{termo_limpo}%'),
                    func.replace(func.replace(func.replace(func.replace(
                        Cliente.telefone, '(', ''), ')', ''), '-', ''), ' ', ''
                    ).ilike(f'%{termo_limpo}%')
                )
            )
        
        return query.order_by(Cliente.nome)
    
    @staticmethod
    def clientes_inadimplentes():
        """Listar clientes inadimplentes"""
        from app.models.venda import Venda
        from app.utils.constants import DIAS_INADIMPLENCIA
        from datetime import date, timedelta
        
        data_limite = date.today() - timedelta(days=DIAS_INADIMPLENCIA)
        
        return Cliente.query.join(Venda).filter(
            Cliente.ativo == True,
            Venda.status == 'aberta',
            Venda.data_vencimento < data_limite
        ).distinct()
    
    @staticmethod
    def clientes_acima_limite():
        """Clientes com saldo acima do limite configurado"""
        # Esta query será implementada no service
        return Cliente.query.filter(Cliente.ativo == True)
    
    def before_update(self):
        """Hook executado antes de atualizar"""
        self.data_atualizacao = datetime.utcnow()
    
    def validate(self):
        """Validar dados do cliente"""
        errors = []
        
        # Validar nome
        if not self.nome or len(self.nome.strip()) < 2:
            errors.append("Nome deve ter pelo menos 2 caracteres")
        
        # Validar CPF se informado
        if self.cpf:
            from app.utils.helpers import validate_cpf
            if not validate_cpf(self.cpf):
                errors.append("CPF inválido")
        
        # Validar limite de crédito
        if self.limite_credito < 0:
            errors.append("Limite de crédito não pode ser negativo")
        
        return errors


# Eventos SQLAlchemy
from sqlalchemy import event

@event.listens_for(Cliente, 'before_update')
def cliente_before_update(mapper, connection, target):
    """Executado antes de atualizar cliente"""
    target.before_update()