#!/bin/bash
set -e

DOMAIN="api.nutec.com.br"
EMAIL="admin@nutec.com.br"
BACKEND_PORT=8080

echo "🚀 Instalando SSL para $DOMAIN..."

# Verificar root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Execute como root: sudo bash install-ssl-nutec.sh"
   exit 1
fi

# Instalar nginx e certbot
echo "📦 Instalando dependências..."
apt update -qq
apt install -y nginx certbot python3-certbot-nginx

# Verificar se aplicação está rodando
if ! netstat -tlnp | grep -q ":$BACKEND_PORT"; then
    echo "⚠️  Aplicação não está rodando na porta $BACKEND_PORT"
    echo "⚠️  Certifique-se de iniciar: docker-compose up -d"
fi

# Criar configuração Nginx
echo "⚙️  Configurando Nginx..."
cat > /etc/nginx/sites-available/gateway-api << 'EOF'
server {
    listen 80;
    server_name api.nutec.com.br;

    access_log /var/log/nginx/gateway-api-access.log;
    error_log /var/log/nginx/gateway-api-error.log;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Ativar site
ln -sf /etc/nginx/sites-available/gateway-api /etc/nginx/sites-enabled/gateway-api
rm -f /etc/nginx/sites-enabled/default

# Testar configuração
echo "🧪 Testando configuração Nginx..."
nginx -t

# Recarregar Nginx
echo "🔄 Recarregando Nginx..."
systemctl reload nginx

# Obter certificado SSL
echo "🔐 Obtendo certificado SSL..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

# Verificar certificado
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo ""
    echo "✅ SSL instalado com sucesso!"
    echo ""
    echo "🌐 URLs:"
    echo "   https://api.nutec.com.br/docs"
    echo "   https://api.nutec.com.br/health"
    echo ""
    echo "🧪 Testar:"
    echo "   curl https://api.nutec.com.br/health"
    echo ""
else
    echo "❌ Erro ao obter certificado SSL"
    exit 1
fi
