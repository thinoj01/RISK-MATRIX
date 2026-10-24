"""PLD Risk Pilot: local-only demonstration with fictional data.
Not a regulatory-compliant production service. Do not store real personal data.
"""
import csv
import io
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('PLD_DB', str(ROOT / 'pilot.db')))
DB.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='PLD Risk Piloto', version='0.1.0', docs_url='/api/docs', redoc_url=None)
app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')

@contextmanager
def connection():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def event(con, action, entity, entity_id, detail):
    con.execute('INSERT INTO audit(timestamp,action,entity,entity_id,detail) VALUES (?,?,?,?,?)',
                (now(), action, entity, entity_id, json.dumps(detail, ensure_ascii=False)))

def initialize():
    with connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS clients (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          customer_type TEXT NOT NULL, industry TEXT NOT NULL,
          jurisdiction TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assessments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
          geography INTEGER NOT NULL CHECK(geography BETWEEN 1 AND 3),
          customer INTEGER NOT NULL CHECK(customer BETWEEN 1 AND 3),
          transactions INTEGER NOT NULL CHECK(transactions BETWEEN 1 AND 3),
          source_funds INTEGER NOT NULL CHECK(source_funds BETWEEN 1 AND 3),
          score REAL NOT NULL, level TEXT NOT NULL, methodology TEXT NOT NULL,
          justification TEXT NOT NULL, assessed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
          action TEXT NOT NULL, entity TEXT NOT NULL,
          entity_id INTEGER NOT NULL, detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        if not c.execute('SELECT 1 FROM config WHERE key=?', ('methodology',)).fetchone():
            values = {'version': 'DEMO-1.0', 'weights': {'geography': 0.20, 'customer': 0.30, 'transactions': 0.30, 'source_funds': 0.20},
                      'medium_threshold': 1.7, 'high_threshold': 2.4}
            c.execute('INSERT INTO config VALUES (?,?)', ('methodology', json.dumps(values)))
        if not c.execute('SELECT 1 FROM clients').fetchone():
            names = [
                ('Desarrollos Sierra (ficticio)', 'Persona moral', 'Desarrolladora', 'CDMX', 'Registro de demostración'),
                ('Residencial Aurora (ficticio)', 'Persona moral', 'Inmobiliaria', 'Jalisco', 'Registro de demostración'),
                ('Cliente Ejemplo 003', 'Persona física', 'Comprador', 'Nuevo León', 'Registro de demostración'),
                ('Grupo Horizonte (ficticio)', 'Persona moral', 'Inmobiliaria', 'Yucatán', 'Registro de demostración'),
            ]
            for values in names:
                c.execute('INSERT INTO clients(name,customer_type,industry,jurisdiction,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                          (*values, now(), now()))
            patterns = [(1,1,1,1),(2,2,2,2),(3,3,3,2),(2,1,3,2)]
            methodology = get_methodology(c)
            for client_id, risks in enumerate(patterns, start=1):
                score, level = compute(methodology, dict(zip(methodology['weights'],risks)))
                c.execute('INSERT INTO assessments(client_id,geography,customer,transactions,source_funds,score,level,methodology,justification,assessed_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (client_id,*risks,score,level,json.dumps(methodology), 'Evaluación ficticia inicial.', now()))

def get_methodology(c):
    return json.loads(c.execute('SELECT value FROM config WHERE key=?', ('methodology',)).fetchone()['value'])

def compute(methodology, risks):
    score = round(sum(float(weight)*risks[dimension] for dimension,weight in methodology['weights'].items()), 3)
    level = 'Alto' if score >= methodology['high_threshold'] else 'Medio' if score >= methodology['medium_threshold'] else 'Bajo'
    return score, level

class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    customer_type: Literal['Persona física','Persona moral']
    industry: str = Field(min_length=2, max_length=100)
    jurisdiction: str = Field(min_length=2,max_length=100)
    notes: str = Field(default='',max_length=1200)

    @field_validator('name','industry','jurisdiction')
    @classmethod
    def not_blank(cls, value):
        if not value.strip(): raise ValueError('No puede estar vacío')
        return value.strip()

class AssessmentCreate(BaseModel):
    geography: int = Field(ge=1,le=3)
    customer: int = Field(ge=1,le=3)
    transactions: int = Field(ge=1,le=3)
    source_funds: int = Field(ge=1,le=3)
    justification: str = Field(min_length=5,max_length=2500)

class MethodologyUpdate(BaseModel):
    weights: dict[str,float]
    medium_threshold: float = Field(gt=1,lt=3)
    high_threshold: float = Field(gt=1,le=3)
    version: str = Field(min_length=1,max_length=40)

    @field_validator('weights')
    @classmethod
    def valid_weights(cls, w):
        if set(w) != {'geography','customer','transactions','source_funds'} or any(v<0 or v>1 for v in w.values()) or abs(sum(w.values())-1)>0.0001:
            raise ValueError('Los cuatro pesos deben estar entre 0 y 1 y sumar 1')
        return w

@app.get('/')
def home(): return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/health')
def health(): return {'status': 'ok', 'mode':'DEMO_LOCAL'}

@app.get('/api/methodology')
def methodology():
    with connection() as c: return get_methodology(c)

@app.put('/api/methodology')
def update_methodology(body: MethodologyUpdate):
    if body.high_threshold <= body.medium_threshold:
        raise HTTPException(422,'El umbral alto debe ser mayor que el medio')
    with connection() as c:
        old = get_methodology(c)
        new = body.model_dump()
        c.execute('UPDATE config SET value=? WHERE key=?',(json.dumps(new),'methodology'))
        event(c,'ACTUALIZAR_METODOLOGIA','metodologia',1,{'anterior':old,'nueva':new})
    return new

@app.get('/api/clients')
def clients():
    with connection() as c:
        return [dict(r) for r in c.execute('''
            SELECT c.*, a.score AS latest_score, a.level AS latest_level,
            a.assessed_at AS latest_assessed_at
            FROM clients c LEFT JOIN assessments a ON a.id=(
              SELECT id FROM assessments WHERE client_id=c.id ORDER BY id DESC LIMIT 1)
            ORDER BY c.id DESC''').fetchall()]

@app.post('/api/clients', status_code=201)
def create_client(body: ClientCreate):
    with connection() as c:
        cur = c.execute('INSERT INTO clients(name,customer_type,industry,jurisdiction,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
            (body.name,body.customer_type,body.industry,body.jurisdiction,body.notes,now(),now()))
        event(c,'CREAR_CLIENTE','cliente',cur.lastrowid,body.model_dump())
        return {'id':cur.lastrowid,**body.model_dump()}

@app.get('/api/clients/{client_id}')
def client_detail(client_id: int):
    with connection() as c:
        r = c.execute('SELECT * FROM clients WHERE id=?',(client_id,)).fetchone()
        if not r: raise HTTPException(404,'Cliente no encontrado')
        assessments = [dict(x) for x in c.execute('SELECT * FROM assessments WHERE client_id=? ORDER BY id DESC',(client_id,))]
        for a in assessments: a['methodology']=json.loads(a['methodology'])
        return {'client':dict(r),'assessments':assessments}

@app.post('/api/clients/{client_id}/assessments',status_code=201)
def assess(client_id: int, body: AssessmentCreate):
    with connection() as c:
        if not c.execute('SELECT 1 FROM clients WHERE id=?',(client_id,)).fetchone():
            raise HTTPException(404,'Cliente no encontrado')
        m = get_methodology(c)
        risks = {k:getattr(body,k) for k in m['weights']}
        score, level = compute(m, risks)
        cur = c.execute('''INSERT INTO assessments(client_id,geography,customer,transactions,source_funds,score,level,methodology,justification,assessed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', (client_id,body.geography,body.customer,body.transactions,body.source_funds,
            score,level,json.dumps(m),body.justification.strip(),now()))
        event(c,'EVALUAR_RIESGO','evaluacion',cur.lastrowid,{'cliente':client_id,'factores':risks,'puntaje':score,'nivel':level,'metodologia':m['version']})
        return {'id':cur.lastrowid,'client_id':client_id,'score':score,'level':level,'methodology_version':m['version']}

@app.get('/api/dashboard')
def dashboard():
    with connection() as c:
        rows=c.execute('''SELECT c.id, a.level FROM clients c LEFT JOIN assessments a ON a.id=(
            SELECT id FROM assessments WHERE client_id=c.id ORDER BY id DESC LIMIT 1)''').fetchall()
        out={'total':len(rows),'Bajo':0,'Medio':0,'Alto':0,'Sin evaluar':0}
        for r in rows: out[r['level'] or 'Sin evaluar'] += 1
        out['recent']=[dict(r) for r in c.execute('''SELECT a.id,c.name,a.score,a.level,a.assessed_at FROM assessments a
          JOIN clients c ON c.id=a.client_id ORDER BY a.id DESC LIMIT 8''')]
        return out

@app.get('/api/audit')
def audit():
    with connection() as c:
        return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 150')]

@app.get('/api/export/clients.csv')
def export_clients():
    rows=clients()
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=['id','name','customer_type','industry','jurisdiction','latest_score','latest_level','latest_assessed_at'],extrasaction='ignore')
    writer.writeheader(); writer.writerows(rows)
    return StreamingResponse(iter([out.getvalue().encode('utf-8-sig')]),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':'attachment; filename="pld_clientes_demo.csv"'})

@app.get('/api/export/assessments.csv')
def export_assessments():
    with connection() as c:
        rows=[dict(r) for r in c.execute('''SELECT a.id,c.name AS cliente,a.geography,a.customer,a.transactions,a.source_funds,a.score,a.level,a.justification,a.assessed_at
          FROM assessments a JOIN clients c ON a.client_id=c.id ORDER BY a.id DESC''')]
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=['id','cliente','geography','customer','transactions','source_funds','score','level','justification','assessed_at'])
    writer.writeheader(); writer.writerows(rows)
    return StreamingResponse(iter([out.getvalue().encode('utf-8-sig')]),media_type='text/csv; charset=utf-8',
       headers={'Content-Disposition':'attachment; filename="pld_evaluaciones_demo.csv"'})

initialize()
