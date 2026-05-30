.PHONY: setup data score app test lint lint-fix all clean docker help

PYTHON := /usr/bin/python3
PIP := /usr/bin/python3 -m pip
PORT := 8501

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	$(PIP) install --user ".[dev,notebook]"

data: ## Generate synthetic CRM data
	$(PYTHON) -m lead_scorer generate

score: ## Run the scoring pipeline
	$(PYTHON) -m lead_scorer score

app: ## Launch Streamlit demo application
	$(PYTHON) -m streamlit run src/app/main.py --server.port $(PORT)

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v --tb=short

lint: ## Run linting and type checking
	$(PYTHON) -m ruff check src/ tests/ scripts/
	$(PYTHON) -m mypy src/pipeline/ --ignore-missing-imports

lint-fix: ## Auto-fix linting issues
	$(PYTHON) -m ruff check --fix src/ tests/ scripts/
	$(PYTHON) -m ruff format src/ tests/ scripts/

all: data score app ## Full pipeline: generate data → score → launch app

clean: ## Remove generated output files
	rm -rf data/raw/*.csv data/processed/*.csv data/processed/*.xlsx
	rm -rf __pycache__ src/**/__pycache__ tests/__pycache__
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf *.egg-info

docker: ## Build and run Docker container
	docker build -t lead-scoring-poc .
	docker run -p $(PORT):$(PORT) lead-scoring-poc

validate: test lint ## Run full validation (tests + lint)
