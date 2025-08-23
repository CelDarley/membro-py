from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func
from ..db import db
from ..models import Lookup, Membro

bp = Blueprint('lookups', __name__)

ALLOWED_TYPES = {
	'concurso',
	'cargo_efetivo',
	'titularidade',
	'cargo_especial',
	'unidade_lotacao',
	'comarca_lotacao',
	'time_extraprofissionais',
	'estado_origem',
	'grupos_identitarios',
}

UF_LIST = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']


def is_admin_identity():
	claims = get_jwt() or {}
	return (claims.get('role') or '').lower() == 'admin'


@bp.get('/lookups')
@jwt_required()
def list_lookups():
	type_ = (request.args.get('type') or '').strip().lower()
	if type_ not in ALLOWED_TYPES:
		return {'data': [], 'total': 0}
	q = (request.args.get('q') or '').strip()
	page = int(request.args.get('page', 1))
	per_page = int(request.args.get('per_page', 30))
	query = Lookup.query.filter(Lookup.type == type_)
	if q:
		query = query.filter(Lookup.value.ilike(f'%{q}%'))
	p = query.order_by(Lookup.value.asc()).paginate(page=page, per_page=per_page, error_out=False)
	items = p.items
	# Se for estado_origem e não houver registros, retornar UFs padrão
	if type_ == 'estado_origem' and not items:
		data = [{'id': None, 'type': 'estado_origem', 'value': uf} for uf in UF_LIST if (not q) or (q and uf.lower().find(q.lower()) != -1)]
		return {'data': data, 'total': len(data)}
	data = [{'id': it.id, 'type': it.type, 'value': it.value} for it in items]
	return {'data': data, 'total': p.total}


@bp.post('/lookups')
@jwt_required()
def create_lookup():
	if not is_admin_identity():
		return {'message': 'Apenas administradores.'}, 403
	body = request.get_json() or {}
	type_ = (body.get('type') or '').strip().lower()
	value = (body.get('value') or '').strip()
	if type_ not in ALLOWED_TYPES or not value:
		return {'message': 'Dados inválidos'}, 422
	# evitar duplicado
	exists = Lookup.query.filter_by(type=type_, value=value).first()
	if exists:
		return {'id': exists.id, 'type': exists.type, 'value': exists.value}
	lk = Lookup(type=type_, value=value)
	db.session.add(lk)
	db.session.commit()
	return {'id': lk.id, 'type': lk.type, 'value': lk.value}


@bp.put('/lookups/<int:id>')
@jwt_required()
def update_lookup(id: int):
	if not is_admin_identity():
		return {'message': 'Apenas administradores.'}, 403
	lk = Lookup.query.get_or_404(id)
	body = request.get_json() or {}
	value = (body.get('value') or '').strip()
	if not value:
		return {'message': 'Valor inválido'}, 422
	# check unique
	exists = Lookup.query.filter(Lookup.type == lk.type, Lookup.value == value, Lookup.id != lk.id).first()
	if exists:
		return {'message': 'Valor já cadastrado'}, 422
	lk.value = value
	db.session.commit()
	return {'success': True}


@bp.delete('/lookups/<int:id>')
@jwt_required()
def delete_lookup(id: int):
	if not is_admin_identity():
		return {'message': 'Apenas administradores.'}, 403
	lk = Lookup.query.get_or_404(id)
	db.session.delete(lk)
	db.session.commit()
	return {'success': True}


@bp.post('/lookups/populate-from-membros')
@jwt_required()
def populate_from_membros():
	if not is_admin_identity():
		return {'message': 'Apenas administradores.'}, 403
	# map: lookup type -> column
	mapping = {
		'concurso': Membro.concurso,
		'cargo_efetivo': Membro.cargo_efetivo,
		'titularidade': Membro.titularidade,
		'cargo_especial': Membro.cargo_especial,
		'unidade_lotacao': Membro.unidade_lotacao,
		'comarca_lotacao': Membro.comarca_lotacao,
		'time_extraprofissionais': Membro.time_extraprofissionais,
		'estado_origem': Membro.estado_origem,
		'grupos_identitarios': Membro.grupos_identitarios,
	}
	inserted = 0
	# Inserir UFs padrão para estado_origem
	for uf in UF_LIST:
		if not Lookup.query.filter_by(type='estado_origem', value=uf).first():
			db.session.add(Lookup(type='estado_origem', value=uf))
			inserted += 1
	# Popular demais tipos a partir dos membros
	for t, col in mapping.items():
		vals = [r[0] for r in db.session.query(col).filter(col.isnot(None)).distinct().all()]
		for v in vals:
			v = str(v).strip()
			if not v:
				continue
			if not Lookup.query.filter_by(type=t, value=v).first():
				db.session.add(Lookup(type=t, value=v))
				inserted += 1
	db.session.commit()
	return {'inserted': inserted} 