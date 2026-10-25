import io
import pytest
from fastapi.testclient import TestClient
from app import app

api=TestClient(app)
CLIENTS=b"""external_id,name,customer_type,industry,jurisdiction,notes,identity_verified,beneficial_owner_verified,occupation_verified,source_of_funds_verified,pep_review,expected_monthly_mxn,expected_transactions_month,evidence_reference
QA-001,Persona Ficticia QA,Persona fisica,Prueba,CDMX,Ficticio,si,si,si,si,sin_coincidencia,100000,1,EXP-TEST-001
""".replace(b"Persona fisica", "Persona física".encode("utf-8"))
TX=b"""transaction_id,client_external_id,date,activity,amount_mxn,payment_method,third_party,property_type,jurisdiction,notes
QA-TX-001,QA-001,2026-10-05,V,1000000,Transferencia,si,Casa,CDMX,Prueba
"""
def test_rules():
 r=api.get("/api/compliance/rules")
 assert r.status_code==200
 assert r.json()["activities"]["V"]["notice_uma"]==8025

def test_invalid_csv():
 r=api.post("/api/compliance/import/clients", files={"file":("bad.csv",b"foo,bar\na,b\n","text/csv")})
 assert r.status_code==422

def test_import_and_analysis():
 # Run with a fresh PLD_DB path in CI.
 a=api.post("/api/compliance/import/clients",files={"file":("clients.csv",CLIENTS,"text/csv")})
 assert a.status_code==200,a.text
 b=api.post("/api/compliance/import/transactions",files={"file":("tx.csv",TX,"text/csv")})
 assert b.status_code==200,b.text
 c=api.post("/api/compliance/analyze",json={"uma_mxn":117.31,"year":2026})
 assert c.status_code==200,c.text
 match=next(x for x in c.json()["clients"] if x["external_id"]=="QA-001")
 assert match["operations"][0]["single_operation_above_threshold"] is True
 assert any(x["type"]=="OPERACION" for x in match["flags"])
