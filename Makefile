.DEFAULT_GOAL:=help

.PHONY: setup setup-dev black isort pylint setup-db test run help

setup: requirements.txt
	pip install -Ur requirements.txt

setup-dev: requirements-dev.txt
	pip install -Ur requirements-dev.txt

black: setup-dev ## Formats code with black
	black .

isort: setup-dev ## Sorts imports using isort
	isort .

pylint: setup-dev ## Lints code using pylint
	pylint todolist
	pylint todolistproject

setup-db: setup ## Set up DB tables
	python manage.py migrate

test: setup-db ## Run all unit tests
	python manage.py test

run: setup-db ## Run the server
	python manage.py runserver

help: ## Show this help message.
	@echo 'usage: make [target]'
	@echo
	@echo 'targets:'
	@grep -E '^[8+a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
