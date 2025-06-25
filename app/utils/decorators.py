"""
Decoradores customizados para a aplicação
"""

import functools
import time
from datetime import datetime
from typing import Callable, Any, Dict, Optional
from flask import request, jsonify, session, current_app, g
from flask import redirect, url_for, request
from werkzeug.exceptions import RequestEntityTooLarge


def admin_required(f: Callable) -> Callable:
    """
    Decorator para verificar se usuário é administrador
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Como é sistema local, verificar se usuário está logado
        # Em futuras versões pode incluir níveis de acesso
        if not session.get('user_logged', False):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Acesso negado. Login requerido.'
                }), 403
            else:
                from flask import redirect, url_for, flash
                flash('Acesso negado. Faça login como administrador.', 'danger')
                return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def log_action(action: str, description: str = None):
    """
    Decorator para registrar ações do usuário
    
    Args:
        action: Tipo de ação (create, update, delete, etc.)
        description: Descrição adicional da ação
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Executar função original
            try:
                result = f(*args, **kwargs)
                
                # Calcular tempo de execução
                execution_time = time.time() - start_time
                
                # Log da ação
                log_data = {
                    'action': action,
                    'description': description or f"Execução de {f.__name__}",
                    'user': session.get('user_name', 'Sistema'),
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'execution_time': round(execution_time, 3),
                    'timestamp': datetime.utcnow(),
                    'success': True
                }
                
                current_app.logger.info(f"[{action.upper()}] {log_data['description']} - "
                                      f"User: {log_data['user']} - "
                                      f"Time: {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                # Log do erro
                execution_time = time.time() - start_time
                
                log_data = {
                    'action': action,
                    'description': description or f"Erro em {f.__name__}",
                    'user': session.get('user_name', 'Sistema'),
                    'ip_address': request.remote_addr,
                    'error': str(e),
                    'execution_time': round(execution_time, 3),
                    'timestamp': datetime.utcnow(),
                    'success': False
                }
                
                current_app.logger.error(f"[{action.upper()}] ERRO: {log_data['description']} - "
                                       f"User: {log_data['user']} - "
                                       f"Error: {str(e)}")
                
                raise
        
        return decorated_function
    return decorator


def validate_json(required_fields: list = None, optional_fields: list = None):
    """
    Decorator para validar JSON em requisições
    
    Args:
        required_fields: Campos obrigatórios
        optional_fields: Campos opcionais
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se é JSON
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type deve ser application/json'
                }), 400
            
            try:
                data = request.get_json()
                
                if data is None:
                    return jsonify({
                        'success': False,
                        'error': 'JSON inválido'
                    }), 400
                
                # Validar campos obrigatórios
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in data or data[field] is None or data[field] == '':
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return jsonify({
                            'success': False,
                            'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
                        }), 400
                
                # Validar campos permitidos
                if required_fields or optional_fields:
                    allowed_fields = set(required_fields or []) | set(optional_fields or [])
                    unexpected_fields = set(data.keys()) - allowed_fields
                    
                    if unexpected_fields:
                        return jsonify({
                            'success': False,
                            'error': f'Campos não permitidos: {", ".join(unexpected_fields)}'
                        }), 400
                
                # Adicionar dados validados ao contexto
                g.validated_json = data
                
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Erro na validação: {str(e)}'
                }), 400
        
        return decorated_function
    return decorator


def cache_response(timeout: int = 300):
    """
    Decorator para cache de respostas
    
    Args:
        timeout: Tempo de cache em segundos
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Gerar chave de cache baseada na função e argumentos
            cache_key = f"{f.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Verificar se existe cache
            if hasattr(g, 'cache_store'):
                cached_result = g.cache_store.get(cache_key)
                if cached_result:
                    current_app.logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
            
            # Executar função e armazenar resultado
            result = f(*args, **kwargs)
            
            # Armazenar no cache (implementação simples em memória)
            if not hasattr(g, 'cache_store'):
                g.cache_store = {}
            
            g.cache_store[cache_key] = result
            current_app.logger.debug(f"Cache set for {cache_key}")
            
            return result
        
        return decorated_function
    return decorator


def limit_content_length(max_length: int):
    """
    Decorator para limitar tamanho do conteúdo da requisição
    
    Args:
        max_length: Tamanho máximo em bytes
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            
            if content_length and content_length > max_length:
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': f'Conteúdo muito grande. Máximo: {max_length} bytes'
                    }), 413
                else:
                    raise RequestEntityTooLarge()
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit(calls: int = 100, period: int = 3600):
    """
    Decorator para limitação de taxa de requisições
    
    Args:
        calls: Número máximo de chamadas
        period: Período em segundos
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Identificar cliente (IP + user)
            client_id = f"{request.remote_addr}_{session.get('user_name', 'anonymous')}"
            
            # Chave para armazenar contadores
            rate_key = f"rate_limit_{f.__name__}_{client_id}"
            
            # Verificar rate limit (implementação simples)
            if not hasattr(g, 'rate_limit_store'):
                g.rate_limit_store = {}
            
            now = time.time()
            
            if rate_key in g.rate_limit_store:
                timestamps = g.rate_limit_store[rate_key]
                # Remover timestamps antigos
                timestamps = [ts for ts in timestamps if now - ts < period]
                
                if len(timestamps) >= calls:
                    if request.is_json:
                        return jsonify({
                            'success': False,
                            'error': 'Limite de requisições excedido. Tente novamente mais tarde.'
                        }), 429
                    else:
                        from flask import abort
                        abort(429)
                
                timestamps.append(now)
                g.rate_limit_store[rate_key] = timestamps
            else:
                g.rate_limit_store[rate_key] = [now]
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def measure_performance(log_slow_queries: bool = True, slow_threshold: float = 1.0):
    """
    Decorator para medir performance de funções
    
    Args:
        log_slow_queries: Se deve logar queries lentas
        slow_threshold: Limite em segundos para considerar lenta
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
                execution_time = time.time() - start_time
                
                # Log de performance
                if execution_time > slow_threshold and log_slow_queries:
                    current_app.logger.warning(
                        f"SLOW QUERY: {f.__name__} took {execution_time:.3f}s "
                        f"(threshold: {slow_threshold}s)"
                    )
                else:
                    current_app.logger.debug(
                        f"PERFORMANCE: {f.__name__} took {execution_time:.3f}s"
                    )
                
                # Adicionar tempo de execução ao contexto se necessário
                if hasattr(g, 'performance_data'):
                    g.performance_data[f.__name__] = execution_time
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                current_app.logger.error(
                    f"ERROR in {f.__name__} after {execution_time:.3f}s: {str(e)}"
                )
                raise
        
        return decorated_function
    return decorator


def require_fields(*fields):
    """
    Decorator para validar campos obrigatórios em formulários
    
    Args:
        *fields: Campos obrigatórios
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            missing_fields = []
            
            for field in fields:
                value = request.form.get(field) or request.args.get(field)
                if not value or not value.strip():
                    missing_fields.append(field)
            
            if missing_fields:
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': f'Campos obrigatórios: {", ".join(missing_fields)}'
                    }), 400
                else:
                    from flask import flash, redirect, url_for
                    flash(f'Campos obrigatórios: {", ".join(missing_fields)}', 'danger')
                    return redirect(request.referrer or url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def handle_db_errors(f: Callable) -> Callable:
    """
    Decorator para tratar erros de banco de dados
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
            from app import db
            from app.utils.helpers import get_error_message, flash_error
            
            # Rollback da transação
            db.session.rollback()
            
            # Obter mensagem amigável
            error_message = get_error_message(e)
            
            # Log do erro
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            
            # Resposta baseada no tipo de requisição
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': error_message
                }), 500
            else:
                flash_error(error_message)
                return redirect(request.referrer or url_for('main.dashboard'))
    
    return decorated_function


def cors_enabled(origins: str = "*", methods: str = "GET,POST,PUT,DELETE"):
    """
    Decorator para habilitar CORS
    
    Args:
        origins: Origens permitidas
        methods: Métodos permitidos
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # Adicionar headers CORS
            if hasattr(response, 'headers'):
                response.headers['Access-Control-Allow-Origin'] = origins
                response.headers['Access-Control-Allow-Methods'] = methods
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            
            return response
        
        return decorated_function
    return decorator


def json_required(f: Callable) -> Callable:
    """
    Decorator para exigir requisições JSON
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type deve ser application/json'
            }), 400
        
        return f(*args, **kwargs)
    
    return decorated_function


def development_only(f: Callable) -> Callable:
    """
    Decorator para funções que só devem executar em desenvolvimento
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.debug:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Funcionalidade disponível apenas em desenvolvimento'
                }), 403
            else:
                from flask import abort
                abort(403)
        
        return f(*args, **kwargs)
    
    return decorated_function