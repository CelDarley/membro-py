from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import IntegrityError
from ..db import db
from ..models import Membro, MembroRelacionamento

bp = Blueprint('relationships', __name__)

ALLOWED_DEGREES = {'spouse','parent','child','sibling'}


def is_admin():
	claims = get_jwt() or {}
	return (claims.get('role') or '').lower() == 'admin'


@bp.get('/membros/<int:id>/relationships')
@jwt_required()
def list_relationships(id: int):
	# lista relacionamentos de saída e de entrada para exibir ambos
	rels_out = MembroRelacionamento.query.filter_by(source_id=id).all()
	rels_in = MembroRelacionamento.query.filter_by(target_id=id).all()
	def fmt(r: MembroRelacionamento, direction: str):
		other_id = r.target_id if direction=='out' else r.source_id
		other = Membro.query.get(other_id)
		return { 'id': r.id, 'degree': r.degree, 'direction': direction, 'other_id': other_id, 'other_name': other.nome if other else ('#'+str(other_id)) }
	data = [fmt(r,'out') for r in rels_out] + [fmt(r,'in') for r in rels_in]
	return { 'data': data }


@bp.get('/relationships')
@jwt_required()
def list_all_relationships():
	degree = (request.args.get('degree') or '').strip().lower()
	query = MembroRelacionamento.query
	if degree and degree in ALLOWED_DEGREES:
		query = query.filter_by(degree=degree)
	rels = query.limit(50000).all()
	return { 'data': [ { 'id': r.id, 'source_id': r.source_id, 'target_id': r.target_id, 'degree': r.degree } for r in rels ] }


@bp.post('/membros/<int:id>/relationships')
@jwt_required()
def add_relationship(id: int):
	if not is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	body = request.get_json() or {}
	target_id = int(body.get('target_id') or 0)
	degree = str(body.get('degree') or '').strip().lower()
	if not target_id or degree not in ALLOWED_DEGREES:
		return { 'message': 'Dados inválidos' }, 422
	if target_id == id:
		return { 'message': 'Não é possível relacionar com o próprio registro' }, 422
	if not Membro.query.get(target_id):
		return { 'message': 'Membro destino não encontrado' }, 404
	rel = MembroRelacionamento(source_id=id, target_id=target_id, degree=degree)
	try:
		db.session.add(rel)
		db.session.commit()
		return { 'id': rel.id }
	except IntegrityError:
		db.session.rollback()
		return { 'message': 'Relacionamento já existe' }, 422
	except Exception as e:
		db.session.rollback()
		return { 'message': f'Erro ao adicionar: {str(e)[:200]}' }, 422


@bp.delete('/relationships/<int:rel_id>')
@jwt_required()
def delete_relationship(rel_id: int):
	if not is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	rel = MembroRelacionamento.query.get_or_404(rel_id)
	db.session.delete(rel)
	db.session.commit()
	return { 'success': True } 