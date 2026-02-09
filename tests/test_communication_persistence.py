import multiprocessing as mp
import time
from src.core.communication_manager import CommunicationManager, MetricMessage

def test_communication_manager_persistence():
    # Use use_manager=False for simple local testing without a full Manager process
    cm = CommunicationManager(use_manager=False)
    
    # Simulate processing 2000 POs (double the old buffer limit)
    # Even if buffer is now 500, state should persist for all 2000
    for i in range(2000):
        cm.send_metric({
            'worker_id': i % 4,
            'po_id': f"PO-{i}",
            'status': 'COMPLETED',
            'timestamp': time.time()
        })
    
    # Drain the queue
    cm.get_metrics(drain_all=True)
    
    # Check aggregation
    agg = cm.get_aggregated_metrics(drain_all=True)
    
    print(f"Total processed: {agg['total_processed']}")
    print(f"Total successful: {agg['total_successful']}")
    print(f"Buffer size: {len(cm._metrics_buffer)}")
    
    assert agg['total_processed'] == 2000
    assert agg['total_successful'] == 2000
    assert len(cm._metrics_buffer) <= 500
    
    # Test worker state persistence
    assert len(agg['workers_status']) == 4
    for i in range(4):
        assert agg['workers_status'][i]['worker_id'] == i

if __name__ == "__main__":
    try:
        test_communication_manager_persistence()
        print("✅ CommunicationManager persistence test PASSED")
    except Exception as e:
        print(f"❌ CommunicationManager persistence test FAILED: {e}")
        import traceback
        traceback.print_exc()
