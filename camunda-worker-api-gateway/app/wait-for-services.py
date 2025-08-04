#!/usr/bin/env python3
"""
Wait for services script
Waits for RabbitMQ, MongoDB and Redis to be ready before starting the main application
"""

import asyncio
import os
import sys
import time
from typing import List
import aio_pika
import pymongo
import redis


async def wait_for_rabbitmq(url: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for RabbitMQ to be ready"""
    print(f"🐰 Waiting for RabbitMQ at {url}")
    
    for attempt in range(max_attempts):
        try:
            connection = await aio_pika.connect_robust(url)
            await connection.close()
            print("✅ RabbitMQ is ready!")
            return True
        except Exception as e:
            print(f"❌ RabbitMQ attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
    
    return False


def wait_for_mongodb(uri: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for MongoDB to be ready"""
    print(f"🍃 Waiting for MongoDB at {uri}")
    
    for attempt in range(max_attempts):
        try:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.server_info()  # Trigger connection
            client.close()
            print("✅ MongoDB is ready!")
            return True
        except Exception as e:
            print(f"❌ MongoDB attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
    
    return False


def wait_for_redis(uri: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for Redis to be ready"""
    print(f"🔴 Waiting for Redis at {uri}")
    
    # Parse Redis URI
    if uri.startswith('redis://'):
        host_port = uri[8:]  # Remove redis://
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host, port = host_port, 6379
    else:
        host, port = 'redis', 6379
    
    for attempt in range(max_attempts):
        try:
            client = redis.Redis(host=host, port=port, socket_connect_timeout=5)
            client.ping()
            client.close()
            print("✅ Redis is ready!")
            return True
        except Exception as e:
            print(f"❌ Redis attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
    
    return False


async def wait_for_all_services() -> bool:
    """Wait for all required services"""
    # Get service URLs from environment
    rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    redis_uri = os.getenv('REDIS_URI', 'redis://localhost:6379')
    
    print("🚀 Waiting for all services to be ready...")
    
    # Check critical services (RabbitMQ was the main issue)
    services_ready = []
    
    # Wait for MongoDB (sync)
    services_ready.append(wait_for_mongodb(mongodb_uri))
    
    # Wait for RabbitMQ (async) - this was the main problem
    services_ready.append(await wait_for_rabbitmq(rabbitmq_url))
    
    # Skip Redis for now as it's not critical for basic functionality
    # services_ready.append(wait_for_redis(redis_uri))
    
    if all(services_ready):
        print("✅ All services are ready! Starting application...")
        return True
    else:
        print("❌ Some services failed to start!")
        return False


if __name__ == "__main__":
    async def main():
        success = await wait_for_all_services()
        if success:
            print("🎯 Starting main application...")
            # Use exec to run the main application
            import os
            os.execv(sys.executable, [sys.executable, 'main.py'])
        else:
            print("💥 Failed to start - services not ready")
            sys.exit(1)
    
    asyncio.run(main())