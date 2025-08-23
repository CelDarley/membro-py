from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from ..db import db
from ..models import User

bp = Blueprint('users', __name__)


def is_admin():
	claims = get_jwt() or {}
	return (claims.get('role') or '').lower() == 'admin'


@bp.get('/users')
@jwt_required()
def list_users():
	q = (request.args.get('q') or '').strip()
	query = User.query
	if q:
		query = query.filter((User.name.ilike(f'%{q}%')) | (User.email.ilike(f'%{q}%')))
	users = query.order_by(User.id.desc()).limit(200).all()
	data = [{ 'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role, 'phone': u.phone, 'two_factor_enabled': bool(u.two_factor_enabled), 'active': bool(u.active) } for u in users]
	return { 'data': data }


@bp.post('/users')
@jwt_required()
def create_user():
	admins_count = User.query.filter_by(role='admin').count()
	if not is_admin() and admins_count > 0:
		return { 'message': 'Apenas administradores.' }, 403
	body = request.get_json() or {}
	name = (body.get('name') or '').strip()
	email = (body.get('email') or '').strip().lower()
	role = (body.get('role') or 'user').strip().lower()
	phone = (body.get('phone') or '').strip()
	password = (body.get('password') or '').strip()
	confirm = (body.get('confirm') or '').strip()
	twofa = bool(body.get('two_factor_enabled'))
	active = bool(body.get('active', True))
	if admins_count == 0:
		role = 'admin'
	if not name or not email or not password or password != confirm or role not in ('user','admin'):
		return { 'message': 'Dados inválidos' }, 422
	if User.query.filter_by(email=email).first():
		return { 'message': 'Email já cadastrado' }, 422
	u = User(name=name, email=email, role=role, phone=phone, two_factor_enabled=twofa, active=active)
	u.set_password(password)
	db.session.add(u)
	db.session.commit()
	return { 'id': u.id }


@bp.put('/users/<int:id>')
@jwt_required()
def update_user(id: int):
	if not is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	u = User.query.get_or_404(id)
	body = request.get_json() or {}
	u.name = (body.get('name') or u.name).strip()
	new_email = (body.get('email') or u.email).strip().lower()
	if new_email != u.email and User.query.filter_by(email=new_email).first():
		return { 'message': 'Email já cadastrado' }, 422
	u.email = new_email
	role = (body.get('role') or u.role).strip().lower()
	if role not in ('user','admin'):
		return { 'message': 'Permissão inválida' }, 422
	u.role = role
	u.phone = (body.get('phone') or u.phone or '').strip()
	u.two_factor_enabled = bool(body.get('two_factor_enabled'))
	u.active = bool(body.get('active', u.active))
	new_pass = (body.get('password') or '').strip()
	confirm = (body.get('confirm') or '').strip()
	if new_pass:
		if new_pass != confirm:
			return { 'message': 'Confirmação de senha não confere' }, 422
		u.set_password(new_pass)
	db.session.commit()
	return { 'success': True }


@bp.delete('/users/<int:id>')
@jwt_required()
def delete_user(id: int):
	if not is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	u = User.query.get_or_404(id)
	db.session.delete(u)
	db.session.commit()
	return { 'success': True }


@bp.post('/users/<int:id>/toggle-active')
@jwt_required()
def toggle_active(id: int):
	if not is_admin():
		return { 'message': 'Apenas administradores.' }, 403
	u = User.query.get_or_404(id)
	u.active = not bool(u.active)
	db.session.commit()
	return { 'active': bool(u.active) }


@bp.post('/users/<int:id>/auth-test')
@jwt_required()
def auth_test(id: int):
	# endpoint placeholder para eventualmente disparar 2FA
	return { 'ok': True } 