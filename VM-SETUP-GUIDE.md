# VM Setup Guide - Camunda BPM Ecosystem

This guide explains how to set up a fresh Ubuntu VM for the Camunda BPM ecosystem using the automated setup commands.

## Quick Start

### Complete VM Setup (Recommended)
```bash
# Setup complete VM with default settings (self-signed SSL)
make vm-setup

# Setup with Let's Encrypt SSL
DOMAIN=yourdomain.com SSL_EMAIL=admin@yourdomain.com SSL_PROVIDER=letsencrypt make vm-setup

# Setup without confirmation prompt
make vm-setup-force
```

### Remote VM Setup
```bash
# Setup remote VM (uses default HOST from Makefile)
make vm-setup-remote

# Setup specific remote host
make vm-setup-remote HOST=192.168.1.100

# Setup with custom SSH key
SSH_KEY=/path/to/key VM_USER=root make vm-setup-remote HOST=1.2.3.4
```

## Individual Setup Commands

### Docker Installation
```bash
# Install Docker + Docker Compose + Initialize Swarm
make vm-setup-docker
```

### SSL Certificates
```bash
# Generate self-signed certificate (default)
make vm-setup-ssl

# Let's Encrypt certificate
DOMAIN=yourdomain.com SSL_PROVIDER=letsencrypt make vm-setup-ssl

# Custom certificate
CUSTOM_CERT_PATH=/path/to/cert.pem CUSTOM_KEY_PATH=/path/to/key.pem SSL_PROVIDER=custom make vm-setup-ssl
```

### Security Hardening
```bash
# Configure firewall, fail2ban, security settings
make vm-setup-security
```

### Testing and Verification
```bash
# Test VM setup completeness
make vm-test

# Show SSL certificate information
./scripts/ssl-setup.sh info

# Show security status
./scripts/security-setup.sh status
```

## What Gets Installed

### Complete VM Setup (`make vm-setup`) includes:

1. **System Updates**
   - Latest Ubuntu packages
   - Essential system tools (curl, wget, git, htop, etc.)
   - Network and monitoring tools

2. **Docker Environment**
   - Docker CE (latest)
   - Docker Compose (latest)
   - Docker Swarm initialization
   - Backend overlay network creation

3. **SSL Certificates**
   - Self-signed certificates (default)
   - Let's Encrypt certificates (if configured)
   - Custom certificates (if provided)
   - Auto-renewal setup (for Let's Encrypt)

4. **Security Hardening**
   - UFW firewall configuration (ports for Camunda ecosystem)
   - Fail2ban installation and configuration
   - SSH security hardening
   - System security parameters
   - Log rotation setup

5. **Application Structure**
   - `/opt/camunda/` directories (data, logs, backups, ssl)
   - `/var/log/camunda/` logging directory
   - Proper permissions and ownership

## Environment Variables

### SSL Configuration
```bash
DOMAIN=yourdomain.com              # Domain for SSL certificate
SSL_PROVIDER=letsencrypt          # letsencrypt, selfsigned, custom
SSL_EMAIL=admin@yourdomain.com    # Email for Let's Encrypt
ADDITIONAL_IPS=1.2.3.4,5.6.7.8   # Additional IPs for self-signed certs
```

### SSH Configuration (for remote setup)
```bash
VM_USER=ubuntu                    # SSH username
VM_HOST=201.23.67.197            # Default remote host
SSH_PORT=22                      # SSH port
SSH_KEY=~/.ssh/mac_m2_ssh        # SSH private key path
```

### Docker Configuration
```bash
SWARM_IP=192.168.1.100           # Swarm advertise IP (auto-detected if not set)
```

## Supported Operating Systems

- **Ubuntu 20.04 LTS** (Recommended)
- **Ubuntu 22.04 LTS** (Recommended)
- **Ubuntu 18.04 LTS** (Supported with warnings)

## Network Ports Configured

The firewall is automatically configured to allow:

| Port  | Service                    | Description                          |
|-------|----------------------------|--------------------------------------|
| 22    | SSH                        | Remote access                        |
| 80    | HTTP                       | Web traffic                          |
| 443   | HTTPS                      | Secure web traffic                   |
| 8080  | Camunda BPM               | Camunda web applications             |
| 9090  | Prometheus                | Metrics monitoring                   |
| 3001  | Grafana                   | Monitoring dashboard                 |
| 8000  | API Gateway               | Worker API Gateway                   |
| 8001  | Worker 1                  | Hello World Worker                   |
| 8002  | Worker 2                  | Publicacao Worker                    |
| 15672 | RabbitMQ Management       | Message queue management             |
| 2376-2377 | Docker                | Docker daemon and Swarm management   |
| 7946  | Docker Swarm              | Node communication                   |
| 4789  | Docker Overlay            | Overlay network traffic              |

## Post-Setup Steps

After VM setup completion:

1. **Logout and login again** (if user was added to docker group)
2. **Deploy the ecosystem:**
   ```bash
   make deploy-all              # Complete production deployment
   make platform-deploy         # Platform only
   make start                   # Local development
   ```
3. **Verify services:**
   ```bash
   make status                  # Local status
   make status-remote           # Remote status
   make health                  # Health checks
   ```
4. **Access services:**
   - Camunda: `https://yourdomain.com:8080` (admin/admin)
   - Prometheus: `https://yourdomain.com:9090`
   - Grafana: `https://yourdomain.com:3001` (admin/admin)

## Troubleshooting

### Permission Issues
If you get permission errors, ensure you're running with sudo:
```bash
sudo make vm-setup-force
```

### SSH Connection Issues
Check SSH configuration:
```bash
ssh -i ~/.ssh/mac_m2_ssh ubuntu@your-server-ip
```

### SSL Certificate Issues
Check certificate status:
```bash
./scripts/ssl-setup.sh verify
./scripts/ssl-setup.sh info
```

### Docker Issues
Verify Docker installation:
```bash
sudo ./scripts/vm-provision.sh verify
docker --version
docker info
```

### Firewall Issues
Check firewall status:
```bash
./scripts/security-setup.sh status
sudo ufw status numbered
```

## Complete Setup Example

Here's a complete example of setting up a production VM:

```bash
# 1. Clean setup (if needed)
make vm-clean-force

# 2. Set up VM with Let's Encrypt SSL
DOMAIN=camunda.mycompany.com \
SSL_EMAIL=admin@mycompany.com \
SSL_PROVIDER=letsencrypt \
make vm-setup-force

# 3. Deploy ecosystem
make deploy-all

# 4. Verify everything is working
make health
make status

# 5. Access Camunda
# https://camunda.mycompany.com:8080
```

## Script Locations

- **Main VM Setup:** `./scripts/vm-provision.sh`
- **SSL Management:** `./scripts/ssl-setup.sh`  
- **Security Hardening:** `./scripts/security-setup.sh`

Each script can be run independently with various options. Use `script.sh help` to see available commands.