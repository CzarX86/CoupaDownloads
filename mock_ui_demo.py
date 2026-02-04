import time
import threading
from src.ui_controller import UIController
from src.core.communication_manager import CommunicationManager

def mock_ui_demo():
    print("🎨 Testing Enhanced Terminal UI")
    
    comm_manager = CommunicationManager(use_manager=False)
    ui_controller = UIController()
    
    # Simulate some initial state
    ui_controller.global_stats["total"] = 15
    
    # Start UI updates
    ui_controller.start_live_updates(comm_manager, update_interval=0.5)
    
    # Simulate worker activity
    for i in range(30):
        # Simulate worker 1
        comm_manager.send_metric({
            'worker_id': 0,
            'po_id': f'PO_{100 + (i//3)}',
            'status': 'PROCESSING' if i % 10 != 9 else 'COMPLETED',
            'timestamp': time.time(),
            'duration': i * 1.5,
            'attachments_found': 10,
            'attachments_downloaded': (i % 10) + 1,
            'message': f'Worker 1: Downloading attachment {i % 10 + 1} of 10...'
        })
        
        # Simulate worker 2
        comm_manager.send_metric({
            'worker_id': 1,
            'po_id': f'PO_{200 + (i//5)}',
            'status': 'PROCESSING' if i % 15 != 14 else 'FAILED',
            'timestamp': time.time(),
            'duration': i * 1.2,
            'attachments_found': 5,
            'attachments_downloaded': min(5, (i % 5) + 1),
            'message': f'Worker 2: Analyzing attachments for PO_{200 + (i//5)}...'
        })
        
        # Add some random log messages
        if i % 7 == 0:
            ui_controller.add_log(f"System Check: Worker {i%2 + 1} is performing well.")
            
        time.sleep(0.5)
        
    time.sleep(2)
    ui_controller.stop_live_updates()
    print("\n✅ Enhanced UI Demo Finished")

if __name__ == "__main__":
    mock_ui_demo()
