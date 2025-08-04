"""
PublicacaoWorker with Gateway Integration
Updated version that works with Worker API Gateway
"""

import sys
import os

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from common.utils import log_task_start, log_task_complete, log_task_error, get_timestamp
from intimation_client import IntimationAPIClient


class PublicacaoWorkerGateway(BaseWorker):
    """PublicacaoWorker with Gateway integration"""

    def __init__(self):
        super().__init__(
            worker_id="publicacao-worker-gateway",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Initialize API client with environment variables or default test credentials
        self.api_client = IntimationAPIClient(
            usuario=os.getenv('INTIMATION_USER', '100049'),
            senha=os.getenv('INTIMATION_PASSWORD', 'DcDpW@24'),
            timeout=90,
            max_retries=3
        )
        
        # Subscribe to topic - handler_func is only used in direct mode
        # In Gateway mode, the processing logic is in the Gateway's TaskProcessor
        self.subscribe(Topics.NOVA_PUBLICACAO, self.receive_publicacao_direct)

    def receive_publicacao_direct(self, task):
        """
        Handle the 'nova_publicacao' external task in direct mode.
        This method is only called when Gateway is disabled.
        When Gateway is enabled, processing happens in the Gateway.
        """
        if self.gateway_enabled:
            # This should not be called in Gateway mode, but just in case
            self.logger.warning("Direct handler called while Gateway mode is enabled")
            return
        
        log_task_start(task)
        
        try:
            result = self.process_publicacao_direct(task)
            
            # Complete the task with result
            self.complete_task(task, result)
            log_task_complete(task)
        except Exception as e:
            log_task_error(task, e)
            self.handle_error(task, e)
            
    def process_publicacao_direct(self, task):
        """
        Process the publication task directly (legacy mode).
        This is the original processing logic that runs when Gateway is disabled.
        """
        variables = task.get_variables()
        
        # Get parameters from task variables
        cod_grupo = variables.get('cod_grupo', 0)
        operation = variables.get('operation', 'import_all')
        
        if operation == 'import_all':
            # Import all non-exported publications
            publicacoes = self.api_client.importar_publicacoes_rotina(cod_grupo)
            
            return {
                "status": "success",
                "message": f"Imported {len(publicacoes)} publications",
                "publicacoes_count": len(publicacoes),
                "timestamp": get_timestamp()
            }
            
        elif operation == 'import_period':
            # Import publications from a specific period
            data_inicial = variables.get('data_inicial')
            data_final = variables.get('data_final')
            
            if not data_inicial or not data_final:
                raise ValueError("data_inicial and data_final are required for period import")
            
            publicacoes = self.api_client.get_publicacoes(data_inicial, data_final, cod_grupo)
            
            return {
                "status": "success",
                "message": f"Imported {len(publicacoes)} publications from period {data_inicial} to {data_final}",
                "publicacoes_count": len(publicacoes),
                "data_inicial": data_inicial,
                "data_final": data_final,
                "timestamp": get_timestamp()
            }
            
        elif operation == 'get_statistics':
            # Get publication statistics
            data = variables.get('data')
            if not data:
                raise ValueError("data is required for statistics operation")
                
            estatisticas = self.api_client.get_estatisticas_publicacoes(data, cod_grupo)
            
            return {
                "status": "success",
                "message": "Statistics retrieved successfully",
                "estatisticas": {
                    "grupo": estatisticas.grupo,
                    "total_publicacoes": estatisticas.total_publicacoes,
                    "total_nao_importadas": estatisticas.total_nao_importadas
                },
                "timestamp": get_timestamp()
            }
            
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def handle_error(self, task, error):
        """Handle task processing errors"""
        error_message = str(error)
        
        # Increment retry count in metadata if available
        metadata = task.get_variables().get('metadata', {})
        retry_count = metadata.get('retries', 0) + 1
        
        if retry_count < 3:
            # Retry the task
            self.logger.info(f"Retrying task {task.get_task_id()}, attempt {retry_count}")
            return task.failure(
                error_message=error_message,
                error_details=f"Retry attempt {retry_count}: {error_message}",
                retries=1,
                retry_timeout=30000  # 30 seconds
            )
        else:
            # Max retries reached, fail permanently
            self.logger.error(f"Task {task.get_task_id()} failed after {retry_count} attempts")
            return task.failure(
                error_message=error_message,
                error_details=f"Task failed after {retry_count} attempts: {error_message}",
                retries=0,
                retry_timeout=0
            )


def main():
    """Main entry point for the PublicacaoWorker with Gateway support"""
    try:
        # Validate configuration
        WorkerConfig.validate_config()
        
        # Create and start worker
        worker = PublicacaoWorkerGateway()
        
        print("🚀 Starting PublicacaoWorker with Gateway support...")
        print(f"📡 Connecting to Camunda at: {WorkerConfig.CAMUNDA_URL}")
        print(f"🎯 Subscribed to topic: {Topics.NOVA_PUBLICACAO}")
        
        # Show mode information
        if worker.gateway_enabled:
            print("🌐 Gateway mode: Tasks will be processed via Worker API Gateway")
            gateway_health = worker.gateway_client.health_check()
            print(f"🏥 Gateway health: {gateway_health['gateway_status']}")
        else:  
            print("⚡ Direct mode: Tasks will be processed directly by worker")
        
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