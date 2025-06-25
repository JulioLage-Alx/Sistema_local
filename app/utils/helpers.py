"""
Funções auxiliares e utilitárias do sistema
"""

import re
import locale
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Union, Optional, Any, Dict, List
from flask import flash, request
from werkzeug.security import generate_password_hash, check_password_hash


# Configurar locale para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        # Fallback para C locale
        locale.setlocale(locale.LC_ALL, 'C')


def format_currency(value: Union[Decimal, float, int, str], symbol: str = 'R$') -> str:
    """
    Formatar valor como moeda brasileira
    
    Args:
        value: Valor a ser formatado
        symbol: Símbolo da moeda
        
    Returns:
        String formatada (ex: "R$ 1.234,56")
    """
    try:
        if value is None:
            return f"{symbol} 0,00"
        
        # Converter para Decimal para precisão
        if isinstance(value, str):
            value = parse_currency(value)
        
        decimal_value = Decimal(str(value))
        
        # Formatar usando locale brasileiro
        try:
            formatted = locale.currency(float(decimal_value), grouping=True, symbol=False)
            return f"{symbol} {formatted}"
        except:
            # Fallback manual se locale não funcionar
            abs_value = abs(decimal_value)
            formatted = f"{abs_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            if decimal_value < 0:
                formatted = f"-{formatted}"
            return f"{symbol} {formatted}"
    
    except (ValueError, TypeError, InvalidOperation):
        return f"{symbol} 0,00"


def parse_currency(value: Union[str, float, int, Decimal]) -> Decimal:
    """
    Converter string de moeda para Decimal
    
    Args:
        value: Valor a ser convertido (ex: "R$ 1.234,56" ou "1234.56")
        
    Returns:
        Valor como Decimal
    """
    try:
        if value is None:
            return Decimal('0.00')
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        # Remover símbolos e espaços
        clean_value = str(value).strip()
        clean_value = re.sub(r'[R$\s]', '', clean_value)
        
        # Se está vazio, retornar zero
        if not clean_value:
            return Decimal('0.00')
        
        # Verificar formato brasileiro (vírgula como decimal)
        if ',' in clean_value and '.' in clean_value:
            # Formato: 1.234,56
            clean_value = clean_value.replace('.', '').replace(',', '.')
        elif ',' in clean_value and clean_value.count(',') == 1:
            # Formato: 1234,56
            clean_value = clean_value.replace(',', '.')
        
        return Decimal(clean_value)
    
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0.00')


def validate_cpf(cpf: str) -> bool:
    """
    Validar CPF brasileiro
    
    Args:
        cpf: CPF a ser validado
        
    Returns:
        True se CPF é válido
    """
    if not cpf:
        return False
    
    # Remover formatação
    cpf_numbers = re.sub(r'[^0-9]', '', cpf)
    
    # Verificar se tem 11 dígitos
    if len(cpf_numbers) != 11:
        return False
    
    # Verificar se não são todos iguais
    if cpf_numbers == cpf_numbers[0] * 11:
        return False
    
    # Calcular primeiro dígito verificador
    sum1 = sum(int(cpf_numbers[i]) * (10 - i) for i in range(9))
    digit1 = 11 - (sum1 % 11)
    if digit1 >= 10:
        digit1 = 0
    
    # Calcular segundo dígito verificador
    sum2 = sum(int(cpf_numbers[i]) * (11 - i) for i in range(10))
    digit2 = 11 - (sum2 % 11)
    if digit2 >= 10:
        digit2 = 0
    
    # Verificar se os dígitos estão corretos
    return cpf_numbers[-2:] == f"{digit1}{digit2}"


def format_cpf(cpf: str) -> str:
    """
    Formatar CPF com máscara
    
    Args:
        cpf: CPF sem formatação
        
    Returns:
        CPF formatado (ex: "123.456.789-01")
    """
    if not cpf:
        return ""
    
    cpf_numbers = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf_numbers) == 11:
        return f"{cpf_numbers[:3]}.{cpf_numbers[3:6]}.{cpf_numbers[6:9]}-{cpf_numbers[9:]}"
    
    return cpf


def format_phone(phone: str) -> str:
    """
    Formatar telefone brasileiro
    
    Args:
        phone: Telefone sem formatação
        
    Returns:
        Telefone formatado
    """
    if not phone:
        return ""
    
    phone_numbers = re.sub(r'[^0-9]', '', phone)
    
    if len(phone_numbers) == 11:
        # Celular: (11) 99999-9999
        return f"({phone_numbers[:2]}) {phone_numbers[2:7]}-{phone_numbers[7:]}"
    elif len(phone_numbers) == 10:
        # Fixo: (11) 9999-9999
        return f"({phone_numbers[:2]}) {phone_numbers[2:6]}-{phone_numbers[6:]}"
    
    return phone


def clean_phone(phone: str) -> str:
    """
    Limpar telefone removendo formatação
    
    Args:
        phone: Telefone com ou sem formatação
        
    Returns:
        Apenas números
    """
    if not phone:
        return ""
    
    return re.sub(r'[^0-9]', '', phone)


def format_date(date_value: Union[date, datetime, str], format_type: str = 'short') -> str:
    """
    Formatar data
    
    Args:
        date_value: Data a ser formatada
        format_type: 'short' (01/01/2023) ou 'long' (1 de janeiro de 2023)
        
    Returns:
        Data formatada
    """
    try:
        if isinstance(date_value, str):
            # Tentar converter string para data
            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
        elif isinstance(date_value, datetime):
            date_value = date_value.date()
        
        if format_type == 'short':
            return date_value.strftime('%d/%m/%Y')
        elif format_type == 'long':
            months = [
                'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
            ]
            return f"{date_value.day} de {months[date_value.month - 1]} de {date_value.year}"
        else:
            return date_value.strftime('%d/%m/%Y')
    
    except (ValueError, TypeError, AttributeError):
        return ""


def parse_date(date_string: str) -> Optional[date]:
    """
    Converter string para data
    
    Args:
        date_string: String de data (formatos: dd/mm/yyyy, yyyy-mm-dd)
        
    Returns:
        Objeto date ou None
    """
    if not date_string:
        return None
    
    try:
        # Formato brasileiro: dd/mm/yyyy
        if '/' in date_string:
            return datetime.strptime(date_string, '%d/%m/%Y').date()
        # Formato ISO: yyyy-mm-dd
        elif '-' in date_string:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        
        return None
    
    except ValueError:
        return None


def is_valid_date(date_string: str) -> bool:
    """
    Verificar se string representa uma data válida
    
    Args:
        date_string: String de data
        
    Returns:
        True se data é válida
    """
    return parse_date(date_string) is not None


def safe_int(value: Any, default: int = 0) -> int:
    """
    Conversão segura para inteiro
    
    Args:
        value: Valor a ser convertido
        default: Valor padrão se conversão falhar
        
    Returns:
        Valor convertido ou padrão
    """
    try:
        if value is None or value == '':
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Conversão segura para float
    
    Args:
        value: Valor a ser convertido
        default: Valor padrão se conversão falhar
        
    Returns:
        Valor convertido ou padrão
    """
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def flash_success(message: str) -> None:
    """Flash message de sucesso"""
    flash(message, 'success')


def flash_error(message: str) -> None:
    """Flash message de erro"""
    flash(message, 'danger')


def flash_warning(message: str) -> None:
    """Flash message de aviso"""
    flash(message, 'warning')


def flash_info(message: str) -> None:
    """Flash message informativa"""
    flash(message, 'info')


def paginate_query(query, page: int = 1, per_page: int = 20, error_out: bool = False) -> Any:
    """
    Paginar query SQLAlchemy
    
    Args:
        query: Query SQLAlchemy
        page: Página atual
        per_page: Itens por página
        error_out: Se deve gerar erro em página inválida
        
    Returns:
        Objeto Pagination
    """
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=error_out
    )


def get_page_from_request(default: int = 1) -> int:
    """
    Obter número da página do request
    
    Args:
        default: Página padrão
        
    Returns:
        Número da página
    """
    return safe_int(request.args.get('page'), default)


def get_per_page_from_request(default: int = 20, max_per_page: int = 100) -> int:
    """
    Obter itens por página do request
    
    Args:
        default: Valor padrão
        max_per_page: Máximo permitido
        
    Returns:
        Itens por página
    """
    per_page = safe_int(request.args.get('per_page'), default)
    return min(per_page, max_per_page)


def generate_hash_password(password: str) -> str:
    """
    Gerar hash da senha
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash da senha
    """
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verificar senha contra hash
    
    Args:
        password: Senha em texto plano
        password_hash: Hash da senha
        
    Returns:
        True se senha confere
    """
    return check_password_hash(password_hash, password)


def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    Truncar texto
    
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


def slugify(text: str) -> str:
    """
    Converter texto para slug
    
    Args:
        text: Texto a ser convertido
        
    Returns:
        Slug
    """
    if not text:
        return ""
    
    # Converter para minúsculas
    text = text.lower()
    
    # Remover acentos
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Manter apenas letras, números e espaços
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Substituir espaços por hífens
    text = re.sub(r'\s+', '-', text)
    
    # Remover hífens duplicados
    text = re.sub(r'-+', '-', text)
    
    # Remover hífens no início e fim
    return text.strip('-')


def calculate_age(birth_date: date) -> int:
    """
    Calcular idade
    
    Args:
        birth_date: Data de nascimento
        
    Returns:
        Idade em anos
    """
    try:
        today = date.today()
        age = today.year - birth_date.year
        
        # Verificar se ainda não fez aniversário este ano
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    except (AttributeError, TypeError):
        return 0


def percentage(part: Union[int, float], total: Union[int, float], decimals: int = 1) -> float:
    """
    Calcular porcentagem
    
    Args:
        part: Parte
        total: Total
        decimals: Casas decimais
        
    Returns:
        Porcentagem
    """
    try:
        if total == 0:
            return 0.0
        
        result = (part / total) * 100
        return round(result, decimals)
    
    except (ZeroDivisionError, TypeError):
        return 0.0


def clean_string(text: str) -> str:
    """
    Limpar string removendo espaços extras e caracteres especiais
    
    Args:
        text: Texto a ser limpo
        
    Returns:
        Texto limpo
    """
    if not text:
        return ""
    
    # Remover espaços no início e fim
    text = text.strip()
    
    # Remover espaços extras
    text = re.sub(r'\s+', ' ', text)
    
    return text


def format_file_size(size_bytes: int) -> str:
    """
    Formatar tamanho de arquivo
    
    Args:
        size_bytes: Tamanho em bytes
        
    Returns:
        Tamanho formatado (ex: "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def mask_cpf(cpf: str) -> str:
    """
    Mascarar CPF para exibição (ex: ***456.789-**)
    
    Args:
        cpf: CPF a ser mascarado
        
    Returns:
        CPF mascarado
    """
    if not cpf:
        return ""
    
    cpf_clean = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf_clean) == 11:
        return f"***{cpf_clean[3:6]}.{cpf_clean[6:9]}-**"
    
    return cpf


def mask_phone(phone: str) -> str:
    """
    Mascarar telefone para exibição
    
    Args:
        phone: Telefone a ser mascarado
        
    Returns:
        Telefone mascarado
    """
    if not phone:
        return ""
    
    phone_clean = re.sub(r'[^0-9]', '', phone)
    
    if len(phone_clean) == 11:
        return f"({phone_clean[:2]}) ****-{phone_clean[-4:]}"
    elif len(phone_clean) == 10:
        return f"({phone_clean[:2]}) ***-{phone_clean[-4:]}"
    
    return phone


def get_client_ip() -> str:
    """
    Obter IP do cliente
    
    Returns:
        IP do cliente
    """
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']


def build_filters_from_request(allowed_filters: List[str]) -> Dict[str, Any]:
    """
    Construir dicionário de filtros a partir do request
    
    Args:
        allowed_filters: Lista de filtros permitidos
        
    Returns:
        Dicionário com filtros
    """
    filters = {}
    
    for filter_name in allowed_filters:
        value = request.args.get(filter_name)
        if value and value.strip():
            filters[filter_name] = value.strip()
    
    return filters


def generate_random_string(length: int = 32) -> str:
    """
    Gerar string aleatória
    
    Args:
        length: Comprimento da string
        
    Returns:
        String aleatória
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def is_ajax_request() -> bool:
    """
    Verificar se é uma requisição AJAX
    
    Returns:
        True se é AJAX
    """
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def get_error_message(exception: Exception, default: str = "Erro interno do sistema") -> str:
    """
    Obter mensagem de erro amigável
    
    Args:
        exception: Exceção
        default: Mensagem padrão
        
    Returns:
        Mensagem de erro
    """
    # Mapear tipos de erro para mensagens amigáveis
    error_messages = {
        'IntegrityError': 'Violação de integridade dos dados',
        'OperationalError': 'Erro na operação do banco de dados',
        'DataError': 'Dados inválidos',
        'ProgrammingError': 'Erro de programação',
        'InternalError': 'Erro interno',
        'NotSupportedError': 'Operação não suportada',
        'DatabaseError': 'Erro no banco de dados'
    }
    
    exception_name = type(exception).__name__
    return error_messages.get(exception_name, default)