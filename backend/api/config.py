from dotenv import load_dotenv
import os

load_dotenv()

# Получение переменных окружения
POSTGRES_NAME = os.getenv('POSTGRES_NAME')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

smtp_server = os.getenv('smtp_server')
smtp_port = os.getenv('smtp_port')
smtp_user = os.getenv('smtp_user')
smtp_password = os.getenv('smtp_password')

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')

# Проверка наличия всех необходимых переменных
required_vars = ['POSTGRES_NAME', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
                 'POSTGRES_HOST', 'POSTGRES_PORT', 'SECRET_KEY', 'ALGORITHM',
                 'ACCESS_TOKEN_EXPIRE_MINUTES']
missing_vars = [var for var in required_vars if os.getenv(var) is None]

if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(ACCESS_TOKEN_EXPIRE_MINUTES)
except ValueError:
    raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer")
