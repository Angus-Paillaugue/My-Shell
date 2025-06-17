requirements:
	poetry export -f requirements.txt --without-hashes -o requirements.txt
dev: init dev-launch
dev-launch:
	GTK_DEBUG=interactive DEV_MODE=true python app.py
init:
	python init.py
venv:
	python -m venv .venv
install:
	pip install -r requirements.txt
install-dev:
	poetry install --with dev
run:
	./run.sh
version-bump:
	./workflows/version-bump.sh
format:
	./workflows/format.sh
update:
	./workflows/update.sh
kill:
	pkill my-shell
