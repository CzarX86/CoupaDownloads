#!/usr/bin/env python3
"""
MyScript Poetry Runner - Executa o sistema MyScript usando Poetry
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Executa o MyScript usando Poetry."""
    print("🚀 MyScript - Sistema Avançado de Automação CoupaDownloads")
    print("=" * 60)
    
    # Caminho para o diretório MyScript
    myscript_dir = Path(__file__).parent
    
    try:
        # Executar usando Poetry
        cmd = ["poetry", "run", "python", "run.py"]
        result = subprocess.run(cmd, cwd=myscript_dir, check=True)
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar com Poetry: {e}")
        return e.returncode
        
    except FileNotFoundError:
        print("❌ Poetry não encontrado!")
        print("   Execute: pip install poetry")
        return 1
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
