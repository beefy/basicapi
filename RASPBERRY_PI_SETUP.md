# Raspberry Pi Setup Guide - Simple Authentication

This guide shows how to securely connect your Raspberry Pi devices to your FastAPI monitoring system using **standard username/password authentication**. Much simpler than the previous complex system!

## Security Features

✅ **Standard Authentication** - Username and password like any website  
✅ **JWT Tokens** - Secure, time-limited access tokens  
✅ **Dynamic IP Support** - Works from anywhere with any IP address  
✅ **Automatic Token Refresh** - Pi handles login automatically  
✅ **No Complex Setup** - Just register a user and go!  

## How It Works

1. **User Registration** - Create a username/password for each Pi
2. **Pi Login** - Pi logs in and gets a JWT token  
3. **API Calls** - Pi uses token for authenticated requests
4. **Auto-Refresh** - Pi automatically gets new tokens when they expire

## Step 1: Register Your Pi as a User

1. **Start your API server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

2. **Register each Pi as a user**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
          "username": "pi-livingroom",
          "password": "secure-password-here", 
          "full_name": "Living Room Pi Sensor"
        }'
   ```

3. **Test login** to make sure it works:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -u pi-livingroom:secure-password-here
   ```

   You should get back a JWT token like:
   ```json
   {"access_token": "eyJ...", "token_type": "bearer"}
   ```

## Step 2: Setup Raspberry Pi Client

1. **Copy the client script to your Pi**:
   ```bash
   scp raspberry_pi_client.py pi@YOUR_PI_IP:/home/pi/
   ```

2. **Create a simple config file** on your Pi (`/home/pi/pi_config.py`):
   ```python
   # Pi Configuration
   API_URL = "http://your-api-server.com"  # Change to your server
   USERNAME = "pi-livingroom"               # Your Pi's username
   PASSWORD = "secure-password-here"       # Your Pi's password
   AGENT_NAME = "pi-livingroom"            # Name for data logging
   ```

3. **Create the monitoring script** (`/home/pi/pi_monitor.py`):
   ```python
   #!/usr/bin/env python3
   import requests
   import json
   import time
   import psutil
   from datetime import datetime, timedelta
   from pi_config import API_URL, USERNAME, PASSWORD, AGENT_NAME
   
   
   class PiAuth:
       def __init__(self):
           self.token = None
           self.token_expires = None
       
       def login(self):
           """Get new JWT token"""
           try:
               response = requests.post(
                   f"{API_URL}/api/v1/auth/login",
                   auth=(USERNAME, PASSWORD),
                   timeout=10
               )
               if response.status_code == 200:
                   data = response.json()
                   self.token = data["access_token"]
                   # Tokens expire in 30 minutes, refresh at 25 minutes
                   self.token_expires = datetime.now() + timedelta(minutes=25)
                   print(f"✅ Logged in successfully")
                   return True
               else:
                   print(f"❌ Login failed: {response.status_code}")
                   return False
           except Exception as e:
               print(f"❌ Login error: {e}")
               return False
       
       def get_headers(self):
           """Get authorization headers, auto-login if needed"""
           if not self.token or datetime.now() >= self.token_expires:
               if not self.login():
                   raise Exception("Failed to authenticate")
           
           return {"Authorization": f"Bearer {self.token}"}
       
       def post_data(self, endpoint, data):
           """Post data to authenticated endpoint"""
           try:
               response = requests.post(
                   f"{API_URL}{endpoint}",
                   json=data,
                   headers=self.get_headers(),
                   timeout=10
               )
               if response.status_code == 200:
                   print(f"✅ Posted to {endpoint}")
                   return True
               else:
                   print(f"❌ Post failed to {endpoint}: {response.status_code}")
                   return False
           except Exception as e:
               print(f"❌ Post error to {endpoint}: {e}")
               return False
   
   
   def get_system_stats():
       """Get current system statistics"""
       return {
           "agent_name": AGENT_NAME,
           "cpu": psutil.cpu_percent(interval=1),
           "memory": psutil.virtual_memory().percent,
           "disk": psutil.disk_usage('/').percent,
           "ts": datetime.utcnow().isoformat() + "Z"
       }
   
   
   def main():
       print(f"🤖 Starting Pi Monitor for {AGENT_NAME}")
       auth = PiAuth()
       
       # Send system info
       system_stats = get_system_stats()
       auth.post_data("/api/v1/system-info/", system_stats)
       
       # Send status update
       status_update = {
           "agent_name": AGENT_NAME,
           "update_text": f"System check - CPU: {system_stats['cpu']:.1f}%, RAM: {system_stats['memory']:.1f}%",
           "timestamp": datetime.utcnow().isoformat() + "Z"
       }
       auth.post_data("/api/v1/status-updates/", status_update)
       
       # Send heartbeat
       heartbeat = {
           "agent_name": AGENT_NAME,
           "last_heartbeat_ts": datetime.utcnow().isoformat() + "Z"
       }
       auth.post_data("/api/v1/heartbeat/", heartbeat)
       
       print(f"✅ Monitoring complete for {AGENT_NAME}")
   
   
   if __name__ == "__main__":
       main()
   ```

4. **Install required packages** on your Pi:
   ```bash
   pip3 install requests psutil
   ```

5. **Test the script**:
   ```bash
   python3 /home/pi/pi_monitor.py
   ```

## Step 3: Set Up Automated Monitoring

1. **Make the script executable**:
   ```bash
   chmod +x /home/pi/pi_monitor.py
   ```

2. **Add to crontab for automatic execution**:
   ```bash
   crontab -e
   # Add this line to run every 5 minutes:
   */5 * * * * /usr/bin/python3 /home/pi/pi_monitor.py >> /home/pi/monitor.log 2>&1
   ```

3. **Check the logs**:
   ```bash
   tail -f /home/pi/monitor.log
   ```

## Step 4: View Your Data

1. **API Documentation**: http://your-api-server.com/docs
2. **Query data** (no authentication needed for GET):
   ```bash
   # Get all status updates
   curl "http://your-api-server.com/api/v1/status-updates/"
   
   # Get data for specific Pi
   curl "http://your-api-server.com/api/v1/status-updates/?agent_name=pi-livingroom"
   
   # Get system info
   curl "http://your-api-server.com/api/v1/system-info/?agent_name=pi-livingroom"
   ```

## Why This is Much Better

✅ **Simpler** - No device fingerprinting complexity  
✅ **Standard** - Uses normal web authentication everyone understands  
✅ **Secure** - JWT tokens expire automatically (30 minutes)  
✅ **Portable** - Pi can move networks without reconfiguration  
✅ **Debuggable** - Standard HTTP auth tools work  
✅ **Familiar** - Like logging into any website  

## Security Notes

🔒 **Store credentials securely** on your Pi:
- Keep `/home/pi/pi_config.py` permissions restricted: `chmod 600 pi_config.py`
- Use strong passwords for each Pi user account
- Consider using environment variables instead of config files

🛡️ **If someone steals your Pi**:
1. Change the password for that Pi's user account
2. All existing tokens become invalid immediately
3. The thief can't access your API without the new password

⚡ **If you reimage/replace your Pi**:
1. Keep the same username/password
2. Copy the config and monitoring scripts
3. No server-side changes needed!

## Troubleshooting

### "Could not validate credentials"
- Check username/password are correct in `pi_config.py`
- Verify the user account exists on the server
- Test login manually with curl

### Connection timeouts
- Verify your API server is reachable from the Pi
- Check firewall settings
- Ensure API server is running

### No data appearing
- Check the Pi's monitoring logs: `tail -f /home/pi/monitor.log`
- Look for HTTP error codes in the logs
- Test the API endpoints manually from your computer

### "Failed to authenticate" errors
- The JWT token may have expired
- Check if the API server is rejecting logins
- Verify the system clock on your Pi is correct

## Multiple Pi Setup

For multiple Pis, just repeat the process:

1. **Register each Pi** with a unique username:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username": "pi-bedroom", "password": "another-secure-password"}'
   
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username": "pi-kitchen", "password": "yet-another-password"}'
   ```

2. **Update config on each Pi** with its unique credentials

3. **Same monitoring script** works on all Pis!

Much simpler than the old API key system! 🎉