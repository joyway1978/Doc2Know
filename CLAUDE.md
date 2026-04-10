# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Doc2Know is a Python CLI tool that converts Word documents (.docx) into structured Markdown knowledge bases using LLM analysis. It extracts document structure, generates summaries/tags, and creates an indexed knowledge base suitable for AI systems (e.g., customer service bots).

## Architecture

The project follows a **pipeline architecture** with 5 main modules:

```
Raw Docs → Parser → Analyzer → Generator → Indexer → Knowledge Base
(.docx)    (extract)  (LLM)      (markdown)  (index)    (output/)
```

**Module Responsibilities:**

1. **config.py**: Configuration management with YAML + environment variable override
   - Config validation (API keys, directory permissions)
   - Environment variables: `DOCS2KNOW_API_KEY`, `DOCS2KNOW_RAW_DIR`, `DOCS2KNOW_OUTPUT_DIR`

2. **parser.py**: Word document parsing
   - Primary: `python-docx` with style-based heading detection
   - Fallback: `pandoc` for complex documents
   - Returns structured content with heading levels

3. **analyzer.py**: LLM content analysis
   - OpenAI-compatible API client
   - Exponential backoff retry (tenacity)
   - Chunking for large documents
   - Extracts: title, summary, tags, sections

4. **generator.py**: Markdown generation
   - YAML frontmatter with metadata
   - Slug-based filenames with conflict resolution
   - Hierarchical section structure

5. **indexer.py**: Knowledge base index management
   - Scans generated markdown files
   - Creates `output/index.md` with document table
   - Incremental updates

6. **cli.py**: Command-line interface
   - Entry point: `doc2know` command
   - DocumentProcessor orchestrates the pipeline
   - Progress reporting

## Common Development Commands

```bash
# Install in development mode
pip install -e .

# Run the tool (uses config.yaml)
doc2know
doc2know --config /path/to/config.yaml

# Run tests
pytest
pytest tests/test_config.py  # Single test file
pytest -v                     # Verbose

# Test coverage
pytest --cov=doc2know --cov-report=html

# Test LLM connection
python test_llm.py
```

## Configuration System

**Priority order (highest to lowest):**
1. Environment variables (`DOCS2KNOW_API_KEY`, etc.)
2. `config.yaml` (user-provided)
3. Default values in `config.py`

**Key config sections:**
```yaml
llm:
  base_url: "https://api.openai.com/v1"  # OpenAI-compatible API
  api_key: "sk-..."
  model: "gpt-3.5-turbo"

paths:
  raw_dir: "./raw_docs"      # Input Word docs
  output_dir: "./output"     # Generated markdown

processing:
  chunk_size: 4000           # Character limit per LLM call
  max_concurrent: 3          # Parallel processing
```

**Security Note:** `config.yaml` is in `.gitignore` and should never be committed. Use `config.yaml.example` for templates.

## Output Structure

```
output/
├── index.md              # Auto-generated index with table
└── topics/
    ├── document-title.md # Individual markdown files
    └── ...
```

Each generated markdown file includes YAML frontmatter:
```yaml
---
title: "Document Title"
summary: "Brief description"
tags: ["tag1", "tag2"]
source: "raw_docs/original.docx"
generated_at: "2024-01-15T10:30:00"
---
```

## Design Decisions

From `docs/design-doc2know.md`:

- **Word parsing**: Dual-engine approach (python-docx primary, pandoc fallback)
- **LLM retry**: Exponential backoff (1s, 2s, 4s, 8s) for rate limiting
- **Chunking**: Documents exceeding `chunk_size` are split and merged
- **Naming**: Title slugification with numeric suffix for conflicts
- **Error handling**: JSON parsing failures fallback to regex extraction

## Dependencies

Core: `python-docx`, `openai`, `pyyaml`, `click`, `tenacity`
Test: `pytest`, `pytest-cov`
Optional: `pandoc` (for complex document structures)

Python >= 3.9 required.
