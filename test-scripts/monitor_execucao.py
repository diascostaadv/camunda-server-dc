#!/usr/bin/env python3
"""
Monitor de execução para processos Camunda VM
Monitora instâncias de processo e tarefas externas em tempo real
"""

import os
import sys
import json
import time
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict


class CamundaExecutionMonitor:
    """Monitor de execução para Camunda VM"""
    
    def __init__(self, camunda_url: str = "http://201.23.67.197:8080"):
        self.camunda_url = camunda_url
        self.engine_rest_url = f"{camunda_url}/engine-rest"
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Estado interno
        self.monitored_instances: Set[str] = set()
        self.execution_stats = defaultdict(int)
        
        print(f"🔍 Monitor configurado para: {camunda_url}")
    
    def test_connection(self) -> bool:
        """Testa conexão com o Camunda"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/engine")
            if response.status_code == 200:
                print("✅ Conexão com Camunda OK")
                return True
            else:
                print(f"❌ Erro na conexão: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Falha na conexão: {e}")
            return False
    
    def get_running_process_instances(self, process_key: str = None) -> List[Dict]:
        """Obtém instâncias de processo em execução"""
        try:
            params = {}
            if process_key:
                params['processDefinitionKey'] = process_key
            
            response = self.session.get(
                f"{self.engine_rest_url}/process-instance",
                params=params
            )
            
            if response.status_code == 200:
                instances = response.json()
                return instances
            else:
                print(f"❌ Erro ao obter instâncias: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Erro ao obter instâncias: {e}")
            return []
    
    def get_process_instance_details(self, instance_id: str) -> Optional[Dict]:
        """Obtém detalhes de uma instância específica"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-instance/{instance_id}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "not_found_or_completed"}
            else:
                return {"status": "error", "http_code": response.status_code}
                
        except Exception as e:
            return {"status": "exception", "error": str(e)}
    
    def get_activity_instances(self, instance_id: str) -> List[Dict]:
        """Obtém instâncias de atividade de um processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-instance/{instance_id}/activity-instances")
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            print(f"❌ Erro ao obter atividades de {instance_id}: {e}")
            return []
    
    def get_external_tasks(self, topic_name: str = None) -> List[Dict]:
        """Obtém tarefas externas disponíveis"""
        try:
            params = {}
            if topic_name:
                params['topicName'] = topic_name
            
            response = self.session.get(
                f"{self.engine_rest_url}/external-task",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erro ao obter tarefas externas: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Erro ao obter tarefas externas: {e}")
            return []
    
    def get_process_instance_variables(self, instance_id: str) -> Dict:
        """Obtém variáveis de uma instância de processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-instance/{instance_id}/variables")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            print(f"❌ Erro ao obter variáveis de {instance_id}: {e}")
            return {}
    
    def get_historic_process_instances(self, process_key: str = None, 
                                      finished_after: datetime = None,
                                      finished_before: datetime = None) -> List[Dict]:
        """Obtém instâncias históricas de processo"""
        try:
            params = {}
            if process_key:
                params['processDefinitionKey'] = process_key
            if finished_after:
                params['finishedAfter'] = finished_after.isoformat()
            if finished_before:
                params['finishedBefore'] = finished_before.isoformat()
            
            response = self.session.get(
                f"{self.engine_rest_url}/history/process-instance",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erro ao obter histórico: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Erro ao obter histórico: {e}")
            return []
    
    def monitor_process_execution(self, process_key: str, duration_minutes: int = 10,
                                 check_interval: int = 5, save_logs: bool = True) -> Dict:
        """Monitora execução de processos por período determinado"""
        
        print(f"🕐 Iniciando monitoramento de '{process_key}' por {duration_minutes} minutos")
        print(f"⏱️ Intervalo de verificação: {check_interval}s")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        monitoring_data = {
            "process_key": process_key,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "check_interval": check_interval,
            "snapshots": [],
            "summary": {}
        }
        
        snapshot_count = 0
        
        try:
            while datetime.now() < end_time:
                snapshot_count += 1
                snapshot_time = datetime.now()
                
                print(f"\n📸 Snapshot {snapshot_count} - {snapshot_time.strftime('%H:%M:%S')}")
                
                # Obter dados atuais
                running_instances = self.get_running_process_instances(process_key)
                external_tasks = self.get_external_tasks()
                
                # Filtrar tarefas do processo monitorado
                process_external_tasks = []
                for task in external_tasks:
                    # Verificar se a tarefa pertence a uma instância do processo monitorado
                    for instance in running_instances:
                        if task.get('processInstanceId') == instance.get('id'):
                            process_external_tasks.append(task)
                            break
                
                snapshot = {
                    "timestamp": snapshot_time.isoformat(),
                    "running_instances": len(running_instances),
                    "external_tasks_total": len(external_tasks),
                    "external_tasks_process": len(process_external_tasks),
                    "instances": running_instances,
                    "external_tasks": process_external_tasks
                }
                
                monitoring_data["snapshots"].append(snapshot)
                
                # Exibir estatísticas do snapshot
                print(f"   📊 Instâncias ativas: {len(running_instances)}")
                print(f"   📋 Tarefas externas (total): {len(external_tasks)}")
                print(f"   🎯 Tarefas do processo: {len(process_external_tasks)}")
                
                # Mostrar instâncias ativas
                if running_instances:
                    print(f"   🔍 Instâncias ativas:")
                    for instance in running_instances:
                        instance_id = instance.get('id', 'N/A')
                        business_key = instance.get('businessKey', 'N/A')
                        print(f"      • {instance_id} (key: {business_key})")
                
                # Mostrar tarefas externas do processo
                if process_external_tasks:
                    print(f"   📝 Tarefas externas do processo:")
                    task_topics = defaultdict(int)
                    for task in process_external_tasks:
                        topic = task.get('topicName', 'N/A')
                        task_topics[topic] += 1
                    
                    for topic, count in task_topics.items():
                        print(f"      • {topic}: {count}")
                
                # Aguardar próximo check (exceto no último)
                if datetime.now() < end_time:
                    time.sleep(check_interval)
            
            # Gerar resumo
            monitoring_data["summary"] = self._generate_monitoring_summary(monitoring_data)
            
            # Salvar logs se solicitado
            if save_logs:
                log_file = self._save_monitoring_logs(monitoring_data)
                print(f"\n💾 Logs salvos em: {log_file}")
            
            print(f"\n🏁 Monitoramento concluído - {snapshot_count} snapshots coletados")
            return monitoring_data
            
        except KeyboardInterrupt:
            print(f"\n⏹️ Monitoramento interrompido pelo usuário")
            monitoring_data["interrupted"] = True
            return monitoring_data
        except Exception as e:
            print(f"\n💥 Erro durante monitoramento: {e}")
            monitoring_data["error"] = str(e)
            return monitoring_data
    
    def _generate_monitoring_summary(self, monitoring_data: Dict) -> Dict:
        """Gera resumo dos dados de monitoramento"""
        
        snapshots = monitoring_data.get("snapshots", [])
        if not snapshots:
            return {"error": "Nenhum snapshot disponível"}
        
        # Estatísticas básicas
        running_instances_counts = [s["running_instances"] for s in snapshots]
        external_tasks_counts = [s["external_tasks_process"] for s in snapshots]
        
        # Instâncias únicas observadas
        all_instances = set()
        for snapshot in snapshots:
            for instance in snapshot.get("instances", []):
                all_instances.add(instance.get("id"))
        
        # Tópicos de tarefas externas observados
        all_topics = set()
        for snapshot in snapshots:
            for task in snapshot.get("external_tasks", []):
                all_topics.add(task.get("topicName"))
        
        summary = {
            "total_snapshots": len(snapshots),
            "unique_instances_observed": len(all_instances),
            "external_task_topics_observed": list(all_topics),
            "running_instances": {
                "min": min(running_instances_counts) if running_instances_counts else 0,
                "max": max(running_instances_counts) if running_instances_counts else 0,
                "avg": sum(running_instances_counts) / len(running_instances_counts) if running_instances_counts else 0
            },
            "external_tasks": {
                "min": min(external_tasks_counts) if external_tasks_counts else 0,
                "max": max(external_tasks_counts) if external_tasks_counts else 0,
                "avg": sum(external_tasks_counts) / len(external_tasks_counts) if external_tasks_counts else 0
            }
        }
        
        return summary
    
    def _save_monitoring_logs(self, monitoring_data: Dict) -> str:
        """Salva logs de monitoramento em arquivo JSON"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        process_key = monitoring_data.get("process_key", "unknown")
        log_file = f"monitor_{process_key}_{timestamp}.json"
        log_path = os.path.join(os.path.dirname(__file__), log_file)
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, ensure_ascii=False, indent=2)
            return log_file
        except Exception as e:
            print(f"❌ Erro ao salvar logs: {e}")
            return None
    
    def show_current_status(self, process_key: str = None):
        """Exibe status atual do Camunda"""
        
        print(f"📊 === STATUS ATUAL CAMUNDA ===")
        print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 URL: {self.camunda_url}")
        
        if process_key:
            print(f"🎯 Processo: {process_key}")
        
        # Instâncias em execução
        running_instances = self.get_running_process_instances(process_key)
        print(f"\n🏃 Instâncias em execução: {len(running_instances)}")
        
        if running_instances:
            for instance in running_instances:
                instance_id = instance.get('id', 'N/A')
                business_key = instance.get('businessKey', 'N/A')
                definition_key = instance.get('processDefinitionKey', 'N/A')
                print(f"   • {instance_id}")
                print(f"     Processo: {definition_key}")
                print(f"     Business Key: {business_key}")
        
        # Tarefas externas
        external_tasks = self.get_external_tasks()
        print(f"\n📋 Tarefas externas pendentes: {len(external_tasks)}")
        
        if external_tasks:
            topic_counts = defaultdict(int)
            for task in external_tasks:
                topic = task.get('topicName', 'N/A')
                topic_counts[topic] += 1
            
            for topic, count in topic_counts.items():
                print(f"   • {topic}: {count}")
        
        # Histórico recente (últimas 24h)
        yesterday = datetime.now() - timedelta(days=1)
        historical = self.get_historic_process_instances(
            process_key=process_key,
            finished_after=yesterday
        )
        
        print(f"\n📚 Instâncias finalizadas (24h): {len(historical)}")
        
        if historical:
            completed = len([h for h in historical if h.get('state') == 'COMPLETED'])
            terminated = len([h for h in historical if h.get('state') == 'EXTERNALLY_TERMINATED'])
            internally_terminated = len([h for h in historical if h.get('state') == 'INTERNALLY_TERMINATED'])
            
            print(f"   • Completadas: {completed}")
            print(f"   • Terminadas externamente: {terminated}")
            print(f"   • Terminadas internamente: {internally_terminated}")
    
    def watch_external_tasks(self, topic_name: str = None, duration_minutes: int = 5):
        """Observa tarefas externas em tempo real"""
        
        print(f"👀 Observando tarefas externas por {duration_minutes} minutos")
        if topic_name:
            print(f"🎯 Tópico: {topic_name}")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        last_task_count = -1
        
        try:
            while datetime.now() < end_time:
                tasks = self.get_external_tasks(topic_name)
                
                if len(tasks) != last_task_count:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"\n[{timestamp}] 📋 {len(tasks)} tarefa(s) externa(s)")
                    
                    if tasks:
                        for task in tasks:
                            task_id = task.get('id', 'N/A')[:8]  # Primeiros 8 chars
                            topic = task.get('topicName', 'N/A')
                            process_instance = task.get('processInstanceId', 'N/A')[:8]
                            retries = task.get('retries', 'N/A')
                            
                            print(f"   • {task_id} | {topic} | Processo: {process_instance} | Retries: {retries}")
                    
                    last_task_count = len(tasks)
                
                time.sleep(2)  # Check a cada 2 segundos
                
        except KeyboardInterrupt:
            print(f"\n⏹️ Observação interrompida pelo usuário")


def main():
    """Função principal com interface CLI"""
    
    parser = argparse.ArgumentParser(description="Monitor de execução Camunda VM")
    parser.add_argument("--url", default="http://201.23.67.197:8080",
                       help="URL do Camunda (default: http://201.23.67.197:8080)")
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")
    
    # Comando: status
    status_parser = subparsers.add_parser("status", help="Mostra status atual")
    status_parser.add_argument("--process", help="Chave do processo específico")
    
    # Comando: monitor
    monitor_parser = subparsers.add_parser("monitor", help="Monitora execução de processo")
    monitor_parser.add_argument("process_key", help="Chave do processo para monitorar")
    monitor_parser.add_argument("--duration", type=int, default=10, 
                               help="Duração em minutos (default: 10)")
    monitor_parser.add_argument("--interval", type=int, default=5,
                               help="Intervalo entre checks em segundos (default: 5)")
    monitor_parser.add_argument("--no-save", action="store_true",
                               help="Não salvar logs em arquivo")
    
    # Comando: watch-tasks
    watch_parser = subparsers.add_parser("watch-tasks", help="Observa tarefas externas")
    watch_parser.add_argument("--topic", help="Tópico específico para observar")
    watch_parser.add_argument("--duration", type=int, default=5,
                             help="Duração em minutos (default: 5)")
    
    # Comando: test
    subparsers.add_parser("test", help="Testa conexão com o Camunda")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Criar monitor
    monitor = CamundaExecutionMonitor(args.url)
    
    # Executar comando
    try:
        if args.command == "test":
            success = monitor.test_connection()
            sys.exit(0 if success else 1)
            
        elif args.command == "status":
            if not monitor.test_connection():
                sys.exit(1)
            monitor.show_current_status(args.process)
            
        elif args.command == "monitor":
            if not monitor.test_connection():
                sys.exit(1)
            
            monitoring_data = monitor.monitor_process_execution(
                args.process_key,
                duration_minutes=args.duration,
                check_interval=args.interval,
                save_logs=not args.no_save
            )
            
            # Exibir resumo
            summary = monitoring_data.get("summary", {})
            if summary:
                print(f"\n📈 === RESUMO DO MONITORAMENTO ===")
                print(f"📸 Snapshots coletados: {summary.get('total_snapshots', 0)}")
                print(f"🔍 Instâncias únicas observadas: {summary.get('unique_instances_observed', 0)}")
                
                running_stats = summary.get('running_instances', {})
                print(f"🏃 Instâncias ativas (min/avg/max): {running_stats.get('min', 0)}/{running_stats.get('avg', 0):.1f}/{running_stats.get('max', 0)}")
                
                topics = summary.get('external_task_topics_observed', [])
                if topics:
                    print(f"📋 Tópicos observados: {', '.join(topics)}")
            
        elif args.command == "watch-tasks":
            if not monitor.test_connection():
                sys.exit(1)
            monitor.watch_external_tasks(args.topic, args.duration)
            
    except KeyboardInterrupt:
        print("\n⏹️ Operação cancelada pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()