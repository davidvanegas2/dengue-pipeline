# Cómo trabajar en este repositorio

## Primera vez

```bash
uv sync                      # dependencias exactas de uv.lock
uv run pre-commit install    # revisa tu código antes de cada commit
```

## El ciclo

1. Crea una rama: `git switch -c feature/my-change`.
2. Haz tu cambio.
3. `make format` (o `uv run ruff format . && uv run sqlfluff fix sql`).
4. `make lint` y `make test`. Todo en verde.
5. Commit con un mensaje que diga **qué** y **por qué**: `feat(extract): read bulletin tables across two pages`.

## Recetas

**Agregar una transformación SQL.** Crea `sql/silver/05_new_source.sql` (o en `gold/`).
Se ejecuta sola en orden alfabético. Usa `CREATE OR REPLACE TABLE schema.table AS ...`
para que se pueda correr muchas veces. Agrega una prueba en `tests/test_pipeline.py`.

**Agregar una fuente.** Una función en `src/dengue_pipeline/extract/` que devuelva un
DataFrame **sin transformar** (todo como texto si viene de CSV o Excel). Cárgala a
`bronze` en `pipeline.load_bronze()` y límpiala en un archivo SQL de plata.

**Agregar una verificación de calidad.** Una función en `quality.py` que devuelva un
`CheckResult`, agregada a `CHECKS`. Usa `critical=False` si fallar debe ser solo
un aviso.

**Cambiar el notebook del taller.** Edita **solo** `notebooks/workshop_facilitator.py`.
Marca lo que verá la estudiante con bloques `>>> SOLUTION` / `>>> STUDENT` y corre
`make student-notebook`. No edites `notebooks/workshop.py` a mano: se regenera.

## Convenciones

* Código en inglés: nombres de archivos, módulos, funciones, variables, tablas y columnas
  propias, comentarios, docstrings, pruebas y comandos.
* README, retos, documentación y explicaciones visibles del notebook en español.
* Conserva los nombres y valores originales de las fuentes en `data/raw/` y `data/reference/`
  y al leerlos en bronce. Expón nombres en inglés mediante alias en plata; no traduzcas
  campos oficiales como `cod_eve` o `semana`, nombres de lugares ni etiquetas de origen.
* Tipos en todas las funciones públicas (mypy en modo estricto).
* Las pruebas que necesitan internet llevan `@pytest.mark.network`; las lentas, `@pytest.mark.slow`.
