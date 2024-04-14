setup: requirements.txt
	pip install -r requirements.txt

clean:
	rm ./logs/*

dev:
	LITESTAR_APP=app:app litestar run --port 8000 --reload

dev-models:
	LITESTAR_APP=models.app:app litestar run --port 8001
