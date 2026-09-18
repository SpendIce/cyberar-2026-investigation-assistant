# Inferencia local con Ollama (#4)

`InferenciaOllama` implementa el puerto `MotorDeInferencia` contra el
endpoint `/api/chat` de un servidor Ollama, con salida restringida por
esquema JSON (`format`). El mismo adaptador sirve al nodo privado y al
modelo local reducido: sólo cambian `base_url`, `modelo` y `modalidad`
(ADR-0011). El catálogo local ATT&CK
(`src/investigacion/datos/catalogo_attack.json`) fija qué técnicas puede
citar el modelo y `ValidadorDeReferencias` rechaza, además de referencias
inexistentes, cualquier técnica fuera de ese catálogo.

## Preparación

1. Instalar y ejecutar [Ollama](https://ollama.com) localmente: `ollama serve`.
2. Descargar el modelo elegido en ADR-0014: `ollama pull qwen2.5:7b-instruct`
   (o `llama3.2:3b` como alternativa más liviana documentada en el mismo ADR).

## Uso

```python
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.modelos import ModalidadInferencia

# Modelo local reducido (fallback)
motor_local = InferenciaOllama(
    "qwen2.5:7b-instruct", modalidad=ModalidadInferencia.MODELO_LOCAL,
)

# Nodo privado preferido (mismo contrato, otro endpoint y modalidad)
motor_privado = InferenciaOllama(
    "modelo-mayor-en-el-nodo",
    base_url="https://nodo-privado.interno:11434",
    modalidad=ModalidadInferencia.NODO_PRIVADO,
)
```

Cualquier falla de red, timeout, código distinto de 200, contenido ausente,
JSON no parseable o forma que no cumple el esquema esperado se traduce a
`InferenciaNoDisponible`; `ModuloDeInvestigacion.investigar_caso` ya sabe
convertir esa excepción en modo degradado (#2). La validación semántica de
referencias y técnicas ocurre después, en `ValidadorDeReferencias`.

## Qué recibe el modelo

Sólo la evidencia ya seleccionada (los eventos que se le pasen a `proponer`,
no el caso completo) y la lista `{id, nombre}` de técnicas del catálogo
local. El *system prompt* (`PROMPT_SISTEMA` en
`investigacion/adaptadores/ollama.py`) instruye explícitamente a tratar el
contenido de los eventos como datos citables, nunca como instrucciones, y a
abstenerse (`"hallazgos": []`) si la evidencia no alcanza. Esto no es una
garantía criptográfica contra manipulación — es responsabilidad del
validador posterior rechazar cualquier cosa que el modelo no pudo justificar
con referencias reales.

## Verificación

```bash
uv run pytest tests/test_inferencia_ollama.py   # unitarias, sin red: transporte sustituido
uv run mypy src
```

La prueba de contrato end-to-end contra un Ollama real es opt-in y requiere
el servidor corriendo con el modelo descargado:

```bash
OLLAMA_MODELO_PRUEBA=qwen2.5:7b-instruct uv run pytest tests/test_inferencia_ollama_real.py
```

Ejecuta el caso sembrado con temperatura 0 y semilla fija, e inspecciona el
resultado a través del mismo contrato que usa la interfaz
(`crear_caso` → `investigar_caso` → `consultar_caso`), no funciones internas.
`OLLAMA_BASE_URL` permite apuntar a otro endpoint.

Del mismo modo, `tests/test_manipulacion_ollama_real.py` corre el caso D del
spec #1 (una instrucción insertada en un campo de evidencia) contra un
Ollama real y comprueba que ningún hallazgo persistido cite la técnica o el
evento que esa instrucción pedía inventar — independientemente de si el
modelo obedeció o no. Detalle en `docs/pruebas.md`.

Estas pruebas cargan un modelo completo en memoria/GPU. Verificar con
`ollama ps` que no quede residente después, y liberarlo con
`ollama stop <modelo>` si hace falta.

## Elección de modelo y límites

La comparación entre modelos candidatos, su metodología y sus limitaciones
documentadas están en `docs/adr/0014-eleccion-modelo-local-ollama.md` y en
`docs/benchmarks/resultados-modelos.{json,md}`. En particular: ningún modelo
candidato completó de forma confiable el campo estructurado
`tecnicas_candidatas` aunque mencionara las técnicas correctas en el texto de
la hipótesis; la interfaz debe presentar ese campo vacío como tal, no como
ausencia de interpretación.

## Endpoints fuera de la infraestructura controlada

`InferenciaOllama` clasifica el `base_url` antes de enviar evidencia
(`investigacion/soberania.py`, ADR-0016): loopback, RFC1918, link-local y
la IP CGNAT de la tailnet (100.64.0.0/10) cuentan como infraestructura
controlada, más cualquier host declarado con `hosts_controlados` /
`--host-controlado` (útil cuando el nodo privado se alcanza por una
dirección pública administrada por el equipo). Un nombre `*.ts.net` no
cuenta por sí solo: cualquier tailnet ajena usa el mismo sufijo, así que
un nodo Tailscale se declara por nombre o por su IP CGNAT.

Un endpoint externo sin opt-in se comporta como un nodo caído:
`InferenciaNoDisponible` y la cadena de respaldo continúa con el modelo
local. Con `permitir_externo` / `--permitir-externo` la evidencia viaja y
la advertencia queda persistida en `caso.errores`, visible en Streamlit y
en el informe exportado. La decisión es del usuario; el rastro es del
sistema.

## Medir un modelo más capaz en un nodo remoto

El mismo contrato sirve para un modelo más potente alojado en un nodo
privado (ADR-0011): basta apuntar `base_url`/`--ollama-url-remoto` al
endpoint remoto con `modalidad=NODO_PRIVADO`. Si el nodo se alcanza por
dirección pública administrada por el equipo, declararlo con
`--host-controlado`; si el endpoint es de un tercero, la medición exige
`--permitir-externo` y la advertencia queda registrada en cada caso
procesado. La corrida remota de `scripts/evaluar_enfoques.py` acepta ambos
flags; sin un endpoint configurado la fila remota del reporte declara "no
configurado en esta máquina".
