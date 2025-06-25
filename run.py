#!/usr/bin/env python
"""
Sistema de Crediário para Açougue
Arquivo principal de execução da aplicação
"""

import os
import sys
from flask.cli import FlaskGroup
from app import create_app, db


def create_cli_app():
    """Criar aplicação para CLI"""
    return create_app()


# Configurar Flask CLI
cli = FlaskGroup(create_app=create_cli_app)


@cli.command("init-db")
def init_db():
    """Inicializar banco de dados com tabelas e dados iniciais"""
    print("Criando tabelas do banco de dados...")
    db.create_all()
    
    # Executar seeders se existirem
    try:
        from scripts.seeders import run_seeders
        print("Inserindo dados iniciais...")
        run_seeders()
        print("Banco de dados inicializado com sucesso!")
    except ImportError:
        print("Tabelas criadas. Seeders não encontrados.")
    except Exception as e:
        print(f"Erro ao inserir dados iniciais: {e}")


@cli.command("reset-db")
def reset_db():
    """Resetar banco de dados (CUIDADO: Remove todos os dados!)"""
    if input("ATENÇÃO: Isso irá apagar todos os dados! Digite 'CONFIRMAR' para continuar: ") == "CONFIRMAR":
        print("Removendo tabelas existentes...")
        db.drop_all()
        print("Criando novas tabelas...")
        db.create_all()
        
        # Executar seeders
        try:
            from scripts.seeders import run_seeders
            print("Inserindo dados iniciais...")
            run_seeders()
            print("Banco de dados resetado com sucesso!")
        except ImportError:
            print("Banco resetado. Seeders não encontrados.")
        except Exception as e:
            print(f"Erro ao inserir dados iniciais: {e}")
    else:
        print("Operação cancelada.")


@cli.command("backup")
def backup_db():
    """Criar backup do banco de dados"""
    try:
        from scripts.backup import create_backup
        backup_file = create_backup()
        print(f"Backup criado com sucesso: {backup_file}")
    except ImportError:
        print("Script de backup não encontrado.")
    except Exception as e:
        print(f"Erro ao criar backup: {e}")


@cli.command("test-printer")
def test_printer():
    """Testar conexão com a impressora"""
    try:
        from app.services.impressora_service import ImpressoraService
        service = ImpressoraService()
        service.testar_conexao()
        print("Teste de impressora executado. Verifique a saída na impressora.")
    except Exception as e:
        print(f"Erro no teste da impressora: {e}")


@cli.command("create-user")
def create_user():
    """Criar usuário para acesso ao sistema"""
    username = input("Nome de usuário: ")
    password = input("Senha: ")
    
    if len(password) < 6:
        print("Senha deve ter pelo menos 6 caracteres.")
        return
    
    # Como é sistema local, vamos salvar em arquivo ou variável de ambiente
    print(f"Usuário '{username}' criado com sucesso!")
    print("Configure as variáveis de ambiente:")
    print(f"SYSTEM_USERNAME={username}")
    print(f"SYSTEM_PASSWORD={password}")


def main():
    """Função principal"""
    
    # Verificar se o diretório de logs existe
    os.makedirs('logs', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    
    # Se executado diretamente, iniciar o servidor
    if len(sys.argv) == 1:
        print("Sistema de Crediário para Açougue")
        print("=" * 40)
        print("Iniciando servidor de desenvolvimento...")
        print("Acesse: http://localhost:5000")
        print("Para parar o servidor: Ctrl+C")
        print("=" * 40)
        
        app = create_app()
        
        # Configurações do servidor de desenvolvimento
        host = os.environ.get('FLASK_HOST', '127.0.0.1')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
    else:
        # Executar comandos CLI
        cli()


if __name__ == '__main__':
    main()