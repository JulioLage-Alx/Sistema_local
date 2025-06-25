"""
Blueprint de Autenticação - Login e logout do sistema
"""

import functools
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, current_app, g, jsonify
)
from app.utils.helpers import flash_success, flash_error, flash_warning
from app.utils.decorators import log_action


auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """
    Decorator para verificar se usuário está logado
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged', False):
            # Se é requisição AJAX, retornar JSON
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'error': 'Sessão expirada. Faça login novamente.',
                    'redirect': url_for('auth.login')
                }), 401
            
            # Para requisições normais, redirecionar para login
            flash_warning('Você precisa estar logado para acessar esta página.')
            next_url = request.url if request.method == 'GET' else None
            return redirect(url_for('auth.login', next=next_url))
        
        # Verificar se sessão não expirou
        last_activity = session.get('last_activity')
        if last_activity:
            last_activity = datetime.fromisoformat(last_activity)
            session_timeout = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=8))
            
            if datetime.utcnow() - last_activity > session_timeout:
                session.clear()
                flash_warning('Sua sessão expirou. Faça login novamente.')
                return redirect(url_for('auth.login'))
        
        # Atualizar última atividade
        session['last_activity'] = datetime.utcnow().isoformat()
        
        return f(*args, **kwargs)
    
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
@log_action('login', 'Tentativa de login')
def login():
    """Página e processamento de login"""
    
    # Se já está logado, redirecionar para dashboard
    if session.get('user_logged', False):
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember_me') == 'on'
        next_url = request.form.get('next', '')
        
        # Validações básicas
        if not username:
            flash_error('Nome de usuário é obrigatório.')
            return render_template('login.html', next=next_url)
        
        if not password:
            flash_error('Senha é obrigatória.')
            return render_template('login.html', next=next_url, username=username)
        
        # Verificar credenciais
        if verificar_credenciais(username, password):
            # Login bem-sucedido
            session.permanent = remember_me
            session['user_logged'] = True
            session['user_name'] = username
            session['login_time'] = datetime.utcnow().isoformat()
            session['last_activity'] = datetime.utcnow().isoformat()
            session['login_ip'] = request.remote_addr
            
            # Log de sucesso
            current_app.logger.info(f'Login bem-sucedido: {username} - IP: {request.remote_addr}')
            flash_success(f'Bem-vindo(a), {username}!')
            
            # Redirecionar para página solicitada ou dashboard
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            else:
                return redirect(url_for('main.dashboard'))
        else:
            # Login falhado
            current_app.logger.warning(f'Falha no login: {username} - IP: {request.remote_addr}')
            flash_error('Nome de usuário ou senha incorretos.')
            
            # Implementar delay de segurança (simples)
            import time
            time.sleep(1)
    
    # GET request ou falha no login
    next_url = request.args.get('next', '')
    return render_template('login.html', next=next_url)


@auth_bp.route('/logout')
@login_required
@log_action('logout', 'Logout do sistema')
def logout():
    """Logout do usuário"""
    
    username = session.get('user_name', 'Usuário')
    
    # Limpar sessão
    session.clear()
    
    # Log de logout
    current_app.logger.info(f'Logout: {username} - IP: {request.remote_addr}')
    flash_success('Você saiu do sistema com sucesso.')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/check-session')
@login_required
def check_session():
    """API para verificar status da sessão (AJAX)"""
    
    return jsonify({
        'success': True,
        'logged_in': True,
        'user_name': session.get('user_name'),
        'login_time': session.get('login_time'),
        'last_activity': session.get('last_activity')
    })


@auth_bp.route('/extend-session', methods=['POST'])
@login_required
def extend_session():
    """API para estender sessão (AJAX)"""
    
    # Atualizar última atividade
    session['last_activity'] = datetime.utcnow().isoformat()
    
    return jsonify({
        'success': True,
        'message': 'Sessão estendida com sucesso.',
        'last_activity': session['last_activity']
    })


def verificar_credenciais(username: str, password: str) -> bool:
    """
    Verificar credenciais do usuário
    
    Args:
        username: Nome de usuário
        password: Senha
        
    Returns:
        True se credenciais são válidas
    """
    # Como é sistema local, usar credenciais fixas ou de arquivo/env
    system_username = current_app.config.get('SYSTEM_USERNAME', 'admin')
    system_password = current_app.config.get('SYSTEM_PASSWORD', 'admin123')
    
    # Verificação simples para sistema local
    return username == system_username and password == system_password


def is_safe_url(target: str) -> bool:
    """
    Verificar se URL de redirecionamento é segura
    
    Args:
        target: URL de destino
        
    Returns:
        True se URL é segura
    """
    from urllib.parse import urlparse, urljoin
    
    if not target:
        return False
    
    # Parse da URL
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    # Verificar se é do mesmo host
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.before_app_request
def load_logged_in_user():
    """Carregar usuário logado antes de cada request"""
    
    # Adicionar informações do usuário ao contexto global
    g.user_logged = session.get('user_logged', False)
    g.user_name = session.get('user_name', '')
    g.login_time = session.get('login_time')
    g.last_activity = session.get('last_activity')


@auth_bp.app_context_processor
def inject_auth_data():
    """Injetar dados de autenticação nos templates"""
    
    return {
        'user_logged': session.get('user_logged', False),
        'user_name': session.get('user_name', ''),
        'login_time': session.get('login_time'),
        'last_activity': session.get('last_activity')
    }


# Função para criar usuário administrativo (usado em CLI)
def create_admin_user(username: str, password: str) -> bool:
    """
    Criar usuário administrativo
    
    Args:
        username: Nome de usuário
        password: Senha
        
    Returns:
        True se usuário foi criado com sucesso
    """
    try:
        # Em um sistema mais complexo, salvaria no banco de dados
        # Para sistema local, apenas validar e salvar em variáveis de ambiente
        
        if len(password) < 6:
            return False
        
        # Aqui você poderia salvar em arquivo de configuração ou banco
        # Por ora, apenas retornamos True indicando que seria criado
        return True
        
    except Exception as e:
        current_app.logger.error(f'Erro ao criar usuário admin: {str(e)}')
        return False


# Middleware de segurança
@auth_bp.after_app_request
def security_headers(response):
    """Adicionar headers de segurança"""
    
    # Headers de segurança básicos
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # CSP básico
    if not current_app.debug:
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
    
    return response


# Rate limiting simples (em memória)
login_attempts = {}

@auth_bp.before_request
def rate_limit_login():
    """Rate limiting para tentativas de login"""
    
    if request.endpoint == 'auth.login' and request.method == 'POST':
        client_ip = request.remote_addr
        now = datetime.utcnow()
        
        # Limpar tentativas antigas (mais de 1 hora)
        if client_ip in login_attempts:
            login_attempts[client_ip] = [
                attempt for attempt in login_attempts[client_ip]
                if now - attempt < timedelta(hours=1)
            ]
        
        # Verificar limite (5 tentativas por hora)
        if client_ip in login_attempts and len(login_attempts[client_ip]) >= 5:
            flash_error('Muitas tentativas de login. Tente novamente em 1 hora.')
            return render_template('login.html'), 429
        
        # Registrar tentativa
        if client_ip not in login_attempts:
            login_attempts[client_ip] = []
        login_attempts[client_ip].append(now)


# Context processor para dados de sessão
@auth_bp.app_context_processor
def inject_session_data():
    """Injetar dados de sessão nos templates"""
    
    session_data = {}
    
    if session.get('user_logged'):
        login_time = session.get('login_time')
        if login_time:
            login_datetime = datetime.fromisoformat(login_time)
            session_data['session_duration'] = str(datetime.utcnow() - login_datetime).split('.')[0]
    
    return {'session_data': session_data}


# Função para logout automático em caso de inatividade
def auto_logout_check():
    """Verificar se deve fazer logout automático por inatividade"""
    
    if not session.get('user_logged'):
        return False
    
    last_activity = session.get('last_activity')
    if not last_activity:
        return False
    
    last_activity_time = datetime.fromisoformat(last_activity)
    session_timeout = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=8))
    
    if datetime.utcnow() - last_activity_time > session_timeout:
        session.clear()
        return True
    
    return False


# Template filter para formatação de tempo
@auth_bp.app_template_filter('time_ago')
def time_ago_filter(datetime_str):
    """Filter para mostrar tempo decorrido"""
    
    if not datetime_str:
        return ''
    
    try:
        dt = datetime.fromisoformat(datetime_str)
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} dia(s) atrás"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hora(s) atrás"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minuto(s) atrás"
        else:
            return "Agora"
    
    except (ValueError, TypeError):
        return ''