import os
import sys
import uvicorn
from backend.config import settings

def main():
    # Read port dynamically from PORT environment variable (assigned by Render/Heroku/Railway)
    # Falling back to settings.PORT or 8000
    env_port = os.getenv('PORT')
    port = int(env_port) if env_port and env_port.isdigit() else getattr(settings, 'PORT', 8000)
    host = os.getenv('HOST', '0.0.0.0')

    print(f'Starting DocuMind on {host}:{port} (PORT env={env_port})...', flush=True)
    uvicorn.run('backend.main:app', host=host, port=port, log_level='info')

if __name__ == '__main__':
    main()
