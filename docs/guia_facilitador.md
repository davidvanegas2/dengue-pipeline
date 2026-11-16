# Guía para quien dicta el taller

**Formato:** 50 minutos de taller + 10 de preguntas · viernes 4 de diciembre, en la mañana,
**antes** del taller de ML.
**Idea central:** mostrar cada técnica **una vez**, en un caso pequeño, y dejar las
preguntas difíciles abiertas para la hackathon (`RETOS.md`).

**Grupo mixto:** dos ejercicios obligatorios con apoyo: formato de fechas y agregación
semanal. El PDF, la API y los alias son demostraciones guiadas. El código auxiliar está
plegado; cada ejercicio incluye una pista y una solución desplegable para continuar.

---

## Antes del 4 de diciembre

**Estado de preparación — revisión del 15 de noviembre de 2026:** el pipeline y los
ejercicios ya se pueden ensayar localmente. Los checks técnicos no reemplazan el ensayo
con participantes, la prueba en Windows ni la coordinación con ML y la organización.

**Acceso para pruebas:** el responsable del taller confirmó el 15 de noviembre de 2026
que el repositorio se mantiene **público** para probar y revisar el material. La prueba
de molab con una cuenta nueva sigue pendiente; el acceso público permite verificar
las descargas de `REPO_URL`.

**Adaptación del 16 de noviembre:** el recorrido pasa de cuatro TODOs a dos. Las
verificaciones fechadas del 15 de noviembre corresponden a la versión anterior;
hay que repetir la aceptación visual y el ensayo con participantes sobre esta versión.

### Preparación técnica

- [x] **Reemplazar la muestra sintética de SIVIGILA** por datos reales
      ([`data/raw/sivigila/LEEME.md`](../data/raw/sivigila/LEEME.md)): dengue (210) y
      dengue grave (220), años 2024 y 2025. Luego `make pipeline` y versiona
      `data/gold/weekly_dengue_signal.parquet`.
- [x] Crear el [repositorio en GitHub](https://github.com/davidvanegas2/dengue-pipeline).
      Su rama principal es `main` y se mantiene público para las pruebas.
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
- [x] Ejecutar `make format`, `make lint` y `make test-fast`: **144 aprobadas, 1 omitida**
      (las 29 excluidas incluyen notebooks y red).
- [x] Ejecutar `make workshop-check`: **171 pruebas aprobadas, 1 omitida y 2 de red
      excluidas**, cobertura del paquete **95 %**; pipeline con **750 filas** y sin errores
      críticos. El snapshot oro coincide con una ejecución nueva. La primera corrida fue en
      el entorno nuevo; después de corregir el visor PDF y la descarga oficial se repitió en
      el entorno del repositorio.
- [x] Ejecutar por separado `uv run pytest -m network -v`: **2 aprobadas**, incluida la
      consulta que exige recibir datos del IDEAM. Repetir cerca del evento.
- [x] Abrir estudiante y facilitador en **marimo 0.25.2 + Chrome en macOS**: los estados
      iniciales del estudiante eran los esperados y el facilitador mostraba los cuatro
      indicadores de la versión anterior en verde. Esto verifica la apertura, no todo el
      recorrido manual.
- [x] Corregir el visor PDF: marimo solo respeta `initial_page` cuando recibe una URL, así
      que el notebook sirve el archivo y abre el visor en la página donde encontró la
      tabla. Verificado en **Chrome 157 (headless) con marimo 0.25.2** en ambos notebooks:
      semana 26 abre en la página 3 de 6, semana 27 en la página 3 de 7, y el visor sigue
      el selector al cambiar de semana y volver. Las pruebas revisan el `#page=` del visor,
      también con un PDF donde la tabla queda en la página 4. Sin verificar: Safari,
      Firefox y molab.
- [x] Separar la descarga del ejercicio de la **tabla oficial para ML**. El botón oficial
      está en la sección 1 y al final de la sección 6, sin depender de los TODOs. Con un
      servidor marimo local, ambos botones entregan exactamente los **10 415 bytes** del
      parquet oficial (mismo SHA-256), también en la versión del estudiante sin resolver.
      Falta probar la descarga a disco desde el navegador (recorrido de aceptación).

### Validaciones antes de entregar el taller

- [x] **Confirmar el acceso público al repositorio para las pruebas**, por decisión del
      responsable del taller el 15 de noviembre de 2026.
- [ ] Incorporar estos cambios a la versión que se entregará y repetir la verificación
      de los enlaces y datos sobre esa versión.
- [ ] Probar el notebook en **molab con una cuenta nueva**:
      abrir el badge, crear una copia editable (**Fork**), usar un servidor Python
      (**Server**), ejecutar las celdas, resolver los TODOs y descargar el parquet oficial.
      Una vista previa estática no basta; WebAssembly no está validado para este taller.
- [ ] Probar en un **computador Windows limpio**, sin `make`: instalar Git y uv, clonar,
      ejecutar la secuencia de abajo y completar los dos TODOs en el navegador.
- [ ] Completar el **recorrido visual de aceptación** descrito abajo, en ambos notebooks;
      comprobar los controles, la descarga desde el navegador y el plan B sin wifi.
- [ ] **Coordinar con el taller de ML:** que use `data/gold/weekly_dengue_signal.parquet`
      como entrada; acordar columnas (`docs/diccionario_de_datos.md`).
- [ ] **Pedir a la organización:** wifi para ~40 portátiles, proyector, que las
      participantes traigan portátil cargado y cuenta de GitHub o Google (para molab),
      y 1-2 personas de apoyo en sala.
- [ ] **Escanear ambos QR desde un teléfono**, probarlos proyectados desde el fondo de la
      sala y verificar que el acceso de las participantes funciona.
- [ ] Enviar las instrucciones de acceso antes del evento y reservar la instalación o
      el inicio de sesión fuera de los 50 minutos de contenido. Al empezar deben tener
      el notebook abierto y ejecutado.
- [ ] Ensayar con cronómetro con alguien de nivel inicial. Si pasa de 50 minutos, usa
      la "versión corta" (abajo); las pruebas automáticas no validan la duración.

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
estudiante, la demostración del PDF ya pasa y el TODO 1 de fechas está pendiente;
las celdas que necesitan las fechas esperan. En el facilitador, los dos ejercicios
están completos y la tabla del ejercicio coincide con la oficial en las métricas validadas.

Para ensayar los ejercicios conservando tus respuestas, trabaja en una copia local:

```bash
mkdir -p .workshop
cp notebooks/workshop.py .workshop/workshop.py
uv run marimo edit .workshop/workshop.py
```

Crea la copia una sola vez: repetir `cp` reemplaza tus respuestas. `.workshop/` queda
fuera de Git. Si actualizas el facilitador, cierra la sesión del estudiante antes de
ejecutar `make student-notebook` y vuelve a abrirla después; una sesión que sigue
abierta puede conservar código anterior. La regeneración actualiza
`notebooks/workshop.py`, no tu copia de práctica.

**Recorrido de aceptación:**

1. Cambia la entidad de la gráfica y descarga la tabla oficial sin resolver nada.
   Comprueba que se presenta como **vista previa del resultado oficial**: el mapa
   y el panel **Refinamiento actual** deben dejar oro pendiente. En el mapa único deben
   aparecer **6 tablas de bronce, 6 de plata y 1 de oro**, incluidas las pendientes.
   Pulsa `silver.cases`: su ficha muestra que existe, pero sus fechas necesitan revisión.
   Pulsa `bronze.divipola` para consultar la referencia sin salir del mapa.
   Cierra con **Cerrar** o **Esc** y comprueba que conservas la posición de la página.
   En **Seguir conexiones de**, elige `silver.municipality_entity`: deben verse sus
   dos entradas en azul y sus dos salidas en verde, con las otras líneas atenuadas.
   Vuelve a **Todas las tablas**; las 13 tablas siempre deben permanecer visibles.
2. Cambia el boletín 26 → 27 y comprueba el PDF y la comparación de recortes. Vuelve a
   la semana 26: `crop` pierde 733 casos y `within_bbox` conserva el total. La carga
   utiliza el método correcto sin exigir una edición.
3. En el TODO 1, cambia solo `notification_date_format` a `"%d/%m/%Y"`. Comprueba que
   todas las fechas se convierten y que el siguiente bloque se habilita. Prueba también
   `"%d/%M/%Y"` (`%M` son minutos: todas las fechas caen en enero) y `"%D/%m/%Y"` (código
   desconocido): ambos deben dejar el TODO 1 pendiente con una pista en español, sin error
   de DuckDB.
4. Desactiva los alias para observar las estaciones sin municipio y vuelve a activarlos.
   La comparación de nombres debe mostrar los códigos ausentes, y el mapa debe
   actualizar el estado de la lluvia y sus resultados dependientes.
   Pulsa **Revelar** para ver la multiplicación de filas y casos.
5. Antes de editar el TODO 2, la estructura puede estar correcta, pero debe decir
   **TODO 2 pendiente**. Cambia `sum(mm)` por `avg(mm)` en el SELECT final; conserva
   `sum(precipitation_mm)` en el primer paso. Debe aparecer **TODO 2 completo**.
6. Despliega ambas ayudas y soluciones de continuación. Descarga la tabla del ejercicio
   y la oficial. El parquet oficial debe tener **750 filas, 13 columnas, 5 entidades y
   150 semanas**, sin llaves repetidas. Comprueba la legibilidad con el proyector.
   Abre **Seguir una semana real**: las filas por estación deben conducir a una sola
   fila de esa entidad y semana. `per_station` se presenta como CTE, no como tabla guardada.
   Tras completar los ejercicios, vuelve a un formato de fecha inválido: el mapa y
   sus fichas deben retirar los resultados dependientes anteriores. Abre `gold.signal`:
   debe quedar pendiente, sin la muestra anterior. Restaura la solución.
7. Como verificación adicional, abre la sección opcional y mueve el deslizador de rezago.

El notebook no necesita ejecutar antes `dengue-pipeline run`: ya recibe los insumos y
la tabla oficial. Ese comando reconstruye la bodega del paquete y sirve para preparar
el taller o extender el piloto durante la hackathon.

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
y disponible en el botón **Descargar tabla oficial para ML**. El botón está en la
sección 1 y se repite al final de la sección 6; no depende de los TODOs ni de los
checkpoints, así que quien no termine el ejercicio también se lleva la tabla. Entrega
los mismos bytes de `data/gold/weekly_dengue_signal.parquet`.

`mi_weekly_dengue_signal.parquet` es el resultado **del ejercicio**: tiene las mismas 13
columnas que la oficial, pero su cálculo de lluvia depende de la solución al TODO 2 y del
interruptor de alias (activado por defecto). El comparativo comprueba **casos, estaciones
y lluvia en cada entidad y semana**, no la igualdad de las 13 columnas. Una llave que
falte en cualquiera de las tablas cuenta como diferencia. No usar el archivo del ejercicio
como sustituto del contrato de ML.

**Dos verificaciones distintas:** `checkpoint_3` comprueba la estructura y las semanas;
`aggregation_ok` comprueba los valores de lluvia y estaciones. El resumen de la sección 8
se ve desde el inicio y marca completo el TODO 2 solo cuando pasan las dos comprobaciones.
Una suma de estaciones incorrecta puede tener llaves únicas y debe seguir apareciendo
pendiente. Si los alias están desactivados, el aviso del TODO 2 pide activarlos antes de
revisar el cálculo, y el detalle muestra las semanas que difieren de la tabla oficial.

Confirmar con quien dicta ML el [diccionario](diccionario_de_datos.md), la llave
`territorial_entity` + `epi_year` + `epi_week`, los casos semanales frente a los acumulados
y el tratamiento de valores ausentes. Dejar su nombre y confirmación al completar ese
check; preparar el archivo no equivale a haber coordinado la entrega.

---

## Cómo dictarlo

Proyecta **`notebooks/workshop.py`** y ten `workshop_facilitator.py` en otra pestaña
como respaldo. Trabajan en **parejas**: una escribe y la otra explica qué significa el
resultado; intercambian roles en el segundo ejercicio. Solo editan las dos celdas visibles.
No expliques el código auxiliar línea por línea: pueden desplegarlo después.

### Hacer visible el refinamiento

Usa las fichas de tabla como parte de la explicación de cada paso, sin añadir otro
ejercicio. Su secuencia es **cargar → tipar → ubicar → agregar → integrar**; varias
acciones ocurren dentro de plata. Cada ficha muestra las entradas, la transformación,
su propósito y, sobre todo, **qué representa una fila**.

El mapa de la sección 2 y el panel lateral muestran el estado actual de las tablas
del ejercicio. Marimo puede ejecutar varios bloques automáticamente: el estado del
mapa no indica hasta dónde ha leído una participante. La acción resaltada en cada
ficha sitúa la explicación. El conteo de tablas disponibles tampoco es un porcentaje
de calidad: **creada**, **verificación aprobada** y **revisar** tienen significados distintos;
lee siempre el alcance de la comprobación.

Detente brevemente en estos cambios:

- **Fechas:** el mismo texto pasa a una fecha interpretable; seguimos al nivel de caso.
- **Ubicación:** el alias permite encontrar un código común. En la lluvia todavía
  tenemos estación × día, incluso después de añadir la entidad territorial.
- **Agregación:** los días se suman por estación y semana; luego se combinan las
  estaciones de la entidad. El acordeón de una semana real permite seguir los
  valores del ejercicio, incluidos los incorrectos antes de resolver el TODO 2.
- **Integración:** el calendario de oro añade combinaciones sin observaciones.
  Más filas no significa más casos; un vacío no equivale automáticamente a cero.

El mapa reúne las **13 tablas y todas sus dependencias** en una sola vista, con columnas
de **bronce → plata → oro**. Dentro de plata, las flechas distinguen los pasos de tipado,
ubicación y agregación. Las tres fuentes y las tres referencias (DIVIPOLA, alias y
entidades) forman las seis tablas de bronce; cada tabla tiene una descripción breve
de su función. Oro reserva una entrada identificada para cada aporte: años, entidades,
casos semanales, límite del calendario, días sospechosos, acumulados y lluvia semanal.

Para explicar un cruce, usa **Seguir conexiones de**. Las **entradas** a esa tabla se
resaltan en azul; las **salidas** hacia otras tablas, en verde. Las otras líneas se
atenúan y una lista encima del mapa identifica las entradas y los consumidores por
nombre. Las tablas permanecen visibles. Con **Todas las tablas**, puedes explorar
pasando el cursor o enfocando una tabla con Tab. Las líneas continuas transportan las
medidas; las discontinuas aportan referencias, calendario o señales de calidad.
Las flechas terminan en la tabla que consume la entrada; un cruce de líneas no crea
una relación adicional.

Durante la explicación, sigue primero `bronze.sivigila` → `silver.cases` →
`silver.weekly_cases`; después la ruta de lluvia. Usa `silver.municipality_entity`
para mostrar por qué ambas rutas necesitan una referencia territorial común.
Termina en `gold.signal` y lee qué aporta cada entrada al resultado integrado.

Para consultar una tabla, **pulsa su nodo**: la misma ficha del recorrido se abre sobre
el mapa, con sus entradas, propósito, comprobación y hasta cinco filas actuales. Cierra
con **Cerrar**, **Esc** o un clic fuera para seguir en el mismo lugar. También puedes
usar **Tab** y **Enter** para abrir las fichas. Las tablas pendientes permiten leer su
propósito, pero no muestran muestras anteriores. En una pantalla estrecha, desplaza
el mapa horizontalmente para mantener legibles los nombres.
El mapa representa las tablas del notebook: `gold.signal` es el resultado del ejercicio;
`gold.weekly_dengue_signal` es la tabla del paquete que alimenta el archivo oficial.
El boletín entra directamente a oro en el notebook; el paquete tiene además
`silver.bulletin_cumulative_cases`.

Las muestras, los conteos y los estados se calculan durante la ejecución. Al cambiar
una entrada, se retiran de las fichas las muestras de sus dependientes
hasta que vuelvan a ejecutarse, aunque sus tablas anteriores sigan en memoria.
La tabla oficial del inicio permanece disponible como referencia y entrega para ML.

**Verificación local del 16 de noviembre:** formato y lint aprobados, 144 pruebas
rápidas aprobadas (una omitida por usar datos INS) y 34 pruebas del notebook sin red
aprobadas. En Chrome local se recorrieron los estados inicial, fechas resueltas y
ambos ejercicios resueltos; se desactivaron y reactivaron los alias y se comprobó
que un formato de fecha inválido retira del mapa los resultados dependientes.
También se revisaron el mapa por columnas, el foco de entradas y salidas, las siete
entradas identificadas de oro y la apertura de fichas desde sus nodos.

| Min | Sección del notebook | Qué haces | Qué hacen ellas |
|---|---|---|---|
| 0–8 | **1 · Empieza por el final** + **2 · El mapa** | Muestra una fila de la tabla, la gráfica y el botón oficial para ML. Presenta las tres fuentes y bronce → plata → oro | Identifican qué representa una fila; ya tienen abierto el notebook |
| 8–18 | **3 · PDF**, demostración | Explica las conversiones numéricas ya escritas. Compara `crop` y `within_bbox` en ambas semanas y valida contra el Total; vuelve a la semana 26 | Predicen qué recorte conservar y explican por qué 733 casos perdidos son una alerta; no editan código |
| 18–26 | **4 · TODO 1: fechas** | Dedica 2 min a leer `2/12/2024`, 4 min al trabajo en parejas y 2 min al resultado. La extracción del texto, el tipo y la alternativa ISO vienen resueltos | Cambian solo el formato, comprueban las fechas válidas y explican los `NULL` |
| 26–31 | **5 · IDEAM y alias**, demostración | Muestra la consulta agregada y la copia guardada. La API en vivo es opcional. Desactiva y reactiva los alias para mostrar `CALI` vs `SANTIAGO DE CALI` | Observan qué estaciones pierden municipio; dejan los alias activados |
| 31–43 | **6 · TODO 2: agregación y cruce** | Usa 3 min para predecir y revelar el cruce, 2 min para el ejemplo 30/60 mm, 5 min para editar y 2 min para comprobar. Menciona domingo–sábado; deja la tabla ISO plegada | Cambian solo la agregación final; explican la fila por estación y la fila por entidad. Distinguen estructura correcta de cálculo correcto |
| 43–50 | Tabla oficial, CLI y una pregunta abierta | Señala la descarga oficial. Muestra `uv run dengue-pipeline run` como ejecución reproducible del paquete, separada del notebook. Presenta solo «El pasado cambia» y remite a `RETOS.md` | Descargan la tabla oficial y reconocen qué queda abierto para la hackathon |
| 50–60 | Preguntas | Responde sobre las decisiones y el uso del piloto | Preguntan |

**Apoyos y continuación:** deja que intenten cada decisión antes de abrir la pista.
Si una pareja no avanza, puede desplegar «Solución para continuar», aplicar la línea y
explicar el resultado. No necesita esperar a que revises su portátil para seguir.
Quien tenga más experiencia puede leer las preguntas opcionales; no añadas un tercer TODO
obligatorio. Resolver todo desde cero no es la meta de estos 50 minutos.

### Números que vas a ver (con los datos del repo)

* Boletín semana 26: Tabla 17, página 3 del extracto (28 del original), **56 797** casos.
  Semana 27: Tabla 23, **59 262**.
* Con `crop()`: 35 filas y faltan **733** casos (Putumayo 318 + Quindío 195 + Caldas 110 + Risaralda 110).
* TODO 1 con el formato inicial ISO: **0 %** de las fechas de notificación convertidas
  (los 112 908 casos quedan con `NULL`); los municipios sí emparejan al 100 %.
* Sin alias: 5 estaciones de Cali y 1 de Buga sin municipio.
* Explosión de filas: `weekly_cases` tiene **520** filas; con el interruptor de alias activado
  (activado por defecto y restaurado al terminar la demostración) el cruce con la lluvia
  diaria da **10 354** filas y **1 118 315** casos en vez de **112 908**. Con el interruptor
  apagado: 8 350 filas y 904 024 casos.
* El pasado cambia: 56 797 + 2 847 notificados ≠ 59 262. Faltan **382**. Putumayo baja de 318 a 309.
* Lluvia imposible: **825,8 mm** en Juan de Acosta (2026-05-10).

> Los casos de SIVIGILA son microdatos reales del INS (2024-2025, eventos 210 y 220). Si
> cambias el archivo, cambian los números de casos (no los del boletín ni los del IDEAM):
> revísalos.

La muestra sintética usa fechas ISO: `TRY_CAST` ya las convierte y no reproduce la
trampa del TODO 1. Usa los datos INS para mostrarla. La solución admite ambos formatos.
El checkpoint compara los conteos exactos; los porcentajes se redondean solo para mostrarlos.

### Versión corta (si vas atrasado)

* Omite la consulta de la API en vivo y usa directamente la copia guardada.
* En el PDF muestra la comparación de la semana 26 y su total; deja los detalles del
  recorte para consultar después.
* Conserva las dos decisiones de fechas y agregación. Si hace falta, abre la solución
  de continuación y pide que expliquen el resultado, sin detener al resto del grupo.
* Mantén plegada la comparación ISO; di que usamos semanas domingo–sábado.
* En el cierre presenta solo «El pasado cambia». Las demás incógnitas y el deslizador
  de rezago quedan para después. Conserva la descarga oficial y las preguntas.

### Si algo falla

| Problema | Solución |
|---|---|
| molab no carga los datos | Revisa `REPO_URL`, la versión publicada y que las URLs de los datos respondan sin iniciar sesión. Como alternativa, usa el clon local |
| molab muestra solo una vista previa | Crea una copia editable (**Fork**) y ejecútala en **Server**; luego pulsa ▶ |
| marimo muestra celdas sin resultados al abrir | Pulsa ▶ para ejecutar todas; los checkpoints pendientes del estudiante son intencionales |
| `uv` no está instalado | <https://docs.astral.sh/uv/getting-started/installation/> (un comando) |
| La API del IDEAM no responde | Es esperado a veces; el notebook sigue con la copia guardada |
| Alguien se atasca en un TODO | Abre la pista; si no basta, despliega «Solución para continuar» y aplica la línea indicada. Comprueba y explica el resultado |
| Estructura correcta, pero TODO 2 pendiente | Revisa `avg(mm)` en el SELECT final y conserva la suma por estación; si hay municipios sin emparejar, reactiva los alias |
| Una celda no se actualiza | En marimo casi nunca pasa; si pasa, menú → *Restart kernel* |
| El visor PDF abre en la página 1 | Algún navegador puede ignorar la página inicial. El texto bajo el selector dice en qué página está la tabla: ve a ella a mano |
| Aparece "no se pudo actualizar …; uso la copia guardada" | Fuera del repositorio (molab), el notebook vuelve a descargar los datos en cada sesión. Si GitHub no responde, usa la última copia completa; revisa la conexión y `REPO_URL` |

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
