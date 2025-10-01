#!/usr/bin/env python3
"""
Teste de observabilidade do estado atual da implementação.
Verifica se os módulos e serviços implementados estão funcionais.
"""

import sys
import traceback
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_models_import():
    """Testa se os modelos podem ser importados."""
    print("🔍 Testando importação dos modelos...")
    try:
        from models import (
            Worker, WorkerStatus, WorkerConfiguration,
            Profile, ProfileStatus,
            Tab, TabStatus,
            BrowserSession, SessionStatus,
            POTask
        )
        print("✅ Modelos importados com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar modelos: {e}")
        traceback.print_exc()
        return False

def test_services_import():
    """Testa se os serviços podem ser importados."""
    print("\n🔍 Testando importação dos serviços...")
    try:
        from src.services import (
            ProfileManager,
            MemoryMonitor,
            TaskQueue,
            SignalHandler,
            GracefulShutdown,
            WorkerManager
        )
        print("✅ Serviços importados com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar serviços: {e}")
        traceback.print_exc()
        return False

def test_models_instantiation():
    """Testa se os modelos podem ser instanciados."""
    print("\n🔍 Testando instanciação dos modelos...")
    try:
        from models import Worker, Profile, Tab, BrowserSession, POTask, WorkerConfiguration
        import tempfile
        
        # Criar instâncias básicas
        config = WorkerConfiguration(worker_id="test-worker-1")
        worker = Worker(worker_id="test-worker-1", configuration=config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = Profile(profile_id="test-profile", base_path=temp_dir)
            
        tab = Tab(tab_id="test-tab", session_id="test-session")
        session = BrowserSession(session_id="test-session", profile=profile)
        task = POTask(task_id="test-task", po_number="PO123456")
        
        print("✅ Modelos instanciados com sucesso")
        print(f"   Worker: {worker.worker_id} (status: {worker.status})")
        print(f"   Profile: {profile.profile_id} (status: {profile.status})")
        print(f"   Tab: {tab.tab_id} (status: {tab.status})")
        print(f"   Session: {session.session_id}")
        print(f"   Task: {task.task_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao instanciar modelos: {e}")
        traceback.print_exc()
        return False

def test_services_instantiation():
    """Testa se os serviços podem ser instanciados."""
    print("\n🔍 Testando instanciação dos serviços...")
    try:
        from src.services import ProfileManager, MemoryMonitor, TaskQueue
        import tempfile
        
        # Criar instâncias básicas
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_manager = ProfileManager(base_path=temp_dir)
            memory_monitor = MemoryMonitor()
            task_queue = TaskQueue()
        
        print("✅ Serviços instanciados com sucesso")
        print(f"   ProfileManager: max_profiles={profile_manager.max_profiles}")
        print(f"   MemoryMonitor: threshold={memory_monitor.memory_threshold}")
        print(f"   TaskQueue: inicializada")
        return True
    except Exception as e:
        print(f"❌ Erro ao instanciar serviços: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Testa funcionalidades básicas dos serviços."""
    print("\n🔍 Testando funcionalidades básicas...")
    try:
        from src.services import ProfileManager, TaskQueue
        from models import POTask
        import tempfile
        
        # Teste ProfileManager
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_manager = ProfileManager(base_path=temp_dir)
            available_profile = profile_manager.get_available_profile()
            print(f"   Perfil disponível: {available_profile is not None}")
        
        # Teste TaskQueue
        task_queue = TaskQueue()
        test_task = POTask(task_id="test-basic", po_number="PO-BASIC-123")
        task_queue.add_task(test_task)
        
        status = task_queue.get_status()
        print(f"   Status da fila: {status.get('total_tasks', 0)} tarefas")
        
        # Tentar obter próxima tarefa
        next_task = task_queue.get_next_task(worker_id="test-worker")
        print(f"   Próxima tarefa: {next_task.task_id if next_task else 'None'}")
        
        print("✅ Funcionalidades básicas testadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao testar funcionalidades: {e}")
        traceback.print_exc()
        return False

def test_memory_monitoring():
    """Testa o monitoramento de memória."""
    print("\n🔍 Testando monitoramento de memória...")
    try:
        from src.services import MemoryMonitor
        
        memory_monitor = MemoryMonitor()
        system_info = memory_monitor.get_system_memory_info()
        status = memory_monitor.get_status()
        
        print(f"   Uso atual de memória: {system_info.get('usage_percent', 0):.1f}%")
        print(f"   Threshold configurado: {memory_monitor.memory_threshold}")
        print(f"   Monitoring ativo: {status.get('monitoring_active', False)}")
        
        print("✅ Monitoramento de memória testado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao testar monitoramento de memória: {e}")
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes de observabilidade."""
    print("🚀 Iniciando testes de observabilidade da implementação atual\n")
    
    tests = [
        ("Importação de Modelos", test_models_import),
        ("Importação de Serviços", test_services_import),
        ("Instanciação de Modelos", test_models_instantiation),
        ("Instanciação de Serviços", test_services_instantiation),
        ("Funcionalidades Básicas", test_basic_functionality),
        ("Monitoramento de Memória", test_memory_monitoring),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Falha crítica no teste '{test_name}': {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES DE OBSERVABILIDADE")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! A implementação está funcional e observável.")
        print("\n📋 Próximos passos sugeridos:")
        print("   1. Executar testes de integração: pytest tests/integration/")
        print("   2. Implementar Phase 3.5: Integration & Coordination")
        print("   3. Criar testes end-to-end com worker pool completo")
    elif passed > total // 2:
        print(f"\n⚠️  IMPLEMENTAÇÃO PARCIALMENTE FUNCIONAL ({passed}/{total} testes passaram)")
        print("   A base está sólida, mas alguns componentes precisam de ajustes.")
    else:
        print(f"\n🚨 IMPLEMENTAÇÃO COM PROBLEMAS CRÍTICOS ({passed}/{total} testes passaram)")
        print("   Necessário revisar e corrigir os componentes básicos.")

if __name__ == "__main__":
    main()