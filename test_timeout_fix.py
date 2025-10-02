#!/usr/bin/env python3
"""
Teste específico para verificar se o problema de travamento está resolvido.
Vamos testar apenas 1 PO para confirmar que o timeout funciona.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "EXPERIMENTAL"))

from workers.persistent_pool import PersistentWorkerPool
from workers.models.config import PoolConfig


async def test_single_po_processing():
    """Test processing a single PO to verify timeout fix."""
    print("🔧 Testando correção do timeout com 1 PO...")
    
    # Create minimal config
    import tempfile
    temp_dir = tempfile.mkdtemp()
    print(f"Using temp directory: {temp_dir}")
    
    config = PoolConfig(
        worker_count=1,
        headless_mode=True,  # Use headless to speed up
        base_profile_path=temp_dir,
        memory_threshold=0.8,
        shutdown_timeout=30
    )
    
    pool = PersistentWorkerPool(config)
    
    try:
        print("📝 Iniciando worker pool...")
        await pool.start()
        
        # Submit a test task with valid data
        po_data = {
            'po_number': 'PO16854649',
            'supplier': '1000FIX SERVICES LIMITED', 
            'url': 'https://unilever.coupahost.com/order_headers/16854649'
        }
        
        print(f"📝 Submetendo task para {po_data['po_number']}...")
        handle = pool.submit_task(po_data)
        print(f"✅ Task submetida: {handle.task_id}")
        
        # Wait a reasonable time for processing
        print("📝 Aguardando processamento...")
        completed = await pool.wait_for_completion(timeout=60)  # 1 minute
        
        if completed:
            print("✅ Processing completed successfully!")
        else:
            print("⚠️ Processing timed out, but worker didn't freeze!")
        
        # Get status
        status = pool.get_status()
        print(f"📊 Final status: {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("🧹 Shutting down...")
        await pool.shutdown()
        print("✅ Test complete!")


if __name__ == "__main__":
    print("🚀 Starting Single PO Timeout Test...")
    asyncio.run(test_single_po_processing())
    print("🎉 Test finished!")