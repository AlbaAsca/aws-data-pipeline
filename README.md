# aws-data-pipeline · el tiempo en España, de la API al panel

[![CI](https://github.com/AlbaAsca/aws-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/AlbaAsca/aws-data-pipeline/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)
![dbt](https://img.shields.io/badge/transform-dbt%20%2B%20DuckDB-FF694B?logo=dbt&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Lambda%20%C2%B7%20S3%20%C2%B7%20EventBridge-FF9900?logo=amazonwebservices&logoColor=white)
![Coste](https://img.shields.io/badge/coste%20en%20LocalStack-0%20%E2%82%AC-2ea44f)

Un pipeline de datos **de punta a punta, diseñado para AWS** y ejecutado primero en
[LocalStack](https://www.localstack.cloud/) para no gastar ni un céntimo mientras se construye:
cada día una Lambda descarga el tiempo horario de seis ciudades españolas, lo guarda en S3
como Parquet particionado por fecha, dbt + DuckDB lo transforma y comprueba su calidad, y un
panel en Streamlit lo enseña.

![Temperatura media diaria](docs/img/temperature.png)

## El problema

Quería un proyecto de ingeniería de datos que se pareciese a lo que se hace en una empresa
—ingesta programada, data lake, transformaciones versionadas, tests de calidad, infraestructura
como código y CI— pero sin las dos trampas habituales de los proyectos personales en la nube:

1. **La factura.** Es muy fácil dejarse un NAT Gateway o un cluster encendido y pagar 30 $ al
   mes por un proyecto que procesa 150 filas al día.
2. **El «funciona en mi cuenta».** Si para probarlo hace falta una cuenta de AWS, casi nadie lo
   prueba.

La solución: el mismo código y los mismos `.tf` corren en LocalStack (gratis, en local y en el
CI) y en AWS real cambiando solo el *endpoint*.

**Los datos** vienen de [Open-Meteo](https://open-meteo.com/): abiertos, gratuitos, sin clave
de API y con histórico, lo que permite rellenar días pasados (*backfill*). AEMET OpenData
también es gratis, pero exige pedir una clave, y eso lo haría menos reproducible para quien
clone el repo.

## Arquitectura

```mermaid
flowchart LR
    API["🌦️ Open-Meteo<br/>API pública"]
    EB["⏰ EventBridge<br/>cron 06:00 UTC"]
    L["λ Lambda ingest<br/>Python + duckdb"]
    S3[("🪣 S3 · raw/<br/>weather/dt=YYYY-MM-DD/<br/>weather.parquet")]
    DBT["🧱 dbt + DuckDB<br/>(papel de Glue/Athena)<br/>modelos + tests"]
    WH[("🦆 warehouse.duckdb<br/>fct_weather_daily<br/>city_climate_summary")]
    ST["📊 Streamlit"]

    EB -->|1 vez al día| L
    API -->|JSON horario| L
    L -->|Parquet zstd| S3
    S3 -->|read_parquet s3://| DBT
    DBT --> WH --> ST

    subgraph TF["Terraform · tflocal (LocalStack) ⇄ terraform (AWS)"]
        EB
        L
        S3
    end
```

| Capa | En AWS | En este repo (fase 1) |
|---|---|---|
| Programación | EventBridge (regla `cron`) | EventBridge en LocalStack · `make ingest` para *backfill* |
| Ingesta | Lambda Python 3.12 | La misma Lambda, desplegada en LocalStack |
| Almacenamiento | S3, Parquet particionado `dt=` (estilo Hive) | S3 de LocalStack |
| Transformación y consulta | Athena / Glue | dbt-duckdb leyendo `s3://` directamente |
| Calidad de datos | Glue Data Quality / dbt | 16 tests de dbt |
| Visualización | QuickSight | Streamlit |
| Infraestructura | Terraform | Terraform vía `tflocal` |

## Cómo ejecutarlo

Necesitas Python 3.12, Docker y Terraform ≥ 1.6.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

make all          # LocalStack + Terraform + 30 días de ingesta + dbt build
make dashboard    # http://localhost:8501
```

![Panel en Streamlit](docs/img/dashboard.jpg)

`make all` es la suma de cuatro pasos que puedes lanzar sueltos:

| Comando | Qué hace |
|---|---|
| `make up` | Arranca LocalStack (`docker compose`) |
| `make deploy` | Empaqueta la Lambda y crea S3 + Lambda + EventBridge con `tflocal apply` |
| `make ingest DAYS=30` | Invoca la Lambda una vez por cada uno de los últimos 30 días |
| `make transform` | `dbt build` contra el Parquet de S3: modelos y tests de calidad |

**¿Sin Docker?** `make local` ejecuta la misma lógica de ingesta escribiendo en `data/raw/` y
luego dbt sobre esos ficheros; útil para trabajar en los modelos sin levantar nada.

**Tests:** `make test` (ruff + pytest con [moto](https://github.com/getmoto/moto) simulando S3).

![Lluvia acumulada](docs/img/rain.png)

## Qué hay dentro

```
src/ingest/handler.py     Lambda: Open-Meteo -> Parquet -> S3 (idempotente por día)
infra/terraform/          S3 (cifrado, sin acceso público), IAM mínimo, Lambda, EventBridge, logs
transform/                Proyecto dbt: staging (vista) -> marts (tablas) + tests
dashboard/                Streamlit + gráficas mplcyberpunk
scripts/                  build_lambda, backfill, run_local, make_charts
.github/workflows/ci.yml  Lint, tests, dbt, terraform validate y el pipeline entero en LocalStack
```

**Calidad de datos.** dbt comprueba en cada ejecución que no hay duplicados por ciudad y hora,
que cada día tiene sus 24 horas, que no faltan medidas, que los valores son físicamente
plausibles (temperatura entre -25 y 50 °C, humedad entre 0 y 100 %…), que cada fichero
`dt=YYYY-MM-DD` solo contiene horas de ese día y que todas las ciudades existen en la tabla
maestra.

Estos tests ya han cazado un fallo real: la API de previsión de Open-Meteo solo guarda unas
semanas de pasado y, más atrás, devuelve `null` sin dar error. El test
`assert_no_missing_measurements` lo detectó en un *backfill* de 60 días; ahora la Lambda usa
la API de archivo para fechas antiguas y se niega a escribir un día incompleto.

## Decisiones y su porqué

- **Lambda y no Glue para la ingesta.** Son 144 filas al día. Un job de Glue tarda en arrancar
  más de lo que tarda la Lambda en terminar, y se factura por DPU-hora.
- **DuckDB dentro de la Lambda para escribir Parquet.** Lo habitual es añadir la capa de
  *AWS SDK for pandas*, pero esa capa no existe en LocalStack Community. `duckdb` cabe en un zip
  de unos 20 MB, escribe Parquet sin pandas ni pyarrow, y es el mismo motor que usa la
  transformación.
- **Parquet particionado por fecha (`dt=`), en UTC.** Las particiones estilo Hive las entienden
  DuckDB, Athena y Glue sin configuración. Guardar en UTC evita los días de 23 o 25 horas del
  cambio de hora, que romperían el test de «24 horas por día».
- **Idempotencia.** Cada día se escribe siempre en la misma clave: repetir una ingesta (o un
  *backfill*) sobrescribe en lugar de duplicar. Aun así, el modelo de staging deduplica por
  si acaso, quedándose con la carga más reciente.
- **dbt + DuckDB en el papel de Athena.** El SQL de los modelos es casi el mismo que se
  escribiría en Athena, y DuckDB lee `s3://` igual de LocalStack que de AWS. En AWS real se
  puede mantener así o pasar a `dbt-athena`.
- **Mínimo privilegio.** La Lambda solo puede hacer `PutObject` bajo `raw/` y escribir sus
  propios logs. El bucket bloquea el acceso público y cifra con SSE-S3 (gratis; SSE-KMS
  cobra por petición).
- **Logs con caducidad (14 días).** Sin `retention_in_days`, CloudWatch guarda los logs para
  siempre y se acaban pagando.
- **Lambda fuera de una VPC.** Solo habla con una API pública y con S3, así que no necesita
  VPC… ni el NAT Gateway que vendría con ella.
- **LocalStack fijado en la versión 4.14.0.** Desde 2026 las imágenes nuevas piden token de
  cuenta; fijar la versión mantiene el proyecto reproducible sin registrarse en ningún sitio.

## ¿Cuánto costaría en AWS?

Estimación mensual con el volumen real del proyecto (1 invocación diaria de ~5 s con 512 MB,
~10 KB de Parquet al día), con precios públicos de referencia:

| Servicio | Uso al mes | Coste aprox. |
|---|---|---|
| Lambda | 30 invocaciones · ~75 GB-s | 0 $ (capa gratuita permanente: 1 M peticiones y 400 000 GB-s) |
| S3 | < 1 MB almacenado · 30 PUT | < 0,01 $ |
| EventBridge (regla programada) | 30 eventos | 0 $ |
| CloudWatch Logs | < 1 MB | 0 $ |
| Athena (opcional, fase 2) | consultas sobre < 1 MB | ~0 $ (5 $/TB escaneado, mínimo 10 MB por consulta) |
| **Total** | | **< 0,05 $/mes** |

### Lo que se evita a propósito (porque es caro para este volumen)

| Servicio | Por qué no | Orden de coste |
|---|---|---|
| **NAT Gateway** | Solo haría falta si la Lambda estuviese en una VPC privada | ~33 $/mes encendido + datos |
| **AWS Glue** (jobs y crawlers) | Arranque lento y facturación por DPU-hora para 144 filas | 0,44 $/DPU-hora, crawlers con mínimo de 10 min |
| **RDS** | Una base de datos encendida 24/7 para datos que caben en un fichero | ~12–15 $/mes la instancia más pequeña |
| **QuickSight** | Licencia por usuario para un panel personal | decenas de $/usuario/mes |
| **MWAA** (Airflow gestionado) | Orquestar una sola tarea diaria | ~350 $/mes el entorno mínimo |

> Los precios cambian y dependen de la región (`eu-south-2`, España, en este proyecto).
> Antes de desplegar, conviene revisarlos en la
> [calculadora de AWS](https://calculator.aws/) y confirmar las condiciones de la capa
> gratuita, que cambiaron en julio de 2025.

## Fase 2: despliegue real en AWS

> 🚧 **Pendiente.** Esta sección se completará tras desplegar el pipeline un día en una cuenta
> real y destruirlo después.

Plan:

1. Revisar la capa gratuita vigente y crear **primero** una alarma de presupuesto de 1 $.
2. `terraform apply` con credenciales reales (mismos `.tf`, sin `tflocal`).
3. Lanzar la ingesta y `make transform` apuntando a S3 real
   (`S3_ENDPOINT=s3.eu-south-2.amazonaws.com S3_USE_SSL=true S3_URL_STYLE=vhost`).
4. Capturas de la consola (Lambda, S3, EventBridge, CloudWatch) y de la factura.
5. `terraform destroy` y comprobar que no queda nada facturando.

<!-- Capturas y factura real aquí -->

## Licencia

MIT. Datos meteorológicos de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
