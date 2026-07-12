#!/usr/bin/env python3
"""CLI interface for SEO/GEO Framework."""

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def parse_args():
    parser = argparse.ArgumentParser(description="SEO/GEO Framework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Run SEO audit on a site")
    audit_parser.add_parser("url", help="Target URL to audit")
    audit_parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl")
    
    # Sitemap command
    sitemap_parser = subparsers.add_parser("sitemap", help="Generate sitemap")
    sitemap_parser.add_argument("url", help="Base URL")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run the API server locally")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    
    return parser.parse_args()

def run_audit(url: str, max_pages: int):
    print(f"Auditing {url}...")
    try:
        from src.auditor import SEOAuditor
        import json
        auditor = SEOAuditor(url, max_pages=max_pages)
        report = auditor.crawl_and_audit()
        print(json.dumps(report, indent=2))
    except ImportError:
        print("Error: Could not import auditor. Make sure you are in the project root.")
        sys.exit(1)

def run_serve(port: int):
    print(f"Starting server on port {port}...")
    import uvicorn
    from src.main import app
    uvicorn.run(app, host="0.0.0.0", port=port)

def main():
    args = parse_args()
    
    if args.command == "audit":
        run_audit(args.url, args.max_pages)
    elif args.command == "serve":
        run_serve(args.port)
    else:
        print("Please specify a command. Use --help for options.")
        sys.exit(1)

if __name__ == "__main__":
    main()
