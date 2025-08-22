from .db import db


membro_amigos = db.Table(
	'membro_amigos',
	db.Column('membro_id', db.Integer, db.ForeignKey('membros.id'), primary_key=True),
	db.Column('amigo_id', db.Integer, db.ForeignKey('membros.id'), primary_key=True),
)


class User(db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(191), nullable=False)
	email = db.Column(db.String(191), unique=True, nullable=False)
	password_hash = db.Column(db.String(191), nullable=False)
	role = db.Column(db.String(32), default='user', nullable=False)
	two_factor_enabled = db.Column(db.Boolean, default=False)


class Membro(db.Model):
	__tablename__ = 'membros'
	id = db.Column(db.Integer, primary_key=True)
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

	amigos = db.relationship(
		'Membro',
		secondary=membro_amigos,
		primaryjoin=id == membro_amigos.c.membro_id,
		secondaryjoin=id == membro_amigos.c.amigo_id,
		backref='amigos_de',
		lazy='dynamic',
	) 