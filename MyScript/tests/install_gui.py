#!/usr/bin/env python3
"""
Script de Instalação e Configuração da GUI MyScript
Instala dependências e configura o ambiente para a interface gráfica
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou superior é necessário!")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def install_package(package):
    """Instala um pacote usando pip."""
    try:
        print(f"📦 Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar {package}: {e}")
        return False

def check_package(package):
    """Verifica se um pacote está instalado."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def install_customtkinter():
    """Instala CustomTkinter."""
    if check_package("customtkinter"):
        print("✅ CustomTkinter já está instalado!")
        return True
    
    return install_package("customtkinter")

def install_system_dependencies():
    """Instala dependências do sistema MyScript."""
    dependencies = [
        "selenium>=4.15.0",
        "playwright>=1.40.0", 
        "httpx>=0.25.0",
        "polars>=0.20.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "rich>=13.0.0",
        "tenacity>=8.2.0",
        "structlog>=23.0.0",
        "pydantic>=2.0.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "aiofiles>=23.0.0",
        "requests>=2.31.0"
    ]
    
    print("📦 Instalando dependências do sistema...")
    success = True
    
    for dep in dependencies:
        package_name = dep.split(">=")[0].split("==")[0]
        if not check_package(package_name):
            if not install_package(dep):
                success = False
    
    return success

def install_playwright_browsers():
    """Instala browsers do Playwright."""
    try:
        print("🌐 Instalando browsers do Playwright...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        print("✅ Browsers do Playwright instalados!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar browsers do Playwright: {e}")
        return False

def create_directories():
    """Cria diretórios necessários."""
    directories = [
        "src/MyScript/logs",
        "src/MyScript/config",
        "~/Downloads/CoupaDownloads"
    ]
    
    print("📁 Criando diretórios necessários...")
    for directory in directories:
        dir_path = Path(directory).expanduser()
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório criado: {dir_path}")

def test_installation():
    """Testa a instalação."""
    print("🧪 Testando instalação...")
    
    test_imports = [
        "customtkinter",
        "selenium",
        "playwright",
        "httpx",
        "polars",
        "pandas",
        "rich"
    ]
    
    success = True
    for package in test_imports:
        try:
            __import__(package)
            print(f"✅ {package} importado com sucesso!")
        except ImportError as e:
            print(f"❌ Erro ao importar {package}: {e}")
            success = False
    
    return success

def create_sample_config():
    """Cria arquivo de configuração de exemplo."""
    config_content = """{
  "excel_path": "src/MyScript/input.xlsx",
  "csv_path": "src/MyScript/download_inventory.csv",
  "download_dir": "~/Downloads/CoupaDownloads",
  "num_windows": 2,
  "max_tabs_per_window": 3,
  "max_workers": 4,
  "batch_size": 5,
  "headless": false,
  "profile_mode": "minimal"
}"""
    
    config_file = Path("src/MyScript/myscript_config.json")
    if not config_file.exists():
        config_file.write_text(config_content)
        print(f"✅ Arquivo de configuração criado: {config_file}")
    else:
        print(f"ℹ️ Arquivo de configuração já existe: {config_file}")

def main():
    """Função principal de instalação."""
    print("🚀 Instalador da GUI MyScript")
    print("=" * 50)
    
    # Verificar versão do Python
    if not check_python_version():
        return False
    
    # Instalar CustomTkinter
    if not install_customtkinter():
        print("❌ Falha na instalação do CustomTkinter!")
        return False
    
    # Instalar dependências do sistema
    if not install_system_dependencies():
        print("❌ Falha na instalação das dependências!")
        return False
    
    # Instalar browsers do Playwright
    if not install_playwright_browsers():
        print("⚠️ Aviso: Browsers do Playwright não foram instalados")
        print("   O sistema avançado pode não funcionar corretamente")
    
    # Criar diretórios
    create_directories()
    
    # Criar configuração de exemplo
    create_sample_config()
    
    # Testar instalação
    if not test_installation():
        print("❌ Alguns testes falharam!")
        return False
    
    print("\n🎉 Instalação concluída com sucesso!")
    print("\n📋 Próximos passos:")
    print("1. Execute: python src/MyScript/gui_main.py")
    print("2. Configure os parâmetros na aba 'Configuração'")
    print("3. Execute o sistema desejado na aba 'Dashboard'")
    print("\n📚 Documentação:")
    print("- Diagrama do sistema: src/MyScript/SYSTEM_DIAGRAM.md")
    print("- Guia de execução: src/MyScript/EXECUTION_GUIDE.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

