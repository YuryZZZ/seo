"""Example: Running an SEO Audit."""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from auditor import SEOAuditor

def main():
    target_url = "https://example.com"
    print(f"Starting SEO audit for {target_url}...")
    print("This will crawl the site and analyze titles, metas, images, etc.")
    
    auditor = SEOAuditor(target_url, max_pages=10)
    report = auditor.crawl_and_audit()
    
    print("\nAudit Complete!")
    print(f"Pages crawled: {report['pages_crawled']}")
    print(f"Pages with issues: {report['pages_with_issues']}")
    print(f"Broken links: {len(report['broken_links'])}")
    
    print("\nFull Report:")
    print(json.dumps(report, indent=2))
    
    with open("audit_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full report to audit_report.json")

if __name__ == "__main__":
    main()
