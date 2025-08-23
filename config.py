import os
from dotenv import load_dotenv

load_dotenv()


class Config:
	SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
	JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt')
	SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@127.0.0.1:3306/membro')
	SQLALCHEMY_TRACK_MODIFICATIONS = False

	# SMTP
	MAIL_SERVER = os.getenv('MAIL_SERVER', '')
	MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
	MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
	MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
	MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
	MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', '')) 