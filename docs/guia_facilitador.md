# Guía para quien dicta el taller

**Formato:** 50 minutos de taller + 10 de preguntas · viernes 4 de diciembre, en la mañana,
**antes** del taller de ML.
**Idea central:** mostrar cada técnica **una vez**, en un caso pequeño, y dejar las
preguntas difíciles abiertas para la hackathon (`RETOS.md`).

---

## Antes del 4 de diciembre

- [x] **Reemplazar la muestra sintética de SIVIGILA** por datos reales
      ([`data/raw/sivigila/LEEME.md`](../data/raw/sivigila/LEEME.md)): dengue (210) y
      dengue grave (220), años 2024 y 2025. Luego `make pipeline` y versiona
      `data/gold/weekly_dengue_signal.parquet`.
- [x] Crear el [repositorio en GitHub](https://github.com/davidvanegas2/dengue-pipeline).
      Actualmente es público y su rama principal es `main`.
- [x] Configurar `REPO_URL` en `notebooks/workshop_facilitator.py` con
      `https://raw.githubusercontent.com/davidvanegas2/dengue-pipeline/main`
      y regenerar `notebooks/workshop.py` con `make student-notebook`.
- [ ] Agregar al README el badge de molab (generador en <https://molab.marimo.io/github>).
- [ ] Probar el notebook en **molab** con una cuenta nueva (con el repo ya público, o
      con un repo de prueba público).
- [ ] Probar `uv sync && uv run marimo edit notebooks/workshop.py` en un computador limpio
      (ojalá Windows, donde `make` no viene instalado).
- [ ] **Coordinar con el taller de ML:** que use `data/gold/weekly_dengue_signal.parquet`
      como entrada; acordar columnas (`docs/diccionario_de_datos.md`).
- [ ] **Pedir a la organización:** wifi para ~40 portátiles, proyector, que las
      participantes traigan portátil cargado y cuenta de GitHub o Google (para molab),
      y 1-2 personas de apoyo en sala.
- [ ] Generar un **QR** al notebook en molab y otro al repositorio.
- [ ] Ensayar con cronómetro. Si pasa de 50 minutos, usa la "versión corta" (abajo).

**Plan B sin internet:** tu portátil con el repo clonado y `uv sync` hecho. Si el wifi
cae, ellas siguen tu pantalla y corren el notebook después. Todo funciona sin internet
excepto el botón de la API en vivo y molab.

---

## Cómo dictarlo

Proyecta **`notebooks/workshop.py`** (la versión con ejercicios) y resuelve los TODOs en
vivo con ellas. Ten `workshop_facilitator.py` abierto en otra pestaña como respaldo.
Trabajan en **parejas**: una escribe, la otra guía.

| Min | Sección del notebook | Qué haces | Qué hacen ellas |
|---|---|---|---|
| 0-5 | Portada + **1 · Empieza por el final** | Cuenta la historia: *"cada semana una secretaría abre un PDF…"*. Muestra la gráfica final y cambia de entidad | Escanean el QR y abren el notebook |
| 5-8 | **2 · El mapa** | Bronce = mercado, plata = *mise en place*, oro = plato. Única "teoría" del taller | Escuchan |
| 8-12 | **3 · PDF**: el visor y el selector de semana | Pregunta: *"¿cómo sacarían esta tabla, cada semana, para siempre?"*. Cambia de la semana 26 a la 27: la tabla cambia de página y de lado | Responden en voz alta |
| 12-16 | **TODO 1** | Dales 3 minutos. Las pruebas se ponen en verde solas | Escriben `parse_integer` y `parse_decimal` |
| 16-22 | **Checkpoint 1 → TODO 2** | Sale en **rojo**: faltan 733 casos. Lee con ellas las líneas rotas (`Putumayo … 66 e`). ¿De dónde salió la "e"? Abre la ayuda. Cambien `crop` por `within_bbox` | Encuentran el error y lo arreglan |
| 22-24 | Carga a bronce | *"Validar contra el total del propio documento es la mejor prueba que existe"* | — |
| 24-30 | **4 · SIVIGILA → TODO 3** | Muestra la tabla en rojo: 0 % de fechas. Pregunta: *"¿`2/12/2024` es el 2 de diciembre o el 12 de febrero?"* (compárala con `ini_sin`: `28/11/2024`). `CAST` lanza un error; `TRY_CAST` devuelve `NULL` y permite continuar | Escriben `split_part` + `try_strptime`; conservan las fechas ISO con `coalesce` + `try_cast` |
| 30-35 | **5 · IDEAM** | 165 millones de filas: *"no se descarga, se le pregunta"*. Pulsa el botón de la API en vivo. Muestra el cambio `VALLE DEL CAUCA` → `Valle Del Cauca` | — |
| 35-37 | **¿Dónde está Cali?** | Sale la alerta: `CALI` vs `SANTIAGO DE CALI`. Pide a alguien activar el interruptor de alias y señala cómo se recalcula todo | Activan el interruptor |
| 37-42 | **6 · Cruzar**: semana ISO vs epidemiológica; **🤔 Predice** | Que cada pareja escriba su predicción y revelen. Explica la explosión de filas | Predicen y revelan |
| 42-45 | **TODO 4 → Checkpoint 3** | `GROUP BY`. Cuando quede en verde: *"esta es su tabla oro; descárguenla para el taller de ML"*. Si el mensaje de abajo dice *Casi*, nombra la columna que no coincide: ¿es lo mismo promediar los días que sumar la semana por estación y luego promediar estaciones? | Agrupan y descargan |
| 45-50 | **7 · Lo que no cuadra** | Las incógnitas 1 (el pasado cambia) y 3 (825 mm). Mueve el deslizador de rezago. Cierra con `RETOS.md`: *"esto es lo que nadie ha resuelto"* | — |
| 50-60 | Preguntas | — | — |

### Números que vas a ver (con los datos del repo)

* Boletín semana 26: Tabla 17, página 3 del extracto (28 del original), **56 797** casos.
  Semana 27: Tabla 23, **59 262**.
* Con `crop()`: 35 filas y faltan **733** casos (Putumayo 318 + Quindío 195 + Caldas 110 + Risaralda 110).
* TODO 3 sin arreglar: **0 %** de las fechas de notificación convertidas (los 112 908 casos
  quedan con `NULL`); los municipios sí emparejan al 100 %.
* Sin alias: 5 estaciones de Cali y 1 de Buga sin municipio.
* Explosión de filas: `weekly_cases` tiene **520** filas; con el interruptor de alias activado
  (como queda después del minuto 37) el cruce con la lluvia diaria da **10 354** filas y
  **1 118 315** casos en vez de **112 908**. Con el interruptor apagado: 8 350 filas y
  904 024 casos.
* El pasado cambia: 56 797 + 2 847 notificados ≠ 59 262. Faltan **382**. Putumayo baja de 318 a 309.
* Lluvia imposible: **825,8 mm** en Juan de Acosta (2026-05-10).

> Los casos de SIVIGILA son microdatos reales del INS (2024-2025, eventos 210 y 220). Si
> cambias el archivo, cambian los números de casos (no los del boletín ni los del IDEAM):
> revísalos.

La muestra sintética usa fechas ISO: `TRY_CAST` ya las convierte y no reproduce la
trampa del TODO 3. Usa los datos INS para mostrarla. La solución admite ambos formatos.
El checkpoint compara los conteos exactos; los porcentajes se redondean solo para mostrarlos.

### Versión corta (si vas atrasado)

* Haz tú el TODO 1 en vivo (30 segundos) y deja que ellas hagan solo el TODO 2.
* Si el TODO 3 se alarga, escribe tú el `try_strptime` y explica qué hace cada parte.
* Salta la tabla de semana ISO vs epidemiológica: menciónala y sigue.
* En "Lo que no cuadra" muestra solo la incógnita 1 y manda a `RETOS.md`.

### Si algo falla

| Problema | Solución |
|---|---|
| molab no carga los datos | Revisa `REPO_URL` y que el repo sea público |
| `uv` no está instalado | <https://docs.astral.sh/uv/getting-started/installation/> (un comando) |
| La API del IDEAM no responde | Es esperado a veces; el notebook sigue con la copia guardada |
| Alguien se atasca en un TODO | Las pistas están en el texto del TODO y, para los TODOs 2 y 4, en la ayuda (💡); ninguna trae la respuesta. La solución está en el notebook del facilitador |
| Una celda no se actualiza | En marimo casi nunca pasa; si pasa, menú → *Restart kernel* |

---

## En la tarde (preguntas sobre el reto)

Las preguntas más probables y a qué reto apuntan:

| Pregunta | Dónde mirar |
|---|---|
| "¿Cómo saco los casos de 2026 por semana?" | `RETOS.md` #1 y #2 |
| "¿Cómo leo todos los boletines?" | #4, y `dengue-pipeline bulletin <pdf>` para probar uno |
| "Me salen municipios sin código" | #7 y `dengue-pipeline check` |
| "¿Qué hago con la lluvia rara?" | #6 |
| "¿Puedo usar pandas / Excel / otra herramienta?" | Sí. El repo es un punto de partida, no una obligación |

---

## Para el jurado (sábado)

Todas las participantes reciben este kit. Al calificar **ingeniería de datos**, el
mérito está en lo que **va más allá** del piloto:

**Ya viene hecho (no suma por sí solo):** extracción de *un* boletín con validación del
total, carga de SIVIGILA del piloto, códigos DIVIPOLA, alias de Cali y Buga, lluvia
semanal de Valle y Atlántico, tabla oro de 5 entidades, verificaciones de calidad,
estructura del repositorio, linters y pruebas.

**Sí suma:** todos los boletines del año automatizados, serie semanal 2026 a partir de
acumulados, manejo del rezago o *nowcasting*, cobertura nacional, decisiones
documentadas sobre los días sospechosos, temperatura y humedad, separación de las
columnas esperado/observado y un pipeline reproducible con un comando.
