"""
Testes para o processador de datas
"""

import pytest
from datetime import datetime
from services.date_processor import DateProcessor, converter_data_publicacao


class TestDateProcessor:
    """Testes para o processador de datas de movimentações judiciais"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.processor = DateProcessor()
    
    def test_converter_data_valida(self):
        """Teste de conversão de data válida"""
        data_str = "15/03/2024"
        data_convertida = self.processor.converter_data_publicacao(data_str)
        
        assert isinstance(data_convertida, datetime)
        assert data_convertida.day == 15
        assert data_convertida.month == 3
        assert data_convertida.year == 2024
        
    def test_converter_data_formatos_alternativos(self):
        """Teste com formatos alternativos de data"""
        # Formato com traço
        data1 = self.processor.converter_data_publicacao("15-03-2024")
        assert data1.day == 15 and data1.month == 3 and data1.year == 2024
        
        # Formato com ponto
        data2 = self.processor.converter_data_publicacao("15.03.2024")
        assert data2.day == 15 and data2.month == 3 and data2.year == 2024
        
    def test_data_invalida_formato(self):
        """Teste com formato de data inválido"""
        with pytest.raises(ValueError, match="Formato de data inválido"):
            self.processor.converter_data_publicacao("2024/03/15")  # Formato americano
            
        with pytest.raises(ValueError, match="Formato de data inválido"):
            self.processor.converter_data_publicacao("15/03/24")  # Ano com 2 dígitos
            
        with pytest.raises(ValueError, match="Formato de data inválido"):
            self.processor.converter_data_publicacao("texto_invalido")
            
    def test_data_vazia(self):
        """Teste com data vazia"""
        with pytest.raises(ValueError, match="Data não pode estar vazia"):
            self.processor.converter_data_publicacao("")
            
        with pytest.raises(ValueError, match="Data não pode estar vazia"):
            self.processor.converter_data_publicacao(None)
            
    def test_data_muito_antiga(self):
        """Teste com data muito antiga"""
        with pytest.raises(ValueError, match="Ano muito antigo"):
            self.processor.converter_data_publicacao("15/03/1800")
            
    def test_data_muito_futura(self):
        """Teste com data muito no futuro"""
        ano_futuro = datetime.now().year + 5
        with pytest.raises(ValueError, match="Ano muito recente"):
            self.processor.converter_data_publicacao(f"15/03/{ano_futuro}")
            
    def test_data_invalida_valores(self):
        """Teste com valores inválidos de data"""
        with pytest.raises(ValueError):
            self.processor.converter_data_publicacao("32/03/2024")  # Dia inválido
            
        with pytest.raises(ValueError):
            self.processor.converter_data_publicacao("15/13/2024")  # Mês inválido
            
        with pytest.raises(ValueError):
            self.processor.converter_data_publicacao("29/02/2023")  # 29 de fev em ano não bissexto
            
    def test_ano_bissexto(self):
        """Teste com ano bissexto"""
        data = self.processor.converter_data_publicacao("29/02/2024")
        assert data.day == 29 and data.month == 2 and data.year == 2024
        
        # Verifica função auxiliar
        assert self.processor._eh_ano_bissexto(2024) is True
        assert self.processor._eh_ano_bissexto(2023) is False
        
    def test_funcao_conveniencia(self):
        """Teste da função de conveniência"""
        data_convertida = converter_data_publicacao("01/01/2024")
        assert isinstance(data_convertida, datetime)
        assert data_convertida.day == 1
        assert data_convertida.month == 1
        assert data_convertida.year == 2024
        
    def test_formatar_data_display(self):
        """Teste de formatação para exibição"""
        data = datetime(2024, 3, 15)
        formatada = self.processor.formatar_data_para_display(data)
        assert formatada == "15/03/2024"
        
        # Formato customizado
        formatada_custom = self.processor.formatar_data_para_display(data, "%d-%m-%Y")
        assert formatada_custom == "15-03-2024"
        
    def test_obter_informacoes_data(self):
        """Teste de obtenção de informações da data"""
        informacoes = self.processor.obter_informacoes_data("15/03/2024")
        
        assert informacoes['data_original'] == "15/03/2024"
        assert informacoes['ano'] == 2024
        assert informacoes['mes'] == 3
        assert informacoes['dia'] == 15
        assert informacoes['trimestre'] == 1
        assert 'eh_passado' in informacoes
        assert 'eh_futuro' in informacoes
        assert 'dias_desde_hoje' in informacoes
        
    def test_obter_informacoes_data_invalida(self):
        """Teste de informações com data inválida"""
        informacoes = self.processor.obter_informacoes_data("data_invalida")
        
        assert informacoes['data_original'] == "data_invalida"
        assert 'erro' in informacoes
        assert informacoes['valida'] is False
        
    def test_validar_formato_data(self):
        """Teste de validação de formato"""
        # Data válida
        validacao = self.processor.validar_formato_data("15/03/2024")
        assert validacao['is_valid'] is True
        assert validacao['formato_detectado'] == "%d/%m/%Y"
        
        # Data inválida
        validacao_invalida = self.processor.validar_formato_data("2024-03-15")
        assert validacao_invalida['is_valid'] is False
        
    def test_converter_iso(self):
        """Teste de conversão para formato ISO"""
        iso_date = self.processor.converter_para_iso("15/03/2024")
        assert iso_date == "2024-03-15"
        
    def test_extrair_componentes(self):
        """Teste de extração de componentes da data"""
        dia, mes, ano = self.processor.extrair_componentes_data("15/03/2024")
        assert dia == 15
        assert mes == 3
        assert ano == 2024
        
    def test_datas_limite_validas(self):
        """Teste com datas nos limites válidos"""
        # Data mínima válida
        data_min = self.processor.converter_data_publicacao("01/01/1900")
        assert data_min.year == 1900
        
        # Data próxima ao limite futuro
        ano_atual = datetime.now().year
        data_atual = self.processor.converter_data_publicacao(f"01/01/{ano_atual}")
        assert data_atual.year == ano_atual