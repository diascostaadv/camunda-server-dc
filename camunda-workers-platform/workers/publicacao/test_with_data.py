#!/usr/bin/env python3
"""
Teste para encontrar dados reais na API
"""
import logging
from intimation_api import IntimationAPIClient

# Configurar logging
logging.basicConfig(level=logging.INFO)

def testar_grupos():
    """Testa diferentes grupos para encontrar dados"""
    
    client = IntimationAPIClient(
        usuario="100049",
        senha="DcDpW@24",
        timeout=90,
        max_retries=2
    )
    
    print("🔍 Testando diferentes grupos para encontrar dados...")
    
    # Testa diferentes grupos
    grupos_teste = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    for grupo in grupos_teste:
        try:
            print(f"\n📋 Testando grupo {grupo}...")
            publicacoes = client.get_publicacoes_nao_exportadas(cod_grupo=grupo)
            
            if publicacoes:
                print(f"✅ ENCONTROU {len(publicacoes)} publicações no grupo {grupo}!")
                
                # Mostra detalhes da primeira
                primeira = publicacoes[0]
                print(f"   • Código: {primeira.cod_publicacao}")
                print(f"   • Processo: {primeira.numero_processo}")
                print(f"   • UF: {primeira.uf_publicacao}")
                print(f"   • Tribunal: {primeira.descricao_diario}")
                print(f"   • Data: {primeira.data_publicacao}")
                
                # Salva JSON do grupo com dados
                json_data = client.publicacoes_to_json(publicacoes)
                filename = f'publicacoes_grupo_{grupo}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                print(f"💾 Salvo em: {filename}")
                
                return grupo, publicacoes
            else:
                print(f"   ❌ Grupo {grupo}: sem dados")
                
        except Exception as e:
            print(f"   ⚠️ Erro no grupo {grupo}: {e}")
    
    print("\n❌ Nenhum grupo com dados encontrado")
    return None, []

def testar_periodo_recente():
    """Testa período recente para encontrar dados"""
    
    client = IntimationAPIClient(
        usuario="100049",
        senha="DcDpW@24",
        timeout=90,
        max_retries=2
    )
    
    print("\n📅 Testando períodos recentes...")
    
    periodos = [
        ("2025-07-01", "2025-07-31"),
        ("2025-06-01", "2025-06-30"),
        ("2025-05-01", "2025-05-31"),
        ("2025-04-01", "2025-04-30"),
        ("2025-03-01", "2025-03-31"),
        ("2025-02-01", "2025-02-28"),
        ("2025-01-01", "2025-01-31"),
        ("2024-12-01", "2024-12-31"),
    ]
    
    for inicio, fim in periodos:
        try:
            print(f"\n📅 Período {inicio} a {fim}...")
            publicacoes = client.get_publicacoes_periodo_safe(
                data_inicial=inicio,
                data_final=fim,
                cod_grupo=0,
                timeout_override=120
            )
            
            if publicacoes:
                print(f"✅ ENCONTROU {len(publicacoes)} publicações no período!")
                
                # Mostra detalhes da primeira
                primeira = publicacoes[0]
                print(f"   • Código: {primeira.cod_publicacao}")
                print(f"   • Processo: {primeira.numero_processo}")
                print(f"   • Data: {primeira.data_publicacao}")
                
                # Salva JSON do período com dados
                json_data = client.publicacoes_to_json(publicacoes)
                filename = f'publicacoes_periodo_{inicio}_{fim}.json'.replace('-', '_')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                print(f"💾 Salvo em: {filename}")
                
                return publicacoes
            else:
                print(f"   ❌ Período {inicio}-{fim}: sem dados")
                
        except Exception as e:
            print(f"   ⚠️ Erro no período {inicio}-{fim}: {e}")
    
    print("\n❌ Nenhum período com dados encontrado")
    return []

def testar_estatisticas_historicas():
    """Testa estatísticas de diferentes datas"""
    
    client = IntimationAPIClient(
        usuario="100049",
        senha="DcDpW@24",
        timeout=60,
        max_retries=2
    )
    
    print("\n📊 Testando estatísticas históricas...")
    
    datas = [
        "2025-07-24", "2025-07-23", "2025-07-22", "2025-07-21",
        "2025-06-15", "2025-05-15", "2025-04-15", "2025-03-15",
        "2025-02-15", "2025-01-15", "2024-12-15", "2024-11-15"
    ]
    
    for data in datas:
        try:
            print(f"\n📊 Estatísticas para {data}...")
            stats = client.get_estatisticas_publicacoes(data, cod_grupo=0)
            
            if stats.total_publicacoes > 0:
                print(f"✅ ENCONTROU dados para {data}!")
                print(f"   • Total: {stats.total_publicacoes}")
                print(f"   • Não importadas: {stats.total_nao_importadas}")
                print(f"   • Grupo: '{stats.grupo}'")
                
                # Salva estatísticas
                filename = f'stats_{data.replace("-", "_")}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(stats.to_json())
                print(f"💾 Salvo em: {filename}")
                
                return data, stats
            else:
                print(f"   ❌ {data}: sem estatísticas")
                
        except Exception as e:
            print(f"   ⚠️ Erro para {data}: {e}")
    
    print("\n❌ Nenhuma data com estatísticas encontrada")
    return None, None

if __name__ == "__main__":
    print("🚀 Teste para encontrar dados reais na API")
    print("=" * 60)
    
    # 1. Testa grupos
    grupo_com_dados, publicacoes = testar_grupos()
    
    # 2. Testa períodos
    publicacoes_periodo = testar_periodo_recente()
    
    # 3. Testa estatísticas
    data_com_stats, stats = testar_estatisticas_historicas()
    
    # Resumo
    print(f"\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES:")
    
    if grupo_com_dados is not None:
        print(f"✅ Grupo com dados: {grupo_com_dados} ({len(publicacoes)} publicações)")
    else:
        print("❌ Nenhum grupo com publicações encontrado")
    
    if publicacoes_periodo:
        print(f"✅ Períodos com dados: {len(publicacoes_periodo)} publicações")
    else:
        print("❌ Nenhum período com publicações encontrado")
        
    if data_com_stats:
        print(f"✅ Data com estatísticas: {data_com_stats} ({stats.total_publicacoes} total)")
    else:
        print("❌ Nenhuma data com estatísticas encontrada")
    
    print(f"\n💡 Verifique os arquivos JSON gerados para ver a estrutura dos dados")
    print(f"🎯 Use o grupo/período que encontrou dados nos seus testes!")