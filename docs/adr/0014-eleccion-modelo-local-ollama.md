---
status: accepted
---

# Elegir qwen2.5:7b-instruct como modelo local reducido de respaldo

ADR-0009 y ADR-0011 exigen que la elección del modelo local reducido se
resuelva por benchmark reproducible, no por tamaño nominal o reputación. Se
comparó `llama3.2:3b` y `qwen2.5:7b-instruct` mediante Ollama 0.32.15, con el
mismo caso sembrado (`investigacion.sembrado.eventos_sembrados`), el mismo
hardware y los mismos criterios, usando `scripts/benchmark_modelos.py`.

## Hardware de medición

Linux x86_64, 32 CPUs lógicas visibles, ~27 GiB RAM, Ollama con backend
GPU (`ollama ps` reportó `100% GPU` para ambos modelos). La notebook de
presentación puede diferir; el benchmark debe re-ejecutarse allí antes de la
demo (ver "Cómo reproducir" abajo) y sus resultados no deben leerse como
válidos para otro hardware.

## Resultados (temperatura 0, semilla 7, 3 corridas cada uno)

| Modelo | Corridas OK | Latencia media | Hallazgos aceptados/propuestos | Referencias resolubles/citadas | Técnicas en `tecnicas_candidatas`/catálogo | Memoria |
|---|---|---|---|---|---|---|
| llama3.2:3b | 3/3 | 3.56 s | 9/9 | 15/15 | 0/0 | 2.6 GB |
| qwen2.5:7b-instruct | 3/3 | 2.48 s | 3/3 | 6/6 | 0/0 | 4.7 GB |

Detalle corrida por corrida en `docs/benchmarks/resultados-modelos.json`
(generado el 2026-09-16). Ambos modelos cumplieron el esquema JSON exigido en
las tres corridas y sólo citaron `uid` de eventos existentes: ningún dato de
este benchmark viene de una respuesta rechazada.

## Decisión

Se elige **qwen2.5:7b-instruct** como modelo local reducido de respaldo
(`ModalidadInferencia.MODELO_LOCAL`). Con este hardware su latencia fue menor
y más estable que la de `llama3.2:3b`, y produjo una única hipótesis que
integra la instalación del servicio y la ejecución de PowerShell en lugar de
fragmentar la misma evidencia en tres hallazgos separados como hizo
`llama3.2:3b` — más cercano al criterio de "menos ruido, más trazabilidad"
del spec (#1). Se conserva `llama3.2:3b` como alternativa documentada para
hardware más limitado (2.6 GB frente a 4.7 GB de memoria reportada), no como
un segundo fallback activo del MVP (spec #1: "Ninguna arquitectura
multimodelo").

## Limitaciones observadas

- **Ninguno de los dos modelos completó de forma confiable el arreglo
  `tecnicas_candidatas`.** `qwen2.5:7b-instruct` mencionó los identificadores
  de técnica correctos (`T1021.002`, `T1569.002`) dentro del texto de
  `hipotesis`, no en el campo estructurado destinado a eso; `llama3.2:3b` no
  los mencionó en absoluto. El validador (`ValidadorDeReferencias`) no
  inventa técnicas ausentes: un hallazgo sin `tecnicas_candidatas` se acepta
  igual si sus referencias son válidas, y la interfaz debe mostrar ese campo
  como vacío, no como "sin técnica detectada". Esto es una limitación de
  calidad del modelo, no un fallo de validación.
- El benchmark corre sobre un único caso sembrado y hardware con aceleración
  GPU disponible; **no** mide el peor caso (CPU pura) que exige ADR-0009 como
  piso de aceptación en la notebook de presentación. Debe repetirse allí.
- Tres corridas por modelo alcanzan para observar reproducibilidad exacta a
  temperatura 0, pero no para estimar variación real del modelo: no se
  reporta como medición estadística poblacional (spec #1, fuera de alcance).
- El benchmark no ejerce manipulación (texto insertado en campos de evidencia)
  ni evidencia insuficiente; esos escenarios corresponden a un ticket de
  evaluación posterior (#1, "Casos de evaluación" C/D) y usan el mismo
  adaptador `InferenciaOllama`.

## Cómo reproducir

```bash
uv run python scripts/benchmark_modelos.py --modelos llama3.2:3b qwen2.5:7b-instruct --repeticiones 3
```

Requiere `ollama serve` corriendo localmente con ambos modelos descargados
(`ollama pull llama3.2:3b`, `ollama pull qwen2.5:7b-instruct`). Escribe
`docs/benchmarks/resultados-modelos.json` y `.md`; ambos se versionan para
conservar la medición que sustenta esta decisión, y deben regenerarse si
cambia el hardware de referencia o los modelos candidatos.

## Consequences

`ModuloDeInvestigacion` puede construirse con
`InferenciaOllama("qwen2.5:7b-instruct", modalidad=ModalidadInferencia.MODELO_LOCAL)`
como fallback local real. El nodo privado (ADR-0011) sigue siendo preferido
cuando está disponible y usa el mismo adaptador con otro `base_url`, `modelo`
y `modalidad=ModalidadInferencia.NODO_PRIVADO`. La interfaz debe mostrar
`tecnicas_candidatas` vacío sin tratarlo como ausencia de interpretación,
dado el límite documentado arriba.
