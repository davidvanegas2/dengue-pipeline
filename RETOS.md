# 🕵️ Retos e incógnitas

El piloto funciona para **dos departamentos, dos boletines y una variable de clima**.
Todo lo que sigue es lo que **no** resuelve, a propósito. Son problemas reales que
encontramos en los datos, sin solución publicada.

Cada reto trae pistas escalonadas: abre la primera solo si te atascas, y la segunda
solo si la primera no fue suficiente.

---

## 1. El pasado cambia

El boletín de la semana 27 de 2026 dice: *"se notificaron **2 847** casos de dengue:
2 118 casos de esta semana y 729 casos de semanas anteriores"*. Pero el acumulado
nacional pasó de **56 797** (semana 26) a **59 262** (semana 27): solo 2 465 más.
Faltan 382 casos. Y en algunas entidades el acumulado **bajó** (Putumayo: 318 → 309).

**¿Cuál es el número real de casos de una semana? ¿Cuándo deja de cambiar?**

<details><summary>Pista 1</summary>

Los casos se notifican con retraso, y luego se **reclasifican**: algunos se descartan
y salen del conteo. El propio boletín dice que *"los datos son ajustados semanalmente
por rezago en la notificación"*. Junta varios boletines seguidos y mira cómo cambia
la cifra de una misma entidad semana tras semana.
</details>

<details><summary>Pista 2</summary>

Busca *nowcasting*: estimar cuántos casos de la semana actual todavía no se han
reportado, usando cómo se completaron las semanas anteriores. Los microdatos de
SIVIGILA traen la fecha de inicio de síntomas (`ini_sin`) y la de notificación
(`fec_not`): la diferencia entre ellas es el retraso.
</details>

## 2. La costura

SIVIGILA solo publica **años cerrados** (casos semanales hasta 2025). El boletín da
casos **acumulados** de 2026. En la tabla oro del piloto, 2026 tiene solo dos puntos.

**¿Cómo construyes una serie semanal continua de 2007 a hoy?**

<details><summary>Pista 1</summary>

Si tienes el acumulado de la semana *N* y el de la *N-1*, la resta da los casos
**notificados** en la semana *N*, que no es lo mismo que los casos **ocurridos** en
ella (ver reto 1). Ojo con las restas negativas.
</details>

<details><summary>Pista 2</summary>

¿Las definiciones coinciden entre fuentes? El boletín cuenta "casos notificados por
entidad territorial de procedencia". En SIVIGILA hay ocurrencia (`cod_mun_o`),
residencia (`cod_mun_r`) y notificación (`cod_mun_n`). Prueba cuál se parece más.
</details>

## 3. ¿Qué es un caso?

El piloto cuenta como caso los eventos 210 (dengue) y 220 (dengue grave), excluyendo
`ajuste` 6 (descartado) y D (error de digitación), y usa la columna `semana`. Cada una
de esas decisiones cambia la señal.

**¿Probables o solo confirmados? ¿Semana de notificación o de inicio de síntomas?**

<details><summary>Pista</summary>

Revisa en el diccionario oficial del INS los valores de `tip_cas` (clasificación
inicial) y `ajuste` (clasificación final). Compara la curva con cada definición: ¿cuál
se adelanta más? ¿Cuál es más estable?
</details>

## 4. Todos los boletines

El piloto lee **dos** extractos. El INS publica uno por semana.

**Automatiza la descarga y extracción de todos los boletines del año.**

<details><summary>Pista 1</summary>

Encontramos al menos dos patrones de URL distintos para el mismo tipo de documento:
`.../buscador-eventos/BoletinEpidemiologico/2026_Boletin_epidemiologico_semana_N.pdf` y
`.../BibliotecaDigital/2026-bulletin-epidemiologico-semana-N.pdf`.
</details>

<details><summary>Pista 2</summary>

La tabla cambia de número (Tabla 17, Tabla 23…), de página y de lado. Nada garantiza
que todas las semanas tengan el mismo formato. Valida **siempre** cada boletín con su
fila *Total* (`BulletinTable.totals_match()`) y registra los que fallan en vez de ignorarlos
en silencio.
</details>

## 5. Las columnas partidas

Las dos últimas columnas de la tabla (casos *esperados* y *observados* en las últimas
cuatro semanas) a veces salen partidas: `2 139 20 79` es `2139` y `2079`. El piloto las
guarda crudas en `raw_variation`.

**Sepáralas bien. Son la señal de "va en aumento" que el propio INS calcula.**

<details><summary>Pista</summary>

`page.extract_words()` devuelve cada palabra con su posición `x0`/`x1`. Las columnas
están siempre a la misma distancia del borde izquierdo de la tabla.
</details>

## 6. Estaciones fantasma y sensores locos

En la lluvia del IDEAM hay días con **16 416 lecturas** en una estación (lo normal son
144), días de **825 mm** (Juan de Acosta, Atlántico) y meses enteros sin datos en 2024.
El piloto los **marca** (`suspicious_reading`) pero no los corrige.

**¿Qué haces con ellos? ¿Cómo lo explicas en tu producto?**

<details><summary>Pista</summary>

Mira las lecturas crudas de 10 minutos de una estación sospechosa (la API permite
filtrar por `codigoestacion` y fecha). ¿Hay marcas de tiempo repetidas? ¿Un valor que
se repite sin parar? Compara con las estaciones vecinas. Documenta la decisión: la
transparencia también se califica.
</details>

## 7. Escalar a todo el país

El piloto tiene 65 municipios, 5 entidades territoriales y 2 alias de nombres.

**Llévalo a los 1 100+ municipios y las 37 entidades que reporta el boletín.**

<details><summary>Pista</summary>

* `data/reference/entidades_territoriales_piloto.csv`: faltan los demás distritos
  (Cartagena, Santa Marta…) y departamentos.
* `dengue_pipeline.config.PILOT_DEPARTMENTS`: amplíalo y vuelve a descargar.
* La tabla de alias va a crecer: compara los nombres del IDEAM con DIVIPOLA y revisa los
  que no emparejan (`dengue-pipeline check` te dice cuántos son). Recuerda que hay
  municipios con el mismo nombre en departamentos distintos.
* Alternativa: el IDEAM trae latitud y longitud de cada estación.
</details>

## 8. Más clima

La lluvia sola no explica todo. El IDEAM publica en datos.gov.co **temperatura**
(`sbwg-7ju4`) y **humedad** (`uext-mhny`) con la misma estructura.

**Agrégalas a la tabla oro.** Ojo: no se suman como la lluvia.

## 9. ¿Lluvia de cuándo?

El mosquito necesita agua para reproducirse, pero no de un día para otro.

**¿Con cuántas semanas de rezago se relacionan la lluvia y los casos? ¿Es igual en Cali
que en Barranquilla?** Es el puente con el taller de ML.

> Hazlo con los datos **reales** de SIVIGILA: con la muestra sintética cualquier
> relación es ruido.

## 10. Que otra persona lo pueda correr

El jurado va a intentar correr tu solución.

**Un comando, un README y pruebas.** Este repositorio ya trae la estructura: úsala.
`make ci` debe quedar en verde.
