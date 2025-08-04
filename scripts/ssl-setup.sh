#!/bin/bash
# ============================================================================
# SSL CERTIFICATE SETUP SCRIPT
# ============================================================================
# Manages SSL certificates for Camunda BPM ecosystem
# Supports Let's Encrypt, self-signed, and custom certificates
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SSL_DIR="/etc/ssl/camunda"
CERT_FILE="$SSL_DIR/fullchain.pem"
KEY_FILE="$SSL_DIR/privkey.pem"
DOMAIN="${DOMAIN:-localhost}"
SSL_EMAIL="${SSL_EMAIL:-admin@example.com}"
SSL_PROVIDER="${SSL_PROVIDER:-selfsigned}"

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

validate_domain() {
    if [[ -z "$DOMAIN" ]] || [[ "$DOMAIN" == "localhost" ]] && [[ "$SSL_PROVIDER" == "letsencrypt" ]]; then
        log_error "Let's Encrypt requires a valid public domain. Use SSL_PROVIDER=selfsigned for localhost."
    fi
    
    log_info "Setting up SSL certificates for domain: $DOMAIN"
}

setup_directories() {
    log_info "Creating SSL directories..."
    
    mkdir -p "$SSL_DIR"
    mkdir -p /opt/camunda/ssl
    
    # Set proper permissions
    chmod 755 "$SSL_DIR"
    chmod 755 /opt/camunda/ssl
    
    log_success "SSL directories created"
}

install_letsencrypt() {
    log_info "Installing Let's Encrypt certificates..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        log_info "Installing certbot..."
        apt-get update -qq
        apt-get install -y -qq certbot
    fi
    
    # Validate domain is not localhost
    if [[ "$DOMAIN" == "localhost" ]] || [[ "$DOMAIN" == *".local"* ]] || [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Let's Encrypt requires a valid public domain name (not localhost, .local, or IP address)"
    fi
    
    # Check if port 80 is available
    if ss -tlnp | grep -q ":80 "; then
        log_warning "Port 80 is in use. Stopping web services temporarily..."
        systemctl stop nginx apache2 2>/dev/null || true
        sleep 2
    fi
    
    # Generate certificate using standalone mode
    log_info "Generating Let's Encrypt certificate for $DOMAIN..."
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$SSL_EMAIL" \
        --domains "$DOMAIN" \
        --preferred-challenges http
    
    # Copy certificates to our directory
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_FILE"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$KEY_FILE"
    
    # Set permissions
    chmod 644 "$CERT_FILE"
    chmod 600 "$KEY_FILE"
    
    # Setup auto-renewal
    setup_letsencrypt_renewal
    
    log_success "Let's Encrypt certificate installed successfully"
}

setup_letsencrypt_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > /usr/local/bin/renew-camunda-cert.sh << 'EOF'
#!/bin/bash
# Auto-renewal script for Camunda SSL certificates

certbot renew --quiet --deploy-hook "
    # Copy renewed certificates
    cp /etc/letsencrypt/live/*/fullchain.pem /etc/ssl/camunda/
    cp /etc/letsencrypt/live/*/privkey.pem /etc/ssl/camunda/
    chmod 644 /etc/ssl/camunda/fullchain.pem
    chmod 600 /etc/ssl/camunda/privkey.pem
    
    # Update symlinks
    ln -sf /etc/ssl/camunda/* /opt/camunda/ssl/
    
    # Restart services that use SSL
    docker service update --force camunda_camunda 2>/dev/null || true
    systemctl reload nginx 2>/dev/null || true
"
EOF
    
    chmod +x /usr/local/bin/renew-camunda-cert.sh
    
    # Add to crontab (runs twice daily as recommended by Let's Encrypt)
    (crontab -l 2>/dev/null; echo "0 12,0 * * * /usr/local/bin/renew-camunda-cert.sh") | sort -u | crontab -
    
    log_success "Automatic renewal configured (runs twice daily)"
}

generate_selfsigned() {
    log_info "Generating self-signed SSL certificate..."
    
    # Generate private key
    openssl genrsa -out "$KEY_FILE" 2048
    
    # Create certificate signing request config
    cat > /tmp/cert.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = BR
ST = State
L = City
O = Camunda Organization
OU = IT Department
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = localhost
DNS.3 = *.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
    
    # Add additional IPs if provided
    if [[ -n "${ADDITIONAL_IPS:-}" ]]; then
        local ip_counter=3
        IFS=',' read -ra IPS <<< "$ADDITIONAL_IPS"
        for ip in "${IPS[@]}"; do
            echo "IP.$ip_counter = $ip" >> /tmp/cert.conf
            ((ip_counter++))
        done
    fi
    
    # Generate certificate
    openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 -config /tmp/cert.conf -extensions v3_req
    
    # Set permissions
    chmod 644 "$CERT_FILE"
    chmod 600 "$KEY_FILE"
    
    # Clean up
    rm -f /tmp/cert.conf
    
    log_success "Self-signed certificate generated for $DOMAIN (valid for 365 days)"
}

install_custom_certificates() {
    log_info "Setting up custom SSL certificates..."
    
    # Check if custom certificate files are provided
    if [[ -n "${CUSTOM_CERT_PATH:-}" ]] && [[ -n "${CUSTOM_KEY_PATH:-}" ]]; then
        if [[ -f "$CUSTOM_CERT_PATH" ]] && [[ -f "$CUSTOM_KEY_PATH" ]]; then
            cp "$CUSTOM_CERT_PATH" "$CERT_FILE"
            cp "$CUSTOM_KEY_PATH" "$KEY_FILE"
            
            chmod 644 "$CERT_FILE"
            chmod 600 "$KEY_FILE"
            
            log_success "Custom certificates installed"
        else
            log_error "Custom certificate files not found at specified paths"
        fi
    else
        log_error "Custom certificate setup requires CUSTOM_CERT_PATH and CUSTOM_KEY_PATH environment variables"
        echo "Example:"
        echo "  CUSTOM_CERT_PATH=/path/to/cert.pem CUSTOM_KEY_PATH=/path/to/key.pem $0 custom"
    fi
}

create_symlinks() {
    log_info "Creating certificate symlinks..."
    
    # Create symlinks in application directory
    ln -sf "$CERT_FILE" /opt/camunda/ssl/fullchain.pem
    ln -sf "$KEY_FILE" /opt/camunda/ssl/privkey.pem
    
    log_success "Certificate symlinks created"
}

verify_certificates() {
    log_info "Verifying SSL certificates..."
    
    local errors=0
    
    # Check if certificate files exist
    if [[ ! -f "$CERT_FILE" ]]; then
        log_error "Certificate file not found: $CERT_FILE"
        ((errors++))
    fi
    
    if [[ ! -f "$KEY_FILE" ]]; then
        log_error "Private key file not found: $KEY_FILE"
        ((errors++))
    fi
    
    if [[ $errors -gt 0 ]]; then
        return 1
    fi
    
    # Verify certificate is valid
    if ! openssl x509 -in "$CERT_FILE" -text -noout &>/dev/null; then
        log_error "Invalid certificate file"
        return 1
    fi
    
    # Verify private key matches certificate
    cert_hash=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
    key_hash=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
    
    if [[ "$cert_hash" != "$key_hash" ]]; then
        log_error "Private key does not match certificate"
        return 1
    fi
    
    # Show certificate information
    log_success "Certificate verification passed"
    
    echo
    log_info "Certificate Information:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A1 "Subject:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A1 "Issuer:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A2 "Validity"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A5 "Subject Alternative Name" || log_info "No Subject Alternative Names found"
    
    return 0
}

show_certificate_info() {
    if [[ ! -f "$CERT_FILE" ]]; then
        log_warning "No certificate found at $CERT_FILE"
        return 1
    fi
    
    echo
    log_info "============================================"
    log_info "SSL CERTIFICATE INFORMATION"
    log_info "============================================"
    
    echo "Certificate File: $CERT_FILE"
    echo "Private Key File: $KEY_FILE"
    echo
    
    # Certificate details
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After|DNS:|IP Address:)"
    
    # Check expiration
    local expiry=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry" +%s)
    local current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    echo
    if [[ $days_until_expiry -lt 30 ]]; then
        log_warning "Certificate expires in $days_until_expiry days!"
    else
        log_info "Certificate expires in $days_until_expiry days"
    fi
}

# Main execution functions
setup_ssl() {
    log_info "Setting up SSL certificates (provider: $SSL_PROVIDER)..."
    
    check_root
    validate_domain
    setup_directories
    
    case "$SSL_PROVIDER" in
        "letsencrypt")
            install_letsencrypt
            ;;
        "selfsigned")
            generate_selfsigned
            ;;
        "custom")
            install_custom_certificates
            ;;
        *)
            log_error "Unknown SSL provider: $SSL_PROVIDER. Use: letsencrypt, selfsigned, or custom"
            ;;
    esac
    
    create_symlinks
    
    if verify_certificates; then
        log_success "SSL certificates setup completed successfully!"
        show_certificate_info
    else
        log_error "SSL certificate setup failed verification"
    fi
}

# Handle command line arguments
case "${1:-help}" in
    "letsencrypt")
        SSL_PROVIDER="letsencrypt" setup_ssl
        ;;
    "selfsigned")
        SSL_PROVIDER="selfsigned" setup_ssl
        ;;
    "custom")
        SSL_PROVIDER="custom" setup_ssl
        ;;
    "verify")
        verify_certificates
        ;;
    "info")
        show_certificate_info
        ;;
    "renew")
        if [[ -f /usr/local/bin/renew-camunda-cert.sh ]]; then
            /usr/local/bin/renew-camunda-cert.sh
        else
            log_error "Renewal script not found. Only available for Let's Encrypt certificates."
        fi
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  letsencrypt - Install Let's Encrypt certificate"
        echo "  selfsigned  - Generate self-signed certificate"
        echo "  custom      - Install custom certificate"
        echo "  verify      - Verify existing certificates"
        echo "  info        - Show certificate information"
        echo "  renew       - Renew Let's Encrypt certificate"
        echo "  help        - Show this help"
        echo
        echo "Environment variables:"
        echo "  DOMAIN=yourdomain.com          - Domain name for certificate"
        echo "  SSL_EMAIL=admin@yourdomain.com - Email for Let's Encrypt"
        echo "  ADDITIONAL_IPS=1.2.3.4,5.6.7.8 - Additional IPs for self-signed"
        echo "  CUSTOM_CERT_PATH=/path/to/cert.pem - Custom certificate file"
        echo "  CUSTOM_KEY_PATH=/path/to/key.pem   - Custom private key file"
        echo
        echo "Examples:"
        echo "  $0 letsencrypt"
        echo "  DOMAIN=mysite.com SSL_EMAIL=admin@mysite.com $0 letsencrypt"
        echo "  DOMAIN=localhost $0 selfsigned"
        echo "  CUSTOM_CERT_PATH=/tmp/cert.pem CUSTOM_KEY_PATH=/tmp/key.pem $0 custom"
        ;;
    *)
        setup_ssl
        ;;
esac