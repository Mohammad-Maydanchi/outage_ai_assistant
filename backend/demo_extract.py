"""One-off demo: run the real Claude extractor on the AT&T baseline transcript
and print the structured report. Usage: .venv/bin/python demo_extract.py
"""

from pathlib import Path

from app.extraction import ClaudeExtractor

transcript = Path("tests/fixtures/att_baseline_transcript.txt").read_text()

print("Calling Claude to read the AT&T transcript...\n")
report = ClaudeExtractor().extract(transcript)

print("===== STRUCTURED REPORT =====")
for field, value in report.model_dump().items():
    print(f"{field:>22}: {value}")
