#!/usr/bin/env python3
"""
🧪 Script de Execução de Testes para Integração Híbrida

Este script executa todos os testes das fases de integração híbrida
de forma organizada e com relatórios detalhados.

Uso:
    python run_integration_tests.py [--phase PHASE] [--verbose] [--coverage]
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Adicionar o diretório MyScript ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_tests(phase=None, verbose=False, coverage=False):
    """Executa os testes de integração."""
    
    # Comando base do pytest
    cmd = ["python3", "-m", "pytest"]
    
    # Arquivo de teste
    test_file = "src/MyScript/tests/test_hybrid_integration.py"
    
    if phase:
        # Executar apenas uma fase específica
        phase_class = f"TestPhase{phase}ProgressTracking"
        cmd.extend([f"{test_file}::{phase_class}", "-v"])
    else:
        # Executar todos os testes
        cmd.extend([test_file, "-v"])
    
    if verbose:
        cmd.append("--tb=long")
    else:
        cmd.append("--tb=short")
    
    if coverage:
        cmd.extend(["--cov=src/MyScript", "--cov-report=term-missing"])
    
    # Adicionar flags úteis
    cmd.extend([
        "--strict-markers",
        "--disable-warnings",
        "--color=yes"
    ])
    
    print(f"🧪 Executando testes: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=os.getcwd(), capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

def run_phase_tests():
    """Executa testes de cada fase individualmente."""
    phases = [
        (1, "Progress Tracking Avançado"),
        (2, "Formatação de Logs"),
        (3, "Retry e Validação"),
        (4, "Detecção de Erros"),
        (5, "Verificação de Perfil")
    ]
    
    print("🧪 Executando testes por fase...")
    print("=" * 60)
    
    results = {}
    
    for phase_num, phase_name in phases:
        print(f"\n📋 Fase {phase_num}: {phase_name}")
        print("-" * 40)
        
        success = run_tests(phase=phase_num, verbose=True)
        results[phase_num] = success
        
        if success:
            print(f"✅ Fase {phase_num} passou nos testes")
        else:
            print(f"❌ Fase {phase_num} falhou nos testes")
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 60)
    
    for phase_num, phase_name in phases:
        status = "✅ PASSOU" if results[phase_num] else "❌ FALHOU"
        print(f"Fase {phase_num}: {phase_name} - {status}")
    
    total_passed = sum(results.values())
    total_phases = len(phases)
    
    print(f"\n📈 Resultado: {total_passed}/{total_phases} fases passaram nos testes")
    
    if total_passed == total_phases:
        print("🎉 Todas as fases passaram nos testes!")
        return True
    else:
        print("⚠️ Algumas fases falharam nos testes.")
        return False

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Executa testes de integração híbrida")
    parser.add_argument("--phase", type=int, choices=[1,2,3,4,5], 
                      help="Executar apenas uma fase específica")
    parser.add_argument("--verbose", action="store_true", 
                      help="Modo verboso")
    parser.add_argument("--coverage", action="store_true", 
                      help="Incluir relatório de cobertura")
    parser.add_argument("--all-phases", action="store_true", 
                      help="Executar todas as fases individualmente")
    
    args = parser.parse_args()
    
    print("🧪 TESTES DE INTEGRAÇÃO HÍBRIDA")
    print("=" * 60)
    
    if args.all_phases:
        success = run_phase_tests()
    else:
        success = run_tests(
            phase=args.phase, 
            verbose=args.verbose, 
            coverage=args.coverage
        )
    
    if success:
        print("\n🎉 Todos os testes passaram!")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam!")
        sys.exit(1)

if __name__ == "__main__":
    main()
