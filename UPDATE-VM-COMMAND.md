# Comando de Atualização Completa da VM

## Visão Geral

Foi criado um comando `make` que automatiza todo o processo de atualização da VM, incluindo sincronização de código, rebuild de imagens Docker e restart dos serviços.

## Comando

```bash
make -f update-vm.mk update-vm
```

## O que o comando faz

### 1. Sincronização de Código

- **API Gateway**: Sincroniza código usando `rsync` (otimizado)
- **Workers Platform**: Sincroniza código usando `scp`

### 2. Parada dos Serviços

- Para todos os containers do API Gateway
- Para todos os containers dos Workers
- Remove redes Docker não utilizadas

### 3. Limpeza de Imagens

- Remove imagem antiga do API Gateway
- Remove imagem antiga dos Workers

### 4. Rebuild Forçado

- Rebuild da API Gateway **sem cache** (`--no-cache`)
- Rebuild dos Workers **sem cache** (`--no-cache`)

### 5. Inicialização dos Serviços

- Sobe API Gateway com `docker compose up -d`
- Sobe Workers Platform com `docker compose up -d`

### 6. Validação

- Mostra status dos containers
- Exibe informações de portas e saúde dos serviços

## Saída Esperada

```
🔄 Updating VM with fresh code and rebuild...
📁 Syncing API Gateway code...
📁 Syncing Workers Platform code...
🛑 Stopping all services...
🗑️ Removing old images...
🔨 Rebuilding API Gateway without cache...
🔨 Rebuilding Workers Platform without cache...
🚀 Starting API Gateway...
🚀 Starting Workers Platform...
✅ VM update completed successfully!
📊 Checking services status...
```

## Vantagens

1. **Automático**: Um único comando faz tudo
2. **Limpo**: Remove imagens antigas e rebuild sem cache
3. **Seguro**: Para serviços antes de fazer mudanças
4. **Validado**: Mostra status final dos serviços
5. **Otimizado**: Usa rsync para API Gateway (mais rápido)

## Uso Recomendado

Use este comando sempre que:

- Fizer mudanças no código da API Gateway
- Fizer mudanças no código dos Workers
- Quiser garantir que a VM está com o código mais recente
- Tiver problemas de cache ou inconsistências

## Arquivo de Configuração

O comando está no arquivo `update-vm.mk` e pode ser executado de qualquer lugar do projeto:

```bash
# Do diretório raiz do projeto
make -f update-vm.mk update-vm
```

## Configurações

As configurações da VM estão no arquivo `update-vm.mk`:

- **VM_HOST**: 201.23.69.65
- **VM_USER**: ubuntu
- **SSH_KEY**: ~/.ssh/id_rsa
- **SSH_PORT**: 22
