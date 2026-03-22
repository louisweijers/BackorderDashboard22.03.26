#!/usr/bin/env python3
"""
Backorder Dashboard - Flask Server voor Render
"""

from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
import requests
import os
import json
import urllib.parse
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'verander-dit-naar-iets-geheims-in-render')

# ── Configuratie ──────────────────────────────────────────────────────────────
PICQER_SUBDOMAIN = os.environ.get('PICQER_SUBDOMAIN', 'boottotaalnl')
PICQER_API_KEY   = os.environ.get('PICQER_API_KEY', '')

# ── Gebruikers ────────────────────────────────────────────────────────────────
USERS = {
    'louis':  os.environ.get('PASS_LOUIS',  'Welkom123!'),
    'lars':   os.environ.get('PASS_LARS',   'Welkom123!'),
    'birgit': os.environ.get('PASS_BIRGIT', 'Welkom123!'),
    'tim':    os.environ.get('PASS_TIM',    'Welkom123!'),
    'joran':  os.environ.get('PASS_JORAN',  'Welkom123!'),
}

# ── Login vereist decorator ───────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Login pagina ──────────────────────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inloggen — Backorder Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #f1f5f9; font-family: 'Inter', sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  .card { background: #fff; border-radius: 12px; padding: 40px; width: 360px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
  .logo { width: 48px; height: 48px; background: #2563eb; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto 20px; }
  h1 { font-size: 20px; font-weight: 700; text-align: center; margin-bottom: 6px; color: #1e293b; }
  .subtitle { font-size: 13px; color: #94a3b8; text-align: center; margin-bottom: 28px; }
  label { display: block; font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 5px; }
  input { width: 100%; padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-family: 'Inter', sans-serif; font-size: 14px; outline: none; margin-bottom: 16px; transition: border-color .15s; }
  input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
  button { width: 100%; padding: 11px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 600; cursor: pointer; transition: background .15s; }
  button:hover { background: #1d4ed8; }
  .error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }
</style>
</head>
<body>
<div class="card">
  <div class="logo">📦</div>
  <h1>Backorder Dashboard</h1>
  <div class="subtitle">Log in om door te gaan</div>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Gebruikersnaam</label>
    <input type="text" name="username" placeholder="jouw naam" autocomplete="username" required>
    <label>Wachtwoord</label>
    <input type="password" name="password" placeholder="••••••••" autocomplete="current-password" required>
    <button type="submit">Inloggen</button>
  </form>
</div>
</body>
</html>"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').lower().strip()
        password = request.form.get('password', '')
        if username in USERS and USERS[username] == password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        error = 'Gebruikersnaam of wachtwoord onjuist.'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    html_path = os.path.join(os.path.dirname(__file__), 'picqer-backorders.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('</body>', f'<script>window._user = "{session["user"]}";</script></body>')
    return html

@app.route('/picqer/<path:api_path>')
@login_required
def picqer_proxy(api_path):
    subdomain = PICQER_SUBDOMAIN
    if api_path.startswith(subdomain + '/'):
        api_path = api_path[len(subdomain) + 1:]
    url = f"https://{subdomain}.picqer.com/api/v1/{api_path}"
    if request.query_string:
        url += '?' + request.query_string.decode()
    try:
        resp = requests.get(
            url,
            auth=(PICQER_API_KEY, 'x'),
            headers={'User-Agent': 'BackorderDashboard/1.0'},
            timeout=30
        )
        return Response(resp.content, status=resp.status_code, content_type='application/json')
    except Exception as e:
        return jsonify({'error': str(e)}), 502

@app.route('/keuze')
def keuze():
    order = request.args.get('order', '?')
    keuze_val = request.args.get('keuze', '')
    sub   = request.args.get('sub', PICQER_SUBDOMAIN)
    kleur  = '#16a34a' if keuze_val == 'wachten' else '#2563eb'
    label  = 'Wachten op volledige levering' if keuze_val == 'wachten' else 'Deellevering gewenst'
    icoon  = '⏳' if keuze_val == 'wachten' else '📦'
    team_email = 'info@boottotaal.nl' if 'boottotaal' in sub else 'verkoop@aquaservice.nl'
    mail_onderwerp = urllib.parse.quote(f"Keuze bestelling {order} - {label}")
    mail_tekst = urllib.parse.quote(f"Hallo,\n\nMijn keuze voor bestelling {order} is:\n\n➡ {label}\n\nMet vriendelijke groet")
    mailto_link = f"mailto:{team_email}?subject={mail_onderwerp}&body={mail_tekst}"
    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Keuze bestelling {order}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      body{{font-family:Inter,sans-serif;background:#f1f5f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
      .card{{background:#fff;border-radius:12px;padding:40px;max-width:480px;width:90%;box-shadow:0 4px 20px rgba(0,0,0,.08);text-align:center}}
      h2{{font-size:22px;font-weight:700;margin-bottom:8px;color:#1e293b}}
      .badge{{display:inline-block;padding:8px 20px;border-radius:20px;font-size:15px;font-weight:600;background:{kleur};color:#fff;margin:16px 0}}
      p{{color:#475569;font-size:14px;line-height:1.6}}
      .mail-btn{{display:inline-block;margin-top:20px;padding:12px 28px;background:{kleur};color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;}}
      .uitleg{{font-size:12px;color:#94a3b8;margin-top:12px;}}
    </style>
    <script>window.onload = function(){{ window.location.href = "{mailto_link}"; }}</script>
    </head>
    <body><div class="card">
    <div style="font-size:48px;margin-bottom:16px;">{icoon}</div>
    <h2>Bedankt voor je keuze!</h2>
    <div class="badge">{label}</div>
    <p>Je hebt gekozen voor <strong>{label}</strong> voor bestelling <strong>{order}</strong>.</p>
    <p style="margin-top:12px;">Er wordt automatisch een bevestigingsmail geopend. Klik op <strong>Verzenden</strong> om je keuze door te geven.</p>
    <a href="{mailto_link}" class="mail-btn">✉ Bevestig je keuze per mail</a>
    <div class="uitleg">Werkt de mail niet automatisch? Klik dan op de knop hierboven.</div>
    </div></body></html>"""
    return html

@app.route('/config')
@login_required
def config():
    return jsonify({
        'subdomain': PICQER_SUBDOMAIN,
        'user': session['user']
    })

@app.route('/me')
@login_required
def me():
    return jsonify({'user': session['user']})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
