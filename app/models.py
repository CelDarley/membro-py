from .db import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.mysql import BIGINT as MySQLBigInt


membro_amigos = db.Table(
	'membro_amigos',
	db.Column('membro_id', MySQLBigInt(unsigned=True), db.ForeignKey('membros.id'), primary_key=True),
	db.Column('amigo_id', MySQLBigInt(unsigned=True), db.ForeignKey('membros.id'), primary_key=True),
)


class User(db.Model):
	__tablename__ = 'users_py'
	id = db.Column(MySQLBigInt(unsigned=True), primary_key=True)
	name = db.Column(db.String(191), nullable=False)
	email = db.Column(db.String(191), unique=True, nullable=False)
	password_hash = db.Column(db.String(191), nullable=False)
	role = db.Column(db.String(32), default='user', nullable=False)
	two_factor_enabled = db.Column(db.Boolean, default=False)
	phone = db.Column(db.String(50))
	active = db.Column(db.Boolean, default=True, nullable=False)
	reset_code = db.Column(db.String(10))
	reset_expires_at = db.Column(db.DateTime)

	def set_password(self, raw: str) -> None:
		self.password_hash = generate_password_hash(raw)

	def check_password(self, raw: str) -> bool:
		return check_password_hash(self.password_hash, raw)


class Membro(db.Model):
	__tablename__ = 'membros'
	id = db.Column(MySQLBigInt(unsigned=True), primary_key=True)
	nome = db.Column(db.String(255), index=True)
	sexo = db.Column(db.String(50))
	concurso = db.Column(db.String(50))
	cargo_efetivo = db.Column(db.String(255))
	titularidade = db.Column(db.String(255))
	email_pessoal = db.Column(db.String(255))
	cargo_especial = db.Column(db.String(255))
	telefone_unidade = db.Column(db.String(100))
	telefone_celular = db.Column(db.String(100))
	unidade_lotacao = db.Column(db.String(255))
	comarca_lotacao = db.Column(db.String(255))
	time_extraprofissionais = db.Column(db.Text)
	quantidade_filhos = db.Column(db.Integer)
	nomes_filhos = db.Column(db.Text)
	estado_origem = db.Column(db.String(2))
	academico = db.Column(db.Text)
	pretensao_carreira = db.Column(db.Text)
	carreira_anterior = db.Column(db.Text)
	lideranca = db.Column(db.Text)
	grupos_identitarios = db.Column(db.Text)
	# nova: data de inclusão no MP/carreira (para início da timeline)
	data_inclusao = db.Column(db.Date)

	amigos = db.relationship(
		'Membro',
		secondary=membro_amigos,
		primaryjoin=id == membro_amigos.c.membro_id,
		secondaryjoin=id == membro_amigos.c.amigo_id,
		backref='amigos_de',
		lazy='dynamic',
	)


class MembroRelacionamento(db.Model):
	__tablename__ = 'membro_relacionamentos'
	id = db.Column(MySQLBigInt(unsigned=True), primary_key=True)
	source_id = db.Column(MySQLBigInt(unsigned=True), db.ForeignKey('membros.id'), nullable=False, index=True)
	target_id = db.Column(MySQLBigInt(unsigned=True), db.ForeignKey('membros.id'), nullable=False, index=True)
	# graus: spouse, parent, child, sibling
	degree = db.Column(db.String(20), nullable=False, index=True)
	__table_args__ = (db.UniqueConstraint('source_id', 'target_id', 'degree', name='uq_rel_source_target_degree'),)


class Lookup(db.Model):
	__tablename__ = 'lookups'
	id = db.Column(MySQLBigInt(unsigned=True), primary_key=True)
	type = db.Column(db.String(64), index=True, nullable=False)
	value = db.Column(db.String(255), nullable=False)
	__table_args__ = (db.UniqueConstraint('type', 'value', name='uq_lookups_type_value'),)


class MembroHistorico(db.Model):
	__tablename__ = 'membro_historico'
	id = db.Column(MySQLBigInt(unsigned=True), primary_key=True)
	membro_id = db.Column(MySQLBigInt(unsigned=True), db.ForeignKey('membros.id'), nullable=False, index=True)
	data_movimentacao = db.Column(db.Date, nullable=False)
	unidade_lotacao = db.Column(db.String(255))
	comarca_lotacao = db.Column(db.String(255)) 