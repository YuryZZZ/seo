# Contributing to SEO/GEO Framework

First off, thank you for considering contributing to the SEO/GEO Framework. It's people like you that make it such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, please create an issue on GitHub. If you'd like to contribute code, we welcome pull requests!

## Development Setup

1. Fork the repo and clone it locally.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   make install
   ```
3. Create a branch for your changes:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```

## Coding Standards

- Write clean, readable code with docstrings for classes and methods.
- We use standard Python conventions (PEP 8).
- Ensure all new features are covered by tests.

## Running Tests

All tests are written using `pytest`. Run them via:
```bash
make test
```
Make sure all tests pass before submitting a pull request.

## Pull Request Process

1. Ensure your code passes all tests and linting.
2. Update the README.md with details of changes to the interface, if applicable.
3. Submit a Pull Request with a clear description of the problem and the solution.
4. Wait for a review from the maintainers.

## Code of Conduct

Please be respectful and constructive when interacting with other contributors. We are committed to providing a welcoming and inspiring community for all.
