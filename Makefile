PY ?= python
TF_DIR := infra/terraform
DAYS ?= 30

# Credenciales ficticias: LocalStack acepta cualquiera.
export AWS_ACCESS_KEY_ID ?= test
export AWS_SECRET_ACCESS_KEY ?= test
export AWS_DEFAULT_REGION ?= eu-south-2

.PHONY: all up build deploy ingest transform dashboard down local test lint

all: up deploy ingest transform ## LocalStack de punta a punta

up: ## Arranca LocalStack
	docker compose up -d --wait

build: ## Empaqueta la Lambda en dist/ingest_lambda.zip
	$(PY) scripts/build_lambda.py

deploy: build ## Crea S3 + Lambda + EventBridge con Terraform en LocalStack
	cd $(TF_DIR) && tflocal init -input=false && tflocal apply -auto-approve -input=false

ingest: ## Invoca la Lambda una vez por día (DAYS=30)
	AWS_ENDPOINT_URL=http://localhost:4566 $(PY) scripts/backfill.py --days $(DAYS)

transform: ## dbt build sobre el Parquet de S3 (modelos + tests)
	cd transform && RAW_GLOB=$$(cd ../$(TF_DIR) && tflocal output -raw raw_glob) dbt build --target lake --profiles-dir .

dashboard: ## Abre el panel en http://localhost:8501
	streamlit run dashboard/app.py

down: ## Para LocalStack (y borra todo lo creado en él)
	docker compose down

local: ## Sin Docker: Open-Meteo -> data/raw -> dbt
	$(PY) scripts/run_local.py --days $(DAYS)
	cd transform && dbt build --profiles-dir .

lint:
	ruff check . && ruff format --check .

test: lint
	pytest -q
