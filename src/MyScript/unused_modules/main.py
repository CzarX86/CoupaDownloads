#!/usr/bin/env python3
"""
MyScript - Sistema Avançado de Automação CoupaDownloads
Script de entrada principal para o subprojeto independente.
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório atual ao sys.path para importações locais
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def main():
    """Função principal do MyScript."""
    print("🚀 MyScript - Sistema Avançado de Automação CoupaDownloads")
    print("=" * 60)
    
    try:
        # Importar e executar a GUI
        from gui_main import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        print("   Certifique-se de que está executando do diretório correto")
        print(f"   Diretório atual: {current_dir}")
        return 1
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
