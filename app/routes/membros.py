from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func
from ..db import db
from ..models import Membro, MembroHistorico
import json
import re
from datetime import datetime

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
			'Data de inclusão': (m.data_inclusao.isoformat() if m.data_inclusao else None),
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


def parse_int_or_none(value):
	if value in (None, ''):
		return None
	try:
		return int(str(value).strip())
	except Exception:
		return None


def normalize_uf(value):
	if not value:
		return None
	s = str(value).strip().upper()
	# manter apenas letras e pegar as duas primeiras
	letters = re.sub(r'[^A-Z]', '', s)
	return (letters[:2] or None)


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
		quantidade_filhos=parse_int_or_none(data.get('Quantidade de filhos')),
		nomes_filhos=data.get('Nome dos filhos'),
		estado_origem=normalize_uf(data.get('Estado de origem')),
		academico=data.get('Acadêmico'),
		pretensao_carreira=data.get('Pretensão de movimentação na carreira'),
		carreira_anterior=data.get('Carreira anterior'),
		lideranca=data.get('Liderança'),
		grupos_identitarios=data.get('Grupos identitários'),
		data_inclusao=(datetime.strptime(data.get('Data de inclusão'), '%Y-%m-%d').date() if (data.get('Data de inclusão') or '').strip() else None),
	)
	try:
		db.session.add(m)
		db.session.commit()
	except Exception as e:
		db.session.rollback()
		return { 'message': f'Erro ao criar: {str(e)[:200]}' }, 422
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
				if f.id != m.id and f not in m.amigos:
					m.amigos.append(f)
			try:
				db.session.commit()
			except Exception as e:
				db.session.rollback()
				return { 'message': f'Erro ao vincular amigos: {str(e)[:200]}' }, 422
	return {'success': True, 'id': m.id}


@bp.put('/membros/<int:id>')
@jwt_required()
def update_membro(id: int):
	claims = get_jwt() or {}
	role = (claims.get('role') or '').lower()
	if role != 'admin':
		return { 'message': 'Apenas administradores podem editar registros.' }, 403
	try:
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
		qf = data.get('Quantidade de filhos')
		m.quantidade_filhos = parse_int_or_none(qf) if qf not in (None, '') else m.quantidade_filhos
		m.nomes_filhos = data.get('Nome dos filhos') or m.nomes_filhos
		uf = data.get('Estado de origem')
		m.estado_origem = normalize_uf(uf) if uf not in (None, '') else m.estado_origem
		m.academico = data.get('Acadêmico') or m.academico
		m.pretensao_carreira = data.get('Pretensão de movimentação na carreira') or m.pretensao_carreira
		m.carreira_anterior = data.get('Carreira anterior') or m.carreira_anterior
		m.lideranca = data.get('Liderança') or m.lideranca
		m.grupos_identitarios = data.get('Grupos identitários') or m.grupos_identitarios
		vdi = data.get('Data de inclusão')
		if vdi not in (None, ''):
			try:
				m.data_inclusao = datetime.strptime(str(vdi).strip(), '%Y-%m-%d').date()
			except Exception:
				pass
		# sincronizar amigos
		raw = data.get('Amigos no MP (IDs)')
		if raw is not None:
			new_ids = []
			if isinstance(raw, list):
				new_ids = [int(x) for x in raw if str(x).isdigit()]
			elif isinstance(raw, str):
				new_ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
			new_ids = [fid for fid in new_ids if fid != m.id]
			current = m.amigos.all()
			current_ids = set(a.id for a in current)
			to_add = set(new_ids) - current_ids
			to_remove = current_ids - set(new_ids)
			if to_remove:
				for f in current:
					if f.id in to_remove:
						m.amigos.remove(f)
			if to_add:
				friends = Membro.query.filter(Membro.id.in_(list(to_add))).all()
				for f in friends:
					if f.id != m.id and f not in m.amigos:
						m.amigos.append(f)
		try:
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			return { 'message': f'Erro ao salvar: {str(e)[:200]}' }, 422
		return {'success': True}
	except Exception as e:
		return { 'message': f'Erro ao processar: {str(e)[:200]}' }, 422


@bp.get('/membros/<int:id>/historico')
@jwt_required()
def list_historico(id: int):
	m = Membro.query.get_or_404(id)
	items = MembroHistorico.query.filter_by(membro_id=id).order_by(MembroHistorico.data_movimentacao.asc(), MembroHistorico.id.asc()).all()
	data = [{
		'id': h.id,
		'data_movimentacao': h.data_movimentacao.isoformat() if h.data_movimentacao else None,
		'unidade_lotacao': h.unidade_lotacao,
		'comarca_lotacao': h.comarca_lotacao,
	} for h in items]
	return { 'membro_id': id, 'data': data, 'data_inclusao': (m.data_inclusao.isoformat() if m.data_inclusao else None), 'concurso': m.concurso }


def _is_admin():
	claims = get_jwt() or {}
	return (claims.get('role') or '').lower() == 'admin'


@bp.post('/membros/<int:id>/historico')
@jwt_required()
def add_historico(id: int):
	if not _is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	Membro.query.get_or_404(id)
	body = request.get_json() or {}
	date_str = str(body.get('data_movimentacao') or '').strip()
	try:
		data_mov = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
	except Exception:
		return { 'message': 'data_movimentacao inválida (use YYYY-MM-DD)' }, 422
	h = MembroHistorico(
		membro_id=id,
		data_movimentacao=data_mov,
		unidade_lotacao=(body.get('unidade_lotacao') or None),
		comarca_lotacao=(body.get('comarca_lotacao') or None),
	)
	db.session.add(h)
	db.session.commit()
	return { 'id': h.id }


@bp.put('/historico/<int:hist_id>')
@jwt_required()
def update_historico(hist_id: int):
	if not _is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	h = MembroHistorico.query.get_or_404(hist_id)
	body = request.get_json() or {}
	ds = body.get('data_movimentacao')
	if ds not in (None, ''):
		try:
			h.data_movimentacao = datetime.strptime(str(ds).strip(), '%Y-%m-%d').date()
		except Exception:
			return { 'message': 'data_movimentacao inválida (YYYY-MM-DD)' }, 422
	h.unidade_lotacao = body.get('unidade_lotacao') or h.unidade_lotacao
	h.comarca_lotacao = body.get('comarca_lotacao') or h.comarca_lotacao
	db.session.commit()
	return { 'success': True }


@bp.delete('/historico/<int:hist_id>')
@jwt_required()
def delete_historico(hist_id: int):
	if not _is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	h = MembroHistorico.query.get_or_404(hist_id)
	db.session.delete(h)
	db.session.commit()
	return { 'success': True } 