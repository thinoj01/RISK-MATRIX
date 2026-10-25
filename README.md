# PLD Risk — Piloto local v0.1

Plataforma web de demostración para una **matriz de riesgo PLD ilustrativa** orientada a inmobiliarias en México. La aplicación se entrega con cuatro clientes ficticios y una base SQLite local.

## Cómo iniciar

Se requiere Python 3.10+.

```bash
cd pld_piloto
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# En Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Abrir http://127.0.0.1:8000 en el navegador. Documentación técnica API: http://127.0.0.1:8000/api/docs.

Para restablecer la demostración, detener el servidor y borrar `pilot.db`. La próxima ejecución creará datos ficticios de nuevo.

## Funciones implementadas
- Panel con recuento de clientes por riesgo y evaluaciones recientes.
- Altas de clientes y búsqueda local.
- Evaluación con 4 factores (geografía, cliente, operaciones y origen de recursos); niveles 1–3.
- Metodología configurable: pesos que suman 100%, umbrales y versión.
- Persistencia SQLite e historial completo de evaluaciones con la versión de metodología utilizada.
- Bitácora de nuevas evaluaciones, clientes y cambios de configuración.
- Exportación CSV de clientes y evaluaciones.
- Informe imprimible de cada cliente (el navegador permite guardar como PDF).
- API JSON que puede ampliarse para integraciones.

## Advertencias críticas
- **No cumple por sí sola los requisitos PLD aplicables en México**; no se ha hecho validación jurídica ni regulatoria de factores, pesos, metodologías, umbrales o procesos.
- **No introducir datos personales o financieros reales.** No incorpora autenticación, autorización, aislamiento multiempresa, cifrado de datos almacenados, registro de consentimiento, respaldo gestionado, pruebas de penetración ni auditoría inmutable.
- El motor de puntajes es únicamente demostrativo; sus niveles no identifican delitos ni dictan decisiones regulatorias.
- No hay conexión con SAT, UIF, CNBV, PEP, sanciones ni proveedores de KYC.
- Ejecutar solo en `127.0.0.1`, nunca abrir a Internet sin rediseñar la seguridad.

## Próximos pasos antes de uso comercial
1. Contratar especialista mexicano en PLD para definir matriz por actividad, documentación y procesos.
2. Diseñar multi-tenancy con aislamiento sólido, usuarios, SSO/MFA y RBAC.
3. Mover a PostgreSQL con migraciones y cifrado, gestión de secretos y copias de seguridad.
4. Implementar controles de privacidad, retención de información, seguridad, trazabilidad inmutable y alertas operativas.
5. Agregar pruebas de integración, seguridad y revisión legal independiente.


## Evaluación avanzada (v0.2)

Abrir **Evaluación avanzada** en la barra lateral o visitar `/static/advanced.html`. Incluye diez dimensiones de riesgo ponderadas, señales de alerta independientes del promedio, controles documentales, justificación y evidencia, historial y desglose explicable por factor. Nuevas rutas: `GET /api/advanced/schema`, `POST /api/advanced/clients/{id}` y `GET /api/advanced/clients/{id}`.

El módulo y sus reglas son **ilustrativos**, no un criterio oficial de riesgo ni un sistema certificado. No introducir datos reales: faltan autenticación, protección multiempresa y revisión jurídica de las metodologías.

## Módulo importación CSV y revisión de obligaciones (v0.3)

Abrir **Importar CSV / cumplimiento** o `http://127.0.0.1:8000/static/compliance.html`.

1. Importar `examples/clientes_demo.csv` (seis clientes totalmente ficticios).
2. Importar `examples/operaciones_demo.csv` (ocho operaciones ficticias).
3. Introducir el **valor oficial diario de UMA** correspondiente al ejercicio; confirmar valor y año en la fuente oficial antes de analizar.
4. Ver estado de expedientes, pagos de terceros, desviaciones exploratorias de perfil y comparación por **operación individual** contra umbrales expresados en UMA.

API: `GET /api/compliance/rules`, `POST /api/compliance/import/clients`, `POST /api/compliance/import/transactions`, `GET /api/compliance/profiles`, `POST /api/compliance/analyze`.

La importación es **solo para datos sintéticos**. Bloquea identificadores externos repetidos y operaciones duplicadas, valida campos obligatorios, fechas, rangos y vínculos entre archivos. Carga atómica por archivo. Máximo 1000 filas y 2 MB. No sustituye controles empresariales de PII.

### Cobertura y brechas regulatorias

Referencias revisadas: LFPIORPI art. 17 fracciones V, V Bis y XV y art. 18; Reglas de carácter general actualizadas en Acuerdo 115/2026, especialmente arts. 10 Septies, 11, 12, 23 Bis y 41. Fuentes: https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPIORPI.pdf ; https://dof.gob.mx/nota_detalle_popup.php?codigo=5795797 ; https://sppld.sat.gob.mx/pld/interiores/umbrales.html .

Implementado parcialmente: expediente estructurado orientativo, estado de verificación de identidad/beneficiario/origen de fondos, referencias de documentos, operación por cliente y comparación de umbral individual. Las ponderaciones de la matriz avanzada son **hipótesis del prototipo, no prescripciones legales**.

NO IMPLEMENTADO: acumulación reglamentaria por periodo, lógica integral de casos y excepciones, restricciones de efectivo, XML SAT para avisos, validación de PEP y listas oficiales, perfil transaccional mensual normalizado, retención efectiva de 10 años, manual de políticas, auditorías, revisión independiente, seguridad multiempresa, cifrado y autenticación. **El software NO determina de manera concluyente una obligación de aviso y NO realiza presentaciones al SAT.** Requiere análisis legal por actividad, vigencia y caso concreto antes de utilizarse comercialmente.
