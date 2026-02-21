#!/usr/bin/env python3
"""
Raspberry Pi API Client with Device Fingerprinting

This script creates a unique device fingerprint for your Raspberry Pi
and uses it along with API keys for secure authentication.
"""

import requests
import json
import os
import sys
import hashlib
import platform
import subprocess
from datetime import datetime

# Configuration
API_BASE_URL = "https://your-api-domain.com/api/v1"  # Change this to your deployed URL
CONFIG_FILE = "/home/pi/api_config.json"

def get_device_fingerprint():
    """Generate a unique device fingerprint for this Raspberry Pi"""
    fingerprint_data = []
    
    try:
        # Get CPU serial number (unique to each Pi)
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'Serial' in line:
                    fingerprint_data.append(line.split(':')[1].strip())
                    break
    except:
        pass
    
    try:
        # Get MAC address of eth0 or wlan0
        result = subprocess.run(['cat', '/sys/class/net/eth0/address'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            fingerprint_data.append(result.stdout.strip())
        else:
            # Try wlan0 if eth0 not available
            result = subprocess.run(['cat', '/sys/class/net/wlan0/address'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                fingerprint_data.append(result.stdout.strip())
    except:
        pass
    
    try:
        # Get board revision
        with open('/proc/device-tree/model', 'r') as f:
            fingerprint_data.append(f.read().strip())
    except:
        pass
    
    # Fallback to hostname and platform info if Pi-specific info not available
    fingerprint_data.extend([
        platform.node(),
        platform.machine(),
        platform.processor()
    ])
    
    # Create hash of all fingerprint data
    fingerprint_string = '|'.join(filter(None, fingerprint_data))
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()


class APIClient:
    def __init__(self, api_key=None, device_id=None, base_url=API_BASE_URL):
        self.base_url = base_url
        self.api_key = api_key
        self.device_id = device_id
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
        if device_id:
            self.headers["X-Device-ID"] = device_id
    
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
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
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
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
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
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
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
    """Initial setup with device fingerprinting"""
    print("🔧 Raspberry Pi API Client Setup with Device Fingerprinting")
    print("=" * 60)
    
    # Generate device fingerprint
    device_fingerprint = get_device_fingerprint()
    print(f"🔍 Device fingerprint: {device_fingerprint[:16]}...{device_fingerprint[-8:]}")
    
    config = load_config()
    
    # Check if device fingerprint has changed (Pi was replaced/reimaged)
    if config.get("device_fingerprint") and config.get("device_fingerprint") != device_fingerprint:
        print("⚠️  Device fingerprint has changed!")
        print("   This could mean the Pi was replaced or reimaged.")
        print("   You'll need to create a new API key for this device.")
        config = {}  # Reset config
    
    config["device_fingerprint"] = device_fingerprint
    
    # Get API key
    if not config.get("api_key"):
        print("\\n📝 You need an API key tied to this specific device.")
        print("\\nTo get an API key:")
        print("1. Go to your API documentation: https://your-domain.com/docs")
        print("2. Login with admin credentials")
        print("3. Use the /api/v1/api-keys/create endpoint")
        print("4. Include this device fingerprint in the request:")
        print(f"   {device_fingerprint}")
        print("\\nExample API key creation request:")
        print(json.dumps({
            "name": "raspberry-pi-1",
            "description": "Living room Pi sensor",
            "device_id": device_fingerprint
        }, indent=2))
        
        api_key = input("\\nEnter your API key: ").strip()
        if not api_key:
            print("❌ API key is required!")
            sys.exit(1)
        config["api_key"] = api_key
    
    # Get agent name
    if not config.get("agent_name"):
        default_name = f"rpi-{platform.node()}"
        agent_name = input(f"\\nAgent name [{default_name}]: ").strip() or default_name
        config["agent_name"] = agent_name
    
    # Test connection
    client = APIClient(config["api_key"], device_fingerprint)
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
    print("\\n🔒 Security Features:")
    print(f"   • Device fingerprint: {device_fingerprint[:16]}...{device_fingerprint[-8:]}")
    print("   • API key tied to this specific device")
    print("   • Only this Pi can use this API key")
    print("\\nNext steps:")
    print("1. Set up a cron job to run monitoring:")
    print("   crontab -e")
    print("   Add: */5 * * * * /usr/bin/python3 /home/pi/monitor.py")
    print("2. Test the monitoring script:")
    print("   python3 /home/pi/monitor.py")


def monitor():
    """Main monitoring function with device fingerprinting"""
    config = load_config()
    
    if not config.get("api_key") or not config.get("agent_name"):
        print("❌ Not configured! Run with --setup first.")
        sys.exit(1)
    
    # Verify device fingerprint hasn't changed
    current_fingerprint = get_device_fingerprint()
    if config.get("device_fingerprint") != current_fingerprint:
        print("❌ Device fingerprint mismatch!")
        print("   The device appears to have changed. Run --setup again.")
        sys.exit(1)
    
    client = APIClient(config["api_key"], current_fingerprint)
    agent_name = config["agent_name"]
    
    # Send heartbeat
    heartbeat_result = client.send_heartbeat(agent_name)
    
    # Send system stats
    stats = get_system_stats()
    stats_result = client.send_system_info(
        agent_name,
        stats["cpu"],
        stats["memory"],
        stats["disk"]
    )
    
    if heartbeat_result and stats_result:
        print(f"✅ Monitoring data sent for {agent_name}")
    else:
        print(f"❌ Failed to send monitoring data for {agent_name}")
        sys.exit(1)


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