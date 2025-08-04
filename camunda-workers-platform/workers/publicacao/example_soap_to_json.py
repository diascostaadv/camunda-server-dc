#!/usr/bin/env python3
"""
Exemplo de uso da API de Intimações com conversão SOAP para JSON

Este exemplo demonstra como:
1. Fazer requisições SOAP para a API
2. Converter as respostas XML para objetos Python
3. Serializar os objetos para JSON
4. Salvar os dados em arquivo JSON
"""

import json
import os
from intimation_api import IntimationAPIClient, Publicacao

def exemplo_conversao_soap_json():
    """Exemplo completo de conversão SOAP para JSON"""
    
    # Configuração do cliente com timeout otimizado e retry
    client = IntimationAPIClient(
        usuario="100049",
        senha="DcDpW@24",
        timeout=90,  # Timeout maior para consultas pesadas
        max_retries=3  # Retry automático
    )
    
    print("🔄 Iniciando exemplo de conversão SOAP para JSON...")
    
    # Configurar logging para ver os retries
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 0. Testar conexão primeiro
        print("\n🔗 Testando conexão com a API...")
        if not client.test_connection():
            print("❌ Falha na conexão inicial. Abortando exemplo.")
            return False
        # 1. Buscar publicações não exportadas
        print("\n📥 Buscando publicações não exportadas...")
        publicacoes = client.get_publicacoes_nao_exportadas(cod_grupo=5)
        print(f"✅ Encontradas {len(publicacoes)} publicações")
        
        if publicacoes:
            # 2. Mostrar primeira publicação
            primeira = publicacoes[0]
            print(f"\n💼 Primeira publicação encontrada:")
            print(f"   • Código: {primeira.cod_publicacao}")
            print(f"   • Processo: {primeira.numero_processo}")
            print(f"   • UF: {primeira.uf_publicacao}")
            print(f"   • Tribunal: {primeira.descricao_diario}")
            print(f"   • Data: {primeira.data_publicacao}")
            
            # 3. Converter uma publicação para JSON
            print(f"\n🔄 Convertendo publicação {primeira.cod_publicacao} para JSON...")
            json_single = primeira.to_json()
            
            # Salvar publicação individual
            with open('publicacao_exemplo.json', 'w', encoding='utf-8') as f:
                f.write(json_single)
            print("💾 Salva em: publicacao_exemplo.json")
            
            # 4. Converter todas as publicações para JSON
            print(f"\n🔄 Convertendo todas as {len(publicacoes)} publicações para JSON...")
            json_all = client.publicacoes_to_json(publicacoes)
            
            # Salvar todas as publicações
            with open('todas_publicacoes.json', 'w', encoding='utf-8') as f:
                f.write(json_all)
            print("💾 Salvas em: todas_publicacoes.json")
            
            # 5. Exemplo de estrutura JSON
            print(f"\n📄 Estrutura JSON de uma publicação:")
            exemplo_dict = primeira.to_dict()
            print(json.dumps(exemplo_dict, ensure_ascii=False, indent=2)[:500] + "...")
            
        # 6. Buscar publicações por período usando método seguro (período com dados)
        print(f"\n📅 Buscando publicações por período (maio 2025 - período com dados)...")
        publicacoes_periodo = client.get_publicacoes_periodo_safe(
            data_inicial="2025-05-01",
            data_final="2025-05-01",  # Dia específico para ser mais rápido
            cod_grupo=0,
            timeout_override=120  # Timeout específico para este período
        )
        print(f"✅ Encontradas {len(publicacoes_periodo)} publicações no período")
        
        if publicacoes_periodo:
            # Salvar publicações do período
            json_periodo = client.publicacoes_to_json(publicacoes_periodo)
            with open('publicacoes_periodo.json', 'w', encoding='utf-8') as f:
                f.write(json_periodo)
            print("💾 Salvas em: publicacoes_periodo.json")
        
        # 7. Obter estatísticas
        print(f"\n📊 Obtendo estatísticas do dia...")
        stats = client.get_estatisticas_publicacoes("2024-01-24", cod_grupo=0)
        
        # Converter estatísticas para JSON
        stats_json = stats.to_json()
        with open('estatisticas.json', 'w', encoding='utf-8') as f:
            f.write(stats_json)
        
        print(f"✅ Estatísticas:")
        print(f"   • Grupo: {stats.grupo}")
        print(f"   • Total publicações: {stats.total_publicacoes}")
        print(f"   • Não importadas: {stats.total_nao_importadas}")
        print("💾 Salvas em: estatisticas.json")
        
        # 8. Resumo dos arquivos gerados
        print(f"\n🎉 Conversão concluída! Arquivos JSON gerados:")
        arquivos = [
            'publicacao_exemplo.json',
            'todas_publicacoes.json', 
            'publicacoes_periodo.json',
            'estatisticas.json'
        ]
        
        for arquivo in arquivos:
            if os.path.exists(arquivo):
                tamanho = os.path.getsize(arquivo)
                print(f"   • {arquivo} ({tamanho:,} bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante conversão: {e}")
        import traceback
        traceback.print_exc()
        return False

def exemplo_integracao_camunda():
    """Exemplo de como integrar com o Camunda Worker"""
    
    print("\n🔧 Exemplo de integração com Camunda Worker...")
    
    # Simular dados de tarefa do Camunda
    task_variables = {
        'operation': 'import_all',
        'cod_grupo': 5,
        'format': 'json'
    }
    
    client = IntimationAPIClient(
        usuario="100049",
        senha="DcDpW@24",
        timeout=90,
        max_retries=3
    )
    
    try:
        if task_variables['operation'] == 'import_all':
            publicacoes = client.get_publicacoes_nao_exportadas(
                cod_grupo=task_variables.get('cod_grupo', 0)
            )
            
            # Preparar resultado para o Camunda
            resultado = {
                "status": "success",
                "message": f"Imported {len(publicacoes)} publications",
                "publicacoes_count": len(publicacoes),
                "timestamp": "2025-07-24T20:32:53Z"
            }
            
            # Se solicitado JSON, incluir dados completos
            if task_variables.get('format') == 'json':
                resultado['publicacoes'] = client.publicacoes_to_dict(publicacoes)
            
            # Salvar resultado para o Camunda
            with open('camunda_result.json', 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Resultado preparado para Camunda:")
            print(f"   • Status: {resultado['status']}")
            print(f"   • Publicações: {resultado['publicacoes_count']}")
            print("💾 Salvo em: camunda_result.json")
            
            return resultado
            
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error importing publications: {str(e)}",
            "timestamp": "2025-07-24T20:32:53Z"
        }
        
        with open('camunda_error.json', 'w', encoding='utf-8') as f:
            json.dump(error_result, f, ensure_ascii=False, indent=2)
        
        print(f"❌ Erro preparado para Camunda: {e}")
        return error_result

if __name__ == "__main__":
    print("🚀 Exemplos de conversão SOAP para JSON")
    print("=" * 50)
    
    # Executar exemplo principal
    sucesso = exemplo_conversao_soap_json()
    
    if sucesso:
        print("\n" + "=" * 50)
        exemplo_integracao_camunda()
    
    print(f"\n✨ Exemplo concluído!")
    print(f"💡 Verifique os arquivos JSON gerados no diretório atual")
    
    
    

PUBS = """
    1 - Start camunda - processo de tratamento de publicação
    - Topico = BuscarPublicacoes
    - Monta pauta 
    """



 