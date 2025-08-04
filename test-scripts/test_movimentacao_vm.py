#!/usr/bin/env python3
"""
Script de teste para fluxo de movimentação judicial no Camunda VM
Integra com o data provider SOAP e testa o processamento completo.
"""

import json
import sys
import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Any

# Adicionar caminho para importar modules do worker
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'camunda-workers-platform', 'workers', 'publicacao'))

try:
    from intimation_api import IntimationAPIClient, Publicacao
except ImportError as e:
    print(f"❌ Erro ao importar IntimationAPIClient: {e}")
    print("💡 Verifique se o módulo intimation_api está disponível")
    sys.exit(1)


class CamundaVMTestClient:
    """Cliente para testes com Camunda VM online"""
    
    def __init__(self, camunda_url: str = "http://201.23.67.197:8080"):
        self.camunda_url = camunda_url
        self.engine_rest_url = f"{camunda_url}/engine-rest"
        self.session = requests.Session()
        
        # Configurações de timeout
        self.session.timeout = 30
        
        print(f"🔧 Configurado cliente Camunda VM: {camunda_url}")
    
    def test_connection(self) -> bool:
        """Testa conexão com o Camunda VM"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/engine")
            if response.status_code == 200:
                engines = response.json()
                print(f"✅ Conexão OK - Engines disponíveis: {len(engines)}")
                return True
            else:
                print(f"❌ Erro na conexão: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Falha na conexão: {e}")
            return False
    
    def deploy_process(self, bpmn_file_path: str, deployment_name: str = "test_movimentacao") -> str:
        """Deploy de processo BPMN para o Camunda VM"""
        try:
            with open(bpmn_file_path, 'rb') as bpmn_file:
                files = {
                    'deployment-name': (None, deployment_name),
                    'enable-duplicate-filtering': (None, 'true'),
                    'deploy-changed-only': (None, 'true'),
                    'file': ('processar_movimentacao.bpmn', bpmn_file, 'text/xml')
                }
                
                response = self.session.post(
                    f"{self.engine_rest_url}/deployment/create",
                    files=files
                )
                
                if response.status_code == 200:
                    deployment_info = response.json()
                    deployment_id = deployment_info['id']
                    print(f"✅ Processo deployado com sucesso!")
                    print(f"   • Deployment ID: {deployment_id}")
                    print(f"   • Nome: {deployment_name}")
                    print(f"   • Data: {deployment_info.get('deploymentTime', 'N/A')}")
                    return deployment_id
                else:
                    print(f"❌ Erro no deploy: HTTP {response.status_code}")
                    print(f"   Resposta: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Erro durante deploy: {e}")
            return None
    
    def start_process_instance(self, process_key: str, variables: Dict[str, Any]) -> str:
        """Inicia uma instância do processo"""
        try:
            # Formatar variáveis para Camunda
            camunda_variables = {}
            for key, value in variables.items():
                if isinstance(value, str):
                    camunda_variables[key] = {"value": value, "type": "String"}
                elif isinstance(value, int):
                    camunda_variables[key] = {"value": value, "type": "Integer"}
                elif isinstance(value, dict) or isinstance(value, list):
                    camunda_variables[key] = {"value": json.dumps(value), "type": "Json"}
                else:
                    camunda_variables[key] = {"value": str(value), "type": "String"}
            
            payload = {
                "variables": camunda_variables
            }
            
            response = self.session.post(
                f"{self.engine_rest_url}/process-definition/key/{process_key}/start",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                instance_info = response.json()
                instance_id = instance_info['id']
                print(f"✅ Instância iniciada com sucesso!")
                print(f"   • Instance ID: {instance_id}")
                print(f"   • Process Definition ID: {instance_info.get('definitionId', 'N/A')}")
                return instance_id
            else:
                print(f"❌ Erro ao iniciar instância: HTTP {response.status_code}")
                print(f"   Resposta: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao iniciar instância: {e}")
            return None
    
    def get_process_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """Obtém status de uma instância do processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-instance/{instance_id}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "completed_or_not_found"}
            else:
                print(f"❌ Erro ao obter status: HTTP {response.status_code}")
                return {"status": "error", "details": response.text}
                
        except Exception as e:
            print(f"❌ Erro ao obter status: {e}")
            return {"status": "error", "details": str(e)}
    
    def get_activity_instances(self, instance_id: str) -> List[Dict[str, Any]]:
        """Obtém instâncias de atividades de um processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-instance/{instance_id}/activity-instances")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erro ao obter atividades: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Erro ao obter atividades: {e}")
            return []


class MovimentacaoTestRunner:
    """Executor principal dos testes de movimentação"""
    
    def __init__(self):
        self.camunda_client = CamundaVMTestClient()
        self.soap_client = None
        self.results = []
    
    def setup_soap_client(self) -> bool:
        """Configura cliente SOAP para obter dados reais"""
        try:
            self.soap_client = IntimationAPIClient(
                usuario="100049",
                senha="DcDpW@24",
                timeout=90,
                max_retries=3
            )
            
            print("🔄 Testando conexão SOAP...")
            if self.soap_client.test_connection():
                print("✅ Cliente SOAP conectado com sucesso")
                return True
            else:
                print("❌ Falha na conexão SOAP")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao configurar cliente SOAP: {e}")
            return False
    
    def get_real_movimentacao_data(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtém dados reais de movimentações via SOAP"""
        try:
            print(f"📥 Buscando {limit} publicações via SOAP...")
            
            # Buscar publicações não exportadas
            publicacoes = self.soap_client.get_publicacoes_nao_exportadas(cod_grupo=5)
            
            if not publicacoes:
                print("⚠️ Nenhuma publicação encontrada, usando dados de período...")
                # Tentar buscar por período se não houver não exportadas
                publicacoes = self.soap_client.get_publicacoes_periodo_safe(
                    data_inicial="2025-05-01",
                    data_final="2025-05-01",
                    cod_grupo=0,
                    timeout_override=120
                )
            
            if not publicacoes:
                print("❌ Nenhuma publicação encontrada via SOAP")
                return []
            
            # Converter para formato esperado pelo worker
            movimentacoes = []
            for pub in publicacoes[:limit]:
                movimentacao = {
                    "numero_processo": pub.numero_processo or f"TESTE-{pub.cod_publicacao}",
                    "data_publicacao": pub.data_publicacao or "01/01/2024",
                    "texto_publicacao": pub.texto_publicacao or "Texto de teste via SOAP",
                    "fonte": "dw",  # Fonte padrão para dados do DW
                    "tribunal": pub.descricao_diario.lower().replace(" ", "") if pub.descricao_diario else "tjmg",
                    "instancia": "1"
                }
                movimentacoes.append(movimentacao)
                
            print(f"✅ Convertidas {len(movimentacoes)} movimentações para teste")
            return movimentacoes
            
        except Exception as e:
            print(f"❌ Erro ao obter dados SOAP: {e}")
            return []
    
    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        """Retorna dados de teste sintéticos"""
        return [
            {
                "numero_processo": "0024517-94.2019.8.13.0024",
                "data_publicacao": "15/03/2024",
                "texto_publicacao": "Audiência de conciliação designada para o dia 20/03/2024 às 14h00min. Ficam as partes intimadas.",
                "fonte": "manual",
                "tribunal": "tjmg",
                "instancia": "1"
            },
            {
                "numero_processo": "0035689-12.2023.8.13.0035",
                "data_publicacao": "16/03/2024", 
                "texto_publicacao": "Sentença publicada. Julgo procedente o pedido inicial, condenando o réu ao pagamento de R$ 5.000,00.",
                "fonte": "escavador",
                "tribunal": "tjmg",
                "instancia": "1"
            },
            {
                "numero_processo": "0046721-88.2024.8.13.0046",
                "data_publicacao": "17/03/2024",
                "texto_publicacao": "Recurso interposto. Remetam-se os autos ao Tribunal de Justiça para análise.",
                "fonte": "dw",
                "tribunal": "tjmg", 
                "instancia": "2"
            }
        ]
    
    def run_single_test(self, movimentacao_data: Dict[str, Any], test_id: int) -> Dict[str, Any]:
        """Executa um teste individual"""
        print(f"\n🧪 === TESTE {test_id} ===")
        print(f"📋 Processo: {movimentacao_data['numero_processo']}")
        print(f"📅 Data: {movimentacao_data['data_publicacao']}")
        print(f"📝 Texto: {movimentacao_data['texto_publicacao'][:50]}...")
        
        start_time = time.time()
        result = {
            "test_id": test_id,
            "movimentacao": movimentacao_data,
            "start_time": datetime.now().isoformat(),
            "status": "started"
        }
        
        try:
            # Iniciar instância do processo
            instance_id = self.camunda_client.start_process_instance(
                "processar_movimentacao_judicial",
                movimentacao_data
            )
            
            if not instance_id:
                result.update({
                    "status": "failed",
                    "error": "Falha ao iniciar instância do processo",
                    "duration": time.time() - start_time
                })
                return result
            
            result["instance_id"] = instance_id
            
            # Monitorar execução por 60 segundos
            print(f"⏱️ Monitorando execução por 60 segundos...")
            timeout = 60
            check_interval = 5
            elapsed = 0
            
            while elapsed < timeout:
                time.sleep(check_interval)
                elapsed += check_interval
                
                status = self.camunda_client.get_process_instance_status(instance_id)
                
                if status.get("status") == "completed_or_not_found":
                    result.update({
                        "status": "completed",
                        "duration": time.time() - start_time,
                        "end_time": datetime.now().isoformat()
                    })
                    print(f"✅ Teste {test_id} completado em {elapsed}s")
                    return result
                elif status.get("status") == "error":
                    result.update({
                        "status": "error",
                        "error": status.get("details", "Erro desconhecido"),
                        "duration": time.time() - start_time
                    })
                    print(f"❌ Teste {test_id} falhou: {status.get('details')}")
                    return result
                else:
                    print(f"⏳ Teste {test_id} - Aguardando... ({elapsed}s)")
            
            # Timeout
            result.update({
                "status": "timeout",
                "duration": time.time() - start_time,
                "final_status": status
            })
            print(f"⏰ Teste {test_id} timeout após {timeout}s")
            
        except Exception as e:
            result.update({
                "status": "exception",
                "error": str(e),
                "duration": time.time() - start_time
            })
            print(f"💥 Teste {test_id} exception: {e}")
        
        return result
    
    def run_full_test_suite(self, use_real_data: bool = True):
        """Executa suite completa de testes"""
        print("🚀 === INICIANDO SUITE DE TESTES MOVIMENTAÇÃO JUDICIAL ===")
        print(f"🎯 Alvo: {self.camunda_client.camunda_url}")
        print(f"📊 Dados reais: {'Sim' if use_real_data else 'Não'}")
        
        # Testar conexões
        if not self.camunda_client.test_connection():
            print("❌ Camunda VM inacessível - abortando testes")
            return False
        
        # Configurar dados de teste
        test_data = []
        if use_real_data:
            if self.setup_soap_client():
                test_data = self.get_real_movimentacao_data(limit=3)
            
            if not test_data:
                print("⚠️ Usando dados sintéticos como fallback")
                test_data = self.get_sample_test_data()
        else:
            test_data = self.get_sample_test_data()
        
        if not test_data:
            print("❌ Nenhum dado de teste disponível")
            return False
        
        print(f"📋 {len(test_data)} testes serão executados")
        
        # Deploy do processo (se necessário)
        bpmn_path = os.path.join(os.path.dirname(__file__), "processar_movimentacao.bpmn")
        deployment_id = self.camunda_client.deploy_process(bpmn_path)
        
        if not deployment_id:
            print("❌ Falha no deploy do processo - abortando")
            return False
        
        # Executar testes
        print(f"\n🏃 Executando {len(test_data)} testes...")
        for i, movimentacao in enumerate(test_data, 1):
            result = self.run_single_test(movimentacao, i)
            self.results.append(result)
            
            # Pequena pausa entre testes
            if i < len(test_data):
                time.sleep(2)
        
        # Gerar relatório
        self.generate_report()
        return True
    
    def generate_report(self):
        """Gera relatório final dos testes"""
        print(f"\n📊 === RELATÓRIO FINAL DE TESTES ===")
        
        if not self.results:
            print("❌ Nenhum resultado para reportar")
            return
        
        # Estatísticas
        total_tests = len(self.results)
        completed = len([r for r in self.results if r["status"] == "completed"])
        failed = len([r for r in self.results if r["status"] == "failed"])
        timeout = len([r for r in self.results if r["status"] == "timeout"])
        errors = len([r for r in self.results if r["status"] == "exception"])
        
        print(f"📈 Total de testes: {total_tests}")
        print(f"✅ Completados: {completed} ({completed/total_tests*100:.1f}%)")
        print(f"❌ Falhados: {failed} ({failed/total_tests*100:.1f}%)")
        print(f"⏰ Timeout: {timeout} ({timeout/total_tests*100:.1f}%)")
        print(f"💥 Exceções: {errors} ({errors/total_tests*100:.1f}%)")
        
        # Tempo médio
        durations = [r.get("duration", 0) for r in self.results if "duration" in r]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print(f"⏱️ Tempo médio: {avg_duration:.2f}s")
        
        # Salvar relatório detalhado
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), report_file)
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "camunda_url": self.camunda_client.camunda_url,
            "summary": {
                "total": total_tests,
                "completed": completed,
                "failed": failed,
                "timeout": timeout,
                "errors": errors,
                "success_rate": completed/total_tests*100 if total_tests > 0 else 0,
                "avg_duration": sum(durations) / len(durations) if durations else 0
            },
            "detailed_results": self.results
        }
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Relatório salvo: {report_file}")
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
        
        # Exibir detalhes dos testes com problemas
        problematic = [r for r in self.results if r["status"] not in ["completed"]]
        if problematic:
            print(f"\n🔍 Detalhes dos testes com problemas:")
            for result in problematic:
                print(f"   • Teste {result['test_id']}: {result['status']}")
                if "error" in result:
                    print(f"     Erro: {result['error']}")
                print(f"     Processo: {result['movimentacao']['numero_processo']}")


def main():
    """Função principal"""
    print("🎯 Teste de Movimentação Judicial - Camunda VM")
    print("=" * 60)
    
    # Argumentos de linha de comando simples
    use_real_data = "--synthetic" not in sys.argv
    
    runner = MovimentacaoTestRunner()
    
    try:
        success = runner.run_full_test_suite(use_real_data=use_real_data)
        exit_code = 0 if success else 1
        
        print(f"\n🏁 Testes finalizados - Código de saída: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Testes interrompidos pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()