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
