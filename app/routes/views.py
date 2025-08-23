from flask import Blueprint, render_template_string

bp = Blueprint('views', __name__)


@bp.get('/login')
def login_page():
	from flask import redirect
	return render_template_string(open('app/templates/login.html').read())


@bp.get('/')
def members_page():
	return render_template_string(open('app/templates/membros.html').read())


@bp.get('/cadastros')
def cadastros_page():
	html = '''<!doctype html><html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Cadastros</title>
	<style> body{font-family:system-ui,sans-serif;padding:16px} .toolbar{display:flex;gap:8px;align-items:center;margin-bottom:12px} .btn{padding:8px 12px;border:1px solid #334155;background:#334155;color:#fff;border-radius:6px;cursor:pointer} .input{padding:8px;border:1px solid #cbd5e1;border-radius:6px} table{border-collapse:collapse;width:100%} th,td{border:1px solid #e2e8f0;padding:8px;font-size:14px} th{background:#f1f5f9} .row{display:flex;gap:8px;align-items:center;margin:8px 0} select{padding:8px;border:1px solid #cbd5e1;border-radius:6px} </style>
	</head><body>
	<div class="toolbar">
		<select id="type" onchange="loadList()">
			<option value="concurso">Concurso</option>
			<option value="cargo_efetivo">Cargo efetivo</option>
			<option value="titularidade">Titularidade</option>
			<option value="cargo_especial">Cargo especial</option>
			<option value="unidade_lotacao">Unidade de lotação</option>
			<option value="comarca_lotacao">Comarca de lotação</option>
			<option value="time_extraprofissionais">Time de futebol e outros grupos extraprofissionais</option>
			<option value="estado_origem">Estado de origem</option>
			<option value="grupos_identitarios">Grupos identitários</option>
		</select>
		<input id="q" class="input" placeholder="Buscar..." oninput="loadList()" />
		<a class="btn" href="/">Voltar</a>
	</div>
	<div class="row">
		<input id="newVal" class="input" placeholder="Novo valor" />
		<button class="btn" onclick="createVal()">Adicionar</button>
	</div>
	<table><thead><tr><th>Valor</th><th style="width:140px">Ações</th></tr></thead><tbody id="tbody"></tbody></table>
	<script>
	function token(){ return localStorage.getItem('token') || '' }
	function auth(){ return token() ? { 'Authorization': 'Bearer '+token() } : {} }
	async function loadList(page=1){ const type=document.getElementById('type').value; const q=document.getElementById('q').value.trim(); const r=await fetch(`/api/lookups?type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}&page=${page}&per_page=200`, { headers:{ ...auth() } }); const d=await r.json(); const tb=document.getElementById('tbody'); tb.innerHTML=''; for(const it of (d.data||[])){ const tr=document.createElement('tr'); tr.innerHTML=`<td><input class='input' value="${String(it.value).replace(/"/g,'&quot;')}" data-id='${it.id}' style='width:100%'/></td><td><button class='btn' onclick='save(${it.id})'>Salvar</button> <button class='btn' onclick='removeVal(${it.id})'>Excluir</button></td>`; tb.appendChild(tr) } }
	async function createVal(){ const type=document.getElementById('type').value; const value=document.getElementById('newVal').value.trim(); if(!value) return; const r=await fetch('/api/lookups', { method:'POST', headers:{ 'Content-Type':'application/json', ...auth() }, body: JSON.stringify({ type, value }) }); if(r.ok){ document.getElementById('newVal').value=''; loadList() } }
	async function save(id){ const inp = document.querySelector(`[data-id="${id}"]`); const value=inp.value.trim(); const r=await fetch(`/api/lookups/${id}`, { method:'PUT', headers:{ 'Content-Type':'application/json', ...auth() }, body: JSON.stringify({ value }) }); if(r.ok){ loadList() } }
	async function removeVal(id){ if(!confirm('Excluir este valor?')) return; const r=await fetch(`/api/lookups/${id}`, { method:'DELETE', headers:{ ...auth() } }); if(r.ok){ loadList() } }
	async function populate(){ try{ await fetch('/api/lookups/populate-from-membros', { method:'POST', headers:{ ...auth() } }) }catch(e){} }
	(async function init(){ await populate(); loadList() })()
	</script>
	</body></html>'''
	return render_template_string(html) 