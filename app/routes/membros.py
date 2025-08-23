from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func
from ..db import db
from ..models import Membro
import json

bp = Blueprint('membros', __name__)


def label_to_column(label: str):
	m = {
		'Membro': Membro.nome,
		'Mamp': None,  # não temos coluna separada
		'Sexo': Membro.sexo,
		'Concurso': Membro.concurso,
		'Cargo efetivo': Membro.cargo_efetivo,
		'Titularidade': Membro.titularidade,
		'eMail pessoal': Membro.email_pessoal,
		'Cargo Especial': Membro.cargo_especial,
		'Telefone Unidade': Membro.telefone_unidade,
		'Telefone celular': Membro.telefone_celular,
		'Unidade Lotação': Membro.unidade_lotacao,
		'Comarca Lotação': Membro.comarca_lotacao,
		'Time de futebol e outros grupos extraprofissionais': Membro.time_extraprofissionais,
		'Quantidade de filhos': Membro.quantidade_filhos,
		'Nome dos filhos': Membro.nomes_filhos,
		'Estado de origem': Membro.estado_origem,
		'Acadêmico': Membro.academico,
		'Pretensão de movimentação na carreira': Membro.pretensao_carreira,
		'Carreira anterior': Membro.carreira_anterior,
		'Liderança': Membro.lideranca,
		'Grupos identitários': Membro.grupos_identitarios,
	}
	return m.get((label or '').strip())


def apply_filters(query):
	q = (request.args.get('q') or '').strip()
	if q:
		like = f"%{q}%"
		query = query.filter(
			(Membro.nome.ilike(like)) | (Membro.comarca_lotacao.ilike(like)) | (Membro.cargo_efetivo.ilike(like))
		)
	# filtros por coluna vindos do front
	filters_json = request.args.get('filters_json')
	if filters_json:
		try:
			filters = json.loads(filters_json)
			if isinstance(filters, dict):
				for label, values in filters.items():
					if not values:
						continue
					col = label_to_column(label)
					if not col:
						continue
					# normalizar values para strings
					vals = [str(v).strip() for v in values if v is not None and str(v).strip() != '']
					if not vals:
						continue
					query = query.filter(col.in_(vals))
		except Exception:
			pass
	return query


def to_row(m: Membro):
	amigos = list(m.amigos)  # pode consultar
	return {
		'id': m.id,
		'data': {
			'Membro': m.nome,
			'Sexo': m.sexo,
			'Concurso': m.concurso,
			'Cargo efetivo': m.cargo_efetivo,
			'Titularidade': m.titularidade,
			'eMail pessoal': m.email_pessoal,
			'Cargo Especial': m.cargo_especial,
			'Telefone Unidade': m.telefone_unidade,
			'Telefone celular': m.telefone_celular,
			'Unidade Lotação': m.unidade_lotacao,
			'Comarca Lotação': m.comarca_lotacao,
			'Time de futebol e outros grupos extraprofissionais': m.time_extraprofissionais,
			'Quantidade de filhos': m.quantidade_filhos,
			'Nome dos filhos': m.nomes_filhos,
			'Estado de origem': m.estado_origem,
			'Acadêmico': m.academico,
			'Pretensão de movimentação na carreira': m.pretensao_carreira,
			'Carreira anterior': m.carreira_anterior,
			'Liderança': m.lideranca,
			'Grupos identitários': m.grupos_identitarios,
			'Amigos no MP (IDs)': [a.id for a in amigos],
			'Amigos no MP (Nomes)': [a.nome for a in amigos],
		}
	}


@bp.get('/membros')
@jwt_required()
def list_membros():
	query = apply_filters(Membro.query)
	page = int(request.args.get('page', 1))
	per_page = int(request.args.get('per_page', 20))
	p = query.order_by(Membro.nome.asc(), Membro.id.asc()).paginate(page=page, per_page=per_page, error_out=False)
	data = [to_row(m) for m in p.items]
	return {'data': data, 'total': p.total}


@bp.get('/membros/<int:id>')
@jwt_required()
def get_membro(id: int):
	m = Membro.query.get_or_404(id)
	return to_row(m)


@bp.get('/membros/aggregate')
@jwt_required()
def aggregate_membros():
	field = (request.args.get('field') or '').strip()
	col = label_to_column(field)
	if not col:
		return {'field': field, 'data': []}
	query = apply_filters(Membro.query)
	rows = query.with_entities(col.label('v'), func.count(Membro.id).label('c')).group_by(col).order_by(func.count(Membro.id).desc()).limit(int(request.args.get('limit', 50))).all()
	data = [ {'v': r.v, 'c': int(r.c)} for r in rows if r.v ]
	return {'field': field, 'data': data}


@bp.get('/membros/distinct')
@jwt_required()
def distinct_membros():
	field = (request.args.get('field') or '').strip()
	limit = int(request.args.get('limit', 200))
	col = label_to_column(field)
	if not col:
		return {'field': field, 'values': []}
	query = apply_filters(Membro.query)
	vals = [r[0] for r in query.with_entities(col).filter(col.isnot(None)).distinct().order_by(col.asc()).limit(limit).all()]
	return {'field': field, 'values': vals}


@bp.get('/membros/suggest')
@jwt_required()
def suggest_membros():
	q = (request.args.get('q') or '').strip()
	query = Membro.query
	if q:
		like = f"%{q}%"
		query = query.filter(Membro.nome.ilike(like))
	vals = [r[0] for r in query.with_entities(Membro.nome).filter(Membro.nome.isnot(None)).order_by(Membro.nome.asc()).limit(20).all()]
	return {'values': vals}


@bp.get('/membros/search-min')
@jwt_required()
def search_min_membros():
	q = (request.args.get('q') or '').strip()
	query = Membro.query
	if q:
		like = f"%{q}%"
		query = query.filter(Membro.nome.ilike(like))
	rows = query.order_by(Membro.nome.asc()).limit(20).all()
	return {'data': [{'id': m.id, 'nome': m.nome} for m in rows]}


@bp.get('/membros/stats')
@jwt_required()
def stats_membros():
	query = apply_filters(Membro.query)
	total = query.count()
	female = query.filter(Membro.sexo == 'Feminino').count()
	pct = round((female * 100 / total), 1) if total else 0.0
	return {'total': total, 'female_count': female, 'female_pct': pct}


@bp.post('/membros')
@jwt_required()
def create_membro():
	claims = get_jwt() or {}
	role = (claims.get('role') or '').lower()
	if role != 'admin':
		return { 'message': 'Apenas administradores podem criar registros.' }, 403
	data = (request.get_json() or {}).get('data') or {}
	m = Membro(
		nome=data.get('Membro') or data.get('Nome'),
		sexo=data.get('Sexo'),
		concurso=data.get('Concurso'),
		cargo_efetivo=data.get('Cargo efetivo'),
		titularidade=data.get('Titularidade'),
		email_pessoal=data.get('eMail pessoal'),
		cargo_especial=data.get('Cargo Especial'),
		telefone_unidade=data.get('Telefone Unidade'),
		telefone_celular=data.get('Telefone celular'),
		unidade_lotacao=data.get('Unidade Lotação'),
		comarca_lotacao=data.get('Comarca Lotação'),
		time_extraprofissionais=data.get('Time de futebol e outros grupos extraprofissionais'),
		quantidade_filhos=(int(data.get('Quantidade de filhos')) if data.get('Quantidade de filhos') not in (None, '') else None),
		nomes_filhos=data.get('Nome dos filhos'),
		estado_origem=(data.get('Estado de origem')[:2] if data.get('Estado de origem') else None),
		academico=data.get('Acadêmico'),
		pretensao_carreira=data.get('Pretensão de movimentação na carreira'),
		carreira_anterior=data.get('Carreira anterior'),
		lideranca=data.get('Liderança'),
		grupos_identitarios=data.get('Grupos identitários'),
	)
	db.session.add(m)
	db.session.commit()
	# sincronizar amigos se enviados
	raw = data.get('Amigos no MP (IDs)')
	if raw is not None:
		ids = []
		if isinstance(raw, list):
			ids = [int(x) for x in raw if str(x).isdigit()]
		elif isinstance(raw, str):
			ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
		ids = [fid for fid in ids if fid != m.id]
		if ids:
			friends = Membro.query.filter(Membro.id.in_(ids)).all()
			for f in friends:
				if f.id != m.id:
					m.amigos.append(f)
			db.session.commit()
	return {'success': True, 'id': m.id}


@bp.put('/membros/<int:id>')
@jwt_required()
def update_membro(id: int):
	claims = get_jwt() or {}
	role = (claims.get('role') or '').lower()
	if role != 'admin':
		return { 'message': 'Apenas administradores podem editar registros.' }, 403
	m = Membro.query.get_or_404(id)
	data = (request.get_json() or {}).get('data') or {}
	m.nome = data.get('Membro') or data.get('Nome') or m.nome
	m.sexo = data.get('Sexo') or m.sexo
	m.concurso = data.get('Concurso') or m.concurso
	m.cargo_efetivo = data.get('Cargo efetivo') or m.cargo_efetivo
	m.titularidade = data.get('Titularidade') or m.titularidade
	m.email_pessoal = data.get('eMail pessoal') or m.email_pessoal
	m.cargo_especial = data.get('Cargo Especial') or m.cargo_especial
	m.telefone_unidade = data.get('Telefone Unidade') or m.telefone_unidade
	m.telefone_celular = data.get('Telefone celular') or m.telefone_celular
	m.unidade_lotacao = data.get('Unidade Lotação') or m.unidade_lotacao
	m.comarca_lotacao = data.get('Comarca Lotação') or m.comarca_lotacao
	m.time_extraprofissionais = data.get('Time de futebol e outros grupos extraprofissionais') or m.time_extraprofissionais
	m.quantidade_filhos = (int(data.get('Quantidade de filhos')) if data.get('Quantidade de filhos') not in (None, '') else m.quantidade_filhos)
	m.nomes_filhos = data.get('Nome dos filhos') or m.nomes_filhos
	m.estado_origem = (data.get('Estado de origem')[:2] if data.get('Estado de origem') else m.estado_origem)
	m.academico = data.get('Acadêmico') or m.academico
	m.pretensao_carreira = data.get('Pretensão de movimentação na carreira') or m.pretensao_carreira
	m.carreira_anterior = data.get('Carreira anterior') or m.carreira_anterior
	m.lideranca = data.get('Liderança') or m.lideranca
	m.grupos_identitarios = data.get('Grupos identitários') or m.grupos_identitarios
	# sincronizar amigos
	raw = data.get('Amigos no MP (IDs)')
	if raw is not None:
		new_ids = []
		if isinstance(raw, list):
			new_ids = [int(x) for x in raw if str(x).isdigit()]
		elif isinstance(raw, str):
			new_ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
		new_ids = [fid for fid in new_ids if fid != m.id]
		current_ids = set(a.id for a in m.amigos)
		to_add = set(new_ids) - current_ids
		to_remove = current_ids - set(new_ids)
		if to_remove:
			for f in list(m.amigos):
				if f.id in to_remove:
					m.amigos.remove(f)
		if to_add:
			friends = Membro.query.filter(Membro.id.in_(list(to_add))).all()
			for f in friends:
				if f.id != m.id:
					m.amigos.append(f)
	db.session.commit()
	return {'success': True} 