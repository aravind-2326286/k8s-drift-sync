PYTHON := python
PIP := pip
PACKAGE := k8s-drift-sync
IMAGE := k8s-drift-sync:latest

.PHONY: help
help:
	@echo "Common targets:"
	@echo "  make venv         - create .venv and install deps"
	@echo "  make install      - pip install -e ."
	@echo "  make test         - run pytest"
	@echo "  make build        - build wheel/sdist"
	@echo "  make docker-build - build Docker image"
	@echo "  make docker-run   - run image mounting ./config"
	@echo "  make scan         - run scan using config/config.yaml"

.PHONY: venv
venv:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate || . .venv/Scripts/activate; \
		pip install -r requirements.txt

.PHONY: install
install:
	$(PIP) install -e .

.PHONY: test
test:
	pytest -q

.PHONY: build
build:
	$(PIP) install build
	$(PYTHON) -m build

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

.PHONY: docker-run
docker-run:
	docker run --rm -v $$PWD/config:/app/config -v $$HOME/.kube:/root/.kube:ro $(IMAGE)

.PHONY: scan
scan:
	k8s-drift-sync scan --config config/config.yaml 