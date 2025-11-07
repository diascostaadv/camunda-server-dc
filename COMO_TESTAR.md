# 🧪 Como Testar a Integração DW LAW + CPJ

**5 minutos de testes rápidos**

---

## ⚡ Opção 1: REST Client (VS Code) - MAIS FÁCIL

### 1. Instalar extensão
```bash
code --install-extension humao.rest-client
```

### 2. Abrir arquivo de testes
```bash
code test-scripts/integration-tests.http
```

### 3. Executar requests
- Coloque cursor em qualquer request
- Clique em **"Send Request"** (aparece acima do ###)
- Veja resposta no painel lateral

### 4. Testes Recomendados (nesta ordem)
```
1. Health Check (linha 19)
2. Teste de Conexões (linha 25)
3. Inserir Processo DW LAW (linha 35)
4. Buscar Processo CPJ (linha 168)
```

---

## ⚡ Opção 2: curl (Terminal)

### Testes DW LAW

```bash
# 1. Health
curl http://201.23.69.65:8080/dw-law/health

# 2. Conexões
curl http://201.23.69.65:8080/dw-law/test-connection | jq .

# 3. Inserir processo
curl -X POST http://201.23.69.65:8080/dw-law/inserir-processos \
  -H 'Content-Type: application/json' \
  -d '{"chave_projeto":"diascostacitacaoconsultaunica","processos":[{"numero_processo":"0012205-60.2015.5.15.0077"}]}' | jq .
```

### Testes CPJ

```bash
# 1. Buscar processo
curl -X POST http://201.23.69.65:8080/cpj/processos/buscar-por-numero \
  -H 'Content-Type: application/json' \
  -d '{"numero_cnj":"0012205-60.2015.5.15.0077"}' | jq .

# 2. Buscar publicações
curl -X POST http://201.23.69.65:8080/cpj/publicacoes/nao-vinculadas \
  -H 'Content-Type: application/json' \
  -d '{"limit":5}' | jq .
```

---

## ⚡ Opção 3: Swagger UI (Navegador)

```bash
# Abrir Swagger
open http://201.23.69.65:8080/docs

# Expandir seções:
# - DW LAW e-Protocol
# - CPJ API

# Clicar em "Try it out"
# Preencher campos
# Clicar em "Execute"
```

---

## 📁 Arquivos de Teste

```
test-scripts/dw_law.http          - Testes completos DW LAW (200+ linhas)
test-scripts/cpj.http              - Testes completos CPJ (300+ linhas)
test-scripts/integration-tests.http - Testes combinados (RECOMENDADO)
```

---

## ✅ Resultado Esperado

### DW LAW - Inserção
```json
{
  "success": true,
  "message": "processos inseridos com sucesso",
  "data": {
    "processos": [{
      "numero_processo": "0012205-60.2015.5.15.0077",
      "chave_de_pesquisa": "UUID-GERADO",
      "tribunal": "TRT15",
      "sistema": "PJE",
      "retorno": "SUCESSO"
    }]
  }
}
```

### CPJ - Busca de Processo
```json
[
  {
    "pj": 12345,
    "numero_processo": "0012205-60.2015.5.15.0077",
    "materia": "Trabalhista",
    "envolvidos": [...],
    "pedidos": [...]
  }
]
```

---

## 🎯 Quick Start

**3 comandos para testar tudo**:

```bash
# 1. Abrir testes no VS Code
code test-scripts/integration-tests.http

# 2. Clicar em "Send Request" no teste #3 (conexões)

# 3. Clicar em "Send Request" no teste #4 (inserir processo)
```

**Pronto! Se esses 2 testes passarem, tudo está funcionando! ✅**

---

## 📚 Documentação Completa

- **Setup**: `DW_LAW_SETUP_COMPLETO.md`
- **Deploy**: `DEPLOY_DW_LAW_WORKER.md`
- **Resumo**: `RESUMO_FINAL_DW_LAW.md`
- **Worker**: `workers/dw_law_worker/README.md`

---

**✅ Pronto para testar! Escolha uma das 3 opções acima.**
