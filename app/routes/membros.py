from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func
from ..db import db
from ..models import Membro, MembroHistorico, MembroRelacionamento
import json
import re
from datetime import datetime
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
import os
from werkzeug.utils import secure_filename

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
	# montar URL da foto (se houver) servida via /static
	foto_url = None
	if m.foto_path:
		foto_url = f"/static/{m.foto_path.lstrip('/')}"
	return {
		'id': m.id,
		'data': {
			'Membro': m.nome,
			'Foto URL': foto_url,
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
			'Observação': m.observacao,
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
		observacao=data.get('Observação'),
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
		m.observacao = data.get('Observação') if data.get('Observação') not in (None, '') else m.observacao
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


@bp.post('/membros/<int:id>/photo')
@jwt_required()
def upload_photo(id: int):
	# apenas admin pode alterar foto
	claims = get_jwt() or {}
	role = (claims.get('role') or '').lower()
	if role != 'admin':
		return { 'message': 'Apenas administradores podem enviar foto.' }, 403
	m = Membro.query.get_or_404(id)
	if 'file' not in request.files:
		return { 'message': 'Arquivo não enviado (campo file)' }, 400
	file = request.files['file']
	if not file or file.filename == '':
		return { 'message': 'Arquivo inválido' }, 400
	# validar extensão simples
	name = secure_filename(file.filename)
	ext = os.path.splitext(name)[1].lower()
	if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
		return { 'message': 'Extensão não suportada. Use JPG, PNG ou WEBP.' }, 400
	# diretório destino
	base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'membros', str(id)))
	os.makedirs(base_dir, exist_ok=True)
	dest = os.path.join(base_dir, 'foto'+ext)
	# sobrescrever arquivo
	file.save(dest)
	# salvar caminho relativo para servir via /static
	rel_path = os.path.relpath(dest, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static')))
	m.foto_path = rel_path.replace('\\','/')
	try:
		db.session.commit()
	except Exception as e:
		db.session.rollback()
		return { 'message': f'Erro ao salvar foto: {str(e)[:200]}' }, 422
	return { 'success': True, 'foto_url': f"/static/{m.foto_path}" }


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


@bp.get('/membros/<int:id>/report.pdf')
@jwt_required()
def member_report_pdf(id: int):
	m = Membro.query.get_or_404(id)
	# amigos
	amigos = m.amigos.all()
	# parentescos (in/out)
	rels_out = MembroRelacionamento.query.filter_by(source_id=id).all()
	rels_in = MembroRelacionamento.query.filter_by(target_id=id).all()
	# histórico
	hist = MembroHistorico.query.filter_by(membro_id=id).order_by(MembroHistorico.data_movimentacao.asc(), MembroHistorico.id.asc()).all()

	buf = BytesIO()
	doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
	styles = getSampleStyleSheet()
	story = []

	def h(text):
		story.append(Paragraph(f"<b>{text}</b>", styles['Heading3']))
		story.append(Spacer(1, 4))

	def row_table(data_pairs):
		# duas colunas: label e valor; montar em 2 colunas de pares
		rows = []
		for label, value in data_pairs:
			val = '-' if value in (None, '') else str(value)
			rows.append([Paragraph(f"<b>{label}</b>", styles['Normal']), Paragraph(val, styles['Normal'])])
		t = Table(rows, colWidths=[40*mm, 120*mm])
		t.setStyle(TableStyle([
			('VALIGN',(0,0),(-1,-1),'TOP'),
			('BOTTOMPADDING',(0,0),(-1,-1),4),
			('TOPPADDING',(0,0),(-1,-1),2),
			('INNERGRID',(0,0),(-1,-1),0.25,colors.lightgrey),
			('BOX',(0,0),(-1,-1),0.25,colors.lightgrey),
		]))
		story.append(t)
		story.append(Spacer(1, 8))

	# Tentar carregar a foto do membro
	foto_flowable = None
	static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
	try:
		if getattr(m, 'foto_path', None):
			foto_abs = os.path.abspath(os.path.join(static_dir, m.foto_path))
			if os.path.isfile(foto_abs):
				img = Image(foto_abs)
				# ajustar para caber em 30x30mm mantendo proporção
				max_w, max_h = 30*mm, 30*mm
				ratio = min(max_w/float(img.drawWidth or 1), max_h/float(img.drawHeight or 1))
				img.drawWidth = img.drawWidth * ratio
				img.drawHeight = img.drawHeight * ratio
				img.hAlign = 'LEFT'
				foto_flowable = img
	except Exception:
		foto_flowable = None

	if not foto_flowable:
		# tentar silhouette.* em PNG/JPG/WEBP antes do placeholder
		for fname in ['silhouette.png','silhouette.jpg','silhouette.jpeg','silhouette.webp']:
			cand = os.path.join(static_dir, fname)
			if os.path.isfile(cand):
				try:
					img = Image(cand)
					max_w, max_h = 30*mm, 30*mm
					ratio = min(max_w/float(img.drawWidth or 1), max_h/float(img.drawHeight or 1))
					img.drawWidth = img.drawWidth * ratio
					img.drawHeight = img.drawHeight * ratio
					img.hAlign = 'LEFT'
					foto_flowable = img
					break
				except Exception:
					pass
		if not foto_flowable:
			# placeholder 30x30mm caso não haja imagem
			ph = Table([[" "]], colWidths=[30*mm], rowHeights=[30*mm])
			ph.setStyle(TableStyle([
				('BACKGROUND',(0,0),(0,0), colors.lightgrey),
				('BOX',(0,0),(0,0), 0.25, colors.grey),
			]))
			foto_flowable = ph

	# Cabeçalho com foto à esquerda e título/nome à direita
	head = Table([
		[foto_flowable, Paragraph(f"<b>Relatório do Membro</b><br/>{m.nome or ''}", styles['Heading3'])]
	], colWidths=[30*mm, 150*mm])
	head.setStyle(TableStyle([
		('VALIGN',(0,0),(-1,-1),'MIDDLE'),
		('LEFTPADDING',(0,0),(-1,-1),0),
		('RIGHTPADDING',(0,0),(-1,-1),6),
	]))
	story.append(head)
	story.append(Spacer(1, 8))

	row_table([
		('Membro', m.nome),
		('Sexo', m.sexo),
		('Concurso', m.concurso),
		('Data de inclusão', m.data_inclusao.isoformat() if m.data_inclusao else ''),
		('Cargo efetivo', m.cargo_efetivo),
		('Titularidade', m.titularidade),
		('Email pessoal', m.email_pessoal),
		('Telefone unidade', m.telefone_unidade),
		('Telefone celular', m.telefone_celular),
		('Unidade de lotação', m.unidade_lotacao),
		('Comarca de lotação', m.comarca_lotacao),
		('Estado de origem', m.estado_origem),
	])

	# Outras infos
	h('Informações adicionais')
	row_table([
		('Time/Grupos extraprofissionais', m.time_extraprofissionais),
		('Quantidade de filhos', m.quantidade_filhos),
		('Nome dos filhos', m.nomes_filhos),
		('Acadêmico', m.academico),
		('Pretensão de movimentação', m.pretensao_carreira),
		('Carreira anterior', m.carreira_anterior),
		('Liderança', m.lideranca),
		('Grupos identitários', m.grupos_identitarios),
	])

	# Observação (rich)
	if m.observacao:
		story.append(Paragraph('<b>Observação</b>', styles['Heading3']))
		story.append(Spacer(1,4))
		story.append(Paragraph(m.observacao, styles['Normal']))
		story.append(Spacer(1,8))

	# Amigos no MP
	h('Amigos no MP')
	if amigos:
		rows = [[Paragraph('<b>Nome</b>', styles['Normal'])]] + [[Paragraph(a.nome or '-', styles['Normal'])] for a in amigos]
		t = Table(rows, colWidths=[160*mm])
		t.setStyle(TableStyle([('INNERGRID',(0,0),(-1,-1),0.25,colors.lightgrey),('BOX',(0,0),(-1,-1),0.25,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
		story.append(t)
	else:
		story.append(Paragraph('Sem registros.', styles['Normal']))
	story.append(Spacer(1,8))

	# Família (Parentescos)
	h('Parentescos')
	def fmt_rel(r, direction):
		other_id = r.target_id if direction=='out' else r.source_id
		other = Membro.query.get(other_id)
		return f"{other.nome if other else ('#'+str(other_id))} — {r.degree} { '(dele)' if direction=='in' else '' }"
	all_rels = [fmt_rel(r,'out') for r in rels_out] + [fmt_rel(r,'in') for r in rels_in]
	if all_rels:
		rows = [[Paragraph('<b>Parente</b>', styles['Normal'])]] + [[Paragraph(s, styles['Normal'])] for s in all_rels]
		t = Table(rows, colWidths=[160*mm])
		t.setStyle(TableStyle([('INNERGRID',(0,0),(-1,-1),0.25,colors.lightgrey),('BOX',(0,0),(-1,-1),0.25,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
		story.append(t)
	else:
		story.append(Paragraph('Sem registros.', styles['Normal']))
	story.append(Spacer(1,8))

	# Histórico (timeline)
	h('Histórico de movimentações')
	if hist:
		rows = [[Paragraph('<b>Data</b>', styles['Normal']), Paragraph('<b>Unidade</b>', styles['Normal'])]]
		for h in hist:
			rows.append([Paragraph(h.data_movimentacao.isoformat() if h.data_movimentacao else '-', styles['Normal']), Paragraph(h.unidade_lotacao or '-', styles['Normal'])])
		t = Table(rows, colWidths=[40*mm, 120*mm])
		t.setStyle(TableStyle([('INNERGRID',(0,0),(-1,-1),0.25,colors.lightgrey),('BOX',(0,0),(-1,-1),0.25,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
		story.append(t)
	else:
		story.append(Paragraph('Sem registros.', styles['Normal']))

	doc.build(story)
	buf.seek(0)
	filename = f"membro_{id}.pdf"
	return send_file(buf, mimetype='application/pdf', as_attachment=False, download_name=filename) 