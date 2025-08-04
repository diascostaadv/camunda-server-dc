"""
Testes para o gerador de hash
"""

import pytest
from services.hash_generator import HashGenerator, gerar_hash_unica


class TestHashGenerator:
    """Testes para o gerador de hash única para movimentações judiciais"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.generator = HashGenerator()
    
    def test_gerar_hash_basica(self):
        """Teste básico de geração de hash"""
        hash_result = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",
            tribunal="tjmg"
        )
        
        # Hash SHA256 deve ter 64 caracteres hexadecimais
        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result.lower())
        
    def test_hash_deterministica(self):
        """Teste se a mesma entrada produz a mesma hash"""
        hash1 = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024", 
            texto_original="Audiência marcada",
            tribunal="tjmg"
        )
        
        hash2 = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada", 
            tribunal="tjmg"
        )
        
        assert hash1 == hash2
        
    def test_hash_diferentes_entradas(self):
        """Teste se entradas diferentes produzem hashes diferentes"""
        hash1 = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",
            tribunal="tjmg"
        )
        
        hash2 = self.generator.gerar_hash_unica(
            numero_processo="123457",  # Número diferente
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",
            tribunal="tjmg"
        )
        
        assert hash1 != hash2
        
    def test_hash_normalizacao(self):
        """Teste se a normalização funciona (maiúsculas/minúsculas, espaços)"""
        hash1 = self.generator.gerar_hash_unica(
            numero_processo=" 123456 ",  # Com espaços
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",
            tribunal=" TJMG "  # Maiúsculo com espaços
        )
        
        hash2 = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",
            tribunal="tjmg"  # Minúsculo sem espaços
        )
        
        assert hash1 == hash2
        
    def test_campos_obrigatorios_vazios(self):
        """Teste com campos obrigatórios vazios"""
        with pytest.raises(ValueError, match="Número do processo é obrigatório"):
            self.generator.gerar_hash_unica("", "15/03/2024", "texto", "tjmg")
            
        with pytest.raises(ValueError, match="Data de publicação é obrigatória"):
            self.generator.gerar_hash_unica("123456", "", "texto", "tjmg")
            
        with pytest.raises(ValueError, match="Texto original é obrigatório"):
            self.generator.gerar_hash_unica("123456", "15/03/2024", "", "tjmg")
            
        with pytest.raises(ValueError, match="Tribunal é obrigatório"):
            self.generator.gerar_hash_unica("123456", "15/03/2024", "texto", "")
            
    def test_campos_apenas_espacos(self):
        """Teste com campos contendo apenas espaços"""
        with pytest.raises(ValueError, match="Número do processo é obrigatório"):
            self.generator.gerar_hash_unica("   ", "15/03/2024", "texto", "tjmg")
            
    def test_funcao_conveniencia(self):
        """Teste da função de conveniência"""
        hash_result = gerar_hash_unica("123456", "15/03/2024", "texto", "tjmg")
        assert len(hash_result) == 64
        
    def test_verificar_hash_existente(self):
        """Teste de verificação de hash existente"""
        hash_test = "abcd1234"
        hashes_existentes = ["hash1", "hash2", "abcd1234", "hash3"]
        
        assert self.generator.verificar_hash_existente(hash_test, hashes_existentes) is True
        assert self.generator.verificar_hash_existente("inexistente", hashes_existentes) is False
        assert self.generator.verificar_hash_existente("", hashes_existentes) is False
        assert self.generator.verificar_hash_existente(hash_test, []) is False
        
    def test_gerar_hash_alternativa(self):
        """Teste de geração de hash alternativa com texto limpo"""
        hash_alternativa = self.generator.gerar_hash_alternativa(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_limpo="audiencia marcada",  # Texto já limpo
            tribunal="tjmg"
        )
        
        # Deve ser diferente da hash principal
        hash_principal = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_original="Audiência marcada",  # Texto original
            tribunal="tjmg"
        )
        
        assert hash_alternativa != hash_principal
        assert len(hash_alternativa) == 64
        
    def test_obter_informacoes_hash(self):
        """Teste de obtenção de informações sobre hash"""
        hash_valida = self.generator.gerar_hash_unica("123", "01/01/2024", "teste", "tj")
        informacoes = self.generator.obter_informacoes_hash(hash_valida)
        
        assert informacoes['hash'] == hash_valida
        assert informacoes['algoritmo'] == 'sha256'
        assert informacoes['tamanho'] == 64
        assert informacoes['eh_valida'] is True
        assert informacoes['tipo'] == 'sha256'
        assert len(informacoes['prefixo']) == 8
        assert len(informacoes['sufixo']) == 8
        
    def test_validar_hash_format(self):
        """Teste de validação de formato de hash"""
        # Hash válida
        hash_valida = "a" * 64  # 64 caracteres 'a'
        assert self.generator._validar_hash_format(hash_valida) is True
        
        # Hash inválida - tamanho errado
        assert self.generator._validar_hash_format("abc123") is False
        
        # Hash inválida - caracteres não hex
        hash_invalida = "g" * 64  # 'g' não é hexadecimal
        assert self.generator._validar_hash_format(hash_invalida) is False
        
        # Hash vazia
        assert self.generator._validar_hash_format("") is False
        assert self.generator._validar_hash_format(None) is False
        
    def test_comparar_hashes(self):
        """Teste de comparação entre hashes"""
        hash1 = "a" * 64
        hash2 = "a" * 64
        hash3 = "b" * 64
        
        # Hashes iguais
        resultado = self.generator.comparar_hashes(hash1, hash2)
        assert resultado['sao_iguais'] is True
        assert resultado['hash1_valida'] is True
        assert resultado['hash2_valida'] is True
        assert resultado['diferenca_caracteres'] == 0
        assert resultado['prefixos_iguais'] is True
        assert resultado['sufixos_iguais'] is True
        
        # Hashes diferentes
        resultado = self.generator.comparar_hashes(hash1, hash3)
        assert resultado['sao_iguais'] is False
        assert resultado['diferenca_caracteres'] == 64
        assert resultado['prefixos_iguais'] is False
        assert resultado['sufixos_iguais'] is False
        
    def test_gerar_hash_rapida(self):
        """Teste de geração de hash rápida (MD5)"""
        hash_rapida = self.generator.gerar_hash_rapida("texto teste")
        
        # MD5 tem 32 caracteres hexadecimais
        assert len(hash_rapida) == 32
        assert all(c in '0123456789abcdef' for c in hash_rapida.lower())
        
    def test_hash_com_caracteres_especiais(self):
        """Teste com texto contendo caracteres especiais"""
        hash_result = self.generator.gerar_hash_unica(
            numero_processo="123.456.789-00",
            data_publicacao="15/03/2024",
            texto_original="Processo nº 123 - R$ 1.500,00 (quinze mil)",
            tribunal="tjmg"
        )
        
        # Deve gerar hash normalmente
        assert len(hash_result) == 64
        
    def test_texto_muito_longo(self):
        """Teste com texto muito longo"""
        texto_longo = "Este é um texto muito longo " * 1000  # ~29,000 caracteres
        
        hash_result = self.generator.gerar_hash_unica(
            numero_processo="123456",
            data_publicacao="15/03/2024", 
            texto_original=texto_longo,
            tribunal="tjmg"
        )
        
        # Deve processar normalmente independente do tamanho
        assert len(hash_result) == 64