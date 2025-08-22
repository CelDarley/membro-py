from flask import Flask
from .db import db, migrate
from flask_jwt_extended import JWTManager

def create_app() -> Flask:
	app = Flask(__name__)
	app.config.from_object('config.Config')

	db.init_app(app)
	migrate.init_app(app, db)
	JWTManager(app)

	from .routes.auth import bp as auth_bp
	from .routes.membros import bp as membros_bp
	app.register_blueprint(auth_bp, url_prefix='/api/auth')
	app.register_blueprint(membros_bp, url_prefix='/api')

	@app.get('/api/health')
	def health():
		return { 'status': 'ok' }

	return app 