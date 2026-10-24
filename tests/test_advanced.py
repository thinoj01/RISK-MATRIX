from fastapi.testclient import TestClient
from app import app
from advanced import FACTORS

client = TestClient(app)
BASE = {
 "scores": {k:1 for k in FACTORS}, "red_flags": [], "controls": [],
 "amount_mxn": 1000000, "property_type":"Casa", "transaction_type":"Compraventa",
 "payment_description":"Transferencia bancaria simulada",
 "evidence_reference":"EXP-DEMO-001","analyst":"Analista ficticio",
 "rationale":"Evaluación ficticia para pruebas; documentación pendiente de confirmar."
}

def test_schema_and_ui():
 assert client.get("/api/advanced/schema").status_code == 200
 assert client.get("/static/advanced.html").status_code == 200

def test_low_score_with_critical_flag_is_high():
 body={**BASE,"red_flags":["opaque_ownership"]}
 result=client.post("/api/advanced/clients/1",json=body)
 assert result.status_code==201
 assert result.json()["level"]=="Alto"
 assert result.json()["override_reasons"]==["opaque_ownership"]
 assert client.get("/api/advanced/clients/1").status_code==200

def test_low_risk_without_flags():
 result=client.post("/api/advanced/clients/1",json=BASE)
 assert result.status_code==201
 assert result.json()["level"]=="Bajo"

def test_missing_factor_rejected():
 result=client.post("/api/advanced/clients/1",json={**BASE,"scores":{"identity":1}})
 assert result.status_code==422
