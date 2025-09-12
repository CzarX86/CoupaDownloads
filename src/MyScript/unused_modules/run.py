#!/usr/bin/env python3
"""
MyScript Runner - Executa o sistema MyScript
"""

import sys
import os
from pathlib import Path

# Configurar o ambiente
def setup_environment():
    """Configura o ambiente para o subprojeto MyScript."""
    # Adicionar o diretório atual ao sys.path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Verificar se estamos no diretório correto
    if not (current_dir / "gui_main.py").exists():
        print("❌ Arquivo gui_main.py não encontrado!")
        print(f"   Diretório atual: {current_dir}")
        return False
    
    return True

def main():
    """Função principal."""
    print("🚀 MyScript - Sistema Avançado de Automação CoupaDownloads")
    print("=" * 60)
    
    if not setup_environment():
        return 1
    
    try:
        # Importar e executar a GUI
        import gui_main
        gui_main.main()
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        print("   Verifique se todas as dependências estão instaladas")
        return 1
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
