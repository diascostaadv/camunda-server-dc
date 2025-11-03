# HTTPS Automático - Guia Completo

**Data**: 2025-11-03
**Status**: ✅ Implementado e Operacional
**Domínio**: camunda.nutec.com.br

---

## 🎯 Resumo Executivo

HTTPS está **configurado automaticamente** via Caddy + Let's Encrypt.
**Nenhuma configuração manual é necessária.**

Quando você faz `make deploy`, o HTTPS é automaticamente:
1. ✅ Configurado
2. ✅ Certificado SSL obtido (gratuito)
3. ✅ Renovação automática configurada
4. ✅ Funcionando em ~30 segundos

---

## 🔧 Como Funciona

### Arquitetura

```
Internet (HTTPS/443)
        ↓
   [Caddy Container]
        ↓
   [Camunda Container:8080]
        ↓
   [PostgreSQL Azure]
```

### Fluxo de Tráfego

1. **Cliente** acessa `https://camunda.nutec.com.br`
2. **Caddy** recebe na porta 443 (HTTPS)
3. **Caddy** descriptografa SSL/TLS
4. **Caddy** faz proxy para `camunda:8080` (rede Docker interna)
5. **Camunda** responde
6. **Caddy** criptografa resposta e envia ao cliente

### Obtenção Automática de Certificado

#### Primeira Inicialização (Deploy Inicial)
```bash
make deploy
# ↓
# Docker sobe container Caddy
# ↓
# Caddy lê Caddyfile
# ↓
# Caddy detecta domínio: camunda.nutec.com.br
# ↓
# Caddy contata Let's Encrypt API
# ↓
# Let's Encrypt verifica propriedade do domínio (via DNS)
# ↓
# Let's Encrypt emite certificado SSL
# ↓
# Caddy salva certificado em volume Docker (caddy_data)
# ↓
# HTTPS operacional em ~30 segundos ✅
```

#### Renovação Automática
```
Caddy monitora validade do certificado
        ↓
30 dias antes de expirar
        ↓
Caddy contata Let's Encrypt automaticamente
        ↓
Novo certificado obtido e instalado
        ↓
Zero downtime ✅
```

---

## 📁 Arquivos de Configuração

### 1. Caddyfile
**Localização**: `config/Caddyfile`

```caddyfile
# Configuração global
{
    email admin@nutec.com.br
}

# HTTPS automático para o domínio
camunda.nutec.com.br {
    # Proxy reverso para Camunda
    reverse_proxy camunda:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        transport http {
            dial_timeout 30s
            response_header_timeout 60s
        }
    }

    # Logs
    log {
        output file /var/log/caddy/access.log
        format json
    }

    # Headers de segurança
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        X-XSS-Protection "1; mode=block"
        -Server
    }

    # Compressão
    encode gzip zstd
}
```

**É só isso!** O Caddy faz todo o resto automaticamente:
- ✅ Detecta que precisa de HTTPS
- ✅ Contata Let's Encrypt
- ✅ Obtém certificado
- ✅ Configura HTTPS
- ✅ Redireciona HTTP → HTTPS
- ✅ Renova antes de expirar

### 2. Docker Compose
**Localização**: `docker-compose.simple.yml` e `docker-compose.swarm.yml`

```yaml
caddy:
  image: caddy:2-alpine
  ports:
    - "80:80"       # HTTP (redirecionamento automático)
    - "443:443"     # HTTPS
    - "443:443/udp" # HTTP/3
  volumes:
    - ./config/Caddyfile:/etc/caddy/Caddyfile:ro
    - caddy_data:/data         # Certificados salvos aqui
    - caddy_config:/config     # Configuração do Caddy
    - caddy_logs:/var/log/caddy
  networks: [backend]
  restart: unless-stopped
  depends_on:
    - camunda
```

### 3. Volumes Docker
```yaml
volumes:
  caddy_data:    # Armazena certificados SSL
  caddy_config:  # Armazena configuração Caddy
  caddy_logs:    # Logs de acesso
```

**Importante**: O volume `caddy_data` contém os certificados SSL.
Se você destruir este volume, o Caddy precisará obter novos certificados na próxima inicialização.

---

## 🚀 Deploy e Uso

### Deploy Inicial (Primeira Vez)

```bash
# No seu computador local
cd camunda-platform-standalone
make deploy
```

**O que acontece**:
1. Arquivos copiados para servidor
2. Docker Compose inicia serviços
3. Caddy container sobe
4. Caddy detecta domínio no Caddyfile
5. Caddy contata Let's Encrypt
6. Certificado SSL obtido (~30 segundos)
7. HTTPS operacional ✅

**Logs em tempo real**:
```bash
# Ver processo de obtenção do certificado
ssh ubuntu@201.23.67.197 "docker logs -f camunda-platform-caddy-1"
```

### Deploys Subsequentes

```bash
make deploy
```

**O que acontece**:
1. Caddy reinicia
2. Certificado já existe no volume `caddy_data`
3. HTTPS operacional imediatamente (< 5 segundos) ✅

### Verificar HTTPS

```bash
# Testar HTTPS
curl -I https://camunda.nutec.com.br
# Deve retornar: HTTP/2 200

# Testar redirecionamento HTTP → HTTPS
curl -I http://camunda.nutec.com.br
# Deve retornar: HTTP/1.1 308 Permanent Redirect
# Location: https://camunda.nutec.com.br/

# Testar API com autenticação
curl -u admin:DiasCosta@!!2025 https://camunda.nutec.com.br/engine-rest/version
# Deve retornar: {"version":"7.23.0"}
```

### Ver Informações do Certificado

```bash
# Informações do certificado
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null 2>&1 | openssl x509 -noout -dates

# Ou via SSH no servidor
ssh ubuntu@201.23.67.197 "docker exec camunda-platform-caddy-1 caddy list-certificates"
```

---

## 🔄 Renovação Automática

### Como Funciona

- Certificados Let's Encrypt são **válidos por 90 dias**
- Caddy verifica validade diariamente
- **30 dias antes de expirar**, Caddy:
  1. Contata Let's Encrypt automaticamente
  2. Obtém novo certificado
  3. Instala certificado sem downtime
  4. Continua servindo tráfego normalmente

### Monitorar Renovação

```bash
# Ver logs de renovação
ssh ubuntu@201.23.67.197 "docker logs camunda-platform-caddy-1 | grep -i 'renew\|certificate'"

# Ver data de expiração do certificado
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null 2>&1 | openssl x509 -noout -dates
```

**Exemplo de output**:
```
notBefore=Oct 22 17:03:09 2025 GMT
notAfter=Jan 20 17:03:08 2026 GMT
```

### Forçar Renovação Manual (Opcional)

```bash
ssh ubuntu@201.23.67.197
cd ~/camunda-platform
docker restart camunda-platform-caddy-1
# Caddy verificará se precisa renovar ao iniciar
```

---

## 🛠️ Troubleshooting

### Problema: HTTPS não funciona após deploy

**Sintomas**:
- Timeout ao acessar `https://camunda.nutec.com.br`
- Certificado inválido ou não confiável

**Diagnóstico**:
```bash
# 1. Verificar se Caddy está rodando
ssh ubuntu@201.23.67.197 "docker ps | grep caddy"
# Deve mostrar container rodando

# 2. Ver logs do Caddy
ssh ubuntu@201.23.67.197 "docker logs camunda-platform-caddy-1 --tail 100"

# 3. Verificar DNS
nslookup camunda.nutec.com.br
# Deve retornar 201.23.67.197

# 4. Testar portas
nc -zv camunda.nutec.com.br 443
# Deve retornar "succeeded"
```

**Soluções**:

#### Solução 1: Aguardar (Primeira Inicialização)
```bash
# Aguarde 30-60 segundos para Let's Encrypt emitir certificado
# Monitore logs:
ssh ubuntu@201.23.67.197 "docker logs -f camunda-platform-caddy-1"
```

#### Solução 2: Verificar Firewall
```bash
ssh ubuntu@201.23.67.197 "sudo ufw status | grep -E '80|443'"
# Deve mostrar:
# 80/tcp    ALLOW    Anywhere
# 443/tcp   ALLOW    Anywhere
```

Se portas não estiverem abertas:
```bash
ssh ubuntu@201.23.67.197 "sudo ufw allow 80/tcp && sudo ufw allow 443/tcp"
```

#### Solução 3: Reiniciar Caddy
```bash
ssh ubuntu@201.23.67.197 "cd ~/camunda-platform && docker restart camunda-platform-caddy-1"
```

#### Solução 4: Recriar Container Caddy
```bash
ssh ubuntu@201.23.67.197 "cd ~/camunda-platform && docker compose up -d --force-recreate caddy"
```

#### Solução 5: Limpar Volume e Reobter Certificado
```bash
ssh ubuntu@201.23.67.197
cd ~/camunda-platform

# Parar Caddy
docker compose stop caddy

# Limpar volume de certificados
docker volume rm camunda-platform_caddy_data

# Recriar Caddy
docker compose up -d caddy

# Aguardar 30-60 segundos e verificar logs
docker logs -f camunda-platform-caddy-1
```

### Problema: "ERR certificate signed by unknown authority"

**Causa**: Certificado ainda não foi emitido ou está inválido

**Solução**:
```bash
# Ver status do certificado
ssh ubuntu@201.23.67.197 "docker exec camunda-platform-caddy-1 caddy list-certificates"

# Se não houver certificado, reiniciar Caddy
ssh ubuntu@201.23.67.197 "docker restart camunda-platform-caddy-1"

# Aguardar 30 segundos e verificar novamente
```

### Problema: Renovação não está funcionando

**Sintomas**:
- Certificado próximo de expirar
- Avisos de certificado expirado

**Diagnóstico**:
```bash
# Ver data de expiração
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null 2>&1 | openssl x509 -noout -dates

# Ver logs de renovação
ssh ubuntu@201.23.67.197 "docker logs camunda-platform-caddy-1 | grep -i 'renew'"
```

**Solução**:
```bash
# Forçar renovação (reiniciar Caddy)
ssh ubuntu@201.23.67.197 "docker restart camunda-platform-caddy-1"

# Aguardar 1 minuto
sleep 60

# Verificar novo certificado
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null 2>&1 | openssl x509 -noout -dates
```

---

## 📊 Monitoramento

### Logs Importantes

```bash
# Logs do Caddy (acesso HTTP/HTTPS)
ssh ubuntu@201.23.67.197 "docker exec camunda-platform-caddy-1 cat /var/log/caddy/access.log | tail -20"

# Logs do container
ssh ubuntu@201.23.67.197 "docker logs camunda-platform-caddy-1 --tail 50"

# Logs em tempo real
ssh ubuntu@201.23.67.197 "docker logs -f camunda-platform-caddy-1"
```

### Métricas

```bash
# Status dos containers
ssh ubuntu@201.23.67.197 "docker ps | grep -E 'caddy|camunda'"

# Uso de recursos do Caddy
ssh ubuntu@201.23.67.197 "docker stats camunda-platform-caddy-1 --no-stream"

# Tamanho dos volumes
ssh ubuntu@201.23.67.197 "docker volume ls | grep caddy && du -sh /var/lib/docker/volumes/camunda-platform_caddy_*"
```

---

## 🔒 Segurança

### Recursos Habilitados Automaticamente

1. **TLS 1.2 e 1.3** - Protocolos modernos
2. **HTTP/2 e HTTP/3** - Performance otimizada
3. **HSTS** - Força HTTPS em navegadores (max-age=31536000)
4. **X-Content-Type-Options: nosniff** - Previne MIME sniffing
5. **X-Frame-Options: SAMEORIGIN** - Previne clickjacking
6. **X-XSS-Protection: 1; mode=block** - Proteção XSS
7. **Server header removido** - Oculta versão do servidor
8. **Redirecionamento HTTP → HTTPS** - Todo tráfego criptografado

### Headers de Resposta

```bash
curl -I https://camunda.nutec.com.br
```

**Output esperado**:
```
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains
x-content-type-options: nosniff
x-frame-options: SAMEORIGIN
x-xss-protection: 1; mode=block
```

---

## 📖 Referência Rápida

### Comandos Úteis

```bash
# Ver status do HTTPS
curl -I https://camunda.nutec.com.br

# Ver certificado
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null

# Reiniciar Caddy
ssh ubuntu@201.23.67.197 "docker restart camunda-platform-caddy-1"

# Ver logs
ssh ubuntu@201.23.67.197 "docker logs camunda-platform-caddy-1 --tail 100"

# Verificar data de expiração do certificado
openssl s_client -connect camunda.nutec.com.br:443 -servername camunda.nutec.com.br < /dev/null 2>&1 | openssl x509 -noout -dates
```

### URLs de Acesso

- **HTTPS (Principal)**: https://camunda.nutec.com.br
- **HTTP (Redireciona)**: http://camunda.nutec.com.br
- **Cockpit**: https://camunda.nutec.com.br/camunda/app/cockpit/
- **Tasklist**: https://camunda.nutec.com.br/camunda/app/tasklist/
- **Admin**: https://camunda.nutec.com.br/camunda/app/admin/
- **API REST**: https://camunda.nutec.com.br/engine-rest/

### Credenciais

- **Usuário**: `admin`
- **Senha**: `DiasCosta@!!2025`

---

## ❓ FAQ

### P: Preciso pagar pelo certificado SSL?
**R**: Não! O Let's Encrypt fornece certificados **gratuitos** para sempre.

### P: Preciso renovar manualmente o certificado?
**R**: Não! O Caddy renova **automaticamente** 30 dias antes de expirar.

### P: O que acontece se o certificado expirar?
**R**: Não vai expirar. O Caddy renova automaticamente. Mas se acontecer, basta reiniciar o container Caddy e ele obterá um novo.

### P: Posso usar outro domínio?
**R**: Sim! Basta alterar o domínio no `config/Caddyfile`:
```caddyfile
novo-dominio.exemplo.com {
    reverse_proxy camunda:8080
}
```

### P: Como adicionar mais domínios?
**R**: Adicione mais blocos no Caddyfile:
```caddyfile
camunda.nutec.com.br {
    reverse_proxy camunda:8080
}

outro-dominio.com {
    reverse_proxy camunda:8080
}
```

### P: HTTPS funciona em desenvolvimento local?
**R**: Não automaticamente. Let's Encrypt requer domínio público válido. Para desenvolvimento local, use HTTP ou configure certificado auto-assinado.

### P: O Nginx do sistema interfere?
**R**: Não, desabilitamos o Nginx do sistema (`systemctl disable nginx`) para evitar conflito de portas 80/443.

### P: Onde estão os certificados salvos?
**R**: No volume Docker `caddy_data` em `/var/lib/docker/volumes/camunda-platform_caddy_data/`.

---

## 📚 Documentação Adicional

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [ACESSO_E_SEGURANCA.md](ACESSO_E_SEGURANCA.md) - Guia completo de acesso e segurança
- [QUICK_START_MAINTENANCE.md](QUICK_START_MAINTENANCE.md) - Manutenção rápida
- [DISK_SPACE_FIXES.md](DISK_SPACE_FIXES.md) - Correções de espaço em disco

---

**Última atualização**: 2025-11-03
**Status**: ✅ Operacional e Testado
**Responsável**: Sistema configurado via Claude Code
