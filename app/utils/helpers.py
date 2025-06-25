"""
Funções auxiliares utilizadas em todo o sistema
"""

import re
import locale
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union


def format_currency(value: Union[float, Decimal, None]) -> str:
    """
    Formatar valor monetário para exibição
    
    Args:
        value: Valor a ser formatado
        
    Returns:
        String formatada (ex: "R$ 1.234,56")
    """
    if value is None:
        return "R$ 0,00"
    
    if isinstance(value, str):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return "R$ 0,00"
    
    # Configurar locale brasileiro se disponível
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(value, grouping=True, symbol='R$')
    except locale.Error:
        # Fallback para formatação manual
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def parse_currency(value: str) -> Decimal:
    """
    Converter string monetária para Decimal
    
    Args:
        value: String no formato "R$ 1.234,56" ou "1234,56"
        
    Returns:
        Valor Decimal
    """
    if not value:
        return Decimal('0.00')
    
    # Remover símbolos e espaços
    cleaned = re.sub(r'[^\d,.-]', '', str(value))
    
    # Substituir vírgula por ponto se necessário
    if ',' in cleaned and '.' in cleaned:
        # Formato brasileiro: 1.234,56
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        # Apenas vírgula: 1234,56
        cleaned = cleaned.replace(',', '.')
    
    try:
        return Decimal(cleaned).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return Decimal('0.00')


def format_cpf(cpf: str) -> str:
    """
    Formatar CPF para exibição
    
    Args:
        cpf: CPF sem formatação
        
    Returns:
        CPF formatado (ex: "123.456.789-01")
    """
    if not cpf:
        return ""
    
    # Remover caracteres não numéricos
    numbers = re.sub(r'\D', '', cpf)
    
    if len(numbers) == 11:
        return f"{numbers[:3]}.{numbers[3:6]}.{numbers[6:9]}-{numbers[9:]}"
    
    return cpf


def validate_cpf(cpf: str) -> bool:
    """
    Validar CPF usando algoritmo oficial
    
    Args:
        cpf: CPF a ser validado
        
    Returns:
        True se válido, False caso contrário
    """
    if not cpf:
        return False
    
    # Remover caracteres não numéricos
    numbers = re.sub(r'\D', '', cpf)
    
    # Verificar se tem 11 dígitos
    if len(numbers) != 11:
        return False
    
    # Verificar se todos os dígitos são iguais
    if numbers == numbers[0] * 11:
        return False
    
    # Calcular primeiro dígito verificador
    sum1 = sum(int(numbers[i]) * (10 - i) for i in range(9))
    digit1 = 11 - (sum1 % 11)
    if digit1 >= 10:
        digit1 = 0
    
    # Calcular segundo dígito verificador
    sum2 = sum(int(numbers[i]) * (11 - i) for i in range(10))
    digit2 = 11 - (sum2 % 11)
    if digit2 >= 10:
        digit2 = 0
    
    # Verificar se os dígitos calculados coincidem
    return int(numbers[9]) == digit1 and int(numbers[10]) == digit2


def format_phone(phone: str) -> str:
    """
    Formatar telefone para exibição
    
    Args:
        phone: Telefone sem formatação
        
    Returns:
        Telefone formatado (ex: "(31) 99999-9999")
    """
    if not phone:
        return ""
    
    # Remover caracteres não numéricos
    numbers = re.sub(r'\D', '', phone)
    
    if len(numbers) == 11:
        return f"({numbers[:2]}) {numbers[2:7]}-{numbers[7:]}"
    elif len(numbers) == 10:
        return f"({numbers[:2]}) {numbers[2:6]}-{numbers[6:]}"
    
    return phone


def format_date(date_value: Union[datetime, date, str, None], format_str: str = "%d/%m/%Y") -> str:
    """
    Formatar data para exibição
    
    Args:
        date_value: Data a ser formatada
        format_str: Formato de saída
        
    Returns:
        Data formatada
    """
    if not date_value:
        return ""
    
    if isinstance(date_value, str):
        try:
            # Tentar parsear diferentes formatos
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    date_value = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
        except ValueError:
            return date_value
    
    if isinstance(date_value, datetime):
        date_value = date_value.date()
    
    if isinstance(date_value, date):
        return date_value.strftime(format_str)
    
    return str(date_value)


def format_datetime(datetime_value: Union[datetime, str, None], format_str: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formatar datetime para exibição
    
    Args:
        datetime_value: Datetime a ser formatado
        format_str: Formato de saída
        
    Returns:
        Datetime formatado
    """
    if not datetime_value:
        return ""
    
    if isinstance(datetime_value, str):
        try:
            datetime_value = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime_value
    
    if isinstance(datetime_value, datetime):
        return datetime_value.strftime(format_str)
    
    return str(datetime_value)


def days_between(date1: Union[datetime, date], date2: Union[datetime, date, None] = None) -> int:
    """
    Calcular dias entre duas datas
    
    Args:
        date1: Data inicial
        date2: Data final (padrão: hoje)
        
    Returns:
        Número de dias
    """
    if date2 is None:
        date2 = date.today()
    
    if isinstance(date1, datetime):
        date1 = date1.date()
    if isinstance(date2, datetime):
        date2 = date2.date()
    
    return (date2 - date1).days


def is_overdue(due_date: Union[datetime, date], days_limit: int = 30) -> bool:
    """
    Verificar se uma data está vencida além do limite
    
    Args:
        due_date: Data de vencimento
        days_limit: Limite de dias para considerar inadimplente
        
    Returns:
        True se estiver inadimplente
    """
    if not due_date:
        return False
    
    days_overdue = days_between(due_date)
    return days_overdue > days_limit


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncar texto para exibição
    
    Args:
        text: Texto a ser truncado
        max_length: Comprimento máximo
        suffix: Sufixo para texto truncado
        
    Returns:
        Texto truncado
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitizar nome de arquivo
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Nome sanitizado
    """
    if not filename:
        return "arquivo"
    
    # Remover caracteres especiais
    sanitized = re.sub(r'[^\w\s-.]', '', filename)
    # Substituir espaços por underscore
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remover underscores múltiplos
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized.lower()


def generate_export_filename(prefix: str, extension: str = "csv") -> str:
    """
    Gerar nome de arquivo para exportação
    
    Args:
        prefix: Prefixo do arquivo
        extension: Extensão do arquivo
        
    Returns:
        Nome do arquivo com timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{sanitize_filename(prefix)}_{timestamp}.{extension}"


def paginate_query(query, page: int = 1, per_page: int = 20):
    """
    Paginar query SQLAlchemy
    
    Args:
        query: Query SQLAlchemy
        page: Página atual
        per_page: Itens por página
        
    Returns:
        Objeto Pagination
    """
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )


def flash_success(message: str):
    """
    Adicionar mensagem de sucesso
    
    Args:
        message: Mensagem a ser exibida
    """
    from flask import flash
    flash(message, 'success')


def flash_error(message: str):
    """
    Adicionar mensagem de erro
    
    Args:
        message: Mensagem a ser exibida
    """
    from flask import flash
    flash(message, 'danger')


def flash_warning(message: str):
    """
    Adicionar mensagem de aviso
    
    Args:
        message: Mensagem a ser exibida
    """
    from flask import flash
    flash(message, 'warning')


def flash_info(message: str):
    """
    Adicionar mensagem informativa
    
    Args:
        message: Mensagem a ser exibida
    """
    from flask import flash
    flash(message, 'info')