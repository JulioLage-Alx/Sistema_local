import os
import logging
from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import config

# Inicialização das extensões
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name=None):
    """Factory para criar a aplicação Flask"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar configuração específica
    config[config_name].init_app(app)
    
    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configurar logging
    configure_logging(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar handlers de erro
    register_error_handlers(app)
    
    # Registrar processadores de contexto
    register_context_processors(app)
    
    # Registrar hooks de request
    register_request_hooks(app)
    
    # Criar diretórios necessários
    create_directories(app)
    
    return app


def configure_logging(app):
    """Configurar sistema de logging"""
    
    if app.config['DEBUG']:
        # Em desenvolvimento, log no console
        logging.basicConfig(
            level=getattr(logging, app.config['LOG_LEVEL']),
            format='%(asctime)s %(levelname)s: %(message)s'
        )
    else:
        # Em produção, configuração é feita no config.py
        pass


def register_blueprints(app):
    """Registrar todos os blueprints da aplicação"""
    
    # Blueprint principal (dashboard)
    from .views.main import main_bp
    app.register_blueprint(main_bp)
    
    # Blueprint de autenticação
    from .views.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Blueprint de clientes
    from .views.clientes import clientes_bp
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    
    # Blueprint de vendas
    from .views.vendas import vendas_bp
    app.register_blueprint(vendas_bp, url_prefix='/vendas')
    
    # Blueprint de pagamentos
    from .views.pagamentos import pagamentos_bp
    app.register_blueprint(pagamentos_bp, url_prefix='/pagamentos')
    
    # Blueprint de relatórios
    from .views.relatorios import relatorios_bp
    app.register_blueprint(relatorios_bp, url_prefix='/relatorios')
    
    # Blueprint da API (AJAX)
    from .views.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')


def register_error_handlers(app):
    """Registrar handlers de erro personalizados"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Erro interno: {error}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403


def register_context_processors(app):
    """Registrar processadores de contexto global"""
    
    @app.context_processor
    def inject_config():
        """Injetar configurações no contexto dos templates"""
        return {
            'config': app.config,
            'app_name': 'Sistema Crediário Açougue',
            'app_version': '1.0.0'
        }
    
    @app.context_processor
    def inject_user():
        """Injetar informações do usuário logado"""
        return {
            'current_user': session.get('user_logged', False),
            'user_name': session.get('user_name', 'Usuário')
        }


def register_request_hooks(app):
    """Registrar hooks de request"""
    
    @app.before_request
    def before_request():
        """Executado antes de cada request"""
        
        # Log de requisições em desenvolvimento
        if app.config['DEBUG']:
            app.logger.debug(f'{request.method} {request.url}')
        
        # Verificar se rotas protegidas precisam de autenticação
        protected_endpoints = [
            'clientes', 'vendas', 'pagamentos', 
            'relatorios', 'main.dashboard'
        ]
        
        if (request.endpoint and 
            any(endpoint in request.endpoint for endpoint in protected_endpoints) and
            not session.get('user_logged', False) and
            request.endpoint != 'auth.login'):
            
            from flask import redirect, url_for, flash
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
    
    @app.after_request
    def after_request(response):
        """Executado após cada request"""
        
        # Headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response


def create_directories(app):
    """Criar diretórios necessários para a aplicação"""
    
    directories = [
        'logs',
        'backups',
        'exports',
        'uploads'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Importar modelos para que sejam reconhecidos pelo Flask-Migrate
from .models import cliente, venda, item_venda, pagamento, pagamento_multiplo