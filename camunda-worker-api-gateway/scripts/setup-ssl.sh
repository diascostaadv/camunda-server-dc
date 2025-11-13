#!/bin/bash

###############################################################################
# Script de Instalação SSL/HTTPS para Worker API Gateway
# Servidor: 201.23.69.65:8080
#
# Este script configura Nginx como proxy reverso com SSL via Let's Encrypt
###############################################################################

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║          Worker API Gateway - SSL Setup Script               ║
║              Nginx Proxy + Let's Encrypt SSL                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar se está rodando como root
if [[ $EUID -ne 0 ]]; then
   print_error "Este script precisa ser executado como root (use sudo)"
   exit 1
fi

print_success "Script iniciado como root"

# ==================== COLETA DE INFORMAÇÕES ====================

echo ""
print_info "Vamos configurar o SSL para seu domínio"
echo ""

# Solicitar domínio
read -p "Digite o domínio (ex: api.exemplo.com.br): " DOMAIN
if [ -z "$DOMAIN" ]; then
    print_error "Domínio não pode estar vazio"
    exit 1
fi

print_info "Domínio: $DOMAIN"

# Solicitar email para Let's Encrypt
read -p "Digite seu email para Let's Encrypt: " EMAIL
if [ -z "$EMAIL" ]; then
    print_error "Email não pode estar vazio"
    exit 1
fi

print_info "Email: $EMAIL"

# Porta do backend
BACKEND_PORT=8080
read -p "Porta do backend [8080]: " INPUT_PORT
if [ ! -z "$INPUT_PORT" ]; then
    BACKEND_PORT=$INPUT_PORT
fi

print_info "Porta do backend: $BACKEND_PORT"

# Confirmação
echo ""
print_warning "Confirme as informações:"
echo "  Domínio: $DOMAIN"
echo "  Email: $EMAIL"
echo "  Porta Backend: $BACKEND_PORT"
echo ""
read -p "Continuar? (s/n): " CONFIRM

if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    print_error "Instalação cancelada pelo usuário"
    exit 0
fi

# ==================== INSTALAÇÃO ====================

echo ""
print_info "Iniciando instalação..."

# 1. Atualizar sistema
print_info "1/8 - Atualizando sistema..."
apt update -qq

# 2. Instalar Nginx
print_info "2/8 - Instalando Nginx..."
if ! command -v nginx &> /dev/null; then
    apt install nginx -y -qq
    print_success "Nginx instalado"
else
    print_success "Nginx já instalado"
fi

# 3. Verificar se aplicação está rodando
print_info "3/8 - Verificando aplicação backend..."
if netstat -tlnp | grep -q ":$BACKEND_PORT"; then
    print_success "Aplicação rodando na porta $BACKEND_PORT"
else
    print_warning "Aplicação não está rodando na porta $BACKEND_PORT"
    print_warning "Certifique-se de iniciar a aplicação antes de continuar"
    read -p "Continuar mesmo assim? (s/n): " CONTINUE
    if [ "$CONTINUE" != "s" ] && [ "$CONTINUE" != "S" ]; then
        exit 1
    fi
fi

# 4. Criar configuração Nginx
print_info "4/8 - Criando configuração Nginx..."

NGINX_CONFIG="/etc/nginx/sites-available/gateway-api"

cat > $NGINX_CONFIG << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Logs
    access_log /var/log/nginx/gateway-api-access.log;
    error_log /var/log/nginx/gateway-api-error.log;

    # Proxy para aplicação
    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;

        # Headers de proxy
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Cache bypass
        proxy_cache_bypass \$http_upgrade;
    }

    # Health check endpoint (para monitoramento)
    location /health {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }
}
EOF

print_success "Configuração Nginx criada em $NGINX_CONFIG"

# 5. Ativar site
print_info "5/8 - Ativando site..."

# Remover link simbólico se já existir
if [ -L "/etc/nginx/sites-enabled/gateway-api" ]; then
    rm /etc/nginx/sites-enabled/gateway-api
fi

ln -s $NGINX_CONFIG /etc/nginx/sites-enabled/gateway-api
print_success "Site ativado"

# 6. Testar configuração Nginx
print_info "6/8 - Testando configuração Nginx..."
if nginx -t; then
    print_success "Configuração Nginx válida"
else
    print_error "Erro na configuração Nginx"
    exit 1
fi

# 7. Recarregar Nginx
print_info "7/8 - Recarregando Nginx..."
systemctl reload nginx
print_success "Nginx recarregado"

# 8. Instalar Certbot e obter certificado SSL
print_info "8/8 - Instalando certificado SSL..."

# Instalar certbot
if ! command -v certbot &> /dev/null; then
    print_info "Instalando Certbot..."
    apt install certbot python3-certbot-nginx -y -qq
    print_success "Certbot instalado"
else
    print_success "Certbot já instalado"
fi

# Obter certificado SSL
print_info "Obtendo certificado SSL via Let's Encrypt..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

if [ $? -eq 0 ]; then
    print_success "Certificado SSL obtido com sucesso!"
else
    print_error "Erro ao obter certificado SSL"
    print_warning "Verifique se:"
    print_warning "  1. O domínio $DOMAIN aponta para este servidor"
    print_warning "  2. As portas 80 e 443 estão abertas no firewall"
    print_warning "  3. Não há outro serviço usando as portas 80 ou 443"
    exit 1
fi

# ==================== VERIFICAÇÕES FINAIS ====================

echo ""
print_info "Realizando verificações finais..."

# Verificar se certificado foi instalado
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    print_success "Certificado instalado em /etc/letsencrypt/live/$DOMAIN"

    # Mostrar data de expiração
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/$DOMAIN/cert.pem | cut -d= -f2)
    print_info "Data de expiração: $EXPIRY_DATE"
else
    print_error "Certificado não encontrado"
    exit 1
fi

# Verificar renovação automática
if systemctl is-active --quiet certbot.timer; then
    print_success "Renovação automática de certificados ativa"
else
    print_warning "Timer de renovação não está ativo"
    systemctl enable certbot.timer
    systemctl start certbot.timer
    print_success "Timer de renovação ativado"
fi

# Testar renovação
print_info "Testando processo de renovação..."
if certbot renew --dry-run; then
    print_success "Teste de renovação passou"
else
    print_warning "Teste de renovação falhou (não crítico)"
fi

# ==================== SUMÁRIO ====================

echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                    ✅ INSTALAÇÃO CONCLUÍDA!                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
print_success "SSL configurado com sucesso!"
echo ""
print_info "URLs de acesso:"
echo "  HTTP:  http://$DOMAIN (redireciona para HTTPS)"
echo "  HTTPS: https://$DOMAIN"
echo "  Swagger UI: https://$DOMAIN/docs"
echo "  Health Check: https://$DOMAIN/health"
echo ""
print_info "Testar via curl:"
echo "  curl https://$DOMAIN/health"
echo ""
print_info "Arquivos de configuração:"
echo "  Nginx: $NGINX_CONFIG"
echo "  Certificado: /etc/letsencrypt/live/$DOMAIN/"
echo "  Logs: /var/log/nginx/gateway-api-*.log"
echo ""
print_info "Comandos úteis:"
echo "  Ver logs: sudo tail -f /var/log/nginx/gateway-api-access.log"
echo "  Renovar SSL: sudo certbot renew"
echo "  Recarregar Nginx: sudo systemctl reload nginx"
echo ""

# Perguntar se quer testar
read -p "Deseja testar o endpoint agora? (s/n): " TEST
if [ "$TEST" = "s" ] || [ "$TEST" = "S" ]; then
    echo ""
    print_info "Testando endpoint HTTPS..."
    curl -s https://$DOMAIN/health | jq . || curl -s https://$DOMAIN/health
    echo ""
fi

print_success "Instalação finalizada!"
echo ""
print_warning "Lembre-se de atualizar o arquivo tests-dw-law.http:"
echo "  @gatewayUrl = https://$DOMAIN"
echo ""
