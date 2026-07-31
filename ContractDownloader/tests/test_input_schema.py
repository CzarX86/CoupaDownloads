"""Tests for the shared column schema helpers (input_schema)."""

import json

import pytest

from src.engine.input_schema import (
    detect_required_columns,
    normalize_column_name,
    parse_mapping_env,
    resolve_mapping,
)


def test_normalize_column_name_strips_separators_and_case():
    assert normalize_column_name(" PO_NUMBER ") == "ponumber"
    assert normalize_column_name("Vendor-Name") == "vendorname"
    assert normalize_column_name("") == ""


def test_detect_required_columns_finds_aliases():
    detected = detect_required_columns(["PO Number", "Legal Entity", "Year"])
    assert detected["po"] == "PO Number"
    assert detected["supplier"] == "Legal Entity"


def test_detect_required_columns_returns_none_when_missing():
    detected = detect_required_columns(["Document", "Counterparty", "Year"])
    assert detected["po"] is None
    assert detected["supplier"] is None


def test_resolve_mapping_prefers_explicit_mapping():
    columns = ["Document", "Vendor Name", "PO_NUMBER"]
    resolved = resolve_mapping(columns, {"po": "Document", "supplier": "Vendor Name"})
    assert resolved == {"po": "Document", "supplier": "Vendor Name"}


def test_resolve_mapping_fills_gaps_with_detection():
    columns = ["PO_NUMBER", "Vendor Name"]
    resolved = resolve_mapping(columns, {"supplier": "Vendor Name"})
    assert resolved == {"po": "PO_NUMBER", "supplier": "Vendor Name"}


def test_resolve_mapping_ignores_unknown_column_names():
    columns = ["Document", "Vendor"]
    resolved = resolve_mapping(columns, {"po": "DoesNotExist", "supplier": "Vendor"})
    assert resolved["po"] is None
    assert resolved["supplier"] == "Vendor"


def test_parse_mapping_env_reads_json(monkeypatch):
    monkeypatch.setenv("COUPA_COLUMN_MAPPING", json.dumps({"po": "Document", "supplier": "Vendor Name"}))
    assert parse_mapping_env() == {"po": "Document", "supplier": "Vendor Name"}


def test_parse_mapping_env_ignores_invalid_json(monkeypatch):
    monkeypatch.setenv("COUPA_COLUMN_MAPPING", "not-json")
    assert parse_mapping_env() is None


def test_parse_mapping_env_none_when_absent(monkeypatch):
    monkeypatch.delenv("COUPA_COLUMN_MAPPING", raising=False)
    assert parse_mapping_env() is None


@pytest.mark.parametrize("value,expected", [
    ("po", "po"),
    ("PO", "po"),
    ("pedido", "pedido"),
    ("purchase order number", "purchaseordernumber"),
])
def test_po_aliases_are_covered(value, expected):
    detected = detect_required_columns([value])
    assert detected["po"] == value
    assert normalize_column_name(value) == expected
