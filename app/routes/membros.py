from flask import Blueprint

bp = Blueprint('membros', __name__)

@bp.get('/membros')
def list_membros():
	return {'data': [], 'total': 0}

@bp.get('/membros/aggregate')
def aggregate_membros():
	return {'field': '', 'data': []}

@bp.get('/membros/stats')
def stats_membros():
	return {'total': 0, 'female_count': 0, 'female_pct': 0.0}

@bp.post('/membros')
def create_membro():
	return {'success': True, 'id': 1}

@bp.put('/membros/<int:id>')
def update_membro(id: int):
	return {'success': True} 