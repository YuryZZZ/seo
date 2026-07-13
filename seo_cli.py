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
    audit_parser.add_argument("url", help="Target URL to audit")
    audit_parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl")
    
    # Sitemap command
    sitemap_parser = subparsers.add_parser("sitemap", help="Generate sitemap")
    sitemap_parser.add_argument("url", help="Base URL")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run the API server locally")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to run on")

    # pSEO command
    pseo_parser = subparsers.add_parser("pseo", help="Bulk generate programmatic SEO pages")
    pseo_parser.add_argument("--data", required=True, help="Path to CSV or JSON dataset")
    pseo_parser.add_argument("--title-tmpl", required=True, help="Jinja2 template for page title")
    pseo_parser.add_argument("--meta-tmpl", required=True, help="Jinja2 template for meta description")
    pseo_parser.add_argument("--h1-tmpl", required=True, help="Jinja2 template for H1")
    pseo_parser.add_argument("--body-tmpl", required=True, help="Jinja2 template for page body")
    pseo_parser.add_argument("--out-dir", default="output/pseo_pages", help="Output directory to save pages")
    pseo_parser.add_argument("--no-spin", dest="spin", action="store_false", help="Disable synonym spin-text")
    pseo_parser.set_defaults(spin=True)
    pseo_parser.add_argument("--seed-key", help="Column/field name to seed spin-text generator")
    
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

def run_pseo(data_path: str, title_tmpl: str, meta_tmpl: str, h1_tmpl: str, body_tmpl: str, out_dir: str, spin: bool, seed_key: str):
    try:
        from src.pseo_engine import PSEODataParser, PSEOEngine
    except ImportError:
        from pseo_engine import PSEODataParser, PSEOEngine
    import os
    
    # Resolve input data format
    if data_path.endswith(".csv"):
        dataset = PSEODataParser.parse_csv(data_path)
    elif data_path.endswith(".json"):
        dataset = PSEODataParser.parse_json(data_path)
    else:
        raise ValueError("Unsupported data source format. Must be .csv or .json")
        
    engine = PSEOEngine(
        title_template=title_tmpl,
        meta_desc_template=meta_tmpl,
        h1_template=h1_tmpl,
        body_template=body_tmpl
    )
    
    results = engine.bulk_render(dataset, spin=spin, seed_key=seed_key)
    
    # Write output to out_dir
    os.makedirs(out_dir, exist_ok=True)
    for r in results:
        idx = r["row_index"]
        rendered = r["rendered"]
        
        # Use slug/seed_key or index as filename
        filename = f"page-{idx}.html"
        if seed_key and seed_key in r["data"]:
            filename = f"{str(r['data'][seed_key]).replace(' ', '-').lower()}.html"
        elif "slug" in r["data"]:
            filename = f"{str(r['data']['slug'])}.html"
            
        file_path = os.path.join(out_dir, filename)
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{rendered['title']}</title>
    <meta name="description" content="{rendered['meta_description']}">
</head>
<body>
    <h1>{rendered['h1']}</h1>
    <div>
        {rendered['body'].replace('\n', '<br>')}
    </div>
</body>
</html>"""
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
    print(f"Generated {len(results)} pages in {out_dir}")

def main():
    args = parse_args()
    
    if args.command == "audit":
        run_audit(args.url, args.max_pages)
    elif args.command == "serve":
        run_serve(args.port)
    elif args.command == "pseo":
        run_pseo(
            data_path=args.data,
            title_tmpl=args.title_tmpl,
            meta_tmpl=args.meta_tmpl,
            h1_tmpl=args.h1_tmpl,
            body_tmpl=args.body_tmpl,
            out_dir=args.out_dir,
            spin=args.spin,
            seed_key=args.seed_key
        )
    else:
        print("Please specify a command. Use --help for options.")
        sys.exit(1)

if __name__ == "__main__":
    main()
