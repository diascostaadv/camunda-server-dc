#!/usr/bin/env python3
"""
Script de teste para o fluxo completo de busca automatizada de publicações
Testa a integração: Timer BPMN → Worker → Gateway → ProcessStarter → Processos individuais
"""

import json
import sys
import os
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

# Adicionar caminho para importar modules
script_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(script_dir, '..', 'camunda-worker-api-gateway', 'app'))

try:
    from services.process_starter import ProcessStarter
    from models.buscar_request import BuscarPublicacoesRequest, PublicacaoParaProcessamento
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("💡 Execute do diretório test-scripts")
    sys.exit(1)


class BuscarPublicacoesTester:
    """Tester para o fluxo de busca automatizada de publicações"""
    
    def __init__(self, camunda_url: str = "http://201.23.67.197:8080", 
                 gateway_url: str = "http://localhost:8001"):
        self.camunda_url = camunda_url
        self.gateway_url = gateway_url
        
        # Cliente para Camunda
        self.process_starter = ProcessStarter(
            camunda_url=camunda_url,
            username="demo",
            password="demo"
        )
        
        # Cliente HTTP para Gateway
        self.session = requests.Session()
        self.session.timeout = 300  # 5 minutos
        
        print(f"🔧 Tester configurado:")
        print(f"   • Camunda: {camunda_url}")
        print(f"   • Gateway: {gateway_url}")
    
    def test_connections(self) -> bool:
        """Testa conexões com Camunda e Gateway"""
        print("\n🔗 Testando conexões...")
        
        # Testar Camunda
        camunda_ok = self.process_starter.test_connection()
        if camunda_ok:
            print("✅ Camunda: Conexão OK")
        else:
            print("❌ Camunda: Falha na conexão")
        
        # Testar Gateway
        try:
            response = self.session.get(f"{self.gateway_url}/health", timeout=10)
            gateway_ok = response.status_code == 200
            if gateway_ok:
                print("✅ Gateway: Conexão OK")
            else:
                print(f"❌ Gateway: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Gateway: Erro de conexão - {e}")
            gateway_ok = False
        
        return camunda_ok and gateway_ok
    
    def test_soap_connection(self) -> bool:
        """Testa conexão SOAP via Gateway"""
        print("\n🌐 Testando conexão SOAP...")
        
        try:
            response = self.session.post(f"{self.gateway_url}/buscar-publicacoes/test-soap")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    print("✅ SOAP: Conexão OK")
                    return True
                else:
                    print(f"❌ SOAP: {result.get('message', 'Erro desconhecido')}")
                    return False
            else:
                print(f"❌ SOAP: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ SOAP: Erro - {e}")
            return False
    
    def deploy_timer_process(self) -> bool:
        """Deploy do processo BPMN com timer"""
        print("\n🚀 Fazendo deploy do processo timer...")
        
        bpmn_file = os.path.join(script_dir, "buscar_publicacoes_timer.bpmn")
        
        if not os.path.exists(bpmn_file):
            print(f"❌ Arquivo BPMN não encontrado: {bpmn_file}")
            return False
        
        try:
            # Usar deploy_processo.py script
            deploy_script = os.path.join(script_dir, "deploy_processo.py")
            
            import subprocess
            result = subprocess.run([
                "python", deploy_script, 
                "deploy", bpmn_file,
                "--name", "BuscarPublicacoesTimer"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Processo timer deployado com sucesso")
                return True
            else:
                print(f"❌ Erro no deploy: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Erro durante deploy: {e}")
            return False
    
    def test_gateway_endpoint_direct(self) -> Dict[str, Any]:
        """Testa endpoint do Gateway diretamente"""
        print("\n🎯 Testando endpoint Gateway diretamente...")
        
        # Criar request de teste
        request_data = {
            "cod_grupo": 5,
            "limite_publicacoes": 3,
            "timeout_soap": 90,
            "apenas_nao_exportadas": True
        }
        
        try:
            print(f"📤 Enviando request: {request_data}")
            
            response = self.session.post(
                f"{self.gateway_url}/buscar-publicacoes/processar",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Gateway respondeu com sucesso")
                print(f"   • Total encontradas: {result.get('total_encontradas', 0)}")
                print(f"   • Instâncias criadas: {result.get('instancias_criadas', 0)}")
                print(f"   • Taxa de sucesso: {result.get('taxa_sucesso', 0):.1%}")
                print(f"   • Duração: {result.get('duracao_segundos', 0):.2f}s")
                return result
            else:
                print(f"❌ Gateway error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Erro ao testar Gateway: {e}")
            return {"status": "error", "message": str(e)}
    
    def test_process_starter_direct(self) -> bool:
        """Testa ProcessStarter diretamente"""
        print("\n⚙️ Testando ProcessStarter diretamente...")
        
        # Dados de teste para movimentação
        test_movimentacao = {
            "numero_processo": "TEST-001-2024",
            "data_publicacao": "15/03/2024",
            "texto_publicacao": "Teste de movimentação via ProcessStarter",
            "fonte": "manual",
            "tribunal": "tjmg",
            "instancia": "1"
        }
        
        try:
            print(f"🚀 Iniciando processo de teste...")
            
            instance_id = self.process_starter.start_movimentacao_process(
                test_movimentacao,
                business_key="test_process_starter"
            )
            
            if instance_id:
                print(f"✅ Processo iniciado - Instance ID: {instance_id}")
                
                # Aguardar um pouco e verificar status
                time.sleep(5)
                status = self.process_starter.get_process_instance_status(instance_id)
                
                if status:
                    print(f"📊 Status da instância: {status}")
                
                return True
            else:
                print("❌ Falha ao iniciar processo")
                return False
                
        except Exception as e:
            print(f"❌ Erro no ProcessStarter: {e}")
            return False
    
    def test_timer_process_manual(self) -> bool:
        """Testa processo timer manualmente (sem aguardar timer)"""
        print("\n⏰ Testando processo timer manualmente...")
        
        try:
            # Iniciar processo timer manualmente
            variables = {
                "cod_grupo": 5,
                "limite_publicacoes": 2,
                "trigger_manual": True
            }
            
            instance_id = self.process_starter.start_process_instance(
                "buscar_publicacoes_automatico",
                variables,
                business_key="test_timer_manual"
            )
            
            if instance_id:
                print(f"✅ Processo timer iniciado - Instance ID: {instance_id}")
                
                # Monitorar por 60 segundos
                print("⏳ Monitorando execução por 60 segundos...")
                
                for i in range(12):  # 12 checks de 5 segundos cada
                    time.sleep(5)
                    status = self.process_starter.get_process_instance_status(instance_id)
                    
                    if not status or status.get("status") == "not_found_or_completed":
                        print(f"✅ Processo completado após {(i+1)*5}s")
                        return True
                    else:
                        print(f"⏳ Aguardando... ({(i+1)*5}s)")
                
                print("⏰ Timeout - processo ainda executando")
                return False
                
            else:
                print("❌ Falha ao iniciar processo timer")
                return False
                
        except Exception as e:
            print(f"❌ Erro no teste timer: {e}")
            return False
    
    def run_full_test_suite(self):
        """Executa suite completa de testes"""
        print("🧪 === INICIANDO SUITE DE TESTES BUSCAR PUBLICAÇÕES ===")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        
        results = {}
        
        # 1. Testar conexões básicas
        print(f"\n{'='*60}")
        print("1️⃣ TESTE DE CONEXÕES")
        results["connections"] = self.test_connections()
        
        if not results["connections"]:
            print("❌ Falha nas conexões básicas - abortando testes")
            return results
        
        # 2. Testar SOAP
        print(f"\n{'='*60}")
        print("2️⃣ TESTE DE CONEXÃO SOAP")
        results["soap"] = self.test_soap_connection()
        
        # 3. Deploy processo timer
        print(f"\n{'='*60}")
        print("3️⃣ DEPLOY PROCESSO TIMER")
        results["deploy"] = self.deploy_timer_process()
        
        # 4. Testar ProcessStarter
        print(f"\n{'='*60}")
        print("4️⃣ TESTE PROCESSSTARTER DIRETO")
        results["process_starter"] = self.test_process_starter_direct()
        
        # 5. Testar Gateway endpoint
        print(f"\n{'='*60}")
        print("5️⃣ TESTE GATEWAY ENDPOINT")
        gateway_result = self.test_gateway_endpoint_direct()
        results["gateway"] = gateway_result.get("status") != "error"
        results["gateway_data"] = gateway_result
        
        # 6. Testar processo timer manual
        if results["deploy"]:
            print(f"\n{'='*60}")
            print("6️⃣ TESTE PROCESSO TIMER MANUAL")
            results["timer_process"] = self.test_timer_process_manual()
        else:
            print(f"\n{'='*60}")
            print("6️⃣ TESTE PROCESSO TIMER - PULADO (deploy falhou)")
            results["timer_process"] = False
        
        # 7. Gerar relatório final
        print(f"\n{'='*60}")
        print("📊 RELATÓRIO FINAL")
        
        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v is True)
        
        print(f"📈 Total de testes: {total_tests}")
        print(f"✅ Passou: {passed_tests}")
        print(f"❌ Falhou: {total_tests - passed_tests}")
        print(f"📊 Taxa de sucesso: {passed_tests/total_tests*100:.1f}%")
        
        print(f"\n📋 Detalhes:")
        test_names = {
            "connections": "Conexões básicas",
            "soap": "Conexão SOAP",
            "deploy": "Deploy processo",
            "process_starter": "ProcessStarter direto",
            "gateway": "Gateway endpoint",
            "timer_process": "Processo timer"
        }
        
        for key, result in results.items():
            if key == "gateway_data":
                continue
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   • {test_names.get(key, key)}: {status}")
        
        # Gateway details
        if "gateway_data" in results and isinstance(results["gateway_data"], dict):
            gw_data = results["gateway_data"]
            if gw_data.get("total_encontradas") is not None:
                print(f"\n🌐 Detalhes Gateway:")
                print(f"   • Publicações encontradas: {gw_data.get('total_encontradas', 0)}")
                print(f"   • Instâncias criadas: {gw_data.get('instancias_criadas', 0)}")
                print(f"   • Taxa de sucesso: {gw_data.get('taxa_sucesso', 0):.1%}")
        
        # Salvar relatório
        report = {
            "timestamp": datetime.now().isoformat(),
            "camunda_url": self.camunda_url,
            "gateway_url": self.gateway_url,
            "results": results,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": passed_tests/total_tests*100
            }
        }
        
        report_file = f"buscar_publicacoes_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Relatório salvo: {report_file}")
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
        
        return results


def main():
    """Função principal"""
    print("🎯 Teste de Busca Automatizada de Publicações")
    print("=" * 70)
    
    # URLs configuráveis via argumentos
    camunda_url = "http://201.23.67.197:8080"
    gateway_url = "http://localhost:8001"
    
    if len(sys.argv) > 1:
        if "--local-camunda" in sys.argv:
            camunda_url = "http://localhost:8080"
        if "--vm-gateway" in sys.argv:
            gateway_url = "http://201.23.67.197:8001"
    
    tester = BuscarPublicacoesTester(camunda_url, gateway_url)
    
    try:
        results = tester.run_full_test_suite()
        
        # Código de saída baseado no sucesso geral
        total_critical = 4  # connections, soap, deploy, gateway
        critical_passed = sum(1 for k in ["connections", "soap", "deploy", "gateway"] if results.get(k, False))
        
        if critical_passed == total_critical:
            print(f"\n🎉 Todos os testes críticos passaram!")
            exit_code = 0
        elif critical_passed >= total_critical * 0.75:
            print(f"\n⚠️ Maioria dos testes críticos passou")
            exit_code = 1
        else:
            print(f"\n❌ Muitos testes críticos falharam")
            exit_code = 2
        
        print(f"🏁 Testes finalizados - Código de saída: {exit_code}")
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