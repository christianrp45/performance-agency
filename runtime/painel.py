"""Atalho: python painel.py "<pasta do cliente>" [--porta 8780] [--demo]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from performance_agency.painel import main  # noqa: E402

if __name__ == "__main__":
    main()
