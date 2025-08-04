"""
Testes para o modelo de movimentação judicial
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from models.movimentacao import MovimentacaoJudicial, MovimentacaoProcessingResult


class TestMovimentacaoJudicial:
    """Testes para o modelo MovimentacaoJudicial"""
    
    def test_modelo_valido_completo(self):
        """Teste com modelo válido completo"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_publicacao="Audiência marcada para as 14h",
            fonte="dw",
            tribunal="tjmg",
            instancia="1"
        )
        
        assert movimentacao.numero_processo == "123456"
        assert movimentacao.data_publicacao == "15/03/2024"
        assert movimentacao.fonte == "dw"
        assert movimentacao.tribunal == "tjmg"
        assert movimentacao.instancia == "1"
        assert movimentacao.status_processamento == "pending"
        
    def test_validacao_fonte_valida(self):
        """Teste de validação de fonte válida"""
        # Todas as fontes válidas
        for fonte in ["dw", "manual", "escavador"]:
            movimentacao = MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/03/2024",
                texto_publicacao="Teste",
                fonte=fonte,
                tribunal="tjmg",
                instancia="1"
            )
            assert movimentacao.fonte == fonte
            
    def test_validacao_fonte_invalida(self):
        """Teste de validação de fonte inválida"""
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/03/2024",
                texto_publicacao="Teste",
                fonte="fonte_invalida",
                tribunal="tjmg",
                instancia="1"
            )
        
        assert "Fonte deve ser 'dw', 'manual' ou 'escavador'" in str(exc_info.value)
        
    def test_validacao_data_formato_valido(self):
        """Teste de validação de formato de data válido"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="31/12/2023",
            texto_publicacao="Teste",
            fonte="dw",
            tribunal="tjmg",
            instancia="1"
        )
        assert movimentacao.data_publicacao == "31/12/2023"
        
    def test_validacao_data_formato_invalido(self):
        """Teste de validação de formato de data inválido"""
        # Formato incorreto
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="2024-03-15",  # Formato ISO
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
        assert "Data deve estar no formato dd/mm/yyyy" in str(exc_info.value)
        
        # Data muito curta
        with pytest.raises(ValidationError):
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/3/24",
                texto_publicacao="Teste", 
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
            
    def test_validacao_data_valores_invalidos(self):
        """Teste de validação de valores de data inválidos"""
        # Dia inválido
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="32/03/2024",
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
        assert "Dia deve estar entre 1 e 31" in str(exc_info.value)
        
        # Mês inválido  
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/13/2024",
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
        assert "Mês deve estar entre 1 e 12" in str(exc_info.value)
        
        # Ano inválido
        with pytest.raises(ValidationError):
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/03/1800",
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
            
    def test_validacao_instancia_numerica(self):
        """Teste de validação de instância numérica"""
        # Instância válida
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_publicacao="Teste",
            fonte="dw",
            tribunal="tjmg",
            instancia="2"
        )
        assert movimentacao.instancia == "2"
        
        # Instância inválida (não numérica)
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/03/2024",
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="primeira"
            )
        assert "Instância deve ser numérica" in str(exc_info.value)
        
    def test_validacao_campos_obrigatorios_vazios(self):
        """Teste de validação de campos obrigatórios vazios"""
        # Número do processo vazio
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="",
                data_publicacao="15/03/2024",
                texto_publicacao="Teste",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
        assert "Número do processo é obrigatório" in str(exc_info.value)
        
        # Texto vazio
        with pytest.raises(ValidationError) as exc_info:
            MovimentacaoJudicial(
                numero_processo="123456",
                data_publicacao="15/03/2024",
                texto_publicacao="",
                fonte="dw",
                tribunal="tjmg",
                instancia="1"
            )
        assert "Texto da publicação é obrigatório" in str(exc_info.value)
        
    def test_campos_processados_opcionais(self):
        """Teste de campos processados opcionais"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_publicacao="Teste",
            fonte="dw",
            tribunal="tjmg",
            instancia="1",
            # Campos processados
            texto_publicacao_limpo="teste",
            data_publicacao_parsed=datetime(2024, 3, 15),
            hash_unica="abcd1234",
            timestamp_processamento=datetime.now(),
            status_processamento="step_1_complete"
        )
        
        assert movimentacao.texto_publicacao_limpo == "teste"
        assert movimentacao.data_publicacao_parsed.year == 2024
        assert movimentacao.hash_unica == "abcd1234"
        assert movimentacao.status_processamento == "step_1_complete"
        
    def test_to_dict(self):
        """Teste de conversão para dicionário"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_publicacao="Teste",
            fonte="dw",
            tribunal="tjmg",
            instancia="1"
        )
        
        dict_result = movimentacao.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result['numero_processo'] == "123456"
        assert dict_result['fonte'] == "dw"
        assert 'metadata' in dict_result
        
    def test_from_dict(self):
        """Teste de criação a partir de dicionário"""
        data = {
            "numero_processo": "123456",
            "data_publicacao": "15/03/2024",
            "texto_publicacao": "Teste",
            "fonte": "dw",
            "tribunal": "tjmg",
            "instancia": "1"
        }
        
        movimentacao = MovimentacaoJudicial.from_dict(data)
        
        assert movimentacao.numero_processo == "123456"
        assert movimentacao.fonte == "dw"
        
    def test_normalizacao_espacos(self):
        """Teste de normalização de espaços nos campos"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="  123456  ",  # Com espaços
            data_publicacao="15/03/2024",
            texto_publicacao="  Teste com espaços  ",
            fonte="dw",
            tribunal="tjmg",
            instancia="1"
        )
        
        # Deve remover espaços extras
        assert movimentacao.numero_processo == "123456"
        assert movimentacao.texto_publicacao == "Teste com espaços"


class TestMovimentacaoProcessingResult:
    """Testes para o resultado de processamento"""
    
    def test_resultado_processamento_basico(self):
        """Teste básico do resultado de processamento"""
        result = MovimentacaoProcessingResult(success=True)
        
        assert result.success is True
        assert result.movimentacao is None
        assert result.error_message is None
        assert len(result.processing_steps) == 0
        
    def test_adicionar_passos(self):
        """Teste de adição de passos de processamento"""
        result = MovimentacaoProcessingResult(success=False)
        
        result.add_step("Iniciando processamento")
        result.add_step("Validando dados")
        result.add_step("Processamento concluído")
        
        assert len(result.processing_steps) == 3
        assert "Iniciando processamento" in result.processing_steps[0]
        assert "Validando dados" in result.processing_steps[1]
        assert "Processamento concluído" in result.processing_steps[2]
        
        # Verifica se tem timestamp
        for step in result.processing_steps:
            assert ":" in step  # timestamp + ":" + message
            
    def test_resultado_com_movimentacao(self):
        """Teste de resultado com movimentação"""
        movimentacao = MovimentacaoJudicial(
            numero_processo="123456",
            data_publicacao="15/03/2024",
            texto_publicacao="Teste",
            fonte="dw",
            tribunal="tjmg",
            instancia="1"
        )
        
        result = MovimentacaoProcessingResult(
            success=True,
            movimentacao=movimentacao
        )
        
        assert result.success is True
        assert result.movimentacao is not None
        assert result.movimentacao.numero_processo == "123456"
        
    def test_resultado_com_erro(self):
        """Teste de resultado com erro"""
        result = MovimentacaoProcessingResult(
            success=False,
            error_message="Erro no processamento"
        )
        
        assert result.success is False
        assert result.error_message == "Erro no processamento"