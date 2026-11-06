from dotenv import load_dotenv
import os

load_dotenv()

class Configuration:
    API_PORT = int(os.getenv("API_PORT"))
    API_HOST = str(os.getenv("API_HOST"))
    DB_HOST = str(os.getenv("DB_HOST"))
    DB_USER = str(os.getenv("DB_USER"))
    DB_PASSWORD= str(os.getenv("DB_PASSWORD"))
    DB_NAME = str(os.getenv("DB_NAME"))
    SECRET_KEY= str(os.getenv("SECRET_KEY"))
    TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES"))
    RESEND_API_KEY = str(os.getenv("RESEND_API_KEY"))
    RABBIT_HOST = str(os.getenv("RABBIT_HOST"))
    RABBIT_PORT = int(os.getenv("RABBIT_PORT"))
    RABBIT_USER = str(os.getenv("RABBIT_USER"))
    RABBIT_PASSWORD = str(os.getenv("RABBIT_PASSWORD"))

Config = Configuration()