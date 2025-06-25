import os
from datetime import timedelta


class Config:
    """Configuração base da aplicação"""
    
    # Configurações Flask
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configurações de Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Configurações WTF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Configurações de Banco de Dados
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'acougue_db'
    
    # URI de conexão SQLAlchemy
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Configurações de Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configurações de Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
    
    # Configurações da Impressora ESC/POS
    IMPRESSORA_TIPO = os.environ.get('IMPRESSORA_TIPO') or 'usb'  # usb, network, serial
    IMPRESSORA_VENDOR_ID = os.environ.get('IMPRESSORA_VENDOR_ID') or '0x0471'
    IMPRESSORA_PRODUCT_ID = os.environ.get('IMPRESSORA_PRODUCT_ID') or '0x0055'
    IMPRESSORA_INTERFACE = int(os.environ.get('IMPRESSORA_INTERFACE') or 0)
    IMPRESSORA_ENDPOINT = int(os.environ.get('IMPRESSORA_ENDPOINT') or 0x03)
    
    # Configurações de Negócio
    DIAS_VENCIMENTO_PADRAO = 30
    LIMITE_CREDITO_PADRAO = 500.00
    DIAS_INADIMPLENCIA = 30
    
    # Configurações de Backup
    BACKUP_ENABLED = True
    BACKUP_SCHEDULE = '02:00'  # Horário diário
    BACKUP_RETENTION_DAYS = 30
    BACKUP_PATH = 'backups/'
    
    @staticmethod
    def init_app(app):
        """Inicialização específica da configuração"""
        pass


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # Facilita testes em desenvolvimento
    
    # Banco de desenvolvimento
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'acougue_dev'
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}@"
        f"{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    
    # Logging mais verboso
    LOG_LEVEL = 'DEBUG'
    
    # Configurações de desenvolvimento
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Configurar Flask-DebugToolbar em desenvolvimento
        from flask_debugtoolbar import DebugToolbarExtension
        toolbar = DebugToolbarExtension()
        toolbar.init_app(app)


class ProductionConfig(Config):
    """Configuração para produção"""
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Logging para produção
    LOG_LEVEL = 'WARNING'
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Configurar logging para produção
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            # Criar diretório de logs se não existir
            os.makedirs('logs', exist_ok=True)
            
            # Configurar handler de arquivo
            file_handler = RotatingFileHandler(
                Config.LOG_FILE,
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('Sistema Açougue iniciado')


class TestingConfig(Config):
    """Configuração para testes"""
    
    TESTING = True
    WTF_CSRF_ENABLED = False
    
    # Banco de testes em memória
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Desabilitar impressora em testes
    IMPRESSORA_TIPO = 'dummy'


# Mapeamento de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}