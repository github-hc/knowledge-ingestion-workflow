#!/usr/bin/env python3
"""
Quick diagnostic: test PDF extraction on all PDFs in /tmp that were uploaded.
Run: python3 debug_extract.py /path/to/your.pdf
"""
import sys
import os

# Test pdfminer directly
from pdfminer.high_level import extract_text as pdfminer_extract_text

# Test pdfplumber
import pdfplumber

file_path = sys.argv[1] if len(sys.argv) > 1 else None
if not file_path:
    print("Usage: python3 debug_extract.py <path_to_pdf>")
    sys.exit(1)

print(f"\n=== Testing: {file_path} ===\n")

# --- pdfplumber ---
print("--- pdfplumber ---")
try:
    with pdfplumber.open(file_path) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages, 1):
            try:
                text = page.extract_text() or ""
                print(f"  Page {i}: {len(text)} chars | preview: {repr(text[:80])}")
            except Exception as e:
                print(f"  Page {i}: ERROR - {e}")
except Exception as e:
    print(f"pdfplumber FAILED: {e}")

# --- pdfminer ---
print("\n--- pdfminer high-level ---")
try:
    text = pdfminer_extract_text(file_path) or ""
    print(f"Total chars: {len(text)}")
    print(f"Preview: {repr(text[:300])}")
except Exception as e:
    print(f"pdfminer FAILED: {e}")
