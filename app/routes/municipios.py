from flask import Blueprint, request
from flask_jwt_extended import jwt_required
import json, urllib.request, urllib.parse, unicodedata

bp = Blueprint('municipios', __name__)


def _normalize(s: str) -> str:
	if s is None:
		return ''
	s = unicodedata.normalize('NFD', s)
	s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
	return s.strip()


def _http_get_json(url: str):
	req = urllib.request.Request(url, headers={ 'User-Agent': 'membro-app/1.0' })
	with urllib.request.urlopen(req, timeout=10) as resp:
		data = resp.read()
		return json.loads(data.decode('utf-8'))


def _pick_mg(items, uf_sigla: str):
	if not isinstance(items, list):
		return None
	uf_sigla = (uf_sigla or '').upper().strip()
	if uf_sigla:
		cands = [it for it in items if (it.get('microrregiao') or {}).get('mesorregiao', {}).get('UF', {}).get('sigla') == uf_sigla]
		if cands:
			return cands[0]
	return items[0] if items else None


def _format_like_ibge(item: dict, uf_sigla: str):
	return {
		'id': item.get('id') or item.get('codigo_ibge'),
		'nome': item.get('nome'),
		'microrregiao': {
			'nome': (item.get('microrregiao') or {}).get('nome', ''),
			'mesorregiao': {
				'nome': ((item.get('microrregiao') or {}).get('mesorregiao') or {}).get('nome', ''),
				'UF': { 'sigla': uf_sigla, 'nome': uf_sigla, 'regiao': { 'sigla': '', 'nome': '' } }
			}
		}
	}


@bp.get('/municipios/info')
@jwt_required()
def municipio_info():
	name = (request.args.get('nome') or '').strip()
	uf_req = (request.args.get('uf') or 'MG').strip().upper()
	if not name:
		return { 'message': 'Parâmetro nome é obrigatório' }, 400
	needle_norm = _normalize(name).lower()
	# 1) IBGE localidades por nome
	params = urllib.parse.urlencode({ 'nome': name })
	url_ibge = f'https://servicodados.ibge.gov.br/api/v1/localidades/municipios?{params}'
	chosen = None
	try:
		items = _http_get_json(url_ibge)
		chosen = _pick_mg(items, uf_req)
	except Exception:
		chosen = None
	# 2) Fallback: lista do UF e matching normalizado (exato/contains)
	if not chosen:
		try:
			url_uf = f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{urllib.parse.quote(uf_req)}/municipios?orderBy=nome'
			lst = _http_get_json(url_uf)
			if isinstance(lst, list) and lst:
				# primeiro, match exato normalizado
				for it in lst:
					if _normalize(it.get('nome','')).lower() == needle_norm:
						chosen = _format_like_ibge(it, uf_req)
						break
				# depois, contains
				if not chosen:
					for it in lst:
						if needle_norm in _normalize(it.get('nome','')).lower():
							chosen = _format_like_ibge(it, uf_req)
							break
		except Exception:
			pass
	# 3) Fallback BrasilAPI
	if not chosen:
		try:
			url_brasilapi = f'https://brasilapi.com.br/api/ibge/municipios/v1/{urllib.parse.quote(uf_req)}'
			lst = _http_get_json(url_brasilapi)
			if isinstance(lst, list) and lst:
				for it in lst:
					if _normalize(it.get('nome', '')).lower() == needle_norm or needle_norm in _normalize(it.get('nome', '')).lower():
						chosen = _format_like_ibge(it, uf_req)
						break
		except Exception:
			pass
	if not chosen:
		# Fallback final: retornar dados mínimos com link IBGE Cidades
		mun_name = name
		uf_sigla = uf_req
		mun_slug = _normalize(mun_name).lower().replace(' ', '-')
		links = { 'ibge_cidades': f'https://cidades.ibge.gov.br/brasil/{uf_sigla.lower()}/{mun_slug}' }
		data = {
			'id': None,
			'nome': mun_name,
			'uf': { 'sigla': uf_sigla, 'nome': uf_sigla },
			'regiao': { 'sigla': '', 'nome': '' },
			'mesorregiao': '',
			'microrregiao': '',
			'links': links,
		}
		return { 'data': data }
	uf = ((chosen.get('microrregiao') or {}).get('mesorregiao') or {}).get('UF') or { 'sigla': uf_req, 'nome': uf_req, 'regiao': { 'sigla': '', 'nome': '' } }
	reg = (uf.get('regiao') or {})
	mun_name = chosen.get('nome') or name
	uf_sigla = uf.get('sigla') or uf_req
	mun_slug = _normalize(mun_name).lower().replace(' ', '-')
	links = {
		'ibge_cidades': f'https://cidades.ibge.gov.br/brasil/{uf_sigla.lower()}/{mun_slug}',
	}
	data = {
		'id': chosen.get('id'),
		'nome': mun_name,
		'uf': { 'sigla': uf_sigla, 'nome': uf.get('nome') },
		'regiao': { 'sigla': reg.get('sigla'), 'nome': reg.get('nome') },
		'mesorregiao': ((chosen.get('microrregiao') or {}).get('mesorregiao') or {}).get('nome'),
		'microrregiao': (chosen.get('microrregiao') or {}).get('nome'),
		'links': links,
	}
	return { 'data': data } 