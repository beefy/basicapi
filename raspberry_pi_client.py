#!/usr/bin/env python3
"""
Raspberry Pi API Client Setup Script

This script helps configure your Raspberry Pi to securely communicate 
with your FastAPI monitoring system.
"""

import requests
import json
import os
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "https://your-api-domain.com/api/v1"  # Change this to your deployed URL
CONFIG_FILE = "/home/pi/api_config.json"

class APIClient:
    def __init__(self, api_key=None, base_url=API_BASE_URL):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    def test_connection(self):
        """Test if the API is reachable"""
        try:
            response = requests.get(f"{self.base_url.replace('/api/v1', '')}/health", timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def send_status_update(self, agent_name, update_text):
        """Send a status update"""
        data = {
            "agent_name": agent_name,
            "update_text": update_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            response = requests.post(
                f"{self.base_url}/status-updates/",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send status update: {e}")
            return None
    
    def send_system_info(self, agent_name, cpu, memory, disk):
        """Send system information"""
        data = {
            "agent_name": agent_name,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "ts": datetime.utcnow().isoformat()
        }
        try:
            response = requests.post(
                f"{self.base_url}/system-info/",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send system info: {e}")
            return None
    
    def send_heartbeat(self, agent_name):
        """Send heartbeat"""
        data = {
            "agent_name": agent_name,
            "last_heartbeat_ts": datetime.utcnow().isoformat()
        }
        try:
            response = requests.post(
                f"{self.base_url}/heartbeat/",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send heartbeat: {e}")
            return None


def get_system_stats():
    """Get basic system statistics"""
    import psutil
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }


def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save configuration to file"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def setup():
    """Initial setup"""
    print("🔧 Raspberry Pi API Client Setup")
    print("=" * 40)
    
    config = load_config()
    
    # Get API key
    if not config.get("api_key"):
        print("\\n📝 You need an API key to authenticate with the monitoring API.")
        print("\\nTo get an API key:")
        print("1. Go to your API documentation: https://your-domain.com/docs")
        print("2. Login with admin credentials")
        print("3. Use the /api/v1/api-keys/create endpoint")
        print("4. Copy the generated API key")
        
        api_key = input("\\nEnter your API key: ").strip()
        if not api_key:
            print("❌ API key is required!")
            sys.exit(1)
        config["api_key"] = api_key
    
    # Get agent name
    if not config.get("agent_name"):
        default_name = f"rpi-{os.uname().nodename}"
        agent_name = input(f"\\nAgent name [{default_name}]: ").strip() or default_name
        config["agent_name"] = agent_name
    
    # Test connection
    client = APIClient(config["api_key"])
    print(f"\\n🔌 Testing connection to {API_BASE_URL}...")
    
    if client.test_connection():
        print("✅ API connection successful!")
        
        # Send initial heartbeat
        result = client.send_heartbeat(config["agent_name"])
        if result:
            print(f"✅ Initial heartbeat sent for agent: {config['agent_name']}")
        
        # Send system info
        stats = get_system_stats()
        result = client.send_system_info(
            config["agent_name"],
            stats["cpu"],
            stats["memory"],
            stats["disk"]
        )
        if result:
            print("✅ System info sent successfully!")
        
    else:
        print("❌ API connection failed!")
        print("Check your internet connection and API URL.")
        sys.exit(1)
    
    # Save configuration
    save_config(config)
    print(f"\\n💾 Configuration saved to {CONFIG_FILE}")
    
    print("\\n🎉 Setup complete!")
    print("\\nNext steps:")
    print("1. Set up a cron job to run monitoring:")
    print("   crontab -e")
    print("   Add: */5 * * * * /usr/bin/python3 /home/pi/monitor.py")
    print("2. Test the monitoring script:")
    print("   python3 /home/pi/monitor.py")


def monitor():
    """Main monitoring function"""
    config = load_config()
    
    if not config.get("api_key") or not config.get("agent_name"):
        print("❌ Not configured! Run with --setup first.")
        sys.exit(1)
    
    client = APIClient(config["api_key"])
    agent_name = config["agent_name"]
    
    # Send heartbeat
    client.send_heartbeat(agent_name)
    
    # Send system stats
    stats = get_system_stats()
    client.send_system_info(
        agent_name,
        stats["cpu"],
        stats["memory"],
        stats["disk"]
    )
    
    print(f"✅ Monitoring data sent for {agent_name}")


if __name__ == "__main__":
    # Install required packages if not present
    try:
        import psutil
        import requests
    except ImportError:
        print("Installing required packages...")
        os.system("pip3 install psutil requests")
        import psutil
        import requests
    
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup()
    else:
        monitor()