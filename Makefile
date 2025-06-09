requirements:
	poetry export -f requirements.txt --without-hashes -o requirements.txt
dev:
	DEV_MODE=true python app.py
init:
	python init.py
venv:
	python -m venv .venv
install:
	pip install -r requirements.txt
install-dev:
	poetry install --with dev
run:
	python app.py
version-bump:
	./workflows/version-bump.sh
format:
	./workflows/format.sh
update:
	./workflows/update.sh
