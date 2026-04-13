.PHONY: install run test validate clean

install:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	python run_server.py --reload

test:
	pytest tests/ -v

validate:
	python scripts/validate_data.py

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
