"""
Intimation Service - Cliente SOAP consolidado para API de Intimações
Serviço centralizado para integração com WebService de Intimações no Gateway
"""

import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import List, Dict, Optional, Any

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class Publicacao:
    """Representa uma publicação/intimação da API"""

    ano_publicacao: int = 0
    cod_publicacao: int = 0
    edicao_diario: int = 0
    descricao_diario: str = ""
    pagina_inicial: int = 0
    pagina_final: int = 0
    data_publicacao: str = ""
    data_divulgacao: str = ""
    data_cadastro: str = ""
    numero_processo: str = ""
    uf_publicacao: str = ""
    cidade_publicacao: str = ""
    orgao_descricao: str = ""
    vara_descricao: str = ""
    despacho_publicacao: str = ""
    processo_publicacao: str = ""
    publicacao_corrigida: int = 0
    cod_vinculo: int = 0
    nome_vinculo: str = ""
    oab_numero: int = 0
    oab_estado: str = ""
    diario_sigla_wj: str = ""
    anexo: str = ""
    cod_integracao: str = ""
    publicacao_exportada: int = 0
    cod_grupo: int = 0

    def to_json(self) -> str:
        """Converte a publicação para JSON"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a publicação para dicionário"""
        return asdict(self)

    @property
    def texto_publicacao(self) -> str:
        """Obtém o texto da publicação com fallbacks"""
        return (
            self.despacho_publicacao
            or self.processo_publicacao
            or f"Publicação código {self.cod_publicacao}"
        )


@dataclass
class EstatisticasPublicacoes:
    """Representa estatísticas de publicações"""

    grupo: str = ""
    total_publicacoes: int = 0
    total_nao_importadas: int = 0
    detalhamento: Optional[List["EstatisticasPublicacoes"]] = None

    def to_json(self) -> str:
        """Converte estatísticas para JSON"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Converte estatísticas para dicionário"""
        return asdict(self)


class IntimationServiceError(Exception):
    """Exceção customizada para erros do IntimationService"""

    pass


class IntimationService:
    """
    Serviço consolidado para integração com WebService de Intimações

    Combina as melhores funcionalidades dos clientes existentes em um serviço
    único, robusto e bem testado para uso no Gateway.
    """

    DEFAULT_URL = "https://intimation-panel.azurewebsites.net/wsPublicacao.asmx"

    def __init__(self, usuario: str = None, senha: str = None, **kwargs):
        """
        Inicializa o serviço de intimações

        Args:
            usuario: Usuário para autenticação (ou usa env SOAP_USUARIO)
            senha: Senha para autenticação (ou usa env SOAP_SENHA)
            **kwargs: Configurações opcionais:
                - base_url: URL do webservice
                - timeout: Timeout em segundos (90)
                - max_retries: Máximo de tentativas (3)
        """
        # Configuração com fallback para variáveis de ambiente
        self.usuario = usuario or os.getenv("SOAP_USUARIO", "100049")
        self.senha = senha or os.getenv("SOAP_SENHA", "DcDpW@24")

        self.base_url = kwargs.get(
            "base_url", os.getenv("SOAP_URL", self.DEFAULT_URL)
        ).rstrip("/")
        self.timeout = kwargs.get("timeout", int(os.getenv("SOAP_TIMEOUT", "90")))
        self.max_retries = kwargs.get(
            "max_retries", int(os.getenv("SOAP_MAX_RETRIES", "1"))
        )

        self.session = self._create_session()

        logger.info(
            "IntimationService inicializado - URL: %s, Timeout: %ds, Retries: %d",
            self.base_url,
            self.timeout,
            self.max_retries,
        )

    def _create_session(self) -> requests.Session:
        """Cria uma sessão HTTP com configurações de retry e timeout"""
        session = requests.Session()

        # Desabilitar retry automático do urllib3 para ter melhor controle manual
        # O retry será feito manualmente no método _make_request com melhor logging
        try:
            # Versão mais nova (urllib3 >= 1.26.0)
            retry_strategy = Retry(
                total=0,  # Desabilita retry automático
                read=0,  # Não retentar ReadTimeoutError
                connect=0,  # Não retentar ConnectionError
                status_forcelist=[],  # Não retentar nenhum status HTTP
                backoff_factor=0,
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            )
        except TypeError:
            # Fallback para versão mais antiga (urllib3 < 1.26.0)
            retry_strategy = Retry(
                total=0,
                read=0,
                connect=0,
                status_forcelist=[],
                backoff_factor=0,
                method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
            )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers padrão
        session.headers.update(
            {
                "User-Agent": "IntimationService/1.0",
                "Accept": "text/xml, application/xml",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

        return session

    def _make_request(self, method: str, params: Dict[str, Any]) -> ET.Element:
        """
        Faz uma requisição SOAP para a API com retry automático

        Args:
            method: Nome do método a ser chamado
            params: Parâmetros da requisição

        Returns:
            Elemento XML da resposta

        Raises:
            IntimationServiceError: Em caso de erro na requisição
        """
        # Adiciona credenciais aos parâmetros
        params.update({"strUsuario": self.usuario, "strSenha": self.senha})

        # Monta envelope SOAP
        soap_body = self._build_soap_envelope(method, params)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"http://tempuri.org/{method}"',
        }

        last_exception = None

        for tentativa in range(self.max_retries + 1):
            try:
                if tentativa > 0:
                    wait_time = 2**tentativa  # Backoff exponencial
                    logger.info(
                        "Tentativa %d/%d para %s. Aguardando %ds...",
                        tentativa + 1,
                        self.max_retries + 1,
                        method,
                        wait_time,
                    )
                    time.sleep(wait_time)

                logger.debug(
                    "Fazendo requisição para %s (tentativa %d)", method, tentativa + 1
                )

                response = self.session.post(
                    self.base_url, data=soap_body, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()

                logger.debug(
                    "Requisição %s bem-sucedida após %d tentativa(s)",
                    method,
                    tentativa + 1,
                )
                return self._parse_soap_response(response.text)

            except requests.exceptions.Timeout as exc:
                last_exception = exc
                logger.warning(
                    "Timeout na tentativa %d para %s: %s", tentativa + 1, method, exc
                )
                if tentativa == self.max_retries:
                    break

            except requests.exceptions.ConnectionError as exc:
                last_exception = exc
                logger.warning(
                    "Erro de conexão na tentativa %d para %s: %s",
                    tentativa + 1,
                    method,
                    exc,
                )
                if tentativa == self.max_retries:
                    break

            except requests.exceptions.HTTPError as exc:
                last_exception = exc
                logger.error(
                    "Erro HTTP na tentativa %d para %s: %s", tentativa + 1, method, exc
                )
                # Para erros HTTP 4xx, não tenta novamente
                if 400 <= exc.response.status_code < 500:
                    break
                if tentativa == self.max_retries:
                    break

            except requests.RequestException as exc:
                last_exception = exc
                logger.error(
                    "Erro inesperado na tentativa %d para %s: %s",
                    tentativa + 1,
                    method,
                    exc,
                )
                if tentativa == self.max_retries:
                    break

        # Se chegou aqui, todas as tentativas falharam
        logger.error(
            "Todas as %d tentativas falharam para %s", self.max_retries + 1, method
        )
        raise IntimationServiceError(
            f"Falha após {self.max_retries + 1} tentativas para {method}"
        ) from last_exception

    def _build_soap_envelope(self, method: str, params: Dict[str, Any]) -> str:
        """Constrói envelope SOAP para a requisição"""
        param_elements = ""
        for key, value in params.items():
            if value is not None:
                param_elements += f"<{key}>{value}</{key}>"

        return f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <{method} xmlns="http://tempuri.org/">
                    {param_elements}
                </{method}>
            </soap:Body>
        </soap:Envelope>"""

    def _parse_soap_response(self, response_text: str) -> ET.Element:
        """Parse da resposta SOAP retornando o elemento raiz"""
        try:
            return ET.fromstring(response_text)
        except ET.ParseError as exc:
            logger.error("Erro ao fazer parse da resposta XML: %s", exc)
            raise IntimationServiceError(f"Erro no parse XML: {exc}") from exc

    def get_publicacoes_nao_exportadas(self, cod_grupo: int = 0) -> List[Publicacao]:
        """
        Retorna intimações ainda não marcadas como exportadas

        Args:
            cod_grupo: Filtra por grupo (0 - padrão)

        Returns:
            Lista de publicações não exportadas (máximo 700)
        """
        params = {"intCodGrupo": cod_grupo}

        try:
            logger.info(
                "📤 Buscando publicações não exportadas: cod_grupo=%d", cod_grupo
            )

            response = self._make_request("getPublicacoesNaoExportadas", params)
            publicacoes = self._parse_publicacoes(response)

            logger.info(
                "📥 Obtidas %d publicações não exportadas (grupo %d)",
                len(publicacoes),
                cod_grupo,
            )

            if len(publicacoes) == 0:
                logger.warning(
                    "⚠️ NENHUMA PUBLICAÇÃO NÃO EXPORTADA encontrada para grupo=%d",
                    cod_grupo,
                )

            return publicacoes

        except Exception as exc:
            logger.error("Erro ao obter publicações não exportadas: %s", exc)
            raise IntimationServiceError(
                f"Erro ao obter publicações não exportadas: {exc}"
            ) from exc

    def get_publicacoes_nao_exportadas_v(
        self, cod_grupo: int = 0, versao: int = 5
    ) -> List[Publicacao]:
        """
        Versão com especificação de versão dos dados de retorno

        Args:
            cod_grupo: Filtra por grupo (0 - padrão)
            versao: Versão do retorno de dados

        Returns:
            Lista de publicações não exportadas (máximo 700)
        """
        params = {"intCodGrupo": cod_grupo, "numVersao": versao}

        try:
            response = self._make_request("getPublicacoesNaoExportadasV", params)
            return self._parse_publicacoes(response)
        except Exception as exc:
            raise IntimationServiceError(
                f"Erro ao obter publicações não exportadas V: {exc}"
            ) from exc

    def get_publicacoes_periodo_safe(
        self,
        data_inicial: str,
        data_final: str,
        cod_grupo: int = 0,
        timeout_override: int = None,
    ) -> List[Publicacao]:
        """
        Busca publicações por período com timeout otimizado

        Args:
            data_inicial: Data inicial no formato yyyy-mm-dd
            data_final: Data final no formato yyyy-mm-dd
            cod_grupo: Filtra por grupo (0 - padrão)
            timeout_override: Override do timeout padrão para períodos grandes

        Returns:
            Lista de publicações do período
        """
        # Para períodos grandes, aumenta o timeout
        timeout_original = None
        if timeout_override:
            timeout_original = self.timeout
            self.timeout = timeout_override
            logger.info(
                "Timeout aumentado para %ds para período %s - %s",
                timeout_override,
                data_inicial,
                data_final,
            )

        try:
            # Usa versão V para melhor compatibilidade
            # intExportada: 0=não exportadas, 1=exportadas, omitir=todas
            params = {
                "dteDataInicial": data_inicial,
                "dteDataFinal": data_final,
                "intCodGrupo": cod_grupo,
                "intExportada": 0,  # Buscar apenas publicações NÃO exportadas
                "numVersao": 5,
            }

            # Log dos parâmetros sendo enviados para debug
            logger.info(
                "📤 Parâmetros SOAP: periodo=%s a %s, cod_grupo=%d, intExportada=%d",
                data_inicial,
                data_final,
                cod_grupo,
                params.get("intExportada", -1),
            )

            response = self._make_request("getPublicacoesV", params)
            publicacoes = self._parse_publicacoes(response)

            # Log do resultado
            logger.info(
                "📥 Resultado: %d publicações encontradas no período %s - %s (grupo=%d)",
                len(publicacoes),
                data_inicial,
                data_final,
                cod_grupo,
            )

            # Log do XML bruto quando nenhuma publicação é encontrada para diagnóstico
            if len(publicacoes) == 0:
                logger.warning(
                    "⚠️ NENHUMA PUBLICAÇÃO ENCONTRADA! Parâmetros: periodo=%s a %s, cod_grupo=%d, intExportada=0",
                    data_inicial,
                    data_final,
                    cod_grupo,
                )
                try:
                    # Converte response (ET.Element) para string
                    import xml.etree.ElementTree as ET

                    xml_content = ET.tostring(response, encoding="unicode")

                    logger.warning(
                        "📄 XML Response (primeiros 1500 chars): %s...",
                        xml_content[:1500],
                    )
                except Exception as log_exc:
                    logger.warning("Erro ao logar XML: %s", log_exc)
                    logger.debug("Response type: %s", type(response))

            return publicacoes

        except Exception as exc:
            logger.error("Erro ao obter publicações por período: %s", exc)
            raise IntimationServiceError(
                f"Erro ao obter publicações por período: {exc}"
            ) from exc
        finally:
            # Restaura timeout original
            if timeout_original:
                self.timeout = timeout_original
                logger.debug("Timeout restaurado para %ds", timeout_original)

    def get_estatisticas_publicacoes(
        self, data: str, cod_grupo: int = 0, tipo_agrupamento: str = "", versao: int = 1
    ) -> EstatisticasPublicacoes:
        """
        Retorna estatísticas de publicações de uma data

        Args:
            data: Data no formato yyyy-mm-dd
            cod_grupo: Grupo de publicações
            tipo_agrupamento: Como agrupar ("", "uf", "cad")
            versao: Versão das estatísticas

        Returns:
            Estatísticas de publicações
        """
        params = {
            "dteData": data,
            "intCodGrupo": cod_grupo,
            "strTipoAgrupamento": tipo_agrupamento,
            "numVersao": versao,
        }

        try:
            response = self._make_request("getEstatisticasPublicacoes", params)
            logger.debug("Estatísticas obtidas com sucesso - params: %s", params)
            return self._parse_estatisticas(response)
        except Exception as exc:
            raise IntimationServiceError(f"Erro ao obter estatísticas: {exc}") from exc

    def set_publicacoes(self, codigos_publicacao: List[int]) -> bool:
        """
        Marca intimações como "exportadas"

        Args:
            codigos_publicacao: Lista de códigos das intimações

        Returns:
            True se sucesso, False se erro
        """
        codigos_str = "|".join(str(cod) for cod in codigos_publicacao) + "|"
        params = {"strPublicacoes": codigos_str}

        try:
            response = self._make_request("setPublicacoes", params)
            result = self._parse_boolean_response(response)

            if result:
                logger.info(
                    "Marcadas %d publicações como exportadas", len(codigos_publicacao)
                )
            else:
                logger.warning(
                    "Falha ao marcar %d publicações como exportadas",
                    len(codigos_publicacao),
                )

            return result
        except Exception as exc:
            raise IntimationServiceError(
                f"Erro ao marcar publicações como exportadas: {exc}"
            ) from exc

    def test_connection(self) -> bool:
        """
        Testa a conexão com a API usando método de estatísticas (mais leve)

        Returns:
            True se conexão OK, False caso contrário
        """
        try:
            hoje = date.today().strftime("%Y-%m-%d")

            logger.info("Testando conexão com a API...")
            self.get_estatisticas_publicacoes(hoje, cod_grupo=0)

            logger.info("✅ Conexão com API OK")
            return True

        except Exception as exc:
            logger.error("❌ Falha no teste de conexão: %s", exc)
            return False

    def _parse_publicacoes(self, root: ET.Element) -> List[Publicacao]:
        """Parse das publicações da resposta XML SOAP com namespaces"""
        publicacoes = []

        # Namespaces para busca no XML
        namespaces = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "ns": "http://tempuri.org/",
        }

        try:
            # Busca por elementos de publicação usando namespaces corretos
            publicacao_elements = root.findall(".//ns:publicacaoV2", namespaces)

            if not publicacao_elements:
                # Fallback sem namespace
                publicacao_elements = root.findall(".//publicacaoV2")

            if not publicacao_elements:
                # Busca por qualquer elemento que tenha codPublicacao como filho
                for elem in root.iter():
                    if elem.find(".//ns:codPublicacao", namespaces) is not None:
                        publicacao_elements.append(elem)
                        break

            logger.debug(
                "Encontrados %d elementos de publicação", len(publicacao_elements)
            )

            for pub_elem in publicacao_elements:
                publicacao = Publicacao(
                    ano_publicacao=self._get_int_value_ns(
                        pub_elem, "anoPublicacao", namespaces
                    ),
                    cod_publicacao=self._get_int_value_ns(
                        pub_elem, "codPublicacao", namespaces
                    ),
                    edicao_diario=self._get_int_value_ns(
                        pub_elem, "edicaoDiario", namespaces
                    ),
                    descricao_diario=self._get_text_value_ns(
                        pub_elem, "descricaoDiario", namespaces
                    ),
                    pagina_inicial=self._get_int_value_ns(
                        pub_elem, "paginaInicial", namespaces
                    ),
                    pagina_final=self._get_int_value_ns(
                        pub_elem, "paginaFinal", namespaces
                    ),
                    data_publicacao=self._get_text_value_ns(
                        pub_elem, "dataPublicacao", namespaces
                    ),
                    data_divulgacao=self._get_text_value_ns(
                        pub_elem, "dataDivulgacao", namespaces
                    ),
                    data_cadastro=self._get_text_value_ns(
                        pub_elem, "dataCadastro", namespaces
                    ),
                    numero_processo=self._get_text_value_ns(
                        pub_elem, "numeroProcesso", namespaces
                    ),
                    uf_publicacao=self._get_text_value_ns(
                        pub_elem, "ufPublicacao", namespaces
                    ),
                    cidade_publicacao=self._get_text_value_ns(
                        pub_elem, "cidadePublicacao", namespaces
                    ),
                    orgao_descricao=self._get_text_value_ns(
                        pub_elem, "orgaoDescricao", namespaces
                    ),
                    vara_descricao=self._get_text_value_ns(
                        pub_elem, "varaDescricao", namespaces
                    ),
                    despacho_publicacao=self._get_text_value_ns(
                        pub_elem, "despachoPublicacao", namespaces
                    ),
                    processo_publicacao=self._get_text_value_ns(
                        pub_elem, "processoPublicacao", namespaces
                    ),
                    publicacao_corrigida=self._get_int_value_ns(
                        pub_elem, "publicacaoCorrigida", namespaces
                    ),
                    cod_vinculo=self._get_int_value_ns(
                        pub_elem, "codVinculo", namespaces
                    ),
                    nome_vinculo=self._get_text_value_ns(
                        pub_elem, "nomeVinculo", namespaces
                    ),
                    oab_numero=self._get_int_value_ns(
                        pub_elem, "oABNumero", namespaces
                    ),
                    oab_estado=self._get_text_value_ns(
                        pub_elem, "oABEstado", namespaces
                    ),
                    diario_sigla_wj=self._get_text_value_ns(
                        pub_elem, "diarioSiglaWj", namespaces
                    ),
                    anexo=self._get_text_value_ns(pub_elem, "anexo", namespaces),
                    cod_integracao=self._get_text_value_ns(
                        pub_elem, "codIntegracao", namespaces
                    ),
                    publicacao_exportada=self._get_int_value_ns(
                        pub_elem, "publicacaoExportada", namespaces
                    ),
                    cod_grupo=self._get_int_value_ns(pub_elem, "codGrupo", namespaces),
                )
                publicacoes.append(publicacao)

            logger.info("Parsed %d publicações do XML", len(publicacoes))
            return publicacoes

        except Exception as exc:
            logger.error("Erro ao fazer parse das publicações: %s", exc)
            return []

    def _get_text_value_ns(
        self, element: ET.Element, tag_name: str, namespaces: Dict[str, str]
    ) -> str:
        """Extrai valor de texto de um elemento XML com namespaces"""
        # Tenta primeiro com namespace
        elem = element.find(f"ns:{tag_name}", namespaces)
        if elem is None:
            # Fallback sem namespace
            elem = element.find(tag_name)

        return elem.text.strip() if elem is not None and elem.text else ""

    def _get_int_value_ns(
        self, element: ET.Element, tag_name: str, namespaces: Dict[str, str]
    ) -> int:
        """Extrai valor inteiro de um elemento XML com namespaces"""
        text_value = self._get_text_value_ns(element, tag_name, namespaces)
        try:
            return int(text_value) if text_value else 0
        except ValueError:
            return 0

    def _parse_boolean_response(self, root: ET.Element) -> bool:
        """Parse de resposta booleana (0=sucesso, 1=erro)"""
        try:
            # Busca pelo elemento de resultado (diferentes possibilidades)
            for path in [".//setPublicacoesResult", ".//setPublicacoesGrupoResult"]:
                elem = root.find(path)
                if elem is not None:
                    result = elem.text.strip() if elem.text else "1"
                    return result == "0"  # 0 = sucesso, 1 = erro

            # Fallback: assume sucesso se não encontrar elemento
            logger.warning("Elemento de resultado não encontrado, assumindo sucesso")
            return True

        except Exception as exc:
            logger.error("Erro ao fazer parse da resposta booleana: %s", exc)
            return False

    def _parse_estatisticas(self, root: ET.Element) -> EstatisticasPublicacoes:
        """Parse das estatísticas da resposta XML"""
        try:
            # Busca pelo elemento de resultado das estatísticas
            stats_elem = root.find(".//getEstatisticasPublicacoesResult")

            if stats_elem is not None:
                return EstatisticasPublicacoes(
                    grupo=self._get_text_value_ns(stats_elem, "grupo", {}),
                    total_publicacoes=self._get_int_value_ns(
                        stats_elem, "totalPublicacoes", {}
                    ),
                    total_nao_importadas=self._get_int_value_ns(
                        stats_elem, "totalNaoImportadas", {}
                    ),
                )

            logger.warning("Elemento de estatísticas não encontrado")
            return EstatisticasPublicacoes()

        except Exception as exc:
            logger.error("Erro ao fazer parse das estatísticas: %s", exc)
            return EstatisticasPublicacoes()

    def publicacoes_to_json(self, publicacoes_list: List[Publicacao]) -> str:
        """Converte lista de publicações para JSON"""
        return json.dumps(
            [pub.to_dict() for pub in publicacoes_list], ensure_ascii=False, indent=2
        )

    def publicacoes_to_dict(
        self, publicacoes_list: List[Publicacao]
    ) -> List[Dict[str, Any]]:
        """Converte lista de publicações para lista de dicionários"""
        return [pub.to_dict() for pub in publicacoes_list]


# Instância singleton para uso global no Gateway
_intimation_service_instance = None


def get_intimation_service(
    usuario: str = None, senha: str = None, timeout: int = None
) -> IntimationService:
    """
    Factory function para obter instância do IntimationService

    Args:
        usuario: Usuário SOAP (opcional, usa env se não fornecido)
        senha: Senha SOAP (opcional, usa env se não fornecido)
        timeout: Timeout personalizado (opcional)

    Returns:
        IntimationService: Instância configurada
    """
    global _intimation_service_instance

    if _intimation_service_instance is None:
        kwargs = {}
        if timeout:
            kwargs["timeout"] = timeout

        _intimation_service_instance = IntimationService(
            usuario=usuario, senha=senha, **kwargs
        )

    return _intimation_service_instance


def get_intimation_client() -> IntimationService:
    """
    Dependency function para FastAPI

    Returns:
        IntimationService: Instância para uso como dependency
    """
    return get_intimation_service()


# Para compatibilidade com código existente, expor classe principal
IntimationAPIClient = IntimationService
