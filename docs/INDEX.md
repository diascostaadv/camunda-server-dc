# 📚 Índice de Documentação - Camunda BPM Platform

Este projeto contém documentação completa para o sistema Camunda BPM modularizado em 3 projetos independentes.

## 📖 Documentação Principal

### 🏠 [README.md](README.md)
**Documentação principal do projeto**
- Visão geral da arquitetura
- Guia de instalação e uso
- Cenários de deploy
- URLs e configurações
- Troubleshooting

## 📋 Guias Especializados

### 🗄️ [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)
**Guia completo de migração para bancos gerenciados**
- Modos de operação (local vs externo)
- Configuração Azure Managed Services
- Connection strings e exemplos
- Processo de migração passo-a-passo
- Custos estimados

### 🔧 [README-SEPARATED-PROJECTS.md](README-SEPARATED-PROJECTS.md)
**Detalhes da separação em 3 projetos**
- Motivação da separação
- Comparação antes/depois
- Estrutura de cada projeto
- Vantagens da arquitetura modular

## 📁 Documentação por Projeto

### 🏗️ Projeto 1: Camunda Platform
```
camunda-platform-standalone/
├── README.md                    # Guia específico do projeto
├── .env.local                   # Configuração desenvolvimento
├── .env.production             # Configuração produção
├── .env.azure-example          # Exemplo Azure
└── Makefile                    # Comandos disponíveis
```
**Foco**: Infraestrutura Camunda + PostgreSQL + Monitoramento

### 🌐 Projeto 2: Worker API Gateway
```
camunda-worker-api-gateway/
├── README.md                    # Guia específico do projeto
├── .env.local                   # Configuração desenvolvimento
├── .env.production             # Configuração produção
├── .env.azure-example          # Exemplo Azure services
└── Makefile                    # Comandos disponíveis
```
**Foco**: Gateway FastAPI + MongoDB + RabbitMQ + Redis

### 👷 Projeto 3: Workers Platform
```
camunda-workers-platform/
├── README.md                    # Guia específico do projeto
├── .env.local                   # Configuração desenvolvimento
├── .env.production             # Configuração produção
├── Makefile                    # Comandos disponíveis
└── workers/                    # Sistema de workers
    ├── _config/                # Auto-discovery
    ├── _templates/             # Templates
    ├── common/                 # Classes base
    ├── hello-world/            # Worker exemplo
    └── publicacao/             # Worker publicação
```
**Foco**: Sistema de workers com auto-discovery e templates

## 🚀 Guias Rápidos

### Para Desenvolvedores
1. **Início Rápido**: [README.md](README.md) → Seção "Getting Started"
2. **Desenvolvimento Local**: [README.md](README.md) → Seção "Cenário 1"
3. **Criar Workers**: `camunda-workers-platform/README.md`

### Para DevOps
1. **Deploy Produção**: [README.md](README.md) → Seção "Cenário 3"
2. **Migração Azure**: [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)
3. **Monitoramento**: [README.md](README.md) → Seção "Monitoramento"

### Para Arquitetos
1. **Visão Arquitetural**: [README.md](README.md) → Seção "Arquitetura Geral"
2. **Justificativa da Separação**: [README-SEPARATED-PROJECTS.md](README-SEPARATED-PROJECTS.md)
3. **Custos e Escalabilidade**: [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)

## 🔍 Como Navegar

### Por Necessidade

**Quero começar rapidamente:**
→ [README.md](README.md) + `make local-up`

**Preciso migrar para Azure:**
→ [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)

**Quero entender a arquitetura:**
→ [README-SEPARATED-PROJECTS.md](README-SEPARATED-PROJECTS.md)

**Tenho problemas:**
→ [README.md](README.md) → Seção "Troubleshooting"

### Por Projeto

**Trabalho com Camunda:**
→ `camunda-platform-standalone/README.md`

**Trabalho com APIs/Gateway:**
→ `camunda-worker-api-gateway/README.md`

**Trabalho com Workers:**
→ `camunda-workers-platform/README.md`

## 📊 Matriz de Funcionalidades

| Funcionalidade | Projeto 1 | Projeto 2 | Projeto 3 |
|---------------|-----------|-----------|-----------|
| **Camunda BPM** | ✅ Principal | - | - |
| **PostgreSQL** | ✅ Interno/Azure | - | - |
| **MongoDB** | - | ✅ Interno/Azure | - |
| **Redis** | - | ✅ Interno/Azure | - |
| **RabbitMQ** | - | ✅ Interno/Azure | - |
| **Workers** | - | - | ✅ Múltiplos |
| **Auto-discovery** | - | - | ✅ Sistema |
| **Templates** | - | - | ✅ Geração |
| **Monitoramento** | ✅ Grafana/Prometheus | ✅ Métricas | ✅ Por worker |
| **Escalabilidade** | ✅ Horizontal | ✅ Gateway | ✅ Por worker |

## 🎯 Comandos Essenciais

### Desenvolvimento Local
```bash
# Setup completo local
cd camunda-platform-standalone && make local-up
cd camunda-workers-platform && make local-up

# Com gateway opcional
cd camunda-worker-api-gateway && make local-up
```

### Produção
```bash
# Deploy completo
cd camunda-platform-standalone && make deploy
cd camunda-worker-api-gateway && make deploy
cd camunda-workers-platform && make deploy
```

### Monitoramento
```bash
# Status geral
make local-status    # ou remote-status
make health-check    # gateway específico
```

### Workers
```bash
cd camunda-workers-platform
make list-workers    # ver workers
make new-worker      # criar worker
make build-workers   # build todos
```

## ✅ Checklist de Setup

### Desenvolvimento
- [ ] Ler [README.md](README.md)
- [ ] Executar `make local-up` nos projetos necessários
- [ ] Acessar http://localhost:8080 (Camunda)
- [ ] Testar workers com `make list-workers`

### Produção
- [ ] Ler [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)
- [ ] Configurar serviços Azure (se necessário)
- [ ] Atualizar `.env.production` com URIs
- [ ] Executar `make deploy` nos projetos
- [ ] Verificar com `make remote-status`

### Monitoramento
- [ ] Acessar Grafana
- [ ] Configurar alertas
- [ ] Testar métricas dos workers
- [ ] Validar dashboards

## 🆘 Suporte

**Dúvidas sobre arquitetura:** Consulte [README-SEPARATED-PROJECTS.md](README-SEPARATED-PROJECTS.md)

**Problemas de conectividade:** Veja [README.md](README.md) → Troubleshooting

**Migração Azure:** Siga [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md)

**Issues específicos:** Consulte documentação do projeto específico

---

**Início recomendado:** [README.md](README.md) → Seção "Getting Started" 🚀