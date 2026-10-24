import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/api/advanced", tags=["Evaluaciones avanzadas"])
FACTORS = {
 "identity":("Identidad y expediente",.12,["Identidad verificada","Expediente incompleto","Identidad no verificable"]),
 "beneficial_owner":("Beneficiario controlador",.13,["Identificado","Estructura compleja","No identificado"]),
 "activity":("Actividad económica",.09,["Comprobada","Parcialmente sustentada","Incongruente"]),
 "funds":("Origen de los recursos",.17,["Documentado","Documentación parcial","No sustentado"]),
 "payment":("Medio de pago",.12,["Rastreable","Mixto","Atípico o no rastreable"]),
 "transaction":("Comportamiento operativo",.13,["Esperado","Variaciones","Inusual"]),
 "geography":("Exposición geográfica",.07,["Justificada","Requiere revisión","Elevada"]),
 "third_party":("Intermediarios y terceros",.08,["Justificados","Parcialmente documentados","No justificados"]),
 "pep":("PEP y vínculos",.05,["Sin coincidencia","Pendiente de revisión","Coincidencia confirmada"]),
 "history":("Antecedentes internos",.04,["Sin alertas","Alertas resueltas","Alertas pendientes"])
}
RED_FLAGS = {
 "refuses_documents":"Rechazo reiterado a documentos",
 "third_party_payment":"Pago de tercero sin justificación",
 "fragmented_payments":"Pagos fraccionados atípicos",
 "inconsistent_funds":"Recursos incompatibles con perfil",
 "opaque_ownership":"Propiedad no esclarecida",
 "urgency":"Urgencia inusual",
 "rapid_resale":"Reventa rápida atípica",
 "unresolved_match":"Coincidencia pendiente de verificación"
}
CONTROLS = {
 "id_checked":"Identidad revisada",
 "owner_checked":"Beneficiario revisado",
 "funds_checked":"Origen de fondos revisado",
 "payment_checked":"Pago documentado",
 "reviewer_approved":"Revisión humana registrada"
}
class AdvancedAssessment(BaseModel):
 scores: dict[str,int]
 red_flags: list[str] = Field(default_factory=list)
 controls: list[str] = Field(default_factory=list)
 amount_mxn: float = Field(ge=0,le=100000000000)
 property_type: Literal["Casa","Departamento","Terreno","Local comercial","Otro"]
 transaction_type: Literal["Compraventa","Arrendamiento","Cesión de derechos","Otro"]
 payment_description: str = Field(min_length=8,max_length=1200)
 evidence_reference: str = Field(min_length=5,max_length=1000)
 analyst: str = Field(min_length=2,max_length=100)
 rationale: str = Field(min_length=20,max_length=3000)

def evaluate(body):
 if set(body.scores)!=set(FACTORS) or any(type(v)!=int or v not in (1,2,3) for v in body.scores.values()):
  raise ValueError("Debes calificar los diez factores del 1 al 3")
 if len(body.red_flags)!=len(set(body.red_flags)) or set(body.red_flags)-set(RED_FLAGS): raise ValueError("Alertas inválidas")
 if len(body.controls)!=len(set(body.controls)) or set(body.controls)-set(CONTROLS): raise ValueError("Controles inválidos")
 score=round(sum(body.scores[k]*v[1] for k,v in FACTORS.items()),4)
 level="Alto" if score>=2.4 else "Medio" if score>=1.7 else "Bajo"
 critical=[k for k in ("refuses_documents","opaque_ownership","unresolved_match","inconsistent_funds") if k in body.red_flags]
 if body.red_flags and level=="Bajo": level="Medio"
 if critical or len(body.red_flags)>=3: level="Alto"
 missing=[CONTROLS[k] for k in CONTROLS if k not in body.controls]
 return {"score":score,"level":level,"status":"Revisión reforzada" if level=="Alto" else ("Revisión pendiente" if missing or body.red_flags else "Evaluado"),
 "flags":[{"code":k,"description":RED_FLAGS[k]} for k in body.red_flags],
 "missing_controls":missing,"override_reasons":critical,
 "contributions":[{"factor":k,"label":v[0],"score":body.scores[k],"weight":v[1],"contribution":round(v[1]*body.scores[k],4),"choice":v[2][body.scores[k]-1]} for k,v in FACTORS.items()],
 "rules_version":"DEMO-ADV-1.0","disclaimer":"No constituye dictamen regulatorio ni evidencia de delito."}

def register_advanced(app, db_path, connection_fn, audit_fn):
 with connection_fn() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS advanced_assessments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,client_id INTEGER NOT NULL REFERENCES clients(id),
  payload TEXT NOT NULL,result TEXT NOT NULL,created_at TEXT NOT NULL)""")
 @router.get("/schema")
 def schema(): return {"factors":{k:{"label":v[0],"weight":v[1],"choices":v[2]} for k,v in FACTORS.items()},"red_flags":RED_FLAGS,"controls":CONTROLS,"version":"DEMO-ADV-1.0"}
 @router.post("/clients/{client_id}",status_code=201)
 def create(client_id:int,body:AdvancedAssessment):
  try: result=evaluate(body)
  except ValueError as exc: raise HTTPException(422,str(exc))
  with connection_fn() as c:
   if not c.execute("SELECT 1 FROM clients WHERE id=?",(client_id,)).fetchone(): raise HTTPException(404,"Cliente no encontrado")
   cur=c.execute("INSERT INTO advanced_assessments(client_id,payload,result,created_at) VALUES (?,?,?,?)",
    (client_id,body.model_dump_json(),json.dumps(result,ensure_ascii=False),datetime.now(timezone.utc).isoformat(timespec="seconds")))
   audit_fn(c,"EVALUACION_AVANZADA","evaluacion",cur.lastrowid,{"cliente":client_id,"nivel":result["level"],"reglas":result["rules_version"]})
   return {"id":cur.lastrowid,"client_id":client_id,**result}
 @router.get("/clients/{client_id}")
 def history(client_id:int):
  with connection_fn() as c:
   if not c.execute("SELECT 1 FROM clients WHERE id=?",(client_id,)).fetchone(): raise HTTPException(404,"Cliente no encontrado")
   return [{**dict(r),"payload":json.loads(r["payload"]),"result":json.loads(r["result"])} for r in c.execute("SELECT * FROM advanced_assessments WHERE client_id=? ORDER BY id DESC",(client_id,))]
 app.include_router(router)
