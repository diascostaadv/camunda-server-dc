#!/usr/bin/env python3
"""
Worker Auto-Discovery System
Automatically discovers workers based on directory structure and worker.json configs
"""

import os
import json
import glob
from typing import Dict, List, Any
from pathlib import Path

class WorkerDiscovery:
    """Discovers and manages worker configurations"""
    
    def __init__(self, workers_dir: str = None):
        self.workers_dir = workers_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.discovered_workers = {}
    
    def discover_workers(self) -> Dict[str, Any]:
        """
        Discover all workers by scanning directories for worker.json files
        """
        workers = {}
        workers_path = Path(self.workers_dir)
        
        print(f"🔍 Scanning for workers in: {workers_path}")
        
        # Look for worker.json files in subdirectories
        for worker_config_path in workers_path.rglob("worker.json"):
            if "_config" in str(worker_config_path) or "_templates" in str(worker_config_path):
                continue
                
            try:
                with open(worker_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                worker_dir = worker_config_path.parent
                worker_name = config.get('name', worker_dir.name)
                
                # Validate required fields
                required_fields = ['name', 'entry_point', 'port']
                missing_fields = [field for field in required_fields if field not in config]
                if missing_fields:
                    print(f"⚠️  Skipping {worker_name}: missing fields {missing_fields}")
                    continue
                
                # Add computed fields
                config['directory'] = str(worker_dir.relative_to(workers_path))
                config['absolute_path'] = str(worker_dir)
                config['config_path'] = str(worker_config_path)
                
                workers[worker_name] = config
                print(f"✅ Discovered worker: {worker_name}")
                
            except Exception as e:
                print(f"❌ Error reading {worker_config_path}: {e}")
                continue
        
        self.discovered_workers = workers
        return workers
    
    def get_worker_config(self, worker_name: str) -> Dict[str, Any]:
        """Get configuration for a specific worker"""
        return self.discovered_workers.get(worker_name, {})
    
    def list_workers(self) -> List[str]:
        """List all discovered worker names"""
        return list(self.discovered_workers.keys())
    
    def validate_worker_structure(self, worker_name: str) -> bool:
        """Validate that worker has required files"""
        config = self.get_worker_config(worker_name)
        if not config:
            return False
            
        worker_path = Path(config['absolute_path'])
        entry_point = worker_path / config['entry_point']
        
        # Check if entry point exists
        if not entry_point.exists():
            print(f"❌ {worker_name}: entry point {config['entry_point']} not found")
            return False
        
        # Check for Dockerfile (optional but recommended)
        dockerfile = worker_path / "Dockerfile"
        if not dockerfile.exists():
            print(f"ℹ️  {worker_name}: no custom Dockerfile, will use default")
        
        return True
    
    def get_docker_config(self, worker_name: str, environment: str = "production") -> Dict[str, Any]:
        """Generate Docker service configuration for a worker"""
        config = self.get_worker_config(worker_name)
        if not config:
            return {}
        
        # Default docker service configuration
        docker_config = {
            "image": f"camunda-workers/{worker_name}:latest",
            "environment": [
                f"CAMUNDA_URL=${{CAMUNDA_URL:-http://camunda:8080}}",
                f"METRICS_PORT=${{WORKER_{worker_name.upper()}_PORT:-{config['port']}}}",
                f"MAX_TASKS=${{MAX_TASKS:-{config.get('max_tasks', 1)}}}",
                f"LOCK_DURATION=${{LOCK_DURATION:-{config.get('lock_duration', 60000)}}}",
                f"ASYNC_RESPONSE_TIMEOUT=${{ASYNC_RESPONSE_TIMEOUT:-{config.get('async_response_timeout', 30000)}}}",
                f"RETRIES=${{RETRIES:-{config.get('retries', 3)}}}",
                f"RETRY_TIMEOUT=${{RETRY_TIMEOUT:-{config.get('retry_timeout', 5000)}}}",
                f"SLEEP_SECONDS=${{SLEEP_SECONDS:-{config.get('sleep_seconds', 30)}}}",
                f"LOG_LEVEL=${{LOG_LEVEL:-{config.get('log_level', 'INFO')}}}",
                f"METRICS_ENABLED=${{METRICS_ENABLED:-{str(config.get('metrics_enabled', True)).lower()}}}",
                f"ENVIRONMENT=${{ENVIRONMENT:-{environment}}}",
                f"WORKERS_MODE=${{WORKERS_MODE:-separated}}"
            ],
            "ports": [
                f"${{WORKER_{worker_name.upper()}_PORT:-{config['port']}}}:{config['port']}"
            ],
            "depends_on": config.get('depends_on', ["camunda"]),
            "networks": ["backend"],
            "deploy": {
                "replicas": config.get('replicas', 1)
            }
        }
        
        # Add custom environment variables
        if 'environment' in config:
            for key, value in config['environment'].items():
                docker_config['environment'].append(f"{key}={value}")
        
        return docker_config
    
    def generate_makefile_commands(self) -> str:
        """Generate Makefile commands for all discovered workers"""
        commands = []
        
        # Add build commands
        commands.append("# ======= AUTO-GENERATED WORKER COMMANDS =================================")
        commands.append("build-all-workers: copy")
        commands.append("\t@echo \"🔨 Building all discovered workers...\"")
        
        for worker_name in self.list_workers():
            commands.append(f"\t@echo \"Building {worker_name}...\"")
            commands.append(f"\t@$(SSH) \"cd $(REMOTE_DIR) && docker build -t camunda-worker-{worker_name}:latest ./workers/{self.get_worker_config(worker_name)['directory']}/\"")
        
        commands.append("\t@echo \"✅ All workers built successfully\"")
        commands.append("")
        
        # Add individual worker commands
        for worker_name in self.list_workers():
            config = self.get_worker_config(worker_name)
            
            # Build command
            commands.append(f"build-worker-{worker_name}: copy")
            commands.append(f"\t@echo \"🔨 Building {worker_name}...\"")
            commands.append(f"\t@$(SSH) \"cd $(REMOTE_DIR) && docker build -t camunda-worker-{worker_name}:latest ./workers/{config['directory']}/\"")
            commands.append("")
            
            # Logs command
            commands.append(f"logs-worker-{worker_name}:")
            commands.append(f"\t@echo \"📋 {worker_name} logs (Ctrl+C to stop)...\"")
            commands.append("ifeq ($(SWARM),active)")
            commands.append(f"\t@$(SSH) \"$(LOG_CMD) -f $(STACK)_worker-{worker_name}\"")
            commands.append("else")
            commands.append(f"\t@$(SSH) \"docker compose logs -f worker-{worker_name}\"")
            commands.append("endif")
            commands.append("")
        
        return "\n".join(commands)
    
    def print_summary(self):
        """Print discovery summary"""
        print(f"\n📊 Discovery Summary:")
        print(f"   Found {len(self.discovered_workers)} workers")
        
        for name, config in self.discovered_workers.items():
            status = "✅" if self.validate_worker_structure(name) else "❌"
            print(f"   {status} {name} (port: {config['port']}, topics: {config.get('topics', [])})")


if __name__ == "__main__":
    discovery = WorkerDiscovery()
    workers = discovery.discover_workers()
    discovery.print_summary()
    
    # Generate sample docker config
    print(f"\n🐳 Sample Docker Config for workers:")
    for worker_name in discovery.list_workers():
        print(f"\n--- {worker_name} ---")
        config = discovery.get_docker_config(worker_name)
        print(json.dumps(config, indent=2))