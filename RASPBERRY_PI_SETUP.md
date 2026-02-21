# Raspberry Pi Setup Guide - Device Fingerprinting Authentication

This guide shows how to securely connect your Raspberry Pi devices to your FastAPI monitoring system using **device fingerprinting** instead of IP whitelisting. This approach works perfectly with dynamic IP addresses.

## Security Features

✅ **Device Fingerprinting** - Each Pi has a unique hardware-based fingerprint  
✅ **API Key + Device ID** - API keys are tied to specific hardware  
✅ **Hardware-based Security** - Uses CPU serial, MAC address, board model  
✅ **Dynamic IP Support** - Works from anywhere with any IP address  
✅ **Usage Tracking** - See when each device was last used  

## How It Works

1. **Device Fingerprint Generation** - The Pi creates a unique ID based on:
   - CPU serial number (unique to each Pi)
   - MAC address of network interface  
   - Board model and revision
   - Hostname and platform info

2. **API Key Registration** - Admin creates API keys tied to specific device fingerprints

3. **Authentication** - Each API call includes both the API key and device fingerprint

4. **Verification** - Server verifies the API key AND that it matches the device fingerprint

## Step 1: No IP Configuration Needed! 🎉

Unlike IP whitelisting, you don't need to configure any IP addresses. The system works with dynamic IPs automatically.

## Step 2: Get Device Fingerprint from Your Pi

1. **Copy the client script to your Pi**:
   ```bash
   scp raspberry_pi_client.py pi@YOUR_PI_IP:/home/pi/
   ```

2. **SSH into your Pi and get the device fingerprint**:
   ```bash
   ssh pi@YOUR_PI_IP
   cd /home/pi
   python3 -c "
   import sys
   sys.path.append('.')
   from raspberry_pi_client import get_device_fingerprint
   print('Device Fingerprint:', get_device_fingerprint())
   "
   ```

   **Save this fingerprint** - you'll need it to create the API key!

## Step 3: Generate API Keys

1. **Start your API server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

2. **Get an admin token**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/token" \
        -u admin:secret
   ```

3. **Create API keys for each Pi with their device fingerprint**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/api-keys/create" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "raspberry-pi-1",
          "description": "Living room Pi sensor",
          "device_id": "YOUR_PI_DEVICE_FINGERPRINT_HERE"
        }'
   ```

   **Save the returned API key** - it's only shown once!

## Step 4: Setup Raspberry Pi

1. **Copy the client script to your Pi**:
   ```bash
   scp raspberry_pi_client.py pi@YOUR_PI_IP:/home/pi/
   ```

2. **SSH into your Pi and run setup**:
   ```bash
   ssh pi@YOUR_PI_IP
   cd /home/pi
   python3 raspberry_pi_client.py --setup
   ```

3. **Enter your API key** when prompted

4. **Test the connection** - the script will send initial data

## Step 4: Set Up Automated Monitoring

1. **Create a monitoring script** (`/home/pi/monitor.py`):
   ```python
   #!/usr/bin/env python3
   import subprocess
   import sys
   
   # Run the monitoring
   subprocess.run([sys.executable, "/home/pi/raspberry_pi_client.py"])
   ```

2. **Make it executable**:
   ```bash
   chmod +x /home/pi/monitor.py
   ```

3. **Add to crontab for automatic execution**:
   ```bash
   crontab -e
   # Add this line to run every 5 minutes:
   */5 * * * * /usr/bin/python3 /home/pi/monitor.py >> /home/pi/monitor.log 2>&1
   ```

## Step 5: Test Everything

1. **Test API key authentication**:
   ```bash
   # From your Pi
   curl -X POST "http://your-api-domain.com/api/v1/status-updates/" \
        -H "X-API-Key: YOUR_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
          "agent_name": "raspberry-pi-1",
          "update_text": "Test from Pi"
        }'
   ```

2. **Check the API logs** to see data coming in

3. **View the data** at `http://your-api-domain.com/docs`

## API Usage Examples

### Send Status Update
```python
import requests

headers = {
    "X-API-Key": "your-api-key-here",
    "X-Device-ID": "your-device-fingerprint"
}
data = {
    "agent_name": "raspberry-pi-1",
    "update_text": "Sensor readings normal",
    "timestamp": "2024-01-01T12:00:00"
}

response = requests.post(
    "http://your-api-domain.com/api/v1/status-updates/",
    json=data,
    headers=headers
)
```

## Why Device Fingerprinting is Better Than IP Whitelisting

✅ **Dynamic IP Support** - Works with any internet connection  
✅ **Hardware Security** - Tied to actual physical device  
✅ **No Network Config** - No need to manage IP lists  
✅ **Travel Friendly** - Pi can work from anywhere  
✅ **Harder to Spoof** - Requires physical access to the device  

## Security Notes

🔒 **Device fingerprints include**:
- CPU serial number (unique to each Pi)
- MAC address of primary network interface
- Board model and revision information
- Platform and hostname details

🛡️ **If someone steals your Pi**:
1. Delete the API key from your server
2. The thief can't create a new key (requires admin access)
3. Even with the API key, they need the exact hardware fingerprint

⚡ **If you reimage/replace your Pi**:
1. The device fingerprint will change
2. Create a new API key with the new fingerprint
3. Delete the old key from the server