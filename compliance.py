"""Flujos DEMO de obligaciones LFPIORPI para inmuebles. No presentar avisos reales."""
import csv, io, json, re
from collections import defaultdict
from datetime import date
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field

router=APIRouter(prefix="/api/compliance",tags=["Cumplimiento inmobiliario demo"])
ACTIVITIES={
 "V":{"name":"Comercialización/desarrollo/intermediación inmobiliaria","identification":"Siempre","notice_uma":8025},
 "V_BIS":{"name":"Recepción de recursos para desarrollo inmobiliario","identification":"Siempre","notice_uma":8025},
 "XV":{"name":"Uso o goce de inmuebles (arrendamiento)","identification_uma":1605,"notice_uma":3210}
}
SOURCES={
 "law":"https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPIORPI.pdf",
 "rules":"https://dof.gob.mx/nota_detalle_popup.php?codigo=5795797",
 "sat":"https://sppld.sat.gob.mx/pld/interiores/umbrales.html",
 "forms":"https://sppld.sat.gob.mx/pld/interiores/inmuebles.html"
}
CLIENT_COLUMNS=("external_id","name","customer_type","industry","jurisdiction","notes","identity_verified","beneficial_owner_verified","occupation_verified","source_of_funds_verified","pep_review","expected_monthly_mxn","expected_transactions_month","evidence_reference")
TX_COLUMNS=("transaction_id","client_external_id","date","activity","amount_mxn","payment_method","third_party","property_type","jurisdiction","notes")
YESNO={"si","no","pendiente"}
def yesno(v):return (v or "").strip().lower() in YESNO
def read_csv(contents, columns):
 if len(contents)>2_000_000:raise ValueError("CSV supera 2 MB")
 try: raw=contents.decode("utf-8-sig")
 except UnicodeDecodeError:raise ValueError("Usa CSV UTF-8")
 reader=csv.DictReader(io.StringIO(raw))
 if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):raise ValueError("Cabeceras inválidas o duplicadas")
 missing=set(columns)-set(reader.fieldnames)
 if missing:raise ValueError("Faltan columnas: "+", ".join(sorted(missing)))
 rows=list(reader)
 if len(rows)>1000:raise ValueError("Máximo 1000 filas por archivo")
 return rows
def valid_mxn(value):
 try:
  v=float(value)
  if not (0<=v<=1e11) or not __import__("math").isfinite(v):raise ValueError()
  return v
 except (TypeError,ValueError):raise ValueError("Monto inválido")
def check_client(row):
 if not (2<=len(row["name"].strip())<=160):raise ValueError("Nombre inválido")
 if row["customer_type"] not in ("Persona física","Persona moral"):raise ValueError("Tipo de cliente inválido")
 if not row["external_id"].strip() or len(row["external_id"])>70:raise ValueError("external_id inválido")
 for k in ("identity_verified","beneficial_owner_verified","occupation_verified","source_of_funds_verified"):
  if not yesno(row[k]):raise ValueError(k+" debe ser si/no/pendiente")
 if row["pep_review"] not in ("sin_coincidencia","pendiente","coincidencia_por_verificar"):raise ValueError("pep_review inválido")
 valid_mxn(row["expected_monthly_mxn"])
 n=int(row["expected_transactions_month"])
 if not 0<=n<=100000:raise ValueError("Número esperado inválido")
def check_tx(row):
 if row["activity"] not in ACTIVITIES:raise ValueError("Actividad no soportada")
 date.fromisoformat(row["date"])
 valid_mxn(row["amount_mxn"])
 if row["third_party"] not in ("si","no"):raise ValueError("third_party requiere si/no")
 if not row["transaction_id"].strip():raise ValueError("Falta transaction_id")
class Thresholds(BaseModel):
 uma_mxn:float=Field(gt=0,lt=10000,description="Valor de UMA proporcionado y validado por el usuario")
 year:int=Field(ge=2025,le=2100)
@router.get("/rules")
def rules():
 return {"activities":ACTIVITIES,"sources":SOURCES,"regulation":"LFPIORPI y reglas 2026","notice":"Evaluación orientativa. No presenta avisos ante SAT; los umbrales no sustituyen revisión jurídica."}
def install(app,connection,event,now):
 with connection() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS demo_profiles(
  client_id INTEGER PRIMARY KEY REFERENCES clients(id),external_id TEXT UNIQUE NOT NULL,
  identity_verified TEXT,beneficial_owner_verified TEXT,occupation_verified TEXT,
  source_of_funds_verified TEXT,pep_review TEXT,expected_monthly_mxn REAL,
  expected_transactions_month INTEGER,evidence_reference TEXT);
  CREATE TABLE IF NOT EXISTS demo_transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL,
  client_id INTEGER NOT NULL REFERENCES clients(id),date TEXT NOT NULL,
  activity TEXT NOT NULL,amount_mxn REAL NOT NULL,payment_method TEXT,
  third_party TEXT,property_type TEXT,jurisdiction TEXT,notes TEXT);
  """)
 @router.post("/import/clients")
 async def import_clients(file:UploadFile=File(...)):
  try:
   rows=read_csv(await file.read(),CLIENT_COLUMNS)
   if len({r["external_id"] for r in rows})!=len(rows):raise ValueError("external_id duplicado")
   for i,r in enumerate(rows,2):
    try:check_client(r)
    except Exception as exc:raise ValueError(f"Fila {i}: {exc}")
  except Exception as exc:raise HTTPException(422,str(exc))
  with connection() as c:
   present={r[0] for r in c.execute("SELECT external_id FROM demo_profiles")}
   if present.intersection(r["external_id"] for r in rows):raise HTTPException(409,"Ya existe uno o más external_id; no se duplican registros")
   for r in rows:
    cur=c.execute("INSERT INTO clients(name,customer_type,industry,jurisdiction,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
     (r["name"],r["customer_type"],r["industry"],r["jurisdiction"],r["notes"],now(),now()))
    c.execute("INSERT INTO demo_profiles VALUES(?,?,?,?,?,?,?,?,?,?)",(cur.lastrowid,r["external_id"],r["identity_verified"],r["beneficial_owner_verified"],r["occupation_verified"],r["source_of_funds_verified"],r["pep_review"],float(r["expected_monthly_mxn"]),int(r["expected_transactions_month"]),r["evidence_reference"]))
    event(c,"IMPORTAR_CLIENTE","cliente",cur.lastrowid,{"external_id":r["external_id"],"demo":True})
  return {"imported":len(rows),"type":"clients","status":"ok"}
 @router.post("/import/transactions")
 async def import_transactions(file:UploadFile=File(...)):
  try:
   rows=read_csv(await file.read(),TX_COLUMNS)
   if len({r["transaction_id"] for r in rows})!=len(rows):raise ValueError("transaction_id duplicado")
   for i,r in enumerate(rows,2):
    try:check_tx(r)
    except Exception as exc:raise ValueError(f"Fila {i}: {exc}")
  except Exception as exc:raise HTTPException(422,str(exc))
  with connection() as c:
   profiles={r["external_id"]:r["client_id"] for r in c.execute("SELECT external_id,client_id FROM demo_profiles")}
   if any(r["client_external_id"] not in profiles for r in rows):raise HTTPException(422,"Primero importa los clientes del CSV")
   existing={r[0] for r in c.execute("SELECT transaction_id FROM demo_transactions")}
   if existing.intersection(r["transaction_id"] for r in rows):raise HTTPException(409,"Operación previamente importada")
   for r in rows:
    cur=c.execute("INSERT INTO demo_transactions(transaction_id,client_id,date,activity,amount_mxn,payment_method,third_party,property_type,jurisdiction,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
     (r["transaction_id"],profiles[r["client_external_id"]],r["date"],r["activity"],float(r["amount_mxn"]),r["payment_method"],r["third_party"],r["property_type"],r["jurisdiction"],r["notes"]))
    event(c,"IMPORTAR_OPERACION","operacion",cur.lastrowid,{"transaction_id":r["transaction_id"],"demo":True})
  return {"imported":len(rows),"type":"transactions","status":"ok"}
 @router.get("/profiles")
 def profiles():
  with connection() as c:return [dict(r) for r in c.execute("SELECT c.name,p.* FROM demo_profiles p JOIN clients c ON c.id=p.client_id ORDER BY p.client_id")]
 @router.post("/analyze")
 def analyze(body:Thresholds):
  with connection() as c:
   profiles=[dict(r) for r in c.execute("SELECT p.*,c.name FROM demo_profiles p JOIN clients c ON c.id=p.client_id")]
   txs=[dict(r) for r in c.execute("SELECT * FROM demo_transactions ORDER BY date,id")]
  grouped=defaultdict(list)
  for r in txs:grouped[r["client_id"]].append(r)
  output=[]
  for p in profiles:
   records=grouped[p["client_id"]]; flags=[]
   for key in ("identity_verified","beneficial_owner_verified","occupation_verified","source_of_funds_verified"):
    if p[key]!="si":flags.append({"type":"EXPEDIENTE","detail":key+" no verificado","legal_status":"Revisión requerida"})
   if p["pep_review"]!="sin_coincidencia":flags.append({"type":"LISTAS","detail":"Verificación PEP pendiente; no equivale a coincidencia oficial","legal_status":"Revisión requerida"})
   amount=sum(x["amount_mxn"] for x in records)
   if len(records)>p["expected_transactions_month"] and p["expected_transactions_month"]>0:flags.append({"type":"PERFIL","detail":"Número de operaciones supera referencia mensual sin normalizar periodo","legal_status":"Indicador exploratorio"})
   if amount>p["expected_monthly_mxn"] and p["expected_monthly_mxn"]>0:flags.append({"type":"PERFIL","detail":"Monto acumulado supera referencia mensual sin normalizar periodo","legal_status":"Indicador exploratorio"})
   detail=[]
   for x in records:
    activity=ACTIVITIES[x["activity"]]
    value=x["amount_mxn"]/body.uma_mxn
    above=value>=activity["notice_uma"]
    if x["third_party"]=="si":flags.append({"type":"OPERACION","detail":"Pago de tercero: "+x["transaction_id"],"legal_status":"Revisión requerida"})
    detail.append({"transaction_id":x["transaction_id"],"activity":x["activity"],"amount_mxn":x["amount_mxn"],"amount_uma":round(value,3),"notice_threshold_uma":activity["notice_uma"],"single_operation_above_threshold":above,"notice_status":"Revisión jurídica de aviso" if above else "Revisar acumulación y demás reglas"})
   output.append({"external_id":p["external_id"],"name":p["name"],"transactions":len(records),"total_mxn":round(amount,2),"flags":flags,"operations":detail})
  return {"reference_uma_year":body.year,"uma_mxn":body.uma_mxn,"clients":output,
  "important":"Umbrales por operación orientativos, sin cálculo reglamentario de acumulación, ventanas y excepciones; NO determina obligación definitiva de aviso. El valor UMA debe confirmarse oficialmente. No se han conectado servicios del SAT."}
 app.include_router(router)
