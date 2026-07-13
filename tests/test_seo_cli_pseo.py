import os
import tempfile
import json
from unittest.mock import patch
import pytest
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import seo_cli


def test_seo_cli_pseo():
    # Create temp JSON dataset
    dataset = [
        {"service": "Plumbing", "location": "London", "slug": "plumbing-london"}
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp_data:
        json.dump(dataset, tmp_data)
        data_path = tmp_data.name

    with tempfile.TemporaryDirectory() as tmp_out_dir:
        # Mock sys.argv to run the CLI
        test_args = [
            "seo_cli.py",
            "pseo",
            "--data", data_path,
            "--title-tmpl", "Best {{ service }}",
            "--meta-tmpl", "Meta {{ location }}",
            "--h1-tmpl", "{{ service }}",
            "--body-tmpl", "Body {{ service }}",
            "--out-dir", tmp_out_dir,
            "--seed-key", "slug"
        ]

        with patch("sys.argv", test_args):
            seo_cli.main()

        # Check that page was generated
        expected_file = os.path.join(tmp_out_dir, "plumbing-london.html")
        assert os.path.exists(expected_file)
        with open(expected_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Best Plumbing" in content
            assert "Meta London" in content

    os.remove(data_path)
