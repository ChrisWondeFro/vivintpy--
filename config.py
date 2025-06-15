import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Project root

USERNAME = os.getenv("VIVINT_USER")
PASSWORD = os.getenv("VIVINT_PASS")
REFRESH_TOKEN_FILE = os.getenv("REFRESH_TOKEN_FILE")
