#!/bin/bash
# ============================================================================
# VM PROVISIONING SCRIPT - Complete Ubuntu VM Setup
# ============================================================================
# Sets up a fresh Ubuntu VM with Docker, Docker Swarm, SSL certificates,
# and security hardening for Camunda BPM ecosystem deployment
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/vm-provision.log"
DOCKER_VERSION="latest"
SSL_EMAIL="${SSL_EMAIL:-admin@example.com}"
DOMAIN="${DOMAIN:-localhost}"
SSL_PROVIDER="${SSL_PROVIDER:-selfsigned}"  # letsencrypt, selfsigned, custom

# Functions
log() {
    echo -e "${WHITE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if ! command -v lsb_release &> /dev/null || [[ "$(lsb_release -si)" != "Ubuntu" ]]; then
        log_error "This script is designed for Ubuntu systems only"
        exit 1
    fi
    
    local ubuntu_version=$(lsb_release -sr)
    log_info "Detected Ubuntu $ubuntu_version"
    
    # Check if supported version (18.04+)
    if [[ "$(echo "$ubuntu_version 18.04" | tr ' ' '\n' | sort -V | head -1)" != "18.04" ]]; then
        log_warning "Ubuntu version $ubuntu_version may not be fully supported. Recommended: 20.04 or 22.04"
    fi
}

update_system() {
    log_info "Updating system packages..."
    
    export DEBIAN_FRONTEND=noninteractive
    
    apt-get update -qq
    apt-get upgrade -y -qq
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        wget \
        unzip \
        git \
        htop \
        ufw \
        fail2ban \
        logrotate \
        cron
    
    log_success "System packages updated successfully"
}

install_docker() {
    log_info "Installing Docker..."
    
    # Remove old versions
    apt-get remove -y -qq docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    # Add current user to docker group (if not root)
    if [[ -n "${SUDO_USER:-}" ]]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Added user $SUDO_USER to docker group (logout/login required)"
    fi
    
    # Verify installation
    docker --version
    docker compose version
    
    log_success "Docker installed successfully"
}

init_docker_swarm() {
    log_info "Initializing Docker Swarm..."
    
    # Check if already in swarm mode
    if docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active"; then
        log_warning "Docker Swarm already initialized"
        docker node ls
        return
    fi
    
    # Initialize swarm
    local swarm_ip="${SWARM_IP:-$(hostname -I | awk '{print $1}')}"
    docker swarm init --advertise-addr "$swarm_ip"
    
    # Create overlay network for backend services
    docker network create --driver overlay --attachable backend 2>/dev/null || log_warning "Backend network already exists"
    
    log_success "Docker Swarm initialized successfully"
    docker node ls
}

setup_ssl_certificates() {
    log_info "Setting up SSL certificates (provider: $SSL_PROVIDER)..."
    
    case "$SSL_PROVIDER" in
        "letsencrypt")
            setup_letsencrypt
            ;;
        "selfsigned")
            setup_selfsigned_cert
            ;;
        "custom")
            log_info "Custom SSL setup - please configure manually"
            ;;
        *)
            log_warning "Unknown SSL provider: $SSL_PROVIDER. Skipping SSL setup."
            ;;
    esac
}

setup_letsencrypt() {
    log_info "Installing Let's Encrypt certificates..."
    
    # Install certbot
    apt-get install -y -qq certbot
    
    # Validate domain
    if [[ "$DOMAIN" == "localhost" ]] || [[ "$DOMAIN" == *".local"* ]]; then
        log_error "Let's Encrypt requires a valid public domain. Use SSL_PROVIDER=selfsigned for localhost"
        return 1
    fi
    
    # Create certificate directory
    mkdir -p /etc/ssl/camunda
    
    # Generate certificate (standalone mode)
    certbot certonly --standalone --non-interactive --agree-tos --email "$SSL_EMAIL" -d "$DOMAIN"
    
    # Copy certificates to expected location
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" /etc/ssl/camunda/
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" /etc/ssl/camunda/
    
    # Set up auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log_success "Let's Encrypt certificates configured"
}

setup_selfsigned_cert() {
    log_info "Creating self-signed SSL certificate..."
    
    mkdir -p /etc/ssl/camunda
    cd /etc/ssl/camunda
    
    # Generate private key
    openssl genrsa -out privkey.pem 2048
    
    # Generate certificate
    openssl req -new -x509 -key privkey.pem -out fullchain.pem -days 365 -subj "/C=BR/ST=State/L=City/O=Organization/OU=IT/CN=$DOMAIN"
    
    # Set permissions
    chmod 600 privkey.pem
    chmod 644 fullchain.pem
    
    log_success "Self-signed certificate created for $DOMAIN"
}

setup_security() {
    log_info "Configuring security hardening..."
    
    # Configure UFW firewall
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow Camunda ports
    ufw allow 8080/tcp  # Camunda
    ufw allow 9090/tcp  # Prometheus
    ufw allow 3001/tcp  # Grafana
    ufw allow 8000/tcp  # Gateway
    ufw allow 8001/tcp  # Worker 1
    ufw allow 8002/tcp  # Worker 2
    ufw allow 15672/tcp # RabbitMQ Management
    
    # Allow Docker Swarm ports
    ufw allow 2376/tcp  # Docker daemon
    ufw allow 2377/tcp  # Swarm management
    ufw allow 7946/tcp  # Swarm communication
    ufw allow 7946/udp  # Swarm communication
    ufw allow 4789/udp  # Overlay networks
    
    ufw --force enable
    
    # Configure fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Set up log rotation
    cat > /etc/logrotate.d/camunda << 'EOF'
/var/log/camunda/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
    
    log_success "Security hardening completed"
}

install_system_dependencies() {
    log_info "Installing additional system dependencies..."
    
    # Install monitoring tools
    apt-get install -y -qq \
        htop \
        iotop \
        nethogs \
        ncdu \
        tree \
        jq \
        vim \
        nano
    
    # Install network tools
    apt-get install -y -qq \
        net-tools \
        netstat-nat \
        tcpdump \
        nmap
    
    log_success "System dependencies installed"
}

setup_directories() {
    log_info "Creating application directories..."
    
    # Create application directories
    mkdir -p /opt/camunda/{data,logs,backups,ssl}
    mkdir -p /var/log/camunda
    
    # Set permissions
    chmod 755 /opt/camunda
    chmod 755 /var/log/camunda
    
    # Create symlinks for SSL certificates
    if [[ -d /etc/ssl/camunda ]]; then
        ln -sf /etc/ssl/camunda/* /opt/camunda/ssl/ 2>/dev/null || true
    fi
    
    log_success "Application directories created"
}

verify_installation() {
    log_info "Verifying installation..."
    
    local errors=0
    
    # Check Docker
    if ! docker --version &>/dev/null; then
        log_error "Docker installation failed"
        ((errors++))
    else
        log_success "Docker: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose installation failed"
        ((errors++))
    else
        log_success "Docker Compose: $(docker compose version)"
    fi
    
    # Check Docker Swarm
    if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active"; then
        log_error "Docker Swarm not initialized"
        ((errors++))
    else
        log_success "Docker Swarm: Active"
    fi
    
    # Check SSL certificates
    if [[ -f /etc/ssl/camunda/fullchain.pem ]] && [[ -f /etc/ssl/camunda/privkey.pem ]]; then
        log_success "SSL certificates: Present"
    else
        log_warning "SSL certificates: Not found"
    fi
    
    # Check firewall
    if ufw status | grep -q "Status: active"; then
        log_success "Firewall: Active"
    else
        log_warning "Firewall: Not active"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "All components verified successfully!"
        return 0
    else
        log_error "$errors components failed verification"
        return 1
    fi
}

show_summary() {
    log_info "============================================"
    log_info "VM PROVISIONING COMPLETED"
    log_info "============================================"
    echo
    log_success "Docker version: $(docker --version 2>/dev/null || echo 'Not installed')"
    log_success "Docker Compose version: $(docker compose version 2>/dev/null || echo 'Not installed')"
    log_success "Docker Swarm: $(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'Not initialized')"
    log_success "SSL certificates: $(ls /etc/ssl/camunda/*.pem 2>/dev/null | wc -l) files"
    log_success "Firewall status: $(ufw status | head -1 | cut -d: -f2)"
    echo
    log_info "Next steps:"
    echo "  1. Logout and login again (if user was added to docker group)"
    echo "  2. Deploy Camunda ecosystem: make deploy-all"
    echo "  3. Check system status: make status-remote"
    echo "  4. Access Camunda: https://$DOMAIN:8080"
    echo
    log_info "Log file: $LOG_FILE"
}

# Main execution
main() {
    log_info "Starting VM provisioning for Camunda BPM ecosystem..."
    log_info "Domain: $DOMAIN | SSL Provider: $SSL_PROVIDER | Email: $SSL_EMAIL"
    
    check_root
    check_ubuntu
    
    # Create log file
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    # Run provisioning steps
    update_system
    install_system_dependencies
    install_docker
    init_docker_swarm
    setup_directories
    setup_ssl_certificates
    setup_security
    
    # Verify installation
    if verify_installation; then
        show_summary
        log_success "VM provisioning completed successfully!"
        exit 0
    else
        log_error "VM provisioning completed with errors. Check $LOG_FILE for details."
        exit 1
    fi
}

# Handle command line arguments
case "${1:-help}" in
    "docker")
        check_root && check_ubuntu && install_docker
        ;;
    "swarm")
        check_root && init_docker_swarm
        ;;
    "ssl")
        check_root && setup_ssl_certificates
        ;;
    "security")
        check_root && setup_security
        ;;
    "verify")
        verify_installation
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  (no args) - Complete VM provisioning"
        echo "  docker    - Install Docker only"
        echo "  swarm     - Initialize Docker Swarm only"
        echo "  ssl       - Setup SSL certificates only"
        echo "  security  - Configure security hardening only"
        echo "  verify    - Verify installation"
        echo "  help      - Show this help"
        echo
        echo "Environment variables:"
        echo "  DOMAIN=yourdomain.com"
        echo "  SSL_PROVIDER=letsencrypt|selfsigned|custom"
        echo "  SSL_EMAIL=admin@yourdomain.com"
        echo "  SWARM_IP=192.168.1.100"
        ;;
    *)
        main "$@"
        ;;
esac