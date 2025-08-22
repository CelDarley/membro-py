from flask import Blueprint

bp = Blueprint('auth', __name__)

@bp.get('/me')
def me():
	return {'user': None}, 200 