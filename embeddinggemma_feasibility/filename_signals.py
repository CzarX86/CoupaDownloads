from __future__ import annotations

from typing import Dict

from .entity_parsing import ContractEntityParser

_parser = ContractEntityParser()


def parse_filename_metadata(filename: str) -> Dict[str, str]:
    """Extract structured hints from a filename using semantic heuristics."""

    return _parser.parse_filename(filename)
