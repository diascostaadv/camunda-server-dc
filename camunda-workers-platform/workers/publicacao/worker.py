import sys
import os

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from common.utils import log_task_start, log_task_complete, log_task_error, get_timestamp
from .intimation_client import IntimationAPIClient


class PublicacaoWorker(BaseWorker):

    def __init__(self):
        super().__init__(
            worker_id="publicacao-worker",
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
        
        self.subscribe(Topics.NOVA_PUBLICACAO, self.receive_publicacao)

    def receive_publicacao(self, task):
        """
        Handle the 'nova_publicacao' external task.
        This method is called when a new publication task is received.
        """
        log_task_start(task)
        
        try:
            result = self.process_publicacao(task)
            
            # Complete the task with result
            self.complete_task(task, result)
            log_task_complete(task)
        except Exception as e:
            log_task_error(task, e)
            self.handle_error(task, e)
            
    def process_publicacao(self, task):
        """
        Process the publication task by importing intimations from the API.
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


if __name__ == "__main__":
    worker = PublicacaoWorker()
    worker.start()