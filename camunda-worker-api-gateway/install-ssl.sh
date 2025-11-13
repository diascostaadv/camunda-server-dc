#!/bin/bash
set -e

# Configurações (EDITE AQUI)
DOMAIN="SEU_DOMINIO_AQUI"  # Ex: api.exemplo.com.br
EMAIL="SEU_EMAIL_AQUI"      # Ex: admin@exemplo.com.br
BACKEND_PORT=8080

# Verificar root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Execute como root: sudo bash install-ssl.sh"
   exit 1
fi

echo "🚀 Instalando SSL para $DOMAIN..."

# Instalar dependências
apt update -qq
apt install -y nginx certbot python3-certbot-nginx

# Criar config Nginx
cat > /etc/nginx/sites-available/gateway-api << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Ativar site
ln -sf /etc/nginx/sites-available/gateway-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Testar e recarregar
nginx -t && systemctl reload nginx

# Obter certificado SSL
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

echo "✅ SSL instalado! Acesse: https://$DOMAIN/docs"
