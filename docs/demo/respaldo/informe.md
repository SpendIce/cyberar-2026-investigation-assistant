# Caso 7afe62aa3c2b46d6848a1197eb2545eb

- Procedencia: https://github.com/Yamato-Security/hayabusa-sample-evtx/tree/0845333ecb4afcf64c55c6e10946383f168f308c/DeepBlueCLI
- SHA-256: 971915aa6e7a508c4f0a2cb0e76882fd43234fa61c906dc33adf431efc8f2cd4
- Modalidad de inferencia: modelo_local
- Versiones: binario_sha256 ade927e5b67b63b2116144177db34ab4eb5bf27d4a9c54c552075e2b8c37bdae, config_sha256 14990fa599625ac263fa2180e5e0205cf049ab6cb582df95cb05360851b9a51f, formato jsonl, hayabusa 4.1.0, normalizador 1, perfil all-field-info-verbose, reglas_sha256 d1ea8adb9c6d5b6df23de07846c84539ff241f05f1575220f751ce9b89a9a036, salida_sha256 54c99396e75e9b5136e9c8bfa1678b9a6890c9ddffde7dc1ae929dc679214483

## Cronología (3 eventos)

- `ev-a29e8daa52042298f77bde7695469237b9e44720e2cb27de36f904b064f2578a` 2016-09-20T16:34:04.2724600Z — 104 — Channel=System;EventRecordID=8423
- `ev-0c4a255fbb83e0d8742a83e86e2d3fa3af93e7c07a0a08021d2a8c9a1f5927bb` 2016-09-20T16:35:46.5908200Z — 7045 — Channel=System;EventRecordID=8424
- `ev-780b05f1894ff77c60218e9189003fa25c872ca215fe3dffcda38456644fc871` 2016-09-20T16:35:58.1621090Z — 7045 — Channel=System;EventRecordID=8426

## Hallazgos (1)

### Potencialmente malicioso servicio instalado

- Referencias: ev-a29e8daa52042298f77bde7695469237b9e44720e2cb27de36f904b064f2578a, ev-0c4a255fbb83e0d8742a83e86e2d3fa3af93e7c07a0a08021d2a8c9a1f5927bb, ev-780b05f1894ff77c60218e9189003fa25c872ca215fe3dffcda38456644fc871
- Razón del vínculo: Los eventos indican la instalación de un servicio con un comando potencialmente peligroso y un tipo de servicio no común, lo que sugiere una posible intención maliciosa.
- Técnicas candidatas: T1543.003, T1134.001, T1134.002
- Procedencia del mapeo: modelo
- Estado de revisión: pendiente
- Explicaciones alternativas: El servicio podría ser una herramienta de administración legítima.; El comando podría ser una prueba de concepto o un error humano.
- Evidencia faltante: Información adicional sobre el servicio, como su propósito o la entidad que lo instaló.
- Limitaciones: No se dispone de contexto adicional sobre el entorno de la máquina.


## Integridad

- Sello del caso (SHA-256): `8a24446fa42e841976d8ada0951b889c106680c87dada22fd079aa63a4d695c0`
- Escrituras encadenadas: 2
