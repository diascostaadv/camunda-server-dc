#!/bin/bash
# ============================================================================
# SECURITY SETUP SCRIPT - Ubuntu Security Hardening
# ============================================================================
# Configures firewall, fail2ban, and security settings for Camunda ecosystem
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
    fi
}

configure_firewall() {
    log_info "Configuring UFW firewall..."
    
    # Reset firewall
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH access
    ufw allow ssh
    
    # Web traffic
    ufw allow 80/tcp   # HTTP
    ufw allow 443/tcp  # HTTPS
    
    # Camunda ecosystem ports
    ufw allow 8080/tcp  # Camunda BPM
    ufw allow 9090/tcp  # Prometheus
    ufw allow 3001/tcp  # Grafana
    ufw allow 8000/tcp  # API Gateway
    ufw allow 8001/tcp  # Worker 1
    ufw allow 8002/tcp  # Worker 2
    ufw allow 15672/tcp # RabbitMQ Management
    ufw allow 5432/tcp  # PostgreSQL (if external access needed)
    ufw allow 6379/tcp  # Redis (if external access needed)
    
    # Docker Swarm ports
    ufw allow 2376/tcp  # Docker daemon
    ufw allow 2377/tcp  # Swarm management
    ufw allow 7946/tcp  # Swarm node communication
    ufw allow 7946/udp  # Swarm node communication
    ufw allow 4789/udp  # Overlay network traffic
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured and enabled"
    ufw status numbered
}

configure_fail2ban() {
    log_info "Configuring fail2ban..."
    
    # Install if not present
    if ! command -v fail2ban-server &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq fail2ban
    fi
    
    # Create custom jail configuration
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Ban time: 1 hour
bantime = 3600
# Find time: 10 minutes
findtime = 600
# Max retry: 3 attempts
maxretry = 3
# Ignore local IPs
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 3

# Custom filter for Camunda
[camunda-auth]
enabled = true
filter = camunda-auth
logpath = /var/log/camunda/*.log
maxretry = 5
bantime = 1800
EOF
    
    # Create custom filter for Camunda authentication failures
    cat > /etc/fail2ban/filter.d/camunda-auth.conf << 'EOF'
[Definition]
failregex = Authentication failure.*<HOST>
            Invalid credentials.*from <HOST>
            Failed login.*<HOST>
ignoreregex =
EOF
    
    # Start and enable fail2ban
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    log_success "Fail2ban configured and started"
}

configure_system_security() {
    log_info "Applying system security hardening..."
    
    # Disable root login via SSH (if sshd_config exists)
    if [[ -f /etc/ssh/sshd_config ]]; then
        sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        systemctl reload sshd || true
        log_success "SSH root login disabled"
    fi
    
    # Set up automatic security updates
    if command -v unattended-upgrade &> /dev/null; then
        echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/50unattended-upgrades-custom
        systemctl enable unattended-upgrades
        log_success "Automatic security updates enabled"
    fi
    
    # Configure kernel parameters for security
    cat > /etc/sysctl.d/99-security.conf << 'EOF'
# IP Spoofing protection
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP pings
net.ipv4.icmp_echo_ignore_all = 0

# Ignore Directed pings
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 0
net.ipv6.conf.default.disable_ipv6 = 0
net.ipv6.conf.lo.disable_ipv6 = 0
EOF
    
    sysctl -p /etc/sysctl.d/99-security.conf
    
    log_success "Kernel security parameters configured"
}

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    # Create log rotation for Camunda logs
    cat > /etc/logrotate.d/camunda << 'EOF'
/opt/camunda/logs/*.log /var/log/camunda/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        # Restart services if needed
        systemctl reload docker 2>/dev/null || true
    endscript
}
EOF
    
    # Create log rotation for Docker
    cat > /etc/logrotate.d/docker-containers << 'EOF'
/var/lib/docker/containers/*/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    maxsize 100M
}
EOF
    
    log_success "Log rotation configured"
}

configure_limits() {
    log_info "Configuring system limits..."
    
    # Increase file descriptor limits for Docker
    cat > /etc/security/limits.d/99-camunda.conf << 'EOF'
# Increased limits for Camunda ecosystem
root soft nofile 65536
root hard nofile 65536
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF
    
    log_success "System limits configured"
}

verify_security() {
    log_info "Verifying security configuration..."
    
    local errors=0
    
    # Check firewall
    if ! ufw status | grep -q "Status: active"; then
        log_error "Firewall is not active"
        ((errors++))
    else
        log_success "Firewall: Active"
    fi
    
    # Check fail2ban
    if ! systemctl is-active --quiet fail2ban; then
        log_warning "Fail2ban is not running"
        ((errors++))
    else
        log_success "Fail2ban: Running"
    fi
    
    # Check SSH root login
    if grep -q "PermitRootLogin no" /etc/ssh/sshd_config 2>/dev/null; then
        log_success "SSH root login: Disabled"
    else
        log_warning "SSH root login: Not disabled"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Security verification completed successfully!"
        return 0
    else
        log_warning "$errors security issues found"
        return 1
    fi
}

show_security_status() {
    echo
    log_info "============================================"
    log_info "SECURITY STATUS"
    log_info "============================================"
    echo
    
    echo "Firewall Status:"
    ufw status numbered
    echo
    
    echo "Fail2ban Status:"
    fail2ban-client status
    echo
    
    echo "Open Ports:"
    ss -tlnp | grep LISTEN
    echo
    
    echo "Active Security Services:"
    systemctl is-active ufw fail2ban unattended-upgrades 2>/dev/null || true
}

# Main execution
main() {
    log_info "Starting security hardening..."
    
    check_root
    
    configure_firewall
    configure_fail2ban
    configure_system_security
    setup_log_rotation
    configure_limits
    
    if verify_security; then
        show_security_status
        log_success "Security hardening completed successfully!"
    else
        log_warning "Security hardening completed with warnings. Review the configuration."
    fi
}

# Handle command line arguments
case "${1:-all}" in
    "firewall")
        check_root && configure_firewall
        ;;
    "fail2ban")
        check_root && configure_fail2ban
        ;;
    "system")
        check_root && configure_system_security
        ;;
    "logs")
        check_root && setup_log_rotation
        ;;
    "limits")
        check_root && configure_limits
        ;;
    "verify")
        verify_security
        ;;
    "status")
        show_security_status
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  all       - Complete security hardening (default)"
        echo "  firewall  - Configure UFW firewall only"
        echo "  fail2ban  - Configure fail2ban only"
        echo "  system    - System security hardening only"
        echo "  logs      - Setup log rotation only"
        echo "  limits    - Configure system limits only"
        echo "  verify    - Verify security configuration"
        echo "  status    - Show security status"
        echo "  help      - Show this help"
        ;;
    *)
        main "$@"
        ;;
esac