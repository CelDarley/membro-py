import os
from dotenv import load_dotenv

load_dotenv()


class Config:
	SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
	JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt')
	SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@127.0.0.1:3306/membro')
	SQLALCHEMY_TRACK_MODIFICATIONS = False 