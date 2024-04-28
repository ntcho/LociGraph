setup: requirements.txt
	pip install -r requirements.txt

clean:
	rm ./logs/*

app = LITESTAR_APP=app:app litestar run --port 8000 --reload
app-models = LITESTAR_APP=models.app:app litestar run --port 8001 --reload-dir models

start:
	$(app)

start-models:
	$(app-models)

dev:
	$(app) --pdb

dev-models:
	$(app-models) --pdb
