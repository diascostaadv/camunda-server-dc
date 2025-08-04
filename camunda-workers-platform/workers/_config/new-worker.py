#!/usr/bin/env python3
"""
New Worker Generator
Creates a new worker from template with interactive setup
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
import argparse
import re


class WorkerGenerator:
    """Generates new workers from templates"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.workers_dir = self.script_dir.parent
        self.templates_dir = self.workers_dir / "_templates"
    
    def get_available_ports(self):
        """Get list of ports already in use by other workers"""
        used_ports = set()
        
        for worker_config in self.workers_dir.rglob("worker.json"):
            if "_templates" in str(worker_config) or "_config" in str(worker_config):
                continue
                
            try:
                with open(worker_config, 'r') as f:
                    config = json.load(f)
                    if 'port' in config:
                        used_ports.add(config['port'])
            except:
                continue
        
        return used_ports
    
    def suggest_port(self, used_ports):
        """Suggest next available port starting from 8001"""
        port = 8001
        while port in used_ports:
            port += 1
        return port
    
    def validate_worker_name(self, name):
        """Validate worker name follows conventions"""
        # Only lowercase, numbers, hyphens, underscores
        if not re.match(r'^[a-z0-9_-]+$', name):
            return False, "Worker name must contain only lowercase letters, numbers, hyphens, and underscores"
        
        # Must start with letter
        if not name[0].isalpha():
            return False, "Worker name must start with a letter"
        
        # Check if already exists
        worker_dir = self.workers_dir / name
        if worker_dir.exists():
            return False, f"Worker '{name}' already exists"
        
        return True, ""
    
    def get_class_name(self, worker_name):
        """Convert worker name to class name (PascalCase)"""
        # Replace hyphens and underscores with spaces, title case, remove spaces
        return ''.join(word.capitalize() for word in re.split(r'[-_]', worker_name)) + "Worker"
    
    def get_topic_name(self, worker_name):
        """Convert worker name to topic name"""
        # Replace hyphens with underscores
        return worker_name.replace('-', '_')
    
    def interactive_setup(self):
        """Interactive setup for new worker"""
        print("🚀 Camunda Worker Generator")
        print("==========================")
        
        # Get worker name
        while True:
            worker_name = input("\n📝 Worker name (e.g., 'email-sender', 'data-processor'): ").strip().lower()
            if not worker_name:
                print("❌ Worker name is required")
                continue
            
            valid, error = self.validate_worker_name(worker_name)
            if not valid:
                print(f"❌ {error}")
                continue
            
            break
        
        # Get description
        description = input(f"📝 Description (default: '{worker_name.replace('-', ' ').title()} Worker'): ").strip()
        if not description:
            description = f"{worker_name.replace('-', ' ').title()} Worker"
        
        # Get topic
        default_topic = self.get_topic_name(worker_name)
        topic = input(f"📝 Main topic name (default: '{default_topic}'): ").strip()
        if not topic:
            topic = default_topic
        
        # Get port
        used_ports = self.get_available_ports()
        suggested_port = self.suggest_port(used_ports)
        
        while True:
            port_input = input(f"📝 Port number (default: {suggested_port}): ").strip()
            if not port_input:
                port = suggested_port
                break
            
            try:
                port = int(port_input)
                if port < 1024 or port > 65535:
                    print("❌ Port must be between 1024 and 65535")
                    continue
                if port in used_ports:
                    print(f"❌ Port {port} is already in use")
                    continue
                break
            except ValueError:
                print("❌ Port must be a number")
                continue
        
        # Custom Dockerfile
        use_custom_dockerfile = input("📝 Use custom Dockerfile? (y/n, default: n): ").strip().lower() == 'y'
        
        return {
            'name': worker_name,
            'description': description,
            'topic': topic,
            'port': port,
            'class_name': self.get_class_name(worker_name),
            'use_custom_dockerfile': use_custom_dockerfile
        }
    
    def create_worker(self, config):
        """Create worker from template with given configuration"""
        worker_dir = self.workers_dir / config['name']
        worker_dir.mkdir(exist_ok=True)
        
        print(f"\n🔨 Creating worker '{config['name']}'...")
        
        # Template replacements
        replacements = {
            '{{WORKER_NAME}}': config['name'],
            '{{WORKER_DESCRIPTION}}': config['description'],
            '{{WORKER_TOPIC}}': config['topic'],
            '{{WORKER_PORT}}': str(config['port']),
            '{{WORKER_CLASS_NAME}}': config['class_name'],
            '{{CREATION_DATE}}': datetime.now().isoformat()
        }
        
        # Copy and process templates
        templates = ['worker.json', 'main.py']
        if config['use_custom_dockerfile']:
            templates.append('Dockerfile')
        
        for template in templates:
            template_path = self.templates_dir / template
            target_path = worker_dir / template
            
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Apply replacements
                for placeholder, value in replacements.items():
                    content = content.replace(placeholder, value)
                
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"   ✅ Created {template}")
            else:
                print(f"   ⚠️  Template {template} not found")
        
        # Create README
        readme_content = f"""# {config['description']}

Auto-generated worker for Camunda BPM.

## Configuration

- **Name**: {config['name']}
- **Port**: {config['port']}
- **Topic**: {config['topic']}
- **Entry Point**: main.py

## Usage

### Local Development
```bash
cd workers/{config['name']}
python main.py
```

### Docker
```bash
# Build image
docker build -t camunda-worker-{config['name']}:latest .

# Run container
docker run -p {config['port']}:{config['port']} camunda-worker-{config['name']}:latest
```

### Deploy with Make
```bash
# Build this worker
make build-worker-{config['name']}

# View logs
make logs-worker-{config['name']}

# Deploy all workers
make deploy-workers
```

## Business Logic

Edit the `process_business_logic` method in `main.py` to implement your specific requirements.

## Environment Variables

The worker supports all standard Camunda worker environment variables plus any custom ones defined in `worker.json`.
"""
        
        readme_path = worker_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"   ✅ Created README.md")
        
        print(f"\n🎉 Worker '{config['name']}' created successfully!")
        print(f"   📁 Location: {worker_dir}")
        print(f"   🌐 Port: {config['port']}")
        print(f"   📡 Topic: {config['topic']}")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Edit {worker_dir}/main.py to implement your business logic")
        print(f"   2. Test locally: cd {worker_dir} && python main.py")
        print(f"   3. Deploy: make build-worker-{config['name']} && make deploy")
    
    def create_from_args(self, args):
        """Create worker from command line arguments"""
        used_ports = self.get_available_ports()
        port = args.port or self.suggest_port(used_ports)
        
        valid, error = self.validate_worker_name(args.name)
        if not valid:
            print(f"❌ {error}")
            return False
        
        if port in used_ports:
            print(f"❌ Port {port} is already in use")
            return False
        
        config = {
            'name': args.name,
            'description': args.description or f"{args.name.replace('-', ' ').title()} Worker",
            'topic': args.topic or self.get_topic_name(args.name),
            'port': port,
            'class_name': self.get_class_name(args.name),
            'use_custom_dockerfile': args.dockerfile
        }
        
        self.create_worker(config)
        return True


def main():
    parser = argparse.ArgumentParser(description='Generate new Camunda worker from template')
    parser.add_argument('name', nargs='?', help='Worker name (interactive if not provided)')
    parser.add_argument('--description', help='Worker description')
    parser.add_argument('--topic', help='Main topic name')
    parser.add_argument('--port', type=int, help='Port number')
    parser.add_argument('--dockerfile', action='store_true', help='Create custom Dockerfile')
    
    args = parser.parse_args()
    generator = WorkerGenerator()
    
    if args.name:
        # Command line mode
        success = generator.create_from_args(args)
        if not success:
            exit(1)
    else:
        # Interactive mode
        try:
            config = generator.interactive_setup()
            generator.create_worker(config)
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            exit(1)


if __name__ == "__main__":
    main()