import multiprocessing as mp
import time
from src.core.communication_manager import CommunicationManager, MetricMessage


def test_communication_manager_persistence():
    # Use use_manager=False for simple local testing without a full Manager process
    cm = CommunicationManager(use_manager=False)
    cm.configure_total_pos(2000)
    
    # Simulate processing 2000 POs (double the old buffer limit)
    # Even if buffer is now 500, state should persist for all 2000
    for i in range(2000):
        cm.send_metric({
            'worker_id': i % 4,
            'po_id': f"PO-{i}",
            'status': 'COMPLETED',
            'timestamp': time.time()
        })
    
    # Drain the queue in batches; the manager throttles reads to keep the UI responsive.
    while cm.get_metrics():
        pass
    
    # Check aggregation
    agg = cm.get_aggregated_metrics()
    
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


def test_communication_manager_aggregates_eta_metrics():
    cm = CommunicationManager(use_manager=False)
    cm.configure_total_pos(10)

    completion_times = [0.0, 60.0, 120.0, 180.0, 240.0]
    real_time = time.time
    try:
        for index, timestamp in enumerate(completion_times, start=1):
            time.time = lambda ts=timestamp: ts
            cm.send_metric({
                'worker_id': index % 2,
                'po_id': f"PO-{index}",
                'status': 'COMPLETED',
                'timestamp': timestamp,
            })
            cm.get_metrics()

        time.time = lambda: 300.0
        cm.send_metric({
            'worker_id': 0,
            'po_id': 'PO-6',
            'status': 'STARTED',
            'timestamp': 300.0,
        })
        cm.get_metrics()

        agg = cm.get_aggregated_metrics()
    finally:
        time.time = real_time

    assert agg['throughput']['dynamic_rate_per_minute'] > 0.0
    assert agg['throughput']['confidence_state'] == 'stable'
    assert agg['eta']['seconds'] is not None
    assert agg['eta']['display'].startswith('5m')

if __name__ == "__main__":
    try:
        test_communication_manager_persistence()
        print("✅ CommunicationManager persistence test PASSED")
    except Exception as e:
        print(f"❌ CommunicationManager persistence test FAILED: {e}")
        import traceback
        traceback.print_exc()
