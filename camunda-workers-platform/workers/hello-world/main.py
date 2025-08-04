"""
Hello World Worker - Exemplo Simples
Um worker básico para entender como funciona o sistema Camunda
"""

import sys
import os

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from common.utils import log_task_start, log_task_complete, log_task_error, get_timestamp


class HelloWorldWorker(BaseWorker):
    """Worker simples que processa cumprimentos"""
    
    def __init__(self):
        super().__init__(
            worker_id="hello-world-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Subscribe to hello world topic
        self.subscribe(Topics.SAY_HELLO, self.say_hello)
    
    def say_hello(self, task):
        """
        Processa um cumprimento simples
        
        Expected variables:
        - name: Nome da pessoa para cumprimentar
        
        Returns:
        - greeting: Mensagem de cumprimento
        - processed_at: Timestamp do processamento
        """
        task_id = task.get_task_id()
        log_task_start(self.logger, task_id, Topics.SAY_HELLO)
        
        try:
            # Get the name from task variables
            name = self.get_variable(task, "name", "World")
            
            # Log the input
            self.logger.info(f"Processing greeting for: {name}")
            
            # Create the greeting message
            greeting = f"Hello, {name}!"
            
            # Prepare result variables
            result_variables = {
                "greeting": greeting,
                "processed_at": get_timestamp(),
                "worker_id": self.worker_id,
                "original_name": name
            }
            
            # Log success
            self.logger.info(f"Generated greeting: {greeting}")
            log_task_complete(self.logger, task_id, Topics.SAY_HELLO, {"greeting": greeting})
            
            # Complete the task
            return self.complete_task(task, result_variables)
            
        except Exception as e:
            # Log error
            error_msg = f"Failed to process greeting: {str(e)}"
            self.logger.error(error_msg)
            log_task_error(self.logger, task_id, Topics.SAY_HELLO, e)
            
            # Fail the task
            return self.fail_task(task, error_msg, str(e))


def main():
    """Main entry point for the hello world worker"""
    try:
        # Validate configuration
        WorkerConfig.validate_config()
        
        # Create and start worker
        worker = HelloWorldWorker()
        
        print("🚀 Starting Hello World Worker...")
        print(f"📡 Connecting to Camunda at: {WorkerConfig.CAMUNDA_URL}")
        print(f"🎯 Subscribed to topic: {Topics.SAY_HELLO}")
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