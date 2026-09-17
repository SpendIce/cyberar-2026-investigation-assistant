---
status: accepted
---

# Permitir endpoints externos sólo con decisión explícita y advertencia persistida

La herramienta es local-first por diseño (ADR-0008, ADR-0011), pero el contrato Ollama es agnóstico del destino: la misma URL puede apuntar al modelo local, al nodo privado o a un proveedor externo. En lugar de prohibir el tercer caso —la decisión operativa es de quien usa la herramienta— el adaptador clasifica el endpoint: loopback, RFC1918, link-local y overlays CGNAT (Tailscale) cuentan como infraestructura controlada, más los hosts que el equipo declare como propios. Un endpoint externo sin opt-in se comporta como un nodo caído: `InferenciaNoDisponible` y el respaldo continúa. Con `permitir_externo`/`--permitir-externo` la evidencia viaja, pero la advertencia queda persistida en el caso y visible en el informe.

## Consequences

La soberanía queda como una propiedad del despliegue, no del código: el sistema no impide la salida de evidencia a un tercero, pero la exige declarada y la registra. Esto habilita medir un modelo más potente en un endpoint remoto sin maquillar el costo de soberanía, y deja el rastro auditable en `caso.errores` cuando esa decisión se tomó.
