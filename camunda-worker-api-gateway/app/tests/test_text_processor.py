"""
Testes para o processador de texto
"""

import pytest
from services.text_processor import TextProcessor, limpar_texto_publicacao


class TestTextProcessor:
    """Testes para o processador de texto de movimentações judiciais"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.processor = TextProcessor()
    
    def test_limpar_texto_basico(self):
        """Teste básico de limpeza de texto"""
        texto_original = "Audiência marcada para às 14h00min no FÓRUM Central."
        texto_limpo = self.processor.limpar_texto_publicacao(texto_original)
        
        # Deve remover acentos e converter para minúsculas
        assert "audiencia" in texto_limpo
        assert "forum" in texto_limpo
        assert "às" not in texto_limpo
        assert "14h00min" in texto_limpo
        
    def test_remover_caracteres_especiais(self):
        """Teste de remoção de caracteres especiais"""
        texto_original = "Processo nº 123.456.789-00 - R$ 1.500,00 (valor)"
        texto_limpo = self.processor.limpar_texto_publicacao(texto_original)
        
        # Não deve conter caracteres especiais
        assert "." not in texto_limpo
        assert "-" not in texto_limpo
        assert "$" not in texto_limpo
        assert "," not in texto_limpo
        assert "(" not in texto_limpo
        assert ")" not in texto_limpo
        
        # Deve manter números e letras
        assert "123456789" in texto_limpo
        assert "1500" in texto_limpo
        assert "processo" in texto_limpo
        
    def test_normalizar_espacos(self):
        """Teste de normalização de espaços"""
        texto_original = "Texto    com     múltiplos\n\nespaços\t\te quebras"
        texto_limpo = self.processor.limpar_texto_publicacao(texto_original)
        
        # Não deve ter múltiplos espaços ou quebras de linha
        assert "    " not in texto_limpo
        assert "\n" not in texto_limpo
        assert "\t" not in texto_limpo
        
        # Deve ter apenas espaços simples
        palavras = texto_limpo.split()
        assert len(palavras) == 6  # "texto com multiplos espacos e quebras"
        
    def test_texto_vazio_erro(self):
        """Teste com texto vazio deve gerar erro"""
        with pytest.raises(ValueError, match="Texto original não pode estar vazio"):
            self.processor.limpar_texto_publicacao("")
            
        with pytest.raises(ValueError, match="Texto original não pode estar vazio"):
            self.processor.limpar_texto_publicacao(None)
            
    def test_texto_apenas_espacos(self):
        """Teste com texto apenas espaços deve gerar erro"""
        with pytest.raises(ValueError, match="Texto resultou vazio após limpeza"):
            self.processor.limpar_texto_publicacao("   \n\t   ")
            
    def test_funcao_conveniencia(self):
        """Teste da função de conveniência"""
        texto_original = "Função de CONVENIÊNCIA com acentuação"
        texto_limpo = limpar_texto_publicacao(texto_original)
        
        assert "funcao" in texto_limpo
        assert "conveniencia" in texto_limpo
        assert "acentuacao" in texto_limpo
        
    def test_extrair_informacoes_basicas(self):
        """Teste de extração de informações do texto"""
        texto_original = "Processo 123-ABC com números e símbolos!"
        informacoes = self.processor.extrair_informacoes_basicas(texto_original)
        
        assert informacoes['tamanho_original'] > 0
        assert informacoes['tamanho_limpo'] > 0
        assert informacoes['palavras'] == 6
        assert informacoes['tem_numeros'] is True
        assert informacoes['tem_caracteres_especiais'] is True
        assert informacoes['reducao_tamanho'] >= 0
        
    def test_validar_texto_limpo(self):
        """Teste de validação do texto limpo"""
        texto_original = "Texto original válido"
        texto_limpo = self.processor.limpar_texto_publicacao(texto_original)
        validacao = self.processor.validar_texto_limpo(texto_limpo, texto_original)
        
        assert validacao['is_valid'] is True
        assert len(validacao['errors']) == 0
        
    def test_validar_texto_limpo_invalido(self):
        """Teste de validação com texto inválido"""
        validacao = self.processor.validar_texto_limpo("", "texto original")
        
        assert validacao['is_valid'] is False
        assert "Texto ficou vazio após limpeza" in validacao['errors'][0]
        
    def test_texto_complexo_judicial(self):
        """Teste com texto complexo típico de movimentação judicial"""
        texto_original = """
        INTIMAÇÃO - Processo nº 5002020-12.2023.8.13.0024
        Fica V. Sa. intimada para, no prazo de 15 (quinze) dias,
        apresentar manifestação sobre os documentos juntados aos autos,
        sob pena de preclusão. Belo Horizonte, 15 de março de 2024.
        """
        
        texto_limpo = self.processor.limpar_texto_publicacao(texto_original)
        
        # Verificações gerais
        assert len(texto_limpo) > 0
        assert texto_limpo.islower()  # Deve estar em minúsculas
        assert "intimacao" in texto_limpo
        assert "processo" in texto_limpo
        assert "belo horizonte" in texto_limpo
        
        # Não deve conter quebras de linha ou caracteres especiais
        assert "\n" not in texto_limpo
        assert "." not in texto_limpo
        assert "," not in texto_limpo
        
        # Deve conter números
        assert "5002020" in texto_limpo
        assert "15" in texto_limpo
        assert "2024" in texto_limpo