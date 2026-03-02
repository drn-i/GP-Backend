import os
from dotenv import load_dotenv

load_dotenv()

# Default to development
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')