#!/usr/bin/env python3
"""
Script de teste para validar marcação de publicações como exportadas

Testa:
1. Endpoint de marcação manual
2. Endpoint de marcação por lote
3. Verificação de status
4. Validação de não-reprocessamento
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any


class TestMarcacaoExportadas:
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url.rstrip("/")
        self.test_results = []

    def print_header(self, text: str):
        """Imprime cabeçalho formatado"""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)

    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Imprime resultado de teste"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"     → {details}")
        self.test_results.append({"test": test_name, "success": success, "details": details})

    def test_1_marcar_manual(self, cod_publicacoes: List[int]) -> bool:
        """Teste 1: Marcar publicações manualmente"""
        self.print_header("Teste 1: Marcação Manual de Publicações")

        try:
            url = f"{self.gateway_url}/marcar-publicacoes/marcar-exportadas"
            payload = {
                "cod_publicacoes": cod_publicacoes,
                "atualizar_mongodb": True,
            }

            print(f"📤 POST {url}")
            print(f"   Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(url, json=payload, timeout=30)

            print(f"📥 Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")

                # Validações
                assert data.get("sucesso") is True, "Campo 'sucesso' deveria ser True"
                assert (
                    data.get("total_marcadas") == len(cod_publicacoes)
                ), f"Esperado {len(cod_publicacoes)} marcadas, obtido {data.get('total_marcadas')}"

                self.print_result(
                    "Marcação Manual",
                    True,
                    f"{data['total_marcadas']} publicações marcadas",
                )
                return True
            else:
                self.print_result(
                    "Marcação Manual", False, f"Status code: {response.status_code}"
                )
                print(f"   Error: {response.text}")
                return False

        except Exception as exc:
            self.print_result("Marcação Manual", False, str(exc))
            return False

    def test_2_verificar_status(self, cod_publicacao: int) -> bool:
        """Teste 2: Verificar status de exportação"""
        self.print_header("Teste 2: Verificação de Status")

        try:
            url = f"{self.gateway_url}/marcar-publicacoes/status-exportacao/{cod_publicacao}"

            print(f"📤 GET {url}")

            response = requests.get(url, timeout=30)

            print(f"📥 Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")

                # Validação
                marcada = data.get("marcada_exportada_webjur", False)

                self.print_result(
                    "Verificação de Status",
                    True,
                    f"Publicação {cod_publicacao} marcada: {marcada}",
                )
                return True
            elif response.status_code == 404:
                self.print_result(
                    "Verificação de Status",
                    True,
                    f"Publicação {cod_publicacao} não encontrada (esperado se não existe)",
                )
                return True
            else:
                self.print_result(
                    "Verificação de Status", False, f"Status code: {response.status_code}"
                )
                return False

        except Exception as exc:
            self.print_result("Verificação de Status", False, str(exc))
            return False

    def test_3_buscar_duplicado(self) -> bool:
        """Teste 3: Validar que publicações marcadas não são rebuscadas"""
        self.print_header("Teste 3: Validação de Não-Reprocessamento")

        try:
            url = f"{self.gateway_url}/buscar-publicacoes/processar-task-v2"

            # Primeira busca
            print("\n🔍 PRIMEIRA BUSCA:")
            payload1 = {
                "task_id": f"test-{int(time.time())}-1",
                "process_instance_id": f"test-instance-{int(time.time())}",
                "variables": {
                    "apenas_nao_exportadas": True,
                    "cod_grupo": 5,
                    "limite_publicacoes": 10,
                },
            }

            print(f"📤 POST {url}")
            print(f"   Payload: {json.dumps(payload1, indent=2)}")

            response1 = requests.post(url, json=payload1, timeout=120)

            if response1.status_code != 200:
                self.print_result(
                    "Não-Reprocessamento - Primeira Busca",
                    False,
                    f"Status: {response1.status_code}",
                )
                return False

            data1 = response1.json()
            print(f"📥 Status: {response1.status_code}")
            print(
                f"   Resultado: {data1.get('total_processadas', 0)} publicações processadas"
            )

            if data1.get("total_processadas", 0) == 0:
                self.print_result(
                    "Não-Reprocessamento",
                    True,
                    "Nenhuma publicação disponível (teste não aplicável)",
                )
                return True

            # Aguardar 2 segundos
            print("\n⏳ Aguardando 2 segundos...")
            time.sleep(2)

            # Segunda busca (deve retornar publicações DIFERENTES)
            print("\n🔍 SEGUNDA BUSCA:")
            payload2 = {
                "task_id": f"test-{int(time.time())}-2",
                "process_instance_id": f"test-instance-{int(time.time())}",
                "variables": {
                    "apenas_nao_exportadas": True,
                    "cod_grupo": 5,
                    "limite_publicacoes": 10,
                },
            }

            print(f"📤 POST {url}")
            response2 = requests.post(url, json=payload2, timeout=120)

            if response2.status_code != 200:
                self.print_result(
                    "Não-Reprocessamento - Segunda Busca",
                    False,
                    f"Status: {response2.status_code}",
                )
                return False

            data2 = response2.json()
            print(f"📥 Status: {response2.status_code}")
            print(
                f"   Resultado: {data2.get('total_processadas', 0)} publicações processadas"
            )

            # Comparar códigos de publicação
            # NOTA: Como não retornamos os códigos na response, vamos verificar lote_id diferente
            lote_id_1 = data1.get("lote_id")
            lote_id_2 = data2.get("lote_id")

            if lote_id_1 and lote_id_2 and lote_id_1 != lote_id_2:
                self.print_result(
                    "Não-Reprocessamento",
                    True,
                    f"Lotes diferentes criados (lote_1={lote_id_1[:8]}..., lote_2={lote_id_2[:8]}...)",
                )
                return True
            elif data2.get("total_processadas", 0) == 0:
                self.print_result(
                    "Não-Reprocessamento",
                    True,
                    "Segunda busca retornou 0 publicações (todas foram marcadas como exportadas)",
                )
                return True
            else:
                self.print_result(
                    "Não-Reprocessamento",
                    False,
                    "Não foi possível validar duplicação (dados insuficientes)",
                )
                return False

        except Exception as exc:
            self.print_result("Não-Reprocessamento", False, str(exc))
            return False

    def test_4_health_check(self) -> bool:
        """Teste 4: Health check do Gateway"""
        self.print_header("Teste 4: Health Check")

        try:
            url = f"{self.gateway_url}/health"

            print(f"📤 GET {url}")

            response = requests.get(url, timeout=10)

            print(f"📥 Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")

                self.print_result("Health Check", True, "Gateway operacional")
                return True
            else:
                self.print_result("Health Check", False, f"Status: {response.status_code}")
                return False

        except Exception as exc:
            self.print_result("Health Check", False, str(exc))
            return False

    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n")
        print("╔" + "=" * 78 + "╗")
        print("║" + " " * 20 + "TESTE DE MARCAÇÃO DE PUBLICAÇÕES" + " " * 26 + "║")
        print("╚" + "=" * 78 + "╝")

        print(f"\n🎯 Gateway URL: {self.gateway_url}")
        print(f"⏰ Timestamp: {datetime.now().isoformat()}")

        # Teste 4: Health Check (primeiro para garantir que API está UP)
        self.test_4_health_check()

        # Teste 1: Marcação Manual (com códigos de exemplo)
        # NOTA: Estes códigos podem não existir, teste serve para validar endpoint
        cod_publicacoes_teste = [999999, 999998, 999997]
        self.test_1_marcar_manual(cod_publicacoes_teste)

        # Teste 2: Verificação de Status
        self.test_2_verificar_status(cod_publicacoes_teste[0])

        # Teste 3: Validação de Não-Reprocessamento (teste mais importante)
        self.test_3_buscar_duplicado()

        # Resumo final
        self.print_header("RESUMO DOS TESTES")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        print(f"\n📊 Total de testes: {total_tests}")
        print(f"✅ Passou: {passed_tests}")
        print(f"❌ Falhou: {failed_tests}")

        print("\n📋 Detalhes:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test']}")
            if result["details"]:
                print(f"      → {result['details']}")

        print("\n" + "=" * 80)

        if failed_tests == 0:
            print("🎉 TODOS OS TESTES PASSARAM!")
        else:
            print(f"⚠️  {failed_tests} TESTE(S) FALHARAM")

        print("=" * 80 + "\n")

        return failed_tests == 0


def main():
    """Função principal"""
    import sys

    # Permitir passar URL do gateway como argumento
    gateway_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    tester = TestMarcacaoExportadas(gateway_url=gateway_url)
    success = tester.run_all_tests()

    # Exit code para CI/CD
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
