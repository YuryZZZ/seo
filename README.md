# SEO/GEO Framework

A comprehensive Python-based framework for Search Engine Optimization (SEO) and Generative Engine Optimization (GEO).

## Overview

This framework automates complex SEO tasks, provides robust auditing capabilities, handles keyword tracking and analytics, and includes a full suite of AI-assisted content generation tools. It features 10 specialized agent roles that work together to create highly optimized content.

## Features

- **Technical SEO Auditing**: Crawls sites to detect broken links, missing meta tags, and alt attributes.
- **Content Generation**: Leverages multi-provider LLMs (OpenAI, Anthropic, Gemini, DeepSeek) for writing optimized content.
- **Local SEO & Internationalization**: Generates multi-location schema and manages hreflang tagging.
- **Analytics & Reporting**: Integrates with Google Search Console for keyword tracking and anomaly detection.
- **Automated Deployments**: Easily deployable to Google App Engine or Cloud Run natively.
- **CLI Interface**: Perform audits and generate sitemaps straight from your terminal.

## Requirements

- Python 3.12+
- Dependencies in `requirements.txt`
- API Keys for your preferred LLM providers (e.g., `OPENAI_API_KEY`, `GEMINI_API_KEY`)
- Service account key for Google Cloud integrations

## Installation

```bash
git clone https://github.com/YuryZZZ/seo.git
cd seo
pip install -r requirements.txt
```

## Usage

You can use the CLI or run the built-in API server.

### Command Line Interface

Run a technical SEO audit on a website:
```bash
python seo_cli.py audit https://example.com --max-pages 50
```

Generate a sitemap for a list of URLs:
```bash
python seo_cli.py sitemap https://example.com
```

### API Server

Start the FastAPI server locally:
```bash
python seo_cli.py serve --port 8080
# or via Makefile
make serve
```

Access the API documentation at `http://localhost:8080/docs`

## Examples

See the `examples/` directory for standalone scripts demonstrating how to interact with the library programmatically.

- `examples/generate_sitemap.py`
- `examples/audit_site.py`

## Architecture

The project is structured into modular components:
- `src/api/`: FastAPI routes and endpoints
- `src/auditor.py`: Web crawler and HTML analysis
- `src/seo_analytics.py`: Google Search Console integrations and metrics
- `src/content_generator.py`: LLM integrations and content scaffolding
- `src/local_intl.py`: Multi-region schemas and hreflang builders
- `tests/`: Extensive Pytest suite for all modules

## Deployment

### Google App Engine
A deploy script is provided to deploy seamlessly to Google App Engine standard environment.

```powershell
./deploy.ps1
```
*(Requires `gcloud` CLI installed and authenticated)*

### Cloud Run
You can also deploy it to Cloud Run natively using `app.yaml` equivalent configurations or source-based deployment.

## Contributing

Please see `CONTRIBUTING.md` for details on our code of conduct, and the process for submitting pull requests.

## License

MIT License
