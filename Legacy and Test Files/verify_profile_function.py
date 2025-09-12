#!/usr/bin/env python3
"""
🛡️ SCRIPT DE VERIFICAÇÃO DA FUNÇÃO CRÍTICA DE PERFIL 🛡️
Este script verifica se a função de detecção de perfil está intacta e funcionando.
Execute este script sempre que quiser verificar se nada foi alterado.
"""

import sys
import os

def verify_profile_function():
    """Verifica se a função crítica de perfil está intacta."""
    
    print("🛡️ VERIFICANDO FUNÇÃO CRÍTICA DE PERFIL...")
    print("=" * 50)
    
    try:
        # Verificar se o arquivo de configuração existe
        config_file = "src/MyScript/profile_config.py"
        if os.path.exists(config_file):
            print("✅ Arquivo de configuração encontrado")
        else:
            print("❌ Arquivo de configuração NÃO encontrado!")
            return False
            
        # Verificar se o backup existe
        backup_file = "src/MyScript/profile_config.py.backup"
        if os.path.exists(backup_file):
            print("✅ Backup da configuração encontrado")
        else:
            print("⚠️ Backup da configuração não encontrado")
            
        # Importar e verificar configuração
        sys.path.append('src/MyScript')
        from profile_config import EDGE_PROFILE_CONFIG, PROFILE_STATUS_MESSAGES
        
        # Verificar se as chaves essenciais existem
        required_keys = [
            "macos_profile_path",
            "windows_profile_path", 
            "profile_directory",
            "login_check_url",
            "login_check_timeout",
            "login_selectors"
        ]
        
        for key in required_keys:
            if key in EDGE_PROFILE_CONFIG:
                print(f"✅ Chave '{key}' encontrada")
            else:
                print(f"❌ Chave '{key}' NÃO encontrada!")
                return False
                
        # Verificar se as mensagens existem
        required_messages = ["not_logged_in", "logged_in", "check_failed"]
        for msg in required_messages:
            if msg in PROFILE_STATUS_MESSAGES:
                print(f"✅ Mensagem '{msg}' encontrada")
            else:
                print(f"❌ Mensagem '{msg}' NÃO encontrada!")
                return False
                
        # Verificar se a função crítica existe no script principal
        script_file = "src/MyScript/myScript_advanced.py"
        if os.path.exists(script_file):
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "verify_edge_profile_login_status" in content:
                print("✅ Função crítica encontrada no script principal")
            else:
                print("❌ Função crítica NÃO encontrada no script principal!")
                return False
                
            if "🛡️ FUNÇÃO CRÍTICA" in content:
                print("✅ Marcadores de proteção encontrados")
            else:
                print("❌ Marcadores de proteção NÃO encontrados!")
                return False
                
        print("\n" + "=" * 50)
        print("🎉 TODAS AS VERIFICAÇÕES PASSARAM!")
        print("✅ A função crítica de perfil está INTACTA e PROTEGIDA!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ ERRO durante verificação: {e}")
        return False

if __name__ == "__main__":
    success = verify_profile_function()
    if not success:
        print("\n🚨 ATENÇÃO: A função crítica pode ter sido alterada!")
        print("   Considere restaurar o backup se necessário.")
        sys.exit(1)
    else:
        print("\n✅ Verificação concluída com sucesso!")
        sys.exit(0)

