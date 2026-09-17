---
status: accepted
---

# Control legítimo sintético como paso interino hacia la captura en VM

ADR-0004 pide que el control legítimo sea "una operación administrativa
legítima generada en una VM aislada". En este entorno no había una VM
Windows apropiada para producir esa captura, así que el issue #8 se
implementa con un control sintético/documentado
(`investigacion.escenarios.eventos_control_legitimo`): eventos escritos a
mano con la misma forma que la secuencia sospechosa (PSEXESVC + PowerShell +
SMB hacia un recurso interno), cuyo origen declara `captura: sintetica` y
cuyo sha256 se calcula sobre la serialización canónica de la fixture.

Esto modifica, no elimina, ADR-0004: la captura en VM aislada sigue siendo
el control definitivo y queda como trabajo pendiente. Mientras tanto, el
control sintético habilita la comparación A/B desde la misma interfaz sin
presentarse como telemetría real.

## Regla derivada: la autorización no se anota dentro de la evidencia

La primera versión de la fixture incluía en `contenido` marcas de
autorización ("script firmado, catalogado en CMDB", "recurso de parches
conocido en CMDB", "para CHG-4821"). ADR-0004 exige que la verdad de
referencia permanezca separada "para evitar que nombres, etiquetas ATT&CK o
descripciones del escenario revelen la respuesta esperada", y esas
anotaciones hacían exactamente eso dentro del canal que recibe el modelo:
el caso B llegaba pre-etiquetado como autorizado y dejaba de ser telemetría
comparable con el caso A.

El `contenido` del control describe ahora sólo lo observable (el evento de
ticket existe en el canal Application; la correlación ticket ↔ servicio ↔
script ↔ conexión la hace el analista o el modelo, como en el escenario A).
El contexto de autorización vive únicamente en
`docs/evaluacion/verdad-referencia-escenarios.json`, que no se carga en
`Caso`, `Evento`, SQLite ni en la solicitud al modelo.

## Consequences

- Cuando exista la captura real en VM, `eventos_control_legitimo` se
  reemplaza o se complementa con esa telemetría importada por Hayabusa,
  manteniendo la misma regla: la evidencia lleva lo observable; la verdad
  de referencia lleva la autorización documentada.
- Todo control futuro (sintético o capturado) debe revisarse contra la
  misma regla antes de entregarse al modelo: si el texto del evento afirma
  la autorización en vez de dejarla inferir, contamina la comparación.
