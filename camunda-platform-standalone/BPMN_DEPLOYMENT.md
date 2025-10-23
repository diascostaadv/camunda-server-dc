# Deploy Automático de Arquivos BPMN

Este documento explica como funciona o sistema de deploy automático de arquivos BPMN no Camunda Platform.

## 📁 Estrutura de Arquivos

```
camunda-platform-standalone/
├── bpmn/                          # Pasta com arquivos BPMN para deploy automático
│   ├── Fluxo_gerador_token_cpj.bpmn
│   ├── Fluxo_publicacao_agendamento.bpmn
│   ├── Fluxo_publicacao_captura_intimacoes.bpmn
│   └── ... (outros arquivos BPMN)
├── resources/                     # Pasta com recursos já deployados
├── scripts/
│   ├── deploy_bpmns.py            # Script Python para deploy manual
│   └── init-bpmn-deploy.sh        # Script Bash para deploy automático
└── docker-compose.yml             # Configuração com deploy automático
```

## 🚀 Como Funciona

### 1. Deploy Automático (Recomendado)

Quando você executa `make local-up` ou `make deploy`, o sistema automaticamente:

1. **Inicia o Camunda Platform**
2. **Aguarda o Camunda estar saudável** (health check)
3. **Executa o deploy automático** dos arquivos BPMN da pasta `bpmn/`
4. **Finaliza o processo** e remove o container de deploy

### 2. Deploy Manual

Se você quiser fazer deploy manual dos BPMN files:

```bash
# Deploy local
make deploy-bpmn

# Deploy remoto
make deploy-bpmn-remote
```

### 3. Scripts Individuais

```bash
# Usando o script Python
python3 scripts/deploy_bpmns.py

# Usando o script Bash
bash scripts/init-bpmn-deploy.sh
```

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# Configuração do Camunda
CAMUNDA_BASE_URL=http://localhost:8080
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=admin

# Configuração do deploy
BPMN_DIR=bpmn
MAX_ATTEMPTS=30
DELAY=10
```

### Docker Compose

O serviço `bpmn-deployer` é configurado para:

- **Aguardar** o Camunda estar saudável
- **Montar** a pasta `bpmn/` como volume
- **Executar** o script de deploy automaticamente
- **Finalizar** após o deploy (restart: "no")

## 📋 Arquivos Suportados

O sistema suporta:

- **Arquivos BPMN** (`.bpmn`)
- **Arquivos DMN** (`.dmn`)
- **Formulários** (`.form`)

## 🔍 Monitoramento

### Logs do Deploy

```bash
# Ver logs do deploy automático
docker compose logs bpmn-deployer

# Ver logs do Camunda
docker compose logs camunda
```

### Verificar Deployments

Acesse o Camunda Cockpit em `http://localhost:8080/camunda/app/cockpit/` para ver os deployments criados.

## 🛠️ Troubleshooting

### Problema: Deploy falha

```bash
# Verificar se o Camunda está rodando
curl http://localhost:8080/engine-rest/version

# Verificar logs
docker compose logs bpmn-deployer

# Executar deploy manual
make deploy-bpmn
```

### Problema: Arquivos BPMN não encontrados

```bash
# Verificar se a pasta bpmn existe
ls -la bpmn/

# Verificar se há arquivos BPMN
find bpmn/ -name "*.bpmn"
```

### Problema: Permissões

```bash
# Tornar scripts executáveis
chmod +x scripts/init-bpmn-deploy.sh
chmod +x scripts/deploy_bpmns.py
```

## 📝 Exemplos de Uso

### Adicionar Novo Arquivo BPMN

1. Coloque o arquivo `.bpmn` na pasta `bpmn/`
2. Reinicie o Camunda: `make local-restart`
3. O arquivo será automaticamente deployado

### Deploy Manual de Arquivo Específico

```bash
# Copiar arquivo para a pasta bpmn
cp meu_arquivo.bpmn bpmn/

# Executar deploy manual
make deploy-bpmn
```

### Verificar Deployments

```bash
# Listar deployments via API
curl -u admin:admin http://localhost:8080/engine-rest/deployment
```

## 🎯 Benefícios

- ✅ **Deploy automático** na inicialização
- ✅ **Monitoramento** via logs
- ✅ **Deploy manual** quando necessário
- ✅ **Suporte a múltiplos arquivos**
- ✅ **Integração com Docker Compose**
- ✅ **Configuração flexível**

## 📚 Referências

- [Camunda REST API - Deployments](https://docs.camunda.org/manual/latest/reference/rest/deployment/post-deployment/)
- [Docker Compose Health Checks](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [BPMN 2.0 Specification](https://www.omg.org/spec/BPMN/2.0/)
