# Raspberry Pi Setup Guide

This guide shows how to securely connect your Raspberry Pi devices to your FastAPI monitoring system using API keys.

## Security Features

✅ **API Key Authentication** - Each Pi has its own API key  
✅ **IP Allowlisting** - Only specified IPs can use API keys  
✅ **Automatic Key Rotation** - Easy to generate/revoke keys  
✅ **Usage Tracking** - See when each key was last used  

## Step 1: Configure Allowed IPs

Edit the allowed IPs in your API server:

```python
# In app/core/deps.py, update ALLOWED_IPS list:
ALLOWED_IPS = [
    "127.0.0.1",           # Localhost
    "192.168.1.100",       # Raspberry Pi 1
    "192.168.1.101",       # Raspberry Pi 2  
    "192.168.1.0/24",      # Entire home network
    "your.static.ip.here", # Your external IP if needed
]
```

## Step 2: Generate API Keys

1. **Start your API server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

2. **Get an admin token**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/token" \
        -u admin:secret
   ```

3. **Create API keys for each Pi**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/api-keys/create" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "raspberry-pi-1",
          "description": "Living room Pi sensor"
        }'
   ```

   **Save the returned API key** - it's only shown once!

## Step 3: Setup Raspberry Pi

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

headers = {"X-API-Key": "your-api-key-here"}
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

### Send System Info
```python
data = {
    "agent_name": "raspberry-pi-1",
    "cpu": 45.2,
    "memory": 67.8,
    "disk": 23.1
}

response = requests.post(
    "http://your-api-domain.com/api/v1/system-info/",
    json=data,
    headers=headers
)
```

### Send Heartbeat
```python
data = {
    "agent_name": "raspberry-pi-1",
    "last_heartbeat_ts": "2024-01-01T12:00:00"
}

response = requests.post(
    "http://your-api-domain.com/api/v1/heartbeat/",
    json=data,
    headers=headers
)
```

## API Key Management

### List all API keys
```bash
curl -X GET "http://localhost:8000/api/v1/api-keys/list" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Delete an API key
```bash
curl -X DELETE "http://localhost:8000/api/v1/api-keys/raspberry-pi-1" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Security Best Practices

1. **Use HTTPS in production** - Never send API keys over HTTP
2. **Rotate API keys regularly** - Generate new keys periodically
3. **Monitor usage** - Check the last_used timestamps
4. **Use specific IP ranges** - Don't use 0.0.0.0/0
5. **Firewall your API server** - Only allow necessary ports
6. **Use environment variables** - Don't hardcode API keys in scripts

## Troubleshooting

### "Access denied from IP"
- Check that your Pi's IP is in the ALLOWED_IPS list
- Verify your Pi's actual IP with `curl ifconfig.me`

### "Invalid API key"
- Ensure the API key is correct and not expired
- Check that the key exists with the list endpoint

### Connection timeouts
- Verify your API server is reachable
- Check firewall settings
- Ensure MongoDB is running

### No data appearing
- Check the Pi's monitoring logs: `tail -f /home/pi/monitor.log`
- Verify the API server logs for errors
- Test manual API calls from the Pi