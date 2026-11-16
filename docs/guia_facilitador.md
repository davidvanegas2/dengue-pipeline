# Guía para quien dicta el taller

**Formato:** 50 minutos de taller + 10 de preguntas · viernes 4 de diciembre, en la mañana,
**antes** del taller de ML.
**Idea central:** mostrar cada técnica **una vez**, en un caso pequeño, y dejar las
preguntas difíciles abiertas para la hackathon (`RETOS.md`).

---

## Antes del 4 de diciembre

**Estado de preparación — revisión del 15 de noviembre de 2026:** el pipeline y los
ejercicios ya se pueden ensayar localmente. Los checks técnicos no reemplazan el ensayo
con participantes, la prueba en Windows ni la coordinación con ML y la organización.

**Primero, resolver el acceso:** GitHub reporta el repositorio como **público**, pero
[`AGENTS.md`](../AGENTS.md) exige confidencialidad hasta el 4 de diciembre. No se cambió
la visibilidad durante esta revisión. La documentación de
[molab](https://docs.marimo.io/guides/molab/#sharing) indica que sus notebooks son públicos
por defecto, aunque no aparezcan en búsquedas. Ensaya localmente hasta resolver esta
contradicción con el responsable del taller; no publiques una copia del reto para probar.
Si se restringe GitHub, las descargas anónimas de `REPO_URL` dejarán de funcionar fuera
del clon local y habrá que volver a validar el acceso antes del evento.

### Preparación técnica

- [x] **Reemplazar la muestra sintética de SIVIGILA** por datos reales
      ([`data/raw/sivigila/LEEME.md`](../data/raw/sivigila/LEEME.md)): dengue (210) y
      dengue grave (220), años 2024 y 2025. Luego `make pipeline` y versiona
      `data/gold/weekly_dengue_signal.parquet`.
- [x] Crear el [repositorio en GitHub](https://github.com/davidvanegas2/dengue-pipeline).
      Su rama principal es `main`; la visibilidad requiere la decisión indicada arriba.
- [x] Configurar `REPO_URL` en `notebooks/workshop_facilitator.py` con
      `https://raw.githubusercontent.com/davidvanegas2/dengue-pipeline/main`
      y regenerar `notebooks/workshop.py` con `make student-notebook`.
- [x] Verificar los **9 archivos** que descarga el notebook: sus URLs respondieron y
      sus hashes SHA-256 coincidieron con los archivos locales el 15 de noviembre.
- [x] Agregar al README el badge de molab con el formato del
      [generador oficial](https://molab.marimo.io/github). Preparar el enlace no valida
      todavía la ejecución en molab.
- [x] Generar localmente **QR del notebook y del repositorio**: [molab](assets/qr_molab.svg)
      y [GitHub](assets/qr_repository.svg), también disponibles como PNG en `docs/assets/`.
      Los dos PNG se decodificaron y sus URLs coinciden. Regenerar con `make workshop-qr`
      si cambian los enlaces.
- [x] Instalar las **76 dependencias de `uv.lock` en un entorno virtual nuevo en macOS**
      (Python 3.12.11). Esto comprueba la instalación, no equivale a un computador limpio.
- [x] Ejecutar `make format`, `make lint` y `make test-fast`: **133 aprobadas, 1 omitida**
      (las 15 excluidas incluyen notebooks y red).
- [x] Ejecutar `make workshop-check` desde el entorno nuevo: **146 pruebas aprobadas,
      1 omitida y 2 de red excluidas**, cobertura del paquete **95 %**; pipeline con
      **750 filas** y sin errores críticos. El snapshot oro coincide con una ejecución nueva.
- [x] Ejecutar por separado `uv run pytest -m network -v`: **2 aprobadas**, incluida la
      consulta que exige recibir datos del IDEAM. Repetir cerca del evento.
- [x] Abrir estudiante y facilitador en **marimo 0.25.2 + Chrome en macOS**: los estados
      iniciales del estudiante son los esperados y el facilitador muestra los cuatro
      indicadores en verde. Esto verifica la apertura, no todo el recorrido manual.
- [x] Corregir el visor PDF para seguir el selector de boletín y la página encontrada;
      las pruebas verifican ambos archivos y sus páginas.
- [x] Separar la descarga del ejercicio de la **tabla oficial para ML** y comprobar por
      HTTP local que marimo entrega exactamente los **10 415 bytes** del parquet oficial.

### Validaciones antes de entregar el taller

- [ ] **Resolver la visibilidad y la fecha de distribución** del repositorio y de molab
      con el responsable del taller, respetando la confidencialidad.
- [ ] Incorporar estos cambios a la versión que se entregará y repetir la verificación
      de los enlaces y datos sobre esa versión.
- [ ] Probar el notebook en **molab con una cuenta nueva**, una vez autorizado el acceso:
      abrir el badge, crear una copia editable (**Fork**), usar un servidor Python
      (**Server**), ejecutar las celdas, resolver los TODOs y descargar el parquet oficial.
      Una vista previa estática no basta; WebAssembly no está validado para este taller.
- [ ] Probar en un **computador Windows limpio**, sin `make`: instalar Git y uv, clonar,
      ejecutar la secuencia de abajo y completar los cuatro TODOs en el navegador.
- [ ] Completar el **recorrido visual de aceptación** descrito abajo, en ambos notebooks;
      comprobar los controles, la descarga desde el navegador y el plan B sin wifi.
- [ ] **Coordinar con el taller de ML:** que use `data/gold/weekly_dengue_signal.parquet`
      como entrada; acordar columnas (`docs/diccionario_de_datos.md`).
- [ ] **Pedir a la organización:** wifi para ~40 portátiles, proyector, que las
      participantes traigan portátil cargado y cuenta de GitHub o Google (para molab),
      y 1-2 personas de apoyo en sala.
- [ ] **Escanear ambos QR desde un teléfono**, probarlos proyectados desde el fondo de la
      sala y verificar que el acceso de las participantes funciona.
- [ ] Ensayar con cronómetro. Si pasa de 50 minutos, usa la "versión corta" (abajo).

**Plan B sin internet:** tu portátil con el repo clonado y `uv sync` hecho. Si el wifi
cae, ellas siguen tu pantalla y corren el notebook después. Todo funciona sin internet
excepto el botón de la API en vivo y molab.

## Ensayo técnico repetible

Desde la raíz del repositorio:

```bash
make workshop-check
```

Instala las versiones fijadas, ejecuta lint, **todas las pruebas sin red (incluidos los
notebooks)** y el pipeline. La primera instalación necesita internet; las pruebas y el
pipeline usan los datos locales. `make test-fast` por sí solo **no valida marimo**.

En Windows, o si no tienes `make`, ejecuta cada línea y continúa solo si termina sin errores:

```text
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run sqlfluff lint sql
uv run mypy
uv run marimo check notebooks
uv run python scripts/generate_student_notebook.py --check
uv run pytest -m "not network" --cov --cov-report=term-missing
uv run dengue-pipeline run
uv run marimo edit notebooks/workshop.py
```

Abre el facilitador en otra terminal con
`uv run marimo edit notebooks/workshop_facilitator.py --port 2719`.
Si las celdas aparecen sin ejecutar, pulsa ▶ para correr todas. Al abrir la versión del
estudiante es normal ver TODOs/checkpoints pendientes y celdas dependientes detenidas;
en el facilitador, los cuatro indicadores deben quedar en verde.

**Recorrido de aceptación:** cambiar la entidad de la gráfica; cambiar el boletín 26 → 27
y comprobar el PDF y su lado; **volver a la semana 26 antes del TODO 1** para reproducir la
pérdida de 733 casos; resolver TODOs 1–4; activar alias; pulsar **Revelar**; mover el
deslizador de rezago; descargar ambas tablas. El parquet oficial debe tener **750 filas,
13 columnas, 5 entidades y 150 semanas**, sin llaves repetidas. Revisar también las ayudas
y la legibilidad del PDF con el proyector.

**API opcional:** con internet, `uv run pytest -m network -v`. Puede tardar varios minutos.
La prueba del botón puede pasar aunque falle la API, porque el taller permite continuar;
`test_live_api_responds` exige recibir datos reales. No uses `make pipeline-online` como
prueba de apertura: descarga de nuevo la lluvia y cambia los insumos del piloto.

**Advertencia esperada del pipeline:** **3 464 de 17 698 días-estación** de lluvia quedan
marcados como sospechosos. No bloquea el taller y no se debe "arreglar" filtrándolos:
esa decisión pertenece al reto. La prueba de reproducibilidad de la muestra sintética
se omite porque `ORIGEN.txt` ya dice `INS`.

### Entrega al taller de ML

La entrada acordada debe ser **`weekly_dengue_signal.parquet`**, exportada por el pipeline
y disponible en el botón **Descargar tabla oficial para ML**. Ese botón entrega los
mismos bytes de `data/gold/weekly_dengue_signal.parquet`.

`mi_weekly_dengue_signal.parquet` es el resultado **del ejercicio**: tiene 8 columnas y
su cálculo de lluvia depende de la solución al TODO 4 y del interruptor de alias. El
comparativo del notebook solo comprueba los **conteos de casos**, no la igualdad de las
tablas completas. No usar el archivo del ejercicio como sustituto del contrato de ML.

Confirmar con quien dicta ML el [diccionario](diccionario_de_datos.md), la llave
`territorial_entity` + `epi_year` + `epi_week`, los casos semanales frente a los acumulados
y el tratamiento de valores ausentes. Dejar su nombre y confirmación al completar ese
check; preparar el archivo no equivale a haber coordinado la entrega.

---

## Cómo dictarlo

Proyecta **`notebooks/workshop.py`** (la versión con ejercicios) y resuelve los TODOs en
vivo con ellas. Ten `workshop_facilitator.py` abierto en otra pestaña como respaldo.
Trabajan en **parejas**: una escribe, la otra guía.

| Min | Sección del notebook | Qué haces | Qué hacen ellas |
|---|---|---|---|
| 0-5 | Portada + **1 · Empieza por el final** | Cuenta la historia: *"cada semana una secretaría abre un PDF…"*. Muestra la gráfica final y cambia de entidad | Escanean el QR y abren el notebook |
| 5-8 | **2 · El mapa** | Bronce = mercado, plata = *mise en place*, oro = plato. Única "teoría" del taller | Escuchan |
| 8-12 | **3 · PDF**: el visor y el selector de semana | Pregunta: *"¿cómo sacarían esta tabla, cada semana, para siempre?"*. Cambia de la semana 26 a la 27: cambia el número de tabla y el lado. En ambos extractos está en la página 3. **Vuelve a la semana 26** antes del TODO 1 | Responden en voz alta |
| 12-16 | **TODO 1** | Dales 3 minutos. Las pruebas se ponen en verde solas | Escriben `parse_integer` y `parse_decimal` |
| 16-22 | **Checkpoint 1 → TODO 2** | Sale en **rojo**: faltan 733 casos. Lee con ellas las líneas rotas (`Putumayo … 66 e`). ¿De dónde salió la "e"? Abre la ayuda. Cambien `crop` por `within_bbox` | Encuentran el error y lo arreglan |
| 22-24 | Carga a bronce | *"Validar contra el total del propio documento es la mejor prueba que existe"* | — |
| 24-30 | **4 · SIVIGILA → TODO 3** | Muestra la tabla en rojo: 0 % de fechas. Pregunta: *"¿`2/12/2024` es el 2 de diciembre o el 12 de febrero?"* (compárala con `ini_sin`: `28/11/2024`). `CAST` lanza un error; `TRY_CAST` devuelve `NULL` y permite continuar | Escriben `split_part` + `try_strptime`; conservan las fechas ISO con `coalesce` + `try_cast` |
| 30-35 | **5 · IDEAM** | 165 millones de filas: *"no se descarga, se le pregunta"*. Pulsa el botón de la API en vivo. Muestra el cambio `VALLE DEL CAUCA` → `Valle Del Cauca` | — |
| 35-37 | **¿Dónde está Cali?** | Sale la alerta: `CALI` vs `SANTIAGO DE CALI`. Pide a alguien activar el interruptor de alias y señala cómo se recalcula todo | Activan el interruptor |
| 37-42 | **6 · Cruzar**: semana ISO vs epidemiológica; **🤔 Predice** | Que cada pareja escriba su predicción y revelen. Explica la explosión de filas | Predicen y revelan |
| 42-45 | **TODO 4 → Checkpoint 3** | `GROUP BY`. Cuando quede en verde, distingue el resultado del ejercicio de la **tabla oficial para ML**; señala los dos botones | Agrupan y descargan la tabla oficial para ML |
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
| molab no carga los datos | Revisa `REPO_URL`, la versión publicada y el acceso autorizado. Si GitHub es privado, usa el clon local; no lo hagas público para sortear el error |
| molab muestra solo una vista previa | Crea una copia editable (**Fork**) y ejecútala en **Server**; luego pulsa ▶ |
| marimo muestra celdas sin resultados al abrir | Pulsa ▶ para ejecutar todas; los checkpoints pendientes del estudiante son intencionales |
| `uv` no está instalado | <https://docs.astral.sh/uv/getting-started/installation/> (un comando) |
| La API del IDEAM no responde | Es esperado a veces; el notebook sigue con la copia guardada |
| Alguien se atasca en un TODO | La ayuda (💡) trae una versión válida; el notebook del facilitador, la completa |
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
