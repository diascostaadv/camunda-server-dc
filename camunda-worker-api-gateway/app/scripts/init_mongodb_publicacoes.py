#!/usr/bin/env python3
"""
Script de inicialização do MongoDB para o fluxo de publicações
Cria coleções e índices necessários conforme o BPMN
"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import CollectionInvalid, OperationFailure

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MongoDBPublicacoesInitializer:
    """Inicializador das coleções MongoDB para o fluxo de publicações"""
    
    def __init__(self, connection_string: str = None, database_name: str = "worker_gateway"):
        """
        Inicializa o cliente MongoDB
        
        Args:
            connection_string: String de conexão MongoDB
            database_name: Nome do banco de dados
        """
        self.connection_string = connection_string or os.getenv(
            'MONGODB_CONNECTION_STRING',
            'mongodb://localhost:27017/'
        )
        self.database_name = database_name
        self.client = None
        self.db = None
        
    def connect(self):
        """Conecta ao MongoDB"""
        try:
            logger.info(f"Conectando ao MongoDB: {self.connection_string}")
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Testa conexão
            self.client.server_info()
            logger.info(f"✅ Conectado ao banco de dados: {self.database_name}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao MongoDB: {e}")
            raise
    
    def create_collections(self):
        """Cria as coleções necessárias"""
        collections = {
            'execucoes': {
                'description': 'Log de execuções do processo de busca',
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['data_inicio', 'status'],
                        'properties': {
                            'data_inicio': {'bsonType': 'date'},
                            'data_fim': {'bsonType': 'date'},
                            'status': {'enum': ['running', 'completed', 'error', 'cancelled']},
                            'total_encontradas': {'bsonType': 'int'},
                            'total_processadas': {'bsonType': 'int'},
                            'configuracao': {'bsonType': 'object'}
                        }
                    }
                }
            },
            'lotes': {
                'description': 'Lotes de publicações buscadas',
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['execucao_id', 'timestamp_criacao', 'total_publicacoes'],
                        'properties': {
                            'execucao_id': {'bsonType': 'objectId'},
                            'timestamp_criacao': {'bsonType': 'date'},
                            'total_publicacoes': {'bsonType': 'int'},
                            'cod_grupo': {'bsonType': 'int'},
                            'data_inicial': {'bsonType': 'string'},
                            'data_final': {'bsonType': 'string'},
                            'status': {'enum': ['pendente', 'processando', 'processado', 'erro']}
                        }
                    }
                }
            },
            'publicacoes_bronze': {
                'description': 'Dados brutos das publicações (tabela bronze)',
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['lote_id', 'cod_publicacao', 'numero_processo', 'data_publicacao', 'texto_publicacao'],
                        'properties': {
                            'lote_id': {'bsonType': 'objectId'},
                            'cod_publicacao': {'bsonType': 'int'},
                            'numero_processo': {'bsonType': 'string'},
                            'data_publicacao': {'bsonType': 'string'},
                            'texto_publicacao': {'bsonType': 'string'},
                            'fonte': {'enum': ['dw', 'manual', 'escavador']},
                            'tribunal': {'bsonType': 'string'},
                            'instancia': {'bsonType': 'string'},
                            'descricao_diario': {'bsonType': 'string'},
                            'uf_publicacao': {'bsonType': 'string'},
                            'timestamp_insercao': {'bsonType': 'date'},
                            'status': {'enum': ['nova', 'processada', 'repetida', 'erro']}
                        }
                    }
                }
            },
            'publicacoes_prata': {
                'description': 'Dados higienizados e processados (tabela prata)',
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['publicacao_bronze_id', 'hash_unica', 'numero_processo', 'data_publicacao', 'texto_limpo'],
                        'properties': {
                            'publicacao_bronze_id': {'bsonType': 'objectId'},
                            'hash_unica': {'bsonType': 'string'},
                            'hash_alternativa': {'bsonType': 'string'},
                            'numero_processo': {'bsonType': 'string'},
                            'numero_processo_limpo': {'bsonType': 'string'},
                            'data_publicacao': {'bsonType': 'date'},
                            'data_publicacao_original': {'bsonType': 'string'},
                            'texto_limpo': {'bsonType': 'string'},
                            'texto_original': {'bsonType': 'string'},
                            'fonte': {'enum': ['dw', 'manual', 'escavador']},
                            'tribunal': {'bsonType': 'string'},
                            'instancia': {'bsonType': 'string'},
                            'status': {
                                'enum': ['nova_publicacao_inedita', 'identidade_duvidosa', 'repetida', 'apto_a_agenda']
                            },
                            'score_similaridade': {'bsonType': 'double'},
                            'publicacoes_similares': {
                                'bsonType': 'array',
                                'items': {
                                    'bsonType': 'object',
                                    'properties': {
                                        'publicacao_id': {'bsonType': 'objectId'},
                                        'score': {'bsonType': 'double'}
                                    }
                                }
                            },
                            'classificacao': {
                                'bsonType': 'object',
                                'properties': {
                                    'tipo': {'bsonType': 'string'},
                                    'subtipo': {'bsonType': 'string'},
                                    'urgente': {'bsonType': 'bool'},
                                    'prazo_dias': {'bsonType': 'int'}
                                }
                            },
                            'timestamp_processamento': {'bsonType': 'date'},
                            'camunda_instance_id': {'bsonType': 'string'}
                        }
                    }
                }
            },
            'hashes': {
                'description': 'Índice de hashes para deduplicação rápida',
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['hash_value', 'publicacao_prata_id', 'timestamp_criacao'],
                        'properties': {
                            'hash_value': {'bsonType': 'string'},
                            'publicacao_prata_id': {'bsonType': 'objectId'},
                            'numero_processo': {'bsonType': 'string'},
                            'data_publicacao': {'bsonType': 'date'},
                            'timestamp_criacao': {'bsonType': 'date'}
                        }
                    }
                }
            }
        }
        
        for collection_name, config in collections.items():
            try:
                # Cria coleção com validação
                self.db.create_collection(
                    collection_name,
                    validator=config.get('validator')
                )
                logger.info(f"✅ Coleção '{collection_name}' criada: {config['description']}")
                
            except CollectionInvalid:
                logger.info(f"ℹ️ Coleção '{collection_name}' já existe")
                
            except Exception as e:
                logger.error(f"❌ Erro ao criar coleção '{collection_name}': {e}")
    
    def create_indexes(self):
        """Cria índices otimizados para as coleções"""
        
        indexes = {
            'execucoes': [
                ('data_inicio', DESCENDING),
                ('status', ASCENDING),
                ([('status', ASCENDING), ('data_inicio', DESCENDING)], 'status_data')
            ],
            'lotes': [
                ('execucao_id', ASCENDING),
                ('timestamp_criacao', DESCENDING),
                ('status', ASCENDING),
                ([('execucao_id', ASCENDING), ('status', ASCENDING)], 'execucao_status')
            ],
            'publicacoes_bronze': [
                ('lote_id', ASCENDING),
                ('cod_publicacao', ASCENDING, {'unique': True}),
                ('numero_processo', ASCENDING),
                ('data_publicacao', ASCENDING),
                ('status', ASCENDING),
                ([('numero_processo', ASCENDING), ('data_publicacao', DESCENDING)], 'processo_data'),
                ([('lote_id', ASCENDING), ('status', ASCENDING)], 'lote_status'),
                ('texto_publicacao', TEXT)  # Índice de texto para busca
            ],
            'publicacoes_prata': [
                ('publicacao_bronze_id', ASCENDING, {'unique': True}),
                ('hash_unica', ASCENDING, {'unique': True}),
                ('numero_processo_limpo', ASCENDING),
                ('data_publicacao', DESCENDING),
                ('status', ASCENDING),
                ('score_similaridade', DESCENDING),
                ([('numero_processo_limpo', ASCENDING), ('data_publicacao', DESCENDING)], 'processo_data_limpo'),
                ([('status', ASCENDING), ('score_similaridade', DESCENDING)], 'status_score'),
                ('classificacao.tipo', ASCENDING),
                ('classificacao.urgente', ASCENDING),
                ('camunda_instance_id', ASCENDING),
                ('texto_limpo', TEXT)  # Índice de texto para busca
            ],
            'hashes': [
                ('hash_value', ASCENDING, {'unique': True}),
                ('publicacao_prata_id', ASCENDING),
                ('numero_processo', ASCENDING),
                ('timestamp_criacao', DESCENDING),
                ([('numero_processo', ASCENDING), ('hash_value', ASCENDING)], 'processo_hash')
            ]
        }
        
        for collection_name, collection_indexes in indexes.items():
            collection = self.db[collection_name]
            
            for index_config in collection_indexes:
                try:
                    if isinstance(index_config, tuple):
                        # Índice com configurações especiais
                        if len(index_config) == 2:
                            field, direction = index_config
                            options = {}
                            # Converte direção para string legível
                            dir_str = 'asc' if direction == ASCENDING else 'desc' if direction == DESCENDING else 'text'
                            index_name = f"{field}_{dir_str}"
                        elif len(index_config) == 3:
                            field, direction, options = index_config
                            if isinstance(field, list):
                                # Índice composto
                                index_name = options if isinstance(options, str) else '_'.join([f[0] for f in field])
                                collection.create_index(field, name=index_name)
                                logger.info(f"✅ Índice composto '{index_name}' criado em '{collection_name}'")
                                continue
                            else:
                                # Converte direção para string legível
                                dir_str = 'asc' if direction == ASCENDING else 'desc' if direction == DESCENDING else 'text'
                                index_name = f"{field}_{dir_str}"
                        
                        # Cria índice simples com opções
                        if direction == TEXT:
                            collection.create_index([(str(field), TEXT)], name=f"{field}_text")
                            logger.info(f"✅ Índice de texto '{field}_text' criado em '{collection_name}'")
                        else:
                            collection.create_index([(str(field), direction)], name=index_name, **options)
                            logger.info(f"✅ Índice '{index_name}' criado em '{collection_name}'")
                    
                except OperationFailure as e:
                    if "already exists" in str(e):
                        logger.info(f"ℹ️ Índice já existe em '{collection_name}'")
                    else:
                        logger.error(f"❌ Erro ao criar índice em '{collection_name}': {e}")
                        
    def create_sample_data(self):
        """Cria dados de exemplo para testes"""
        try:
            # Cria execução de exemplo
            execucao = self.db.execucoes.insert_one({
                'data_inicio': datetime.now(),
                'data_fim': None,
                'status': 'running',
                'total_encontradas': 0,
                'total_processadas': 0,
                'configuracao': {
                    'cod_grupo': 5,
                    'limite_publicacoes': 50
                }
            })
            
            # Cria lote de exemplo
            lote = self.db.lotes.insert_one({
                'execucao_id': execucao.inserted_id,
                'timestamp_criacao': datetime.now(),
                'total_publicacoes': 1,
                'cod_grupo': 5,
                'status': 'pendente'
            })
            
            # Cria publicação bronze de exemplo
            publicacao_bronze = self.db.publicacoes_bronze.insert_one({
                'lote_id': lote.inserted_id,
                'cod_publicacao': 12345,
                'numero_processo': '0001234-56.2024.8.13.0000',
                'data_publicacao': '15/01/2024',
                'texto_publicacao': 'SENTENÇA. Processo julgado procedente.',
                'fonte': 'dw',
                'tribunal': 'tjmg',
                'instancia': '1',
                'descricao_diario': 'Diário Oficial TJMG',
                'uf_publicacao': 'MG',
                'timestamp_insercao': datetime.now(),
                'status': 'nova'
            })
            
            logger.info("✅ Dados de exemplo criados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar dados de exemplo: {e}")
    
    def initialize(self, create_sample: bool = False):
        """
        Executa inicialização completa
        
        Args:
            create_sample: Se deve criar dados de exemplo
        """
        try:
            logger.info("🚀 Iniciando configuração do MongoDB para publicações...")
            
            # Conecta ao MongoDB
            self.connect()
            
            # Cria coleções
            logger.info("\n📦 Criando coleções...")
            self.create_collections()
            
            # Cria índices
            logger.info("\n🔍 Criando índices...")
            self.create_indexes()
            
            # Cria dados de exemplo se solicitado
            if create_sample:
                logger.info("\n📝 Criando dados de exemplo...")
                self.create_sample_data()
            
            # Lista estatísticas
            logger.info("\n📊 Estatísticas do banco de dados:")
            for collection_name in self.db.list_collection_names():
                count = self.db[collection_name].count_documents({})
                logger.info(f"  • {collection_name}: {count} documentos")
            
            logger.info("\n✅ Inicialização concluída com sucesso!")
            
        except Exception as e:
            logger.error(f"\n❌ Erro durante inicialização: {e}")
            raise
        
        finally:
            if self.client:
                self.client.close()
                logger.info("🔌 Conexão MongoDB fechada")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Inicializa MongoDB para fluxo de publicações')
    parser.add_argument(
        '--connection-string',
        help='String de conexão MongoDB',
        default=os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    )
    parser.add_argument(
        '--database',
        help='Nome do banco de dados',
        default='camunda_publicacoes'
    )
    parser.add_argument(
        '--sample-data',
        action='store_true',
        help='Criar dados de exemplo'
    )
    
    args = parser.parse_args()
    
    # Executa inicialização
    initializer = MongoDBPublicacoesInitializer(
        connection_string=args.connection_string,
        database_name=args.database
    )
    
    initializer.initialize(create_sample=args.sample_data)


if __name__ == '__main__':
    main()