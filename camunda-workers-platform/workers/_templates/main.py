"""
{{WORKER_DESCRIPTION}}
Auto-generated worker template
"""

import sys
import os

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from common.utils import log_task_start, log_task_complete, log_task_error, get_timestamp


class {{WORKER_CLASS_NAME}}(BaseWorker):
    """{{WORKER_DESCRIPTION}}"""
    
    def __init__(self):
        super().__init__(
            worker_id="{{WORKER_NAME}}",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Subscribe to topics
        self.subscribe("{{WORKER_TOPIC}}", self.process_{{WORKER_NAME}}_task)
    
    def process_{{WORKER_NAME}}_task(self, task):
        """
        Process {{WORKER_NAME}} task
        
        Expected variables:
        - Add your expected variables here
        
        Returns:
        - Add your return variables here
        """
        task_id = task.get_task_id()
        log_task_start(self.logger, task_id, "{{WORKER_TOPIC}}")
        
        try:
            # Get variables from task
            variables = task.get_variables()
            
            # TODO: Implement your business logic here
            self.logger.info(f"Processing task {task_id} with variables: {variables}")
            
            # Example processing
            result = self.process_business_logic(variables)
            
            # Prepare result variables
            result_variables = {
                "status": "success",
                "result": result,
                "processed_at": get_timestamp(),
                "worker_id": self.worker_id
            }
            
            # Log success
            self.logger.info(f"Task {task_id} completed successfully")
            log_task_complete(self.logger, task_id, "{{WORKER_TOPIC}}", result_variables)
            
            # Complete the task
            return self.complete_task(task, result_variables)
            
        except Exception as e:
            # Log error
            error_msg = f"Failed to process {{WORKER_NAME}} task: {str(e)}"
            self.logger.error(error_msg)
            log_task_error(self.logger, task_id, "{{WORKER_TOPIC}}", e)
            
            # Fail the task
            return self.fail_task(task, error_msg, str(e))
    
    def process_business_logic(self, variables):
        """
        Implement your business logic here
        
        Args:
            variables: Dictionary with task variables
            
        Returns:
            Result of processing
        """
        # TODO: Replace with your actual business logic
        return {
            "message": "Task processed successfully",
            "input_variables": variables
        }


def main():
    """Main entry point for the {{WORKER_NAME}} worker"""
    try:
        # Validate configuration
        WorkerConfig.validate_config()
        
        # Create and start worker
        worker = {{WORKER_CLASS_NAME}}()
        
        print("🚀 Starting {{WORKER_DESCRIPTION}}...")
        print(f"📡 Connecting to Camunda at: {WorkerConfig.CAMUNDA_URL}")
        print(f"🎯 Subscribed to topic: {{WORKER_TOPIC}}")
        print(f"📊 Metrics available at: http://localhost:{WorkerConfig.METRICS_PORT}/metrics")
        print("🔄 Waiting for tasks...")
        
        # Start the worker (this will block)
        worker.start()
        
    except KeyboardInterrupt:
        print("\n⏹️  Shutdown requested by user")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()