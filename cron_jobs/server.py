"""
HTTP server for the indicator cron job.

This creates a simple HTTP server that responds to Cloud Scheduler triggers.
When it receives a POST request, it runs the indicator update job.
"""

import asyncio
import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

from update_indicators import update_indicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CronJobHandler(BaseHTTPRequestHandler):
    """HTTP request handler for cron job triggers"""
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"HTTP Request: {format % args}")
    
    def do_GET(self):
        """Handle GET requests for health checks"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'healthy',
                'service': 'indicator-cron-job',
                'timestamp': datetime.utcnow().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to trigger the cron job"""
        try:
            # Log the incoming request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            logger.info(f"Received cron job trigger request from {self.client_address}")
            if post_data:
                logger.debug(f"Request body: {post_data.decode('utf-8', errors='ignore')[:200]}")
            
            # Run the indicator update job
            logger.info("Starting indicator update job...")
            result = asyncio.run(update_indicators())
            
            # Prepare response
            if result['success']:
                self.send_response(200)
                logger.info(f"Cron job completed successfully in {result.get('duration_seconds', 0):.2f} seconds")
            else:
                self.send_response(500)
                logger.error(f"Cron job failed: {result.get('error', 'Unknown error')}")
            
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # Send detailed response
            response = {
                'trigger_timestamp': datetime.utcnow().isoformat(),
                'job_result': result
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            logger.error(f"Error handling POST request: {str(e)}", exc_info=True)
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                'error': 'Internal server error',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode())


def run_server():
    """Run the HTTP server"""
    port = int(os.getenv('PORT', 8080))
    server_address = ('', port)
    
    logger.info(f"Starting HTTP server on port {port}")
    httpd = HTTPServer(server_address, CronJobHandler)
    
    logger.info(f"Cron job server ready to receive triggers")
    logger.info(f"Health check available at: http://localhost:{port}/health")
    logger.info(f"Cron trigger endpoint: http://localhost:{port}/ (POST)")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()