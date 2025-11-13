# Guia de Instalação SSL/HTTPS no Servidor

## Servidor: 201.23.69.65:8080
## Objetivo: Configurar HTTPS com certificado Let's Encrypt

---

## Pré-requisitos

### 1. Domínio configurado
Você precisa de um **domínio** apontando para o IP `201.23.69.65`.

Exemplos de configuração DNS:
```
A record:  api.seudominío.com.br  →  201.23.69.65
A record:  gateway.seudominío.com.br  →  201.23.69.65
```

**⚠️ IMPORTANTE**: Sem um domínio válido, o Let's Encrypt não consegue emitir certificados SSL.

### 2. Acesso SSH ao servidor
```bash
ssh usuario@201.23.69.65
```

### 3. Portas abertas no firewall
```bash
# Verificar portas abertas
sudo ufw status

# Abrir portas necessárias (se não estiverem abertas)
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8080/tcp  # Aplicação backend
```

---

## Opção 1: Instalação Automatizada (Recomendado)

### Passo 1: Download do script automatizado

```bash
# Conectar ao servidor
ssh usuario@201.23.69.65

# Download do script
wget https://raw.githubusercontent.com/leolmcoelho/nginx-proxy-setup/main/add_domain_nginx.sh

# Tornar executável
chmod +x add_domain_nginx.sh
```

### Passo 2: Executar o script

```bash
sudo ./add_domain_nginx.sh
```

### Passo 3: Fornecer informações quando solicitado

O script vai pedir:

1. **Nome do domínio**: `api.seudominío.com.br`
2. **Porta Nginx** (deixe padrão): `80`
3. **IP Backend** (deixe padrão): `127.0.0.1`
4. **Porta Backend**: `8080` ← IMPORTANTE: Digite 8080 aqui

### Passo 4: Configurar Let's Encrypt

O script criará a configuração Nginx, mas você precisará instalar o certificado SSL:

```bash
# Instalar certbot (se não estiver instalado)
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado SSL
sudo certbot --nginx -d api.seudominío.com.br

# Seguir instruções interativas:
# - Fornecer email
# - Aceitar termos
# - Escolher opção 2 (redirecionar HTTP para HTTPS)
```

### Passo 5: Testar a configuração

```bash
# Testar configuração Nginx
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx

# Verificar status
sudo systemctl status nginx
```

### Passo 6: Testar SSL

```bash
# Testar endpoint HTTPS
curl https://api.seudominío.com.br/health

# Verificar certificado
curl -vI https://api.seudominío.com.br
```

---

## Opção 2: Instalação Manual

Se preferir configurar manualmente:

### Passo 1: Instalar Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

### Passo 2: Criar arquivo de configuração

```bash
sudo nano /etc/nginx/sites-available/gateway-api
```

Cole o conteúdo (substitua `SEU_DOMINIO` pelo domínio real):

```nginx
server {
    listen 80;
    server_name SEU_DOMINIO;

    # Logs
    access_log /var/log/nginx/gateway-api-access.log;
    error_log /var/log/nginx/gateway-api-error.log;

    # Proxy para aplicação na porta 8080
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;

        # Headers de proxy
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Cache bypass
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Passo 3: Ativar configuração

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/gateway-api /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

### Passo 4: Instalar certificado SSL

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado
sudo certbot --nginx -d SEU_DOMINIO

# Certbot vai modificar automaticamente a configuração para adicionar SSL
```

### Passo 5: Renovação automática

```bash
# Certbot já configura renovação automática via systemd timer
# Testar renovação
sudo certbot renew --dry-run

# Verificar timer
sudo systemctl status certbot.timer
```

---

## Verificações Pós-Instalação

### 1. Testar HTTP → HTTPS redirect
```bash
curl -I http://SEU_DOMINIO
# Deve retornar 301 Moved Permanently para HTTPS
```

### 2. Testar HTTPS
```bash
curl https://SEU_DOMINIO/health
# Deve retornar resposta da API
```

### 3. Verificar certificado SSL
```bash
# Ver detalhes do certificado
echo | openssl s_client -servername SEU_DOMINIO -connect SEU_DOMINIO:443 2>/dev/null | openssl x509 -noout -dates

# Ou use online:
# https://www.ssllabs.com/ssltest/analyze.html?d=SEU_DOMINIO
```

### 4. Testar Swagger UI
Acesse no navegador:
```
https://SEU_DOMINIO/docs
```

---

## Atualizar arquivo tests-dw-law.http

Após configurar SSL, atualize as variáveis no arquivo de testes:

```http
# Antes:
@gatewayUrl = http://201.23.69.65:8080

# Depois:
@gatewayUrl = https://SEU_DOMINIO
```

---

## Troubleshooting

### Problema: "Connection refused"
```bash
# Verificar se aplicação está rodando na porta 8080
sudo netstat -tlnp | grep 8080

# Ou
sudo lsof -i :8080

# Se não estiver rodando, iniciar aplicação
cd /caminho/do/projeto
make local-up  # ou docker-compose up -d
```

### Problema: "502 Bad Gateway"
```bash
# Verificar logs do Nginx
sudo tail -f /var/log/nginx/gateway-api-error.log

# Verificar se aplicação está respondendo
curl http://127.0.0.1:8080/health

# Verificar configuração do Nginx
sudo nginx -t
```

### Problema: "Certificate verification failed"
```bash
# Re-obter certificado
sudo certbot --nginx -d SEU_DOMINIO --force-renewal

# Verificar status do certbot
sudo systemctl status certbot.timer
```

### Problema: "Too many redirects"
```bash
# Verificar se há loop de redirecionamento
# Editar configuração:
sudo nano /etc/nginx/sites-available/gateway-api

# Verificar se não há múltiplos redirects conflitantes
```

---

## Manutenção

### Renovação manual de certificado
```bash
sudo certbot renew --force-renewal
```

### Ver logs do Nginx
```bash
# Access logs
sudo tail -f /var/log/nginx/gateway-api-access.log

# Error logs
sudo tail -f /var/log/nginx/gateway-api-error.log

# Logs gerais
sudo tail -f /var/log/nginx/error.log
```

### Recarregar configuração Nginx
```bash
# Após modificar configuração
sudo nginx -t && sudo systemctl reload nginx
```

---

## Arquitetura Final

```
Cliente (Navegador/App)
         ↓
    HTTPS (443)
         ↓
    Nginx Proxy Reverso
    (Let's Encrypt SSL)
         ↓
    HTTP (127.0.0.1:8080)
         ↓
  Worker API Gateway
  (FastAPI container)
```

---

## Recursos Adicionais

- **Repositório nginx-proxy-setup**: https://github.com/leolmcoelho/nginx-proxy-setup
- **Documentação Let's Encrypt**: https://letsencrypt.org/docs/
- **Certbot**: https://certbot.eff.org/
- **Nginx Proxy Config**: https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **SSL Labs Test**: https://www.ssllabs.com/ssltest/

---

## Contato e Suporte

Em caso de dúvidas:
1. Verificar logs do Nginx: `sudo tail -f /var/log/nginx/error.log`
2. Verificar logs da aplicação: `docker-compose logs -f gateway`
3. Testar conexões locais antes de culpar o SSL
4. Consultar documentação do certbot para problemas específicos

---

## Checklist de Instalação

- [ ] Domínio configurado apontando para 201.23.69.65
- [ ] Portas 80, 443 e 8080 abertas no firewall
- [ ] Nginx instalado
- [ ] Configuração do site criada em `/etc/nginx/sites-available/`
- [ ] Link simbólico criado em `/etc/nginx/sites-enabled/`
- [ ] Certbot instalado
- [ ] Certificado SSL obtido via Let's Encrypt
- [ ] Renovação automática configurada
- [ ] HTTP redireciona para HTTPS
- [ ] Aplicação responde via HTTPS
- [ ] Swagger UI acessível via HTTPS
- [ ] Arquivo `tests-dw-law.http` atualizado com HTTPS URL
