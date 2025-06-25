"""
Blueprint de Autenticação
Sistema simples de login para uso local
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.helpers import flash_error, flash_success, flash_warning


auth_bp = Blueprint('auth', __name__)


def get_system_credentials():
    """Obter credenciais do sistema das variáveis de ambiente"""
    username = os.environ.get('SYSTEM_USERNAME', 'admin')
    password = os.environ.get('SYSTEM_PASSWORD', 'admin123')
    return username, password


def verify_credentials(username, password):
    """Verificar credenciais do usuário"""
    system_username, system_password = get_system_credentials()
    
    # Comparação simples para sistema local
    return username == system_username and password == system_password


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    
    # Se já está logado, redirecionar para dashboard
    if session.get('user_logged'):
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        # Validar campos
        if not username or not password:
            flash_error('Usuário e senha são obrigatórios.')
            return render_template('login.html')
        
        # Verificar credenciais
        if verify_credentials(username, password):
            # Login realizado com sucesso
            session['user_logged'] = True
            session['user_name'] = username
            session['login_time'] = str(datetime.utcnow())
            
            # Configurar sessão permanente se solicitado
            if remember:
                session.permanent = True
            
            flash_success(f'Bem-vindo, {username}!')
            
            # Redirecionar para página solicitada ou dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash_error('Usuário ou senha incorretos.')
            
            # Log da tentativa de login inválida
            from app import db
            import logging
            logging.warning(f'Tentativa de login inválida: {username} - IP: {request.remote_addr}')
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout do sistema"""
    
    if session.get('user_logged'):
        username = session.get('user_name', 'Usuário')
        
        # Limpar sessão
        session.clear()
        
        flash_success(f'Até logo, {username}!')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Alterar senha do sistema"""
    
    # Verificar se está logado
    if not session.get('user_logged'):
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validar campos
        if not all([current_password, new_password, confirm_password]):
            flash_error('Todos os campos são obrigatórios.')
            return render_template('auth/change_password.html')
        
        # Verificar senha atual
        username = session.get('user_name')
        if not verify_credentials(username, current_password):
            flash_error('Senha atual incorreta.')
            return render_template('auth/change_password.html')
        
        # Validar nova senha
        if len(new_password) < 6:
            flash_error('Nova senha deve ter pelo menos 6 caracteres.')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash_error('Confirmação de senha não confere.')
            return render_template('auth/change_password.html')
        
        # Avisar que a alteração deve ser feita nas variáveis de ambiente
        flash_warning(
            'Para alterar a senha permanentemente, atualize a variável '
            'SYSTEM_PASSWORD no arquivo .env e reinicie o sistema.'
        )
        
        flash_success('Senha temporária alterada! Não se esqueça de atualizar o arquivo .env.')
        
        # Temporariamente, poderíamos armazenar em arquivo ou banco
        # Por simplicidade, apenas mostrar a mensagem
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/change_password.html')


@auth_bp.route('/profile')
def profile():
    """Perfil do usuário"""
    
    # Verificar se está logado
    if not session.get('user_logged'):
        return redirect(url_for('auth.login'))
    
    from datetime import datetime
    
    profile_data = {
        'username': session.get('user_name'),
        'login_time': session.get('login_time'),
        'session_duration': None
    }
    
    # Calcular tempo de sessão
    if profile_data['login_time']:
        try:
            login_dt = datetime.fromisoformat(profile_data['login_time'])
            duration = datetime.utcnow() - login_dt
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            profile_data['session_duration'] = f"{hours}h {minutes}m"
        except:
            pass
    
    return render_template('auth/profile.html', profile=profile_data)


# Funções auxiliares para uso em templates e outras partes da aplicação

def login_required(f):
    """Decorator para rotas que exigem autenticação"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged'):
            flash_warning('Você precisa estar logado para acessar esta página.')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Obter informações do usuário atual"""
    if session.get('user_logged'):
        return {
            'username': session.get('user_name'),
            'is_authenticated': True,
            'login_time': session.get('login_time')
        }
    return {
        'username': None,
        'is_authenticated': False,
        'login_time': None
    }


def is_logged_in():
    """Verificar se o usuário está logado"""
    return session.get('user_logged', False)


# Context processor para disponibilizar funções nos templates
@auth_bp.app_context_processor
def inject_auth_functions():
    """Injetar funções de autenticação nos templates"""
    return {
        'current_user': get_current_user(),
        'is_logged_in': is_logged_in()
    }


# Imports necessários
from datetime import datetime