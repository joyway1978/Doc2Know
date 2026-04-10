# Plan: Add PDF Parsing Support to Doc2Know

## Overview

Add support for parsing PDF documents (.pdf) in addition to the existing Word document (.docx) support. This will allow users to convert PDF files into structured Markdown knowledge bases using the same LLM analysis pipeline.

## Goals

- Parse PDF documents and extract text content
- Support both text-based and image-based (OCR) PDFs
- Integrate with existing Doc2Know pipeline (parser → analyzer → generator → indexer)
- Maintain consistent output format with Word document processing

## Implementation Approaches

### Option A: PyMuPDF (fitz) - Recommended
- **Pros**: Fast, good text extraction, supports OCR with Tesseract, actively maintained
- **Cons**: Additional dependency
- **Effort**: Medium

### Option B: pdfplumber
- **Pros**: Python-native, good for structured text extraction
- **Cons**: OCR requires separate integration
- **Effort**: Medium

### Option C: pypdf + pytesseract
- **Pros**: Lightweight, pure Python
- **Cons**: OCR requires manual integration, less robust
- **Effort**: High

## Proposed Changes

### 1. Add PDF Parser Module

Create `doc2know/pdf_parser.py`:
- `PdfParser` class with `parse(file_path)` method
- Extract text content from PDF pages
- Support OCR for scanned/image-based PDFs (optional v1)
- Return same format as `DocxParser` (title, paragraphs with style/level)

### 2. Update Parser Module

Modify `doc2know/parser.py`:
- Add `PdfParser` import
- Update `parse_docx()` to generic `parse_document()` or add `parse_pdf()`
- Auto-detect file type by extension (.pdf vs .docx)

### 3. Update CLI

Modify `doc2know/cli.py`:
- Update `DocumentProcessor.process_all()` to handle .pdf files
- Scan for both .docx and .pdf in raw_dir

### 4. Add Dependencies

Update `requirements.txt` and `setup.py`:
- `PyMuPDF>=1.23.0` (fitz) OR `pdfplumber>=0.10.0`
- Optional: `pytesseract>=0.3.0` and `Pillow>=10.0.0` for OCR

### 5. Add Tests

Create `tests/test_pdf_parser.py`:
- Test PDF text extraction
- Test error handling for corrupted PDFs
- Test empty PDF handling

## File Structure Changes

```
doc2know/
├── __init__.py
├── cli.py              # Update: handle .pdf files
├── config.py           # No changes
├── parser.py           # Update: add PDF support, auto-detect file type
├── pdf_parser.py       # New: PDF parsing implementation
├── analyzer.py         # No changes
├── generator.py        # No changes
├── indexer.py          # No changes
tests/
├── test_pdf_parser.py  # New: PDF parser tests
├── data/
│   ├── sample.docx
│   └── sample.pdf      # New: test PDF file
```

## Success Criteria

- [ ] Can parse text-based PDF files and extract content
- [ ] Generated Markdown has same quality as Word document output
- [ ] Index file correctly includes PDF-derived documents
- [ ] Tests pass with good coverage (>80%)
- [ ] Documentation updated (README.md, CLAUDE.md)

## Deferred (Future Work)

- OCR support for scanned PDFs (requires Tesseract installation)
- PDF table extraction and formatting
- PDF image extraction

## Risks

- PDF parsing quality varies by document structure
- OCR adds significant complexity and dependencies
- Large PDF files may hit token limits more frequently
