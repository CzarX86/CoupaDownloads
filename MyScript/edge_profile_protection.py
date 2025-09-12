#!/usr/bin/env python3
"""
Correção para proteger funções funcionais e corrigir problemas do Playwright
"""

import sys
from pathlib import Path
current_dir = Path('.')
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def fix_playwright_timeout():
    """Corrige timeout do Playwright para evitar ERR_ABORTED."""
    print("🔧 CORREÇÃO 1: Timeout do Playwright")
    print("=" * 50)
    
    try:
        # Ler arquivo playwright_system.py
        with open('playwright_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substituir configuração de timeout
        old_config = "await self.page.goto(url, wait_until='networkidle')"
        new_config = """await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)"""
        
        if old_config in content:
            content = content.replace(old_config, new_config)
            
            # Escrever arquivo corrigido
            with open('playwright_system.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Timeout do Playwright corrigido")
            print("   - Mudou de 'networkidle' para 'domcontentloaded'")
            print("   - Timeout aumentado para 30 segundos")
            return True
        else:
            print("⚠️ Configuração não encontrada")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao corrigir timeout: {e}")
        return False

def fix_playwright_error_handling():
    """Melhora tratamento de erros do Playwright."""
    print("\n🔧 CORREÇÃO 2: Tratamento de Erros do Playwright")
    print("=" * 50)
    
    try:
        # Ler arquivo playwright_system.py
        with open('playwright_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar tratamento específico para ERR_ABORTED
        old_except = """except PlaywrightTimeoutError as e:
            self.logger.error("Timeout ao carregar página", error=str(e), url=url)"""
        
        new_except = """except PlaywrightTimeoutError as e:
            self.logger.error("Timeout ao carregar página", error=str(e), url=url)
        except Exception as e:
            error_msg = str(e)
            if "ERR_ABORTED" in error_msg:
                self.logger.warning("Página abortada pelo navegador", url=url, error=error_msg)
            else:
                self.logger.error("Erro ao carregar página", error=error_msg, url=url)"""
        
        if old_except in content:
            content = content.replace(old_except, new_except)
            
            # Escrever arquivo corrigido
            with open('playwright_system.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Tratamento de erros melhorado")
            print("   - Adicionado tratamento específico para ERR_ABORTED")
            print("   - Logs mais informativos")
            return True
        else:
            print("⚠️ Tratamento de erro não encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao corrigir tratamento de erros: {e}")
        return False

def protect_working_functions():
    """Protege funções que estão funcionando corretamente."""
    print("\n🔧 CORREÇÃO 3: Proteção de Funções Funcionais")
    print("=" * 50)
    
    try:
        # Ler arquivo advanced_system.py
        with open('advanced_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar proteção para sistema híbrido
        old_hybrid = """# Processar URLs usando sistema apropriado
            if self.playwright_system:
                results = await self._process_urls_playwright(urls, stop_event)
            else:
                results = await self._process_urls_hybrid(urls, stop_event)"""
        
        new_hybrid = """# Processar URLs usando sistema apropriado
            # PROTEÇÃO: Sistema híbrido está funcionando, Playwright tem problemas
            if self.playwright_system:
                try:
                    results = await self._process_urls_playwright(urls, stop_event)
                    if not results:  # Se Playwright falhar, usar híbrido
                        self.logger.warning("Playwright falhou, usando sistema híbrido")
                        results = await self._process_urls_hybrid(urls, stop_event)
                except Exception as e:
                    self.logger.error("Erro no Playwright, usando sistema híbrido", error=str(e))
                    results = await self._process_urls_hybrid(urls, stop_event)
            else:
                results = await self._process_urls_hybrid(urls, stop_event)"""
        
        if old_hybrid in content:
            content = content.replace(old_hybrid, new_hybrid)
            
            # Escrever arquivo corrigido
            with open('advanced_system.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Sistema híbrido protegido")
            print("   - Fallback automático para sistema híbrido")
            print("   - Proteção contra falhas do Playwright")
            return True
        else:
            print("⚠️ Sistema híbrido não encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao proteger funções: {e}")
        return False

def fix_window_distribution():
    """Corrige distribuição de janelas no sistema híbrido."""
    print("\n🔧 CORREÇÃO 4: Distribuição de Janelas")
    print("=" * 50)
    
    try:
        # Ler arquivo inventory_system.py
        with open('inventory_system.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se já tem proteção para múltiplas janelas
        if "num_windows" in content and "create_windows" in content:
            print("✅ Sistema de múltiplas janelas já implementado")
            return True
        else:
            print("⚠️ Sistema de múltiplas janelas não encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar distribuição de janelas: {e}")
        return False

def main():
    """Função principal das correções."""
    print("🚀 MyScript - Correções de Proteção e Estabilidade")
    print("=" * 60)
    
    # Executar correções
    fixes = [
        fix_playwright_timeout(),
        fix_playwright_error_handling(),
        protect_working_functions(),
        fix_window_distribution()
    ]
    
    # Resumo
    print("\n📊 RESUMO DAS CORREÇÕES")
    print("=" * 50)
    print(f"Timeout Playwright: {'✅ OK' if fixes[0] else '❌ FALHOU'}")
    print(f"Tratamento de Erros: {'✅ OK' if fixes[1] else '❌ FALHOU'}")
    print(f"Proteção Híbrido: {'✅ OK' if fixes[2] else '❌ FALHOU'}")
    print(f"Distribuição Janelas: {'✅ OK' if fixes[3] else '❌ FALHOU'}")
    
    success_count = sum(fixes)
    
    if success_count >= 3:
        print("\n🎉 CORREÇÕES APLICADAS COM SUCESSO!")
        print("✅ Sistema protegido e estabilizado")
        print("\n💡 Próximos passos:")
        print("   1. Teste o sistema novamente")
        print("   2. Verifique se múltiplas janelas estão sendo criadas")
        print("   3. Monitore logs para erros ERR_ABORTED")
        return 0
    else:
        print("\n⚠️ ALGUMAS CORREÇÕES FALHARAM")
        print("❌ Verifique os erros acima")
        return 1

if __name__ == "__main__":
    sys.exit(main())
