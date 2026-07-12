.PHONY: test serve install deploy clean

install:
	pip install -r requirements.txt
	pip install pytest pytest-cov bs4 psutil httpx

test:
	pytest tests/ -v

serve:
	python seo_cli.py serve

audit:
	python seo_cli.py audit https://example.com --max-pages 10

deploy:
	powershell ./deploy.ps1

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
