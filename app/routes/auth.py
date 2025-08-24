from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..db import db
from ..models import User
from datetime import datetime, timedelta
import os, random, string, logging, smtplib, socket
from email.message import EmailMessage
from flask import current_app

bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@bp.post('/login')
def login():
	data = request.get_json(force=True)
	email = (data.get('email') or '').strip().lower()
	password = data.get('password') or ''
	user = User.query.filter_by(email=email).first()
	if not user or not user.check_password(password):
		return {'message': 'Credenciais inválidas'}, 401
	if not bool(user.active):
		return {'message': 'Usuário inativo. Contate o administrador.'}, 403
	# identity deve ser string no Flask-JWT-Extended v4; incluir role em additional_claims
	access = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
	return {
		'user': { 'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role },
		'token': access,
		'token_type': 'Bearer',
	}

@bp.get('/me')
@jwt_required()
def me():
	ident = get_jwt_identity()
	user = User.query.get(int(ident)) if ident else None
	if not user:
		return {'user': None}, 200
	return {'user': { 'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role }}

@bp.post('/change-password')
@jwt_required()
def change_password():
	ident = get_jwt_identity()
	user = User.query.get(int(ident)) if ident else None
	if not user:
		return { 'message': 'Usuário não encontrado' }, 404
	data = request.get_json(force=True) or {}
	current = (data.get('current_password') or '').strip()
	new = (data.get('new_password') or '').strip()
	confirm = (data.get('confirm') or '').strip()
	if not current or not new:
		return { 'message': 'Informe a senha atual e a nova senha' }, 422
	if new != confirm:
		return { 'message': 'Confirmação de senha não confere' }, 422
	if not user.check_password(current):
		return { 'message': 'Senha atual incorreta' }, 422
	user.set_password(new)
	db.session.commit()
	return { 'success': True }

@bp.post('/forgot-password')
def forgot_password():
	data = request.get_json(force=True) or {}
	email = (data.get('email') or '').strip().lower()
	if not email:
		return { 'message': 'Informe o e-mail' }, 422
	user = User.query.filter_by(email=email).first()
	# Não revelar se existe ou não. Sempre responder ok.
	code = ''.join(random.choices(string.digits, k=6))
	if user:
		user.reset_code = code
		user.reset_expires_at = datetime.utcnow() + timedelta(minutes=15)
		db.session.commit()
		# Envio: SMTP se configurado, senão log
		try:
			cfg = current_app.config
			server = (cfg.get('MAIL_SERVER') or '').strip()
			username = (cfg.get('MAIL_USERNAME') or '').strip()
			password = (cfg.get('MAIL_PASSWORD') or '').strip()
			sender = (cfg.get('MAIL_DEFAULT_SENDER') or username).strip()
			port = int(cfg.get('MAIL_PORT') or 587)
			use_tls = bool(cfg.get('MAIL_USE_TLS'))
			if server and username and password and sender:
				# Monta mensagem
				msg = EmailMessage()
				msg['Subject'] = 'Código para redefinição de senha'
				msg['From'] = sender
				msg['To'] = email
				msg.set_content(f'Seu código de redefinição é {code}. Ele expira em 15 minutos.')
				# Resolve A records (IPv4) e tenta por IP para evitar rota IPv6 inexistente
				target_hosts = []
				try:
					infos = socket.getaddrinfo(server, port, socket.AF_INET, socket.SOCK_STREAM)
					ips = [ai[4][0] for ai in infos]
					# ordem preservada/únicos
					target_hosts = list(dict.fromkeys(ips))
				except Exception:
					# fallback: usa hostname direto
					target_hosts = [server]
				last_err = None
				for host in (target_hosts or [server]):
					try:
						with smtplib.SMTP(host, port, timeout=10) as smtp:
							if use_tls:
								smtp.starttls()
							smtp.login(username, password)
							smtp.send_message(msg)
						last_err = None
						break
					except Exception as e_send:
						last_err = e_send
				if last_err:
					raise last_err
			else:
				logger.info('Código de reset para %s: %s (válido por 15 min)', email, code)
		except Exception as e:
			logger.error('Falha ao enviar e-mail de reset para %s: %s', email, e)
	return { 'success': True }

@bp.post('/reset-password')
def reset_password():
	data = request.get_json(force=True) or {}
	email = (data.get('email') or '').strip().lower()
	code = (data.get('code') or '').strip()
	new = (data.get('new_password') or '').strip()
	confirm = (data.get('confirm') or '').strip()
	if not email or not code or not new:
		return { 'message': 'Dados incompletos' }, 422
	if new != confirm:
		return { 'message': 'Confirmação de senha não confere' }, 422
	user = User.query.filter_by(email=email).first()
	if not user or not user.reset_code or not user.reset_expires_at:
		return { 'message': 'Código inválido' }, 422
	if user.reset_code != code:
		return { 'message': 'Código inválido' }, 422
	if datetime.utcnow() > user.reset_expires_at:
		return { 'message': 'Código expirado' }, 422
	user.set_password(new)
	user.reset_code = None
	user.reset_expires_at = None
	db.session.commit()
	return { 'success': True } 