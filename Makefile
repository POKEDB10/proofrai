.PHONY: check dev-backend dev-frontend

check:
	ruff check backend scripts
	pytest backend/tests
	npm --prefix frontend run check
	python scripts/style_check.py

dev-backend:
	uvicorn backend.app.main:app --reload --port 8000

dev-frontend:
	npm --prefix frontend run dev
