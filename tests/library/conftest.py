"""Pytest configuration for library tests."""
import sys
from pathlib import Path

# Add parent directory to path so cosori_kettle can be imported
lib_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lib_path))
