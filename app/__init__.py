from flask import Flask
from .db import db, migrate
from flask_jwt_extended import JWTManager


def create_app() -> Flask:
	app = Flask(__name__, template_folder='templates')
	app.config.from_object('config.Config')

	db.init_app(app)
	migrate.init_app(app, db)
	JWTManager(app)

	from .routes.auth import bp as auth_bp
	from .routes.membros import bp as membros_bp
	from .routes.views import bp as views_bp
	from .routes.lookups import bp as lookups_bp
	from .routes.users import bp as users_bp
	from .routes.relationships import bp as rel_bp
	from .routes.municipios import bp as municipios_bp
	app.register_blueprint(auth_bp, url_prefix='/api/auth')
	app.register_blueprint(membros_bp, url_prefix='/api')
	app.register_blueprint(lookups_bp, url_prefix='/api')
	app.register_blueprint(users_bp, url_prefix='/api')
	app.register_blueprint(rel_bp, url_prefix='/api')
	app.register_blueprint(municipios_bp, url_prefix='/api')
	app.register_blueprint(views_bp)

	@app.get('/api/health')
	def health():
		return { 'status': 'ok' }

	return app 