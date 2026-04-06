SHELL := /bin/bash

.PHONY: help init plan apply destroy

help:
	@echo "Alpine Lambda Trade (ALT) - Commands"
	@echo "  make init      : Initialize Terraform"
	@echo "  make plan      : Plan Terraform infrastructure"
	@echo "  make apply     : Apply Terraform infrastructure"
	@echo "  make destroy   : Destroy Terraform infrastructure"
	@echo "  make local-infra-up : Start LocalStack for local testing"
	@echo "  make local-infra-down : Stop LocalStack"
	@echo "  make run-producer   : Run the producer script (dev)"
	@echo "  make test-producer  : Run the tests for the producer"
	@echo "  make dbt-run        : Run dbt incremental models (Sprint 3)"
	@echo "  make dbt-test       : Run dbt schema tests (Sprint 3)"
	@echo "  make build-lambda   : Build python zip package for Lambda (Sprint 4)"
	@echo "  make run-dashboard  : Run Streamlit dashboard (Sprint 5)"

init:
	cd infra && \
	set -a && source ../.env && set +a && \
	terraform init

plan:
	cd infra && \
	set -a && source ../.env && set +a && \
	export TF_VAR_snowflake_account=$$SNOWFLAKE_ACCOUNT && \
	export TF_VAR_snowflake_user=$$SNOWFLAKE_USER && \
	export TF_VAR_snowflake_password=$$SNOWFLAKE_PASSWORD && \
	terraform plan

apply: build-lambda
	cd infra && \
	set -a && source ../.env && set +a && \
	export TF_VAR_snowflake_account=$$SNOWFLAKE_ACCOUNT && \
	export TF_VAR_snowflake_user=$$SNOWFLAKE_USER && \
	export TF_VAR_snowflake_password=$$SNOWFLAKE_PASSWORD && \
	terraform apply

destroy:
	cd infra && \
	set -a && source ../.env && set +a && \
	export TF_VAR_snowflake_account=$$SNOWFLAKE_ACCOUNT && \
	export TF_VAR_snowflake_user=$$SNOWFLAKE_USER && \
	export TF_VAR_snowflake_password=$$SNOWFLAKE_PASSWORD && \
	terraform destroy

local-infra-up:
	docker compose up -d localstack

local-infra-down:
	docker compose down

run-producer:
	set -a && source .env && set +a && \
	uv sync --extra producer && \
	export PYTHONPATH=. && \
	uv run python src/producer/main.py

test-producer:
	set -a && source .env && set +a && \
	uv sync --extra producer --group dev && \
	export PYTHONPATH=. && \
	uv run pytest tests/producer/ -v --cov=src/producer

dbt-run:
	set -a && source .env && set +a && \
	cd src/batch_layer && \
	export DBT_PROFILES_DIR=. && \
	uv sync --extra batch && \
	uv run dbt run --profiles-dir .

dbt-test:
	set -a && source .env && set +a && \
	cd src/batch_layer && \
	export DBT_PROFILES_DIR=. && \
	uv sync --extra batch && \
	uv run dbt test --profiles-dir .

build-lambda:
	mkdir -p src/speed_layer/package
	uv export --only-group speed --no-hashes > src/speed_layer/requirements_lambda.txt
	uv pip install \
    --target=src/speed_layer/package \
    --python-version 3.12 \
    --system \
    -r src/speed_layer/requirements_lambda.txt
	cd src/speed_layer/package && zip -r9 ../speed_layer.zip .
	cd src/speed_layer && zip -g speed_layer.zip app.py
	rm src/speed_layer/requirements_lambda.txt

run-dashboard:
	set -a && source .env && set +a && \
	uv sync --extra serving && \
	uv run streamlit run src/serving_layer/dashboard.py
