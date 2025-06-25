"""
Validações customizadas para formulários e modelos
"""

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from wtforms.validators import ValidationError


class CPFValidator:
    """Validador de CPF para WTForms"""
    
    def __init__(self, message=None):
        if not message:
            message = 'CPF inválido.'
        self.message = message
    
    def __call__(self, form, field):
        if field.data:
            from app.utils.helpers import validate_cpf
            if not validate_cpf(field.data):
                raise ValidationError(self.message)


class PhoneValidator:
    """Validador de telefone brasileiro"""
    
    def __init__(self, message=None):
        if not message:
            message = 'Telefone inválido. Use o formato (11) 99999-9999.'
        self.message = message
    
    def __call__(self, form, field):
        if field.data:
            # Remover formatação
            phone = re.sub(r'\D', '', field.data)
            
            # Validar comprimento (10 ou 11 dígitos)
            if len(phone) not in [10, 11]:
                raise ValidationError(self.message)
            
            # Validar se começa com DDD válido (código de área)
            if len(phone) >= 2:
                ddd = int(phone[:2])
                ddds_validos = [
                    11, 12, 13, 14, 15, 16, 17, 18, 19,  # SP
                    21, 22, 24,  # RJ/ES
                    27, 28,  # ES
                    31, 32, 33, 34, 35, 37, 38,  # MG
                    41, 42, 43, 44, 45, 46,  # PR
                    47, 48, 49,  # SC
                    51, 53, 54, 55,  # RS
                    61,  # DF/GO
                    62, 64,  # GO
                    63,  # TO
                    65, 66,  # MT
                    67,  # MS
                    68,  # AC
                    69,  # RO
                    71, 73, 74, 75, 77,  # BA
                    79,  # SE
                    81, 87,  # PE
                    82,  # AL
                    83,  # PB
                    84,  # RN
                    85, 88,  # CE
                    86, 89,  # PI
                    91, 93, 94,  # PA
                    92, 97,  # AM
                    95,  # RR
                    96,  # AP
                    98, 99  # MA
                ]
                
                if ddd not in ddds_validos:
                    raise ValidationError('DDD inválido.')


class DecimalValidator:
    """Validador para valores decimais"""
    
    def __init__(self, min_value=None, max_value=None, precision=2, message=None):
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision
        self.message = message
    
    def __call__(self, form, field):
        if field.data is None:
            return
        
        try:
            # Converter para Decimal
            if isinstance(field.data, str):
                from app.utils.helpers import parse_currency
                value = parse_currency(field.data)
            else:
                value = Decimal(str(field.data))
            
            # Validar precisão
            if value.as_tuple().exponent < -self.precision:
                message = self.message or f'Máximo {self.precision} casas decimais.'
                raise ValidationError(message)
            
            # Validar valor mínimo
            if self.min_value is not None and value < Decimal(str(self.min_value)):
                message = self.message or f'Valor mínimo: {self.min_value}'
                raise ValidationError(message)
            
            # Validar valor máximo
            if self.max_value is not None and value > Decimal(str(self.max_value)):
                message = self.message or f'Valor máximo: {self.max_value}'
                raise ValidationError(message)
                
        except (InvalidOperation, ValueError):
            message = self.message or 'Valor numérico inválido.'
            raise ValidationError(message)


class QuantityValidator:
    """Validador específico para quantidades"""
    
    def __init__(self, min_value=0.001, max_value=999.999, message=None):
        self.min_value = Decimal(str(min_value))
        self.max_value = Decimal(str(max_value))
        self.message = message
    
    def __call__(self, form, field):
        if field.data is None:
            return
        
        try:
            value = Decimal(str(field.data))
            
            if value <= 0:
                raise ValidationError('Quantidade deve ser maior que zero.')
            
            if value < self.min_value:
                message = self.message or f'Quantidade mínima: {self.min_value}'
                raise ValidationError(message)
            
            if value > self.max_value:
                message = self.message or f'Quantidade máxima: {self.max_value}'
                raise ValidationError(message)
                
        except (InvalidOperation, ValueError):
            raise ValidationError('Quantidade inválida.')


class DateRangeValidator:
    """Validador para faixas de data"""
    
    def __init__(self, min_date=None, max_date=None, message=None):
        self.min_date = min_date
        self.max_date = max_date
        self.message = message
    
    def __call__(self, form, field):
        if field.data is None:
            return
        
        field_date = field.data
        if isinstance(field_date, str):
            try:
                field_date = datetime.strptime(field_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError('Data inválida.')
        
        if self.min_date and field_date < self.min_date:
            message = self.message or f'Data mínima: {self.min_date.strftime("%d/%m/%Y")}'
            raise ValidationError(message)
        
        if self.max_date and field_date > self.max_date:
            message = self.message or f'Data máxima: {self.max_date.strftime("%d/%m/%Y")}'
            raise ValidationError(message)


class CreditLimitValidator:
    """Validador para limite de crédito do cliente"""
    
    def __init__(self, client_field='cliente_id', message=None):
        self.client_field = client_field
        self.message = message or 'Valor excede o limite de crédito do cliente.'
    
    def __call__(self, form, field):
        if field.data is None:
            return
        
        # Obter cliente do formulário
        cliente_id = getattr(form, self.client_field, None)
        if not cliente_id or not cliente_id.data:
            return
        
        try:
            from app.models.cliente import Cliente
            from app.utils.helpers import parse_currency
            
            cliente = Cliente.query.get(cliente_id.data)
            if not cliente:
                return
            
            # Converter valor para Decimal
            if isinstance(field.data, str):
                valor = parse_currency(field.data)
            else:
                valor = Decimal(str(field.data))
            
            # Verificar limite
            if not cliente.verificar_limite_credito(valor):
                credito_disponivel = cliente.credito_disponivel
                raise ValidationError(
                    f'{self.message} Crédito disponível: R$ {credito_disponivel:.2f}'
                )
                
        except Exception:
            # Em caso de erro, não bloquear a validação
            pass


class UniqueValidator:
    """Validador para campos únicos"""
    
    def __init__(self, model, field, exclude_id=None, message=None):
        self.model = model
        self.field = field
        self.exclude_id = exclude_id
        self.message = message or 'Este valor já existe.'
    
    def __call__(self, form, field):
        if field.data is None:
            return
        
        query = self.model.query.filter(
            getattr(self.model, self.field) == field.data
        )
        
        # Excluir registro atual em edições
        if self.exclude_id:
            exclude_value = getattr(form, self.exclude_id, None)
            if exclude_value and exclude_value.data:
                query = query.filter(
                    self.model.id != exclude_value.data
                )
        
        if query.first():
            raise ValidationError(self.message)


class ItemListValidator:
    """Validador para lista de itens da venda"""
    
    def __init__(self, min_items=1, message=None):
        self.min_items = min_items
        self.message = message or f'Adicione pelo menos {min_items} item(ns).'
    
    def __call__(self, form, field):
        # field.data deve ser uma lista de itens
        if not field.data or len(field.data) < self.min_items:
            raise ValidationError(self.message)
        
        # Validar cada item
        for i, item in enumerate(field.data):
            if not item.get('descricao'):
                raise ValidationError(f'Item {i+1}: Descrição é obrigatória.')
            
            try:
                quantidade = Decimal(str(item.get('quantidade', 0)))
                if quantidade <= 0:
                    raise ValidationError(f'Item {i+1}: Quantidade deve ser maior que zero.')
            except (InvalidOperation, ValueError):
                raise ValidationError(f'Item {i+1}: Quantidade inválida.')
            
            try:
                valor_unitario = Decimal(str(item.get('valor_unitario', 0)))
                if valor_unitario <= 0:
                    raise ValidationError(f'Item {i+1}: Valor unitário deve ser maior que zero.')
            except (InvalidOperation, ValueError):
                raise ValidationError(f'Item {i+1}: Valor unitário inválido.')


def validate_payment_amount(venda_id, valor):
    """Validar valor de pagamento"""
    from app.models.venda import Venda
    from app.utils.helpers import parse_currency
    
    venda = Venda.query.get(venda_id)
    if not venda:
        raise ValidationError('Venda não encontrada.')
    
    if isinstance(valor, str):
        valor = parse_currency(valor)
    else:
        valor = Decimal(str(valor))
    
    if valor <= 0:
        raise ValidationError('Valor do pagamento deve ser maior que zero.')
    
    if valor > venda.valor_restante:
        raise ValidationError(
            f'Valor excede o restante da venda. '
            f'Valor restante: R$ {venda.valor_restante:.2f}'
        )


def validate_multiple_payment(vendas_ids, valor_pago):
    """Validar pagamento múltiplo"""
    from app.models.venda import Venda
    from app.utils.helpers import parse_currency
    
    if not vendas_ids:
        raise ValidationError('Selecione pelo menos uma venda.')
    
    vendas = Venda.query.filter(Venda.id.in_(vendas_ids)).all()
    
    if len(vendas) != len(vendas_ids):
        raise ValidationError('Uma ou mais vendas não foram encontradas.')
    
    # Verificar se todas as vendas são do mesmo cliente
    cliente_ids = set(v.cliente_id for v in vendas)
    if len(cliente_ids) > 1:
        raise ValidationError('Todas as vendas devem ser do mesmo cliente.')
    
    # Verificar se todas estão em aberto
    for venda in vendas:
        if venda.status != 'aberta':
            raise ValidationError(f'Venda #{venda.id} não está em aberto.')
    
    # Validar valor pago
    if isinstance(valor_pago, str):
        valor_pago = parse_currency(valor_pago)
    else:
        valor_pago = Decimal(str(valor_pago))
    
    if valor_pago <= 0:
        raise ValidationError('Valor pago deve ser maior que zero.')
    
    valor_total_vendas = sum(v.valor_restante for v in vendas)
    
    if valor_pago > valor_total_vendas:
        raise ValidationError(
            f'Valor pago maior que o total das vendas. '
            f'Total: R$ {valor_total_vendas:.2f}'
        )
    
    return vendas, valor_total_vendas