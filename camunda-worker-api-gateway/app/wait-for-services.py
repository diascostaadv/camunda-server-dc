#!/usr/bin/env python3
"""
Wait for services script
Waits for MongoDB to be ready before starting the main application
"""

import os
import sys
import time
import pymongo


def wait_for_mongodb(uri: str, max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for MongoDB to be ready"""
    print(f"🍃 Waiting for MongoDB at : xxxxxxx")

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


def wait_for_all_services() -> bool:
    """Wait for all required services"""
    # Check if using external services
    external_mode = os.getenv("EXTERNAL_SERVICES_MODE", "false").lower() == "true"

    # Get service URLs from environment
    mongodb_uri = os.getenv(
        "MONGODB_URI",
        "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/",
    )

    print("🚀 Waiting for all services to be ready...")

    if external_mode:
        print("📡 Using external services mode - checking MongoDB Atlas connection...")
        # For external mode, only check MongoDB Atlas
        if "mongodb+srv" in mongodb_uri or "mongodb.net" in mongodb_uri:
            print(f"☁️ Connecting to MongoDB Atlas...")
            services_ready = [wait_for_mongodb(mongodb_uri)]
        else:
            print(f"🗄️ Connecting to MongoDB: {mongodb_uri[:50]}...")
            services_ready = [wait_for_mongodb(mongodb_uri)]
    else:
        print("🗄️ Using local services mode - checking MongoDB...")
        # Check critical services
        services_ready = []

        # Wait for MongoDB (sync)
        services_ready.append(wait_for_mongodb(mongodb_uri))

    if all(services_ready):
        print("✅ All services are ready! Starting application...")
        return True
    else:
        print("❌ Some services failed to start!")
        return False


if __name__ == "__main__":
    success = wait_for_all_services()
    if success:
        print("🎯 Starting main application...")
        # Use exec to run the main application
        import os

        os.execv(sys.executable, [sys.executable, "main.py"])
    else:
        print("💥 Failed to start - services not ready")
        sys.exit(1)
