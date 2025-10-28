#!/bin/bash

# Script de hardening de segurança para o servidor Camunda
# Implementa medidas de proteção contra ataques comuns

echo "🔒 Aplicando medidas de segurança..."

# 1. Configurar firewall básico
echo "📡 Configurando firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Portas essenciais
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8080/tcp  # Camunda (temporário até SSL)
sudo ufw allow 9000/tcp  # Portainer

# 2. Configurar fail2ban para proteção contra ataques
echo "🛡️ Instalando e configurando fail2ban..."
sudo apt update
sudo apt install -y fail2ban

# Configurar fail2ban para Camunda
sudo tee /etc/fail2ban/jail.d/camunda.conf > /dev/null <<EOF
[camunda]
enabled = true
port = 8080
filter = camunda
logpath = /var/log/camunda.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

# 3. Configurar rate limiting (se necessário)
echo "⚡ Configurando rate limiting..."
# Rate limiting será configurado diretamente nos serviços se necessário

# 4. Configurar logs de segurança
echo "📋 Configurando logs de segurança..."
sudo mkdir -p /var/log/camunda
sudo touch /var/log/camunda/security.log
sudo chown ubuntu:ubuntu /var/log/camunda/security.log

# 5. Configurar backup automático
echo "💾 Configurando backup automático..."
sudo tee /etc/cron.daily/camunda-backup > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p \$BACKUP_DIR

# Backup dos volumes Docker
docker run --rm -v camunda_db_data:/data -v \$BACKUP_DIR:/backup alpine tar czf /backup/db_backup_\$DATE.tar.gz -C /data .

# Backup das configurações
tar czf \$BACKUP_DIR/config_backup_\$DATE.tar.gz -C /home/ubuntu/camunda-platform .

# Manter apenas os últimos 7 backups
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

sudo chmod +x /etc/cron.daily/camunda-backup

# 6. Configurar monitoramento de segurança
echo "👁️ Configurando monitoramento de segurança..."
sudo tee /usr/local/bin/security-monitor.sh > /dev/null <<EOF
#!/bin/bash
# Monitor de segurança para Camunda

LOG_FILE="/var/log/camunda/security.log"
DATE=\$(date '+%Y-%m-%d %H:%M:%S')

# Verificar tentativas de acesso suspeitas
SUSPICIOUS_ATTEMPTS=\$(docker logs camunda-simple 2>&1 | grep -i "invalid character\|path contains\|../" | wc -l)

if [ \$SUSPICIOUS_ATTEMPTS -gt 10 ]; then
    echo "[\$DATE] ALERT: \$SUSPICIOUS_ATTEMPTS suspicious access attempts detected" >> \$LOG_FILE
    # Aqui você pode adicionar notificações por email ou Slack
fi

# Verificar uso de recursos
MEMORY_USAGE=\$(free | grep Mem | awk '{printf "%.2f", \$3/\$2 * 100.0}')
if (( \$(echo "\$MEMORY_USAGE > 90" | bc -l) )); then
    echo "[\$DATE] WARNING: High memory usage: \$MEMORY_USAGE%" >> \$LOG_FILE
fi
EOF

sudo chmod +x /usr/local/bin/security-monitor.sh

# Adicionar ao crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/security-monitor.sh") | crontab -

echo "✅ Medidas de segurança aplicadas com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "1. Reiniciar o fail2ban: sudo systemctl restart fail2ban"
echo "2. Verificar status: sudo ufw status"
echo "3. Monitorar logs: tail -f /var/log/camunda/security.log"
echo "4. Configurar SSL/TLS com Let's Encrypt"

