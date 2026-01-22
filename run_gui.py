#!/usr/bin/env python3
"""
Script simples para executar a GUI do CoupaDownloads.
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import tkinter as tk
from src.ui.gui import CoupaDownloadsGUI

def main():
    print("🚀 Iniciando CoupaDownloads GUI...")
    print("📋 Instruções:")
    print("   • Configure as opções no painel de configuração")
    print("   • Use os controles para iniciar/parar downloads")
    print("   • Monitore o progresso no painel de status")
    print("   • Use File -> Exit ou feche a janela para sair")
    print("")

    try:
        root = tk.Tk()
        app = CoupaDownloadsGUI(root)
        app.run()
        print("✅ Aplicação encerrada com sucesso.")
    except KeyboardInterrupt:
        print("\n⚠️  Aplicação interrompida pelo usuário.")
    except Exception as e:
        print(f"❌ Erro na aplicação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()