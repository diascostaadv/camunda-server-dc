# DW LAW Worker - Guia de Integração BPMN

## Visão Geral

O **DW LAW Worker** é responsável por integrar processos Camunda com a plataforma DW LAW e-Protocol, permitindo inserção, exclusão e consulta de processos judiciais monitorados.

**Arquitetura**: Este worker funciona como **orquestrador** - ele valida os dados básicos e delega todo o processamento para o Worker API Gateway.

---

## Tópicos Disponíveis

### 1. `INSERIR_PROCESSOS_DW_LAW`

Insere uma lista de processos judiciais no sistema de monitoramento DW LAW.

#### Variáveis de Entrada (Process Variables)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `chave_projeto` | String | ✅ Sim | Chave única que identifica o projeto DW LAW onde os processos serão inseridos |
| `processos` | Array[Object] | ✅ Sim | Lista de processos a serem inseridos (mínimo 1 processo) |

**Estrutura de cada objeto em `processos`:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `numero_processo` | String | ✅ Sim | Número do processo no formato CNJ: `9999999-99.9999.9.99.9999` |
| `other_info_client1` | String | ❌ Não | Campo livre para informações adicionais do cliente |
| `other_info_client2` | String | ❌ Não | Campo livre para informações adicionais do cliente |

#### Exemplo de Payload BPMN

```json
{
  "chave_projeto": "PROJ_TRABALHISTA_2025",
  "processos": [
    {
      "numero_processo": "1234567-89.2025.5.01.0001",
      "other_info_client1": "Cliente XYZ Ltda",
      "other_info_client2": "Reclamação Trabalhista"
    },
    {
      "numero_processo": "9876543-21.2025.5.01.0002",
      "other_info_client1": "Cliente ABC SA",
      "other_info_client2": "Ação de Cobrança"
    }
  ]
}
```

#### Variáveis de Retorno

Em caso de **sucesso**, o worker retorna:

| Variável | Tipo | Descrição |
|----------|------|-----------|
| `resultado_insercao` | Object | Objeto contendo detalhes da inserção realizada pelo Gateway |
| `processos_inseridos` | Number | Quantidade de processos inseridos com sucesso |
| `chaves_de_pesquisa` | Array[String] | Lista de chaves geradas para cada processo (use para consultas futuras) |

#### Códigos de Erro BPMN

| Código | Descrição | Causa |
|--------|-----------|-------|
| `ERRO_VALIDACAO_INTEGRACAO_DW` | Erro de validação dos dados | Campo obrigatório ausente, formato inválido ou lista vazia |
| `ERRO_CONFIGURACAO_INTEGRACAO_DW` | Erro de configuração | Worker não está configurado para usar o Gateway |
| `ERRO_PROCESSAMENTO_INTEGRACAO_DW` | Erro no processamento | Falha na comunicação com Gateway ou erro interno |

---

### 2. `EXCLUIR_PROCESSOS_DW_LAW`

Remove uma lista de processos judiciais do sistema de monitoramento DW LAW.

#### Variáveis de Entrada (Process Variables)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `chave_projeto` | String | ✅ Sim | Chave única que identifica o projeto DW LAW |
| `lista_de_processos` | Array[Object] | ✅ Sim | Lista de processos a serem excluídos (mínimo 1 processo) |

**Estrutura de cada objeto em `lista_de_processos`:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `numero_processo` | String | ✅ Sim | Número do processo no formato CNJ |

#### Exemplo de Payload BPMN

```json
{
  "chave_projeto": "PROJ_TRABALHISTA_2025",
  "lista_de_processos": [
    {
      "numero_processo": "1234567-89.2025.5.01.0001"
    },
    {
      "numero_processo": "9876543-21.2025.5.01.0002"
    }
  ]
}
```

#### Variáveis de Retorno

Em caso de **sucesso**, o worker retorna:

| Variável | Tipo | Descrição |
|----------|------|-----------|
| `resultado_exclusao` | Object | Objeto contendo detalhes da exclusão realizada pelo Gateway |
| `processos_excluidos` | Number | Quantidade de processos excluídos com sucesso |

#### Códigos de Erro BPMN

Os mesmos códigos de erro do tópico `INSERIR_PROCESSOS_DW_LAW`.

---

### 3. `CONSULTAR_PROCESSO_DW_LAW`

Consulta os dados completos de um processo judicial específico no DW LAW.

#### Variáveis de Entrada (Process Variables)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `chave_de_pesquisa` | String | ✅ Sim | Chave única retornada na inserção do processo (obtida no tópico `INSERIR_PROCESSOS_DW_LAW`) |

#### Exemplo de Payload BPMN

```json
{
  "chave_de_pesquisa": "DW_LAW_KEY_ABC123XYZ789"
}
```

#### Variáveis de Retorno

Em caso de **sucesso**, o worker retorna:

| Variável | Tipo | Descrição |
|----------|------|-----------|
| `dados_processo` | Object | Objeto completo com todos os dados do processo retornados pelo DW LAW |
| `numero_processo` | String | Número do processo consultado |
| `movimentacoes` | Array[Object] | Lista de movimentações processuais (se disponível) |
| `publicacoes` | Array[Object] | Lista de publicações (se disponível) |

**Nota**: A estrutura exata de `dados_processo` depende da resposta da API DW LAW. Consulte a documentação da API para detalhes completos.

#### Códigos de Erro BPMN

Os mesmos códigos de erro dos tópicos anteriores.

---

## Como Usar nos Fluxos BPMN

### Exemplo 1: Service Task para Inserção de Processos

```xml
<bpmn:serviceTask id="InserirProcessosDWLaw" name="Inserir Processos no DW LAW">
  <bpmn:extensionElements>
    <camunda:topic>INSERIR_PROCESSOS_DW_LAW</camunda:topic>
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

**Certifique-se de que as variáveis `chave_projeto` e `processos` estejam disponíveis no contexto do processo antes da execução.**

### Exemplo 2: Service Task com Tratamento de Erro

```xml
<bpmn:serviceTask id="ConsultarProcessoDWLaw" name="Consultar Processo DW LAW">
  <bpmn:extensionElements>
    <camunda:topic>CONSULTAR_PROCESSO_DW_LAW</camunda:topic>
  </bpmn:extensionElements>
</bpmn:serviceTask>

<bpmn:boundaryEvent id="ErroValidacao" attachedToRef="ConsultarProcessoDWLaw">
  <bpmn:errorEventDefinition errorRef="ERRO_VALIDACAO_INTEGRACAO_DW" />
</bpmn:boundaryEvent>

<bpmn:boundaryEvent id="ErroProcessamento" attachedToRef="ConsultarProcessoDWLaw">
  <bpmn:errorEventDefinition errorRef="ERRO_PROCESSAMENTO_INTEGRACAO_DW" />
</bpmn:boundaryEvent>
```

### Exemplo 3: Fluxo Completo - Inserir e Consultar

```xml
<!-- 1. Preparar dados -->
<bpmn:scriptTask id="PrepararDados" scriptFormat="groovy">
  <bpmn:script>
    execution.setVariable("chave_projeto", "PROJ_2025")
    execution.setVariable("processos", [
      [
        "numero_processo": "1234567-89.2025.5.01.0001",
        "other_info_client1": "Cliente A"
      ]
    ])
  </bpmn:script>
</bpmn:scriptTask>

<!-- 2. Inserir processos -->
<bpmn:serviceTask id="InserirProcessos" camunda:topic="INSERIR_PROCESSOS_DW_LAW" />

<!-- 3. Extrair chave de pesquisa -->
<bpmn:scriptTask id="ExtrairChave" scriptFormat="groovy">
  <bpmn:script>
    def chaves = execution.getVariable("chaves_de_pesquisa")
    execution.setVariable("chave_de_pesquisa", chaves[0])
  </bpmn:script>
</bpmn:scriptTask>

<!-- 4. Consultar processo -->
<bpmn:serviceTask id="ConsultarProcesso" camunda:topic="CONSULTAR_PROCESSO_DW_LAW" />
```

---

## Boas Práticas

### ✅ DO (Faça)

1. **Sempre valide os dados antes de enviar** - Use Script Tasks ou Business Rule Tasks para garantir que os dados estão no formato correto
2. **Implemente tratamento de erros BPMN** - Use Boundary Events para capturar os códigos de erro retornados
3. **Guarde as `chaves_de_pesquisa`** - São essenciais para consultas futuras aos processos
4. **Use timeouts apropriados** - As consultas podem demorar até 120 segundos
5. **Log adequadamente** - Armazene em variáveis de processo informações relevantes para auditoria

### ❌ DON'T (Não Faça)

1. **Não envie listas vazias** - Sempre valide que `processos` ou `lista_de_processos` contém ao menos 1 item
2. **Não use formatos de processo inválidos** - O número do processo deve seguir o padrão CNJ
3. **Não ignore os códigos de erro** - Sempre implemente tratamento para os 3 códigos de erro possíveis
4. **Não confie apenas em Happy Path** - DW LAW é uma API externa, sempre prepare para falhas
5. **Não esqueça a `chave_projeto`** - É obrigatória em todos os tópicos de inserção e exclusão

---

## Troubleshooting

### Erro: "Campo obrigatório ausente: chave_projeto"

**Causa**: A variável `chave_projeto` não está definida no contexto do processo.

**Solução**: Adicione um Script Task antes do Service Task para definir a variável:

```groovy
execution.setVariable("chave_projeto", "SEU_PROJETO_AQUI")
```

### Erro: "Lista de processos não pode estar vazia"

**Causa**: O array `processos` ou `lista_de_processos` está vazio.

**Solução**: Valide que o array contém ao menos 1 elemento antes de chamar o tópico.

### Erro: "Modo direto não suportado para DW LAW"

**Causa**: O worker não está configurado para usar o Gateway (configuração de infraestrutura).

**Solução**: Entre em contato com a equipe de infraestrutura. O worker deve ter `GATEWAY_ENABLED=true`.

### Timeout na Consulta

**Causa**: A API DW LAW pode demorar para responder em consultas complexas.

**Solução**: Configure o timeout do External Task no Camunda para pelo menos 180 segundos.

---

## Contato e Suporte

Para dúvidas sobre:
- **Integração BPMN**: Equipe de Processos
- **Configuração do Worker**: Equipe de Infraestrutura
- **API DW LAW**: Consulte a documentação oficial do DW LAW e-Protocol

---

## Changelog

- **v1.0** (2025-01) - Versão inicial com 3 tópicos: inserir, excluir e consultar processos
