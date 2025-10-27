# Environment related
requirements:
	poetry export -f requirements.txt --without-hashes -o requirements.txt
venv:
	python -m venv .venv
install:
	pip install -r requirements.txt
install-dev:
	poetry install --with dev

# Application related
init:
	python init.py
dev: init dev-launch
dev-launch:
	GTK_DEBUG=interactive DEV_MODE=true python app.py
run:
	./run.sh
phonebridge:
	python -m mobile.server.app
kill: kill-shell kill-phonebridge
kill-shell:
	pkill vellum-shell
kill-phonebridge:
	pkill -f vellum-shell-phonebridge-server

# Workflow
version-bump:
	./workflows/version-bump.sh
format:
	./workflows/format.sh
update:
	./workflows/update.sh
