#!/usr/bin/env python3
"""
Script para deploy de processos BPMN no Camunda VM
Utilitário independente para gestão de deployments
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from typing import Dict, List, Optional


class CamundaDeploymentManager:
    """Gerenciador de deployments para Camunda VM"""
    
    def __init__(self, camunda_url: str = "http://201.23.67.197:8080"):
        self.camunda_url = camunda_url
        self.engine_rest_url = f"{camunda_url}/engine-rest"
        self.session = requests.Session()
        self.session.timeout = 60
        
        print(f"🔧 Deployment Manager configurado para: {camunda_url}")
    
    def test_connection(self) -> bool:
        """Testa conexão com o Camunda"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/engine")
            if response.status_code == 200:
                engines = response.json()
                print(f"✅ Conexão OK - {len(engines)} engine(s) disponível(is)")
                for engine in engines:
                    print(f"   • Engine: {engine.get('name', 'N/A')}")
                return True
            else:
                print(f"❌ Erro na conexão: HTTP {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Falha na conexão: {e}")
            return False
    
    def list_deployments(self) -> List[Dict]:
        """Lista todos os deployments existentes"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/deployment")
            if response.status_code == 200:
                deployments = response.json()
                print(f"📋 {len(deployments)} deployment(s) encontrado(s):")
                
                for dep in deployments:
                    print(f"   • ID: {dep['id']}")
                    print(f"     Nome: {dep.get('name', 'N/A')}")
                    print(f"     Data: {dep.get('deploymentTime', 'N/A')}")
                    print(f"     Fonte: {dep.get('source', 'N/A')}")
                    print()
                
                return deployments
            else:
                print(f"❌ Erro ao listar deployments: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Erro ao listar deployments: {e}")
            return []
    
    def get_deployment_resources(self, deployment_id: str) -> List[Dict]:
        """Lista recursos de um deployment específico"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/deployment/{deployment_id}/resources")
            if response.status_code == 200:
                resources = response.json()
                print(f"📁 Recursos do deployment {deployment_id}:")
                for resource in resources:
                    print(f"   • {resource.get('name', 'N/A')} ({resource.get('type', 'N/A')})")
                return resources
            else:
                print(f"❌ Erro ao obter recursos: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Erro ao obter recursos: {e}")
            return []
    
    def deploy_bpmn_file(self, bpmn_file_path: str, deployment_name: str = None, 
                         enable_duplicate_filtering: bool = True,
                         deploy_changed_only: bool = True) -> Optional[str]:
        """Deploy de um arquivo BPMN"""
        
        if not os.path.exists(bpmn_file_path):
            print(f"❌ Arquivo BPMN não encontrado: {bpmn_file_path}")
            return None
        
        if not deployment_name:
            deployment_name = f"deploy_{os.path.basename(bpmn_file_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"🚀 Iniciando deployment...")
        print(f"   • Arquivo: {bpmn_file_path}")
        print(f"   • Nome: {deployment_name}")
        print(f"   • Filtro duplicatas: {enable_duplicate_filtering}")
        print(f"   • Deploy apenas alterações: {deploy_changed_only}")
        
        try:
            with open(bpmn_file_path, 'rb') as bpmn_file:
                files = {
                    'deployment-name': (None, deployment_name),
                    'enable-duplicate-filtering': (None, str(enable_duplicate_filtering).lower()),
                    'deploy-changed-only': (None, str(deploy_changed_only).lower()),
                    'file': (os.path.basename(bpmn_file_path), bpmn_file, 'text/xml')
                }
                
                response = self.session.post(
                    f"{self.engine_rest_url}/deployment/create",
                    files=files
                )
                
                if response.status_code == 200:
                    deployment_info = response.json()
                    deployment_id = deployment_info['id']
                    
                    print(f"✅ Deploy realizado com sucesso!")
                    print(f"   • Deployment ID: {deployment_id}")
                    print(f"   • Data: {deployment_info.get('deploymentTime', 'N/A')}")
                    
                    # Listar recursos deployados
                    if 'deployedProcessDefinitions' in deployment_info:
                        processes = deployment_info['deployedProcessDefinitions']
                        if processes:
                            print(f"   • Processos deployados:")
                            for proc_id, proc_info in processes.items():
                                print(f"     - {proc_info.get('key', 'N/A')} (v{proc_info.get('version', '?')})")
                    
                    return deployment_id
                    
                else:
                    print(f"❌ Erro no deployment: HTTP {response.status_code}")
                    print(f"   Resposta: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Erro durante deployment: {e}")
            return None
    
    def delete_deployment(self, deployment_id: str, cascade: bool = True, 
                          skip_custom_listeners: bool = False,
                          skip_io_mappings: bool = False) -> bool:
        """Remove um deployment"""
        
        print(f"🗑️ Removendo deployment {deployment_id}...")
        print(f"   • Cascade: {cascade}")
        print(f"   • Skip custom listeners: {skip_custom_listeners}")
        print(f"   • Skip IO mappings: {skip_io_mappings}")
        
        try:
            params = {}
            if cascade:
                params['cascade'] = 'true'
            if skip_custom_listeners:
                params['skipCustomListeners'] = 'true'
            if skip_io_mappings:
                params['skipIoMappings'] = 'true'
            
            response = self.session.delete(
                f"{self.engine_rest_url}/deployment/{deployment_id}",
                params=params
            )
            
            if response.status_code == 204:
                print(f"✅ Deployment {deployment_id} removido com sucesso")
                return True
            else:
                print(f"❌ Erro ao remover deployment: HTTP {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao remover deployment: {e}")
            return False
    
    def list_process_definitions(self) -> List[Dict]:
        """Lista todas as definições de processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-definition")
            if response.status_code == 200:
                definitions = response.json()
                print(f"🔧 {len(definitions)} definição(ões) de processo encontrada(s):")
                
                for definition in definitions:
                    print(f"   • Key: {definition.get('key', 'N/A')}")
                    print(f"     ID: {definition.get('id', 'N/A')}")
                    print(f"     Nome: {definition.get('name', 'N/A')}")
                    print(f"     Versão: {definition.get('version', 'N/A')}")
                    print(f"     Deployment ID: {definition.get('deploymentId', 'N/A')}")
                    print()
                
                return definitions
            else:
                print(f"❌ Erro ao listar definições: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Erro ao listar definições: {e}")
            return []
    
    def get_process_definition_xml(self, process_definition_id: str) -> Optional[str]:
        """Obtém o XML de uma definição de processo"""
        try:
            response = self.session.get(f"{self.engine_rest_url}/process-definition/{process_definition_id}/xml")
            if response.status_code == 200:
                xml_data = response.json()
                return xml_data.get('bpmn20Xml')
            else:
                print(f"❌ Erro ao obter XML: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Erro ao obter XML: {e}")
            return None
    
    def export_deployment_summary(self, output_file: str = None):
        """Exporta resumo dos deployments para arquivo JSON"""
        
        if not output_file:
            output_file = f"deployment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        print(f"📤 Exportando resumo para: {output_file}")
        
        try:
            deployments = self.list_deployments()
            process_definitions = self.list_process_definitions()
            
            summary = {
                "export_timestamp": datetime.now().isoformat(),
                "camunda_url": self.camunda_url,
                "total_deployments": len(deployments),
                "total_process_definitions": len(process_definitions),
                "deployments": deployments,
                "process_definitions": process_definitions
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Resumo exportado com sucesso")
            return output_file
            
        except Exception as e:
            print(f"❌ Erro ao exportar resumo: {e}")
            return None


def main():
    """Função principal com interface CLI"""
    
    parser = argparse.ArgumentParser(description="Gerenciador de deployment Camunda VM")
    parser.add_argument("--url", default="http://201.23.67.197:8080", 
                       help="URL do Camunda (default: http://201.23.67.197:8080)")
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")
    
    # Comando: test
    subparsers.add_parser("test", help="Testa conexão com o Camunda")
    
    # Comando: list
    subparsers.add_parser("list", help="Lista deployments existentes")
    
    # Comando: processes
    subparsers.add_parser("processes", help="Lista definições de processo")
    
    # Comando: deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy de arquivo BPMN")
    deploy_parser.add_argument("bpmn_file", help="Caminho para arquivo BPMN")
    deploy_parser.add_argument("--name", help="Nome do deployment")
    deploy_parser.add_argument("--no-duplicate-filter", action="store_true", 
                              help="Desabilita filtro de duplicatas")
    deploy_parser.add_argument("--no-changed-only", action="store_true",
                              help="Deploy todos os recursos mesmo sem alterações")
    
    # Comando: delete
    delete_parser = subparsers.add_parser("delete", help="Remove deployment")
    delete_parser.add_argument("deployment_id", help="ID do deployment")
    delete_parser.add_argument("--no-cascade", action="store_true", 
                              help="Não remove instâncias relacionadas")
    
    # Comando: resources
    resources_parser = subparsers.add_parser("resources", help="Lista recursos de deployment")
    resources_parser.add_argument("deployment_id", help="ID do deployment")
    
    # Comando: export
    export_parser = subparsers.add_parser("export", help="Exporta resumo dos deployments")
    export_parser.add_argument("--output", help="Arquivo de saída (opcional)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Criar manager
    manager = CamundaDeploymentManager(args.url)
    
    # Executar comando
    try:
        if args.command == "test":
            success = manager.test_connection()
            sys.exit(0 if success else 1)
            
        elif args.command == "list":
            manager.list_deployments()
            
        elif args.command == "processes":
            manager.list_process_definitions()
            
        elif args.command == "deploy":
            deployment_id = manager.deploy_bpmn_file(
                args.bpmn_file, 
                args.name,
                enable_duplicate_filtering=not args.no_duplicate_filter,
                deploy_changed_only=not args.no_changed_only
            )
            sys.exit(0 if deployment_id else 1)
            
        elif args.command == "delete":
            success = manager.delete_deployment(
                args.deployment_id,
                cascade=not args.no_cascade
            )
            sys.exit(0 if success else 1)
            
        elif args.command == "resources":
            manager.get_deployment_resources(args.deployment_id)
            
        elif args.command == "export":
            output_file = manager.export_deployment_summary(args.output)
            sys.exit(0 if output_file else 1)
            
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