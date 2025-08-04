#!/usr/bin/env python3
"""
Docker Compose Generator
Generates docker-compose.swarm.yml dynamically based on discovered workers
"""

import os
import sys
import yaml
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from worker_discovery import WorkerDiscovery


class ComposeGenerator:
    """Generates Docker Compose files for Camunda stack with auto-discovered workers"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.workers_dir = self.script_dir.parent
        self.camunda_dir = self.workers_dir.parent
        self.discovery = WorkerDiscovery()
    
    def get_base_services(self):
        """Get base services (DB, Camunda, monitoring)"""
        return {
            "db": {
                "image": "postgres:16.3",
                "environment": [
                    "POSTGRES_DB=${POSTGRES_DB:-camunda}",
                    "POSTGRES_USER=${POSTGRES_USER:-camunda}",
                    "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-camunda}"
                ],
                "volumes": [
                    "db_data:/var/lib/postgresql/data"
                ],
                "networks": ["backend"],
                "deploy": {
                    "replicas": 1,
                    "placement": {
                        "constraints": ["node.role == manager"]
                    }
                }
            },
            "camunda": {
                "image": "camunda/camunda-bpm-platform:run-7.23.0",
                "environment": [
                    "DB_DRIVER=org.postgresql.Driver",
                    "DB_URL=${DATABASE_URL:-jdbc:postgresql://db:5432/camunda}",
                    "DB_USERNAME=${POSTGRES_USER:-camunda}",
                    "DB_PASSWORD=${POSTGRES_PASSWORD:-camunda}",
                    "WAIT_FOR=db:5432",
                    "TZ=${TZ:-America/Sao_Paulo}",
                    "JAVA_OPTS=-javaagent:/camunda/javaagent/jmx_prometheus_javaagent.jar=${CAMUNDA_JMX_PORT:-9404}:/camunda/config/prometheus-jmx.yml"
                ],
                "ports": [
                    "${CAMUNDA_PORT:-8080}:8080",
                    "${CAMUNDA_JMX_PORT:-9404}:${CAMUNDA_JMX_PORT:-9404}"
                ],
                "volumes": [
                    "./config/prometheus-jmx.yml:/camunda/config/prometheus-jmx.yml",
                    "./resources:/camunda/webapps/engine-rest/WEB-INF/classes/"
                ],
                "depends_on": ["db"],
                "networks": ["backend"],
                "deploy": {
                    "replicas": 1,
                    "placement": {
                        "constraints": ["node.role == manager"]
                    }
                }
            },
            "prometheus": {
                "image": "prom/prometheus:latest",
                "ports": [
                    "${PROMETHEUS_PORT:-9090}:9090"
                ],
                "volumes": [
                    "./config/prometheus.yml:/etc/prometheus/prometheus.yml",
                    "prometheus_data:/prometheus"
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--web.enable-lifecycle"
                ],
                "networks": ["backend"],
                "deploy": {
                    "replicas": 1,
                    "placement": {
                        "constraints": ["node.role == manager"]
                    }
                }
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "ports": [
                    "${GRAFANA_PORT:-3001}:3000"
                ],
                "environment": [
                    "GF_SECURITY_ADMIN_PASSWORD=${GF_SECURITY_ADMIN_PASSWORD:-admin}",
                    "GF_SECURITY_ADMIN_USER=${GF_SECURITY_ADMIN_USER:-admin}"
                ],
                "volumes": [
                    "grafana_data:/var/lib/grafana",
                    "./config/grafana/provisioning:/etc/grafana/provisioning"
                ],
                "depends_on": ["prometheus"],
                "networks": ["backend"],
                "deploy": {
                    "replicas": 1,
                    "placement": {
                        "constraints": ["node.role == manager"]
                    }
                }
            }
        }
    
    def generate_worker_service(self, worker_name, config):
        """Generate Docker service configuration for a worker"""
        return {
            "image": f"camunda-workers/{worker_name}:latest",
            "environment": [
                "CAMUNDA_URL=${CAMUNDA_URL:-http://camunda:8080}",
                f"METRICS_PORT=${{WORKER_{worker_name.upper().replace('-', '_')}_PORT:-{config['port']}}}",
                f"MAX_TASKS=${{MAX_TASKS:-{config.get('max_tasks', 1)}}}",
                f"LOCK_DURATION=${{LOCK_DURATION:-{config.get('lock_duration', 60000)}}}",
                f"ASYNC_RESPONSE_TIMEOUT=${{ASYNC_RESPONSE_TIMEOUT:-{config.get('async_response_timeout', 30000)}}}",
                f"RETRIES=${{RETRIES:-{config.get('retries', 3)}}}",
                f"RETRY_TIMEOUT=${{RETRY_TIMEOUT:-{config.get('retry_timeout', 5000)}}}",
                f"SLEEP_SECONDS=${{SLEEP_SECONDS:-{config.get('sleep_seconds', 30)}}}",
                f"LOG_LEVEL=${{LOG_LEVEL:-{config.get('log_level', 'INFO')}}}",
                f"METRICS_ENABLED=${{METRICS_ENABLED:-{str(config.get('metrics_enabled', True)).lower()}}}",
                "ENVIRONMENT=${ENVIRONMENT:-production}",
                "WORKERS_MODE=${WORKERS_MODE:-separated}"
            ] + [f"{k}={v}" for k, v in config.get('environment', {}).items()],
            "ports": [
                f"${{WORKER_{worker_name.upper().replace('-', '_')}_PORT:-{config['port']}}}:{config['port']}"
            ],
            # No dependencies - workers connect externally
            "networks": ["backend"],
            "deploy": {
                "replicas": config.get('replicas', 1)
            }
        }
    
    def generate_compose_file(self, output_path=None):
        """Generate workers-only docker-compose.swarm.yml file"""
        if not output_path:
            output_path = self.camunda_dir / "docker-compose.swarm.yml"
        
        # Discover workers
        workers = self.discovery.discover_workers()
        
        print(f"🔍 Discovered {len(workers)} workers")
        
        # Start with empty services (workers-only mode)
        services = {}
        
        # Add worker services
        for worker_name, config in workers.items():
            if not self.discovery.validate_worker_structure(worker_name):
                print(f"⚠️  Skipping {worker_name}: invalid structure")
                continue
            
            service_name = f"worker-{worker_name}"
            services[service_name] = self.generate_worker_service(worker_name, config)
            print(f"✅ Added service: {service_name}")
        
        # Complete compose structure (workers-only)
        compose_content = {
            "version": "3.9",
            "services": services,
            "networks": {
                "backend": {
                    "driver": "overlay",
                    "external": True
                }
            }
        }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            # Add header comment
            f.write("# Auto-generated docker-compose.swarm.yml\n")
            f.write("# Generated by workers/_config/generate-compose.py\n")
            # f.write(f"# Workers discovered: {', '.join(workers.keys())}\n")
            f.write("# DO NOT EDIT MANUALLY - Use 'make generate-compose' to regenerate\n\n")
            
            yaml.dump(compose_content, f, default_flow_style=False, indent=2, sort_keys=False)
        
        print(f"✅ Generated: {output_path}")
        print(f"   Services: {len(services)} (workers only)")
        
        return output_path
    
    def generate_env_template(self, output_path=None):
        """Generate .env template with all worker ports"""
        if not output_path:
            output_path = self.camunda_dir / ".env.template"
        
        workers = self.discovery.discover_workers()
        
        env_content = [
            "# Auto-generated environment template",
            "# Generated by workers/_config/generate-compose.py",
            "",
            "# Base Configuration",
            "ENVIRONMENT=production",
            "WORKERS_MODE=separated",
            "GATEWAY_MODE=false",
            "",
            "# Camunda Configuration",
            "CAMUNDA_PORT=8080",
            "CAMUNDA_JMX_PORT=9404",
            "CAMUNDA_URL=http://camunda:8080",
            "",
            "# Database Configuration",
            "POSTGRES_DB=camunda",
            "POSTGRES_USER=camunda",
            "POSTGRES_PASSWORD=camunda",
            "DATABASE_URL=jdbc:postgresql://db:5432/camunda",
            "",
            "# Monitoring Configuration",
            "PROMETHEUS_PORT=9090",
            "GRAFANA_PORT=3001",
            "GF_SECURITY_ADMIN_USER=admin",
            "GF_SECURITY_ADMIN_PASSWORD=admin",
            "",
            "# Worker Ports (Auto-discovered)",
        ]
        
        for worker_name, config in workers.items():
            env_var = f"WORKER_{worker_name.upper().replace('-', '_')}_PORT"
            env_content.append(f"{env_var}={config['port']}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_content))
        
        print(f"✅ Generated: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print generation summary"""
        workers = self.discovery.discovered_workers
        
        print(f"\n📊 Generated Configuration Summary:")
        print(f"   Total workers: {len(workers)}")
        print(f"   Total services: {len(workers)} (workers only)")
        
        if workers:
            print(f"\n🔧 Workers configured:")
            for name, config in workers.items():
                print(f"   • {name} (port: {config['port']}, topics: {config.get('topics', [])})")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Review generated docker-compose.swarm.yml")
        print(f"   2. Update .env files as needed")
        print(f"   3. Build workers: make build-all-workers")
        print(f"   4. Deploy: make deploy")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate docker-compose.swarm.yml with auto-discovered workers')
    parser.add_argument('--output', '-o', help='Output file path for docker-compose.swarm.yml')
    parser.add_argument('--env-template', help='Generate .env template file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing files')
    
    args = parser.parse_args()
    
    generator = ComposeGenerator()
    
    if args.dry_run:
        # Just show discovery results
        workers = generator.discovery.discover_workers()
        generator.discovery.print_summary()
        generator.print_summary()
    else:
        # Generate files
        generator.generate_compose_file(args.output)
        
        if args.env_template:
            generator.generate_env_template(args.env_template)
        
        generator.print_summary()


if __name__ == "__main__":
    main()