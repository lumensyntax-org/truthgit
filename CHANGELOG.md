# Changelog

All notable changes to TruthGit will be documented in this file.

## [0.4.0] - 2026-01-03

### Added
- **FastAPI Server** - Production-ready REST API for claim verification
- **Railway Deployment** - Cloud deployment on Railway platform
- **Logos6 Validator** - Custom Vertex AI model integration
- **Debug Endpoints** - `/api/debug/validators` and `/api/debug/test-claude`
- **Proof Certificates** - Cryptographic proof generation and verification
- **API Documentation** - Comprehensive API reference in `docs/API.md`
- **Deployment Guide** - Railway and Vercel deployment in `docs/DEPLOYMENT.md`

### Fixed
- **PROMPT Template Formatting** - Escaped JSON braces in validator prompts
- **Claude JSON Parsing** - Robust parsing with fallback handling
- **Import Ordering** - Fixed E402 lint errors
- **Line Length** - Fixed E501 lint errors (>100 chars)

### Changed
- **Validators Module** - Improved error handling and traceback reporting
- **Server Structure** - Moved GCP credentials setup to lifespan function
- **API Responses** - Standardized error response format

### Infrastructure
- **CI/CD** - GitHub Actions with ruff lint, format, and pytest
- **Railway** - Auto-deploy on push to main
- **Vercel** - UI deployment with NextAuth

## [0.3.0] - 2025-12-15

### Added
- **MCP Server** - Model Context Protocol integration
- **HuggingFace Validator** - Support for HF Inference API
- **Knowledge Extractor** - Extract claims from text

### Changed
- **Ollama Validator** - Improved model detection

## [0.2.0] - 2025-11-01

### Added
- **Cloud Validators** - Claude, GPT, Gemini support
- **Human Validator** - Interactive CLI validation
- **Proof System** - Ed25519 signed certificates

## [0.1.0] - 2025-10-01

### Added
- Initial release
- **TruthRepository** - Core content-addressable storage
- **Claims & Axioms** - Basic object types
- **Ollama Validator** - Local LLM validation
- **CLI** - Command-line interface
