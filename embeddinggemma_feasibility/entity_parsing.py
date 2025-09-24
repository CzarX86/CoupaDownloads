"""Utilities for structured entity extraction without relying on regex.

The helpers in this module provide reusable logic for parsing contract artefacts
such as filenames and PDF snippets. They avoid regular expressions in favour of
lexical analysis, lightweight NLP (when available) and semantic heuristics. This
ensures we can evolve the extraction strategy without brittle pattern matching
while keeping dependencies optional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

try:  # spaCy is optional and only used when available
    import spacy
    from spacy.language import Language
except Exception:  # pragma: no cover - spaCy may be absent in CI environments
    spacy = None  # type: ignore
    Language = None  # type: ignore

try:  # dateparser gives robust multi-format parsing for human dates
    import dateparser
except Exception:  # pragma: no cover - dateparser already optional upstream
    dateparser = None  # type: ignore


@dataclass
class ParsedEntities:
    """Container describing the entities recovered from a text fragment."""

    pwo_number: Optional[str] = None
    po_number: Optional[str] = None
    contract_start_date: Optional[str] = None
    contract_end_date: Optional[str] = None
    sow_value_eur: Optional[str] = None
    managed_by: Optional[str] = None
    contract_type: Optional[str] = None
    sow_currency: Optional[str] = None


def _normalise_digits(text: str) -> str:
    """Return only the digits contained in *text* preserving sign when present."""

    digits: List[str] = []
    sign_seen = False
    for ch in text:
        if ch.isdigit():
            digits.append(ch)
        elif ch == "-" and not digits and not sign_seen:
            digits.append(ch)
            sign_seen = True
    return "".join(digits)


def _clean_amount_token(token: str) -> Optional[str]:
    """Normalise a currency/amount token removing thousand separators."""

    if not token:
        return None
    stripped = token.strip().replace("\xa0", " ")
    if not stripped:
        return None
    allowed = {"-", ",", "."}
    cleaned: List[str] = []
    for ch in stripped:
        if ch.isdigit() or ch in allowed:
            if ch == ",":
                continue  # treat comma as thousand separator
            cleaned.append(ch)
    if not any(ch.isdigit() for ch in cleaned):
        return None
    return "".join(cleaned)


def _sentence_split(text: str) -> List[str]:
    """Basic sentence splitter resilient to PDFs with erratic line breaks."""

    if not text:
        return []
    delimiters = {".", "\n", "\r", "?", "!", ";"}
    sentences: List[str] = []
    current: List[str] = []
    for ch in text:
        current.append(ch)
        if ch in delimiters:
            candidate = "".join(current).strip()
            if candidate:
                sentences.append(candidate)
            current = []
    tail = "".join(current).strip()
    if tail:
        sentences.append(tail)
    return sentences


def _tokenise(text: str) -> List[str]:
    """Tokenise a string without regex relying on whitespace and punctuation."""

    tokens: List[str] = []
    current: List[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"$", "€", "£", "%", "#", "/"}:
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _keywords_from_hint(hint: str) -> List[str]:
    """Extract meaningful keywords from a hint/pattern string."""

    tokens: List[str] = []
    current: List[str] = []
    for ch in hint:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                token = "".join(current)
                if len(token) > 2 or token.upper() in {"PO", "PWO", "FX"}:
                    tokens.append(token.lower())
                current = []
    if current:
        token = "".join(current)
        if len(token) > 2 or token.upper() in {"PO", "PWO", "FX"}:
            tokens.append(token.lower())
    return tokens


class ContractEntityParser:
    """Reusable helper to derive structured entities from unstructured text."""

    def __init__(self) -> None:
        self._nlp = self._load_nlp()

    def _load_nlp(self) -> Optional[Language]:
        if spacy is None:  # pragma: no cover - spaCy optional
            return None
        try:
            return spacy.load("en_core_web_sm")
        except Exception:  # pragma: no cover - fall back to blank pipeline
            return spacy.blank("en")

    # ----------------------------- Public API -----------------------------
    def parse_filename(self, filename: str) -> Dict[str, str]:
        """Return metadata hints embedded in a filename."""

        base = filename.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0]
        tokens = _tokenise(stem)

        result: Dict[str, str] = {}

        pwo = self._extract_labelled_number(tokens, label="pwo", min_digits=5, max_digits=8)
        if pwo:
            result["pwo_number"] = pwo

        po = self._extract_labelled_number(tokens, label="po", min_digits=6, max_digits=10)
        if po:
            result["po_number"] = po

        date_hint = self._extract_date_from_tokens(tokens)
        if date_hint:
            result["date_hint"] = date_hint

        project_name = self._derive_project_name(tokens)
        if project_name:
            result["project_name_hint"] = project_name

        return result

    def extract_entities(
        self,
        text: str,
        *,
        field_hint: Optional[str] = None,
        target_field: Optional[str] = None,
    ) -> ParsedEntities:
        """Analyse a text fragment and recover relevant entities."""

        sentences = _sentence_split(text) or [text]
        keywords = _keywords_from_hint(field_hint or "") if field_hint else []
        parsed = ParsedEntities()

        for sentence in sentences:
            if keywords and not self._sentence_contains_keywords(sentence, keywords):
                continue

            tokens = _tokenise(sentence)
            sentence_lower = sentence.lower()

            if not parsed.pwo_number or target_field == "pwo_number":
                candidate = self._extract_labelled_number(tokens, "pwo", 5, max_digits=8)
                if candidate:
                    parsed.pwo_number = candidate
                    if target_field == "pwo_number":
                        return parsed

            if not parsed.po_number or target_field == "po_number":
                candidate = self._extract_labelled_number(tokens, "po", 6, max_digits=10)
                if candidate:
                    parsed.po_number = candidate
                    if target_field == "po_number":
                        return parsed

            if not parsed.managed_by or target_field == "managed_by":
                candidate = self._extract_choice(tokens, {"vmo", "sl", "sam", "business"})
                if candidate:
                    parsed.managed_by = candidate
                    if target_field == "managed_by":
                        return parsed

            if not parsed.contract_type or target_field == "contract_type":
                candidate = self._extract_contract_type(sentence_lower)
                if candidate:
                    parsed.contract_type = candidate
                    if target_field == "contract_type":
                        return parsed

            if not parsed.sow_currency or target_field == "sow_currency":
                currency = self._extract_currency(tokens)
                if currency:
                    parsed.sow_currency = currency
                    if target_field == "sow_currency":
                        return parsed

            if not parsed.sow_value_eur or target_field == "sow_value_eur":
                amount = self._extract_amount(sentence, preferred_codes={"eur", "€"})
                if amount:
                    parsed.sow_value_eur = amount
                    if target_field == "sow_value_eur":
                        return parsed

            if not parsed.contract_start_date or target_field == "contract_start_date":
                start_date = self._extract_date(sentence, {"start", "commence", "effective"})
                if start_date:
                    parsed.contract_start_date = start_date
                    if target_field == "contract_start_date":
                        return parsed

            if not parsed.contract_end_date or target_field == "contract_end_date":
                end_date = self._extract_date(sentence, {"end", "expiry", "expiration", "terminate"})
                if end_date:
                    parsed.contract_end_date = end_date
                    if target_field == "contract_end_date":
                        return parsed

        return parsed

    # ---------------------------- Helper methods ----------------------------
    def _sentence_contains_keywords(self, sentence: str, keywords: Sequence[str]) -> bool:
        lowered = sentence.lower()
        return all(keyword in lowered for keyword in keywords)

    def _extract_labelled_number(
        self,
        tokens: Sequence[str],
        label: str,
        min_digits: int,
        *,
        max_digits: Optional[int] = None,
    ) -> Optional[str]:
        label_lower = label.lower()
        for idx, token in enumerate(tokens):
            token_lower = token.lower()
            if token_lower.startswith(label_lower):
                suffix = token[len(label):]
                digits = _normalise_digits(suffix)
                if len(digits) >= min_digits and (max_digits is None or len(digits) <= max_digits):
                    return digits
                extra = self._collect_digits(tokens[idx + 1 :], max_digits, digits)
                combined = digits + extra
                if len(combined) >= min_digits and (max_digits is None or len(combined) <= max_digits):
                    return combined
            if token_lower == label_lower:
                digits = self._collect_digits(tokens[idx + 1 :], max_digits)
                if len(digits) >= min_digits and (max_digits is None or len(digits) <= max_digits):
                    return digits
        return None

    def _collect_digits(
        self,
        tokens: Sequence[str],
        max_digits: Optional[int] = None,
        prefix: str = "",
    ) -> str:
        collected: List[str] = []
        running = prefix
        for token in tokens:
            number_part = _normalise_digits(token)
            if number_part:
                tentative = running + number_part
                if max_digits is not None and len(tentative) > max_digits:
                    break
                collected.append(number_part)
                running += number_part
                if max_digits is not None and len(running) >= max_digits:
                    break
            elif collected:
                break
        return "".join(collected)

    def _extract_date_from_tokens(self, tokens: Sequence[str]) -> Optional[str]:
        for token in tokens:
            parsed = self._parse_date(token)
            if parsed:
                return parsed
        for idx in range(len(tokens) - 2):
            window = " ".join(tokens[idx : idx + 3])
            parsed = self._parse_date(window)
            if parsed:
                return parsed
        return None

    def _derive_project_name(self, tokens: Sequence[str]) -> Optional[str]:
        ignore = {"po", "pwo", "draft", "final", "version"}
        words: List[str] = []
        for token in tokens:
            lower = token.lower()
            if lower in ignore:
                continue
            if token.isdigit():
                continue
            if lower.startswith("v") and lower[1:].isdigit():
                continue
            words.append(token)
            if len(words) >= 6:
                break
        return " ".join(words) if words else None

    def _extract_choice(self, tokens: Sequence[str], options: Iterable[str]) -> Optional[str]:
        option_set = {opt.lower() for opt in options}
        for token in tokens:
            lower = token.lower()
            if lower in option_set:
                return token.upper()
        return None

    def _extract_contract_type(self, sentence: str) -> Optional[str]:
        candidates = {
            "statement of work": "Statement of Work",
            "subs order form": "Subs Order form",
            "sow": "SOW",
            "change request": "CR",
            "cr": "CR",
            "quote": "Quote",
        }
        for key, value in candidates.items():
            if key in sentence:
                return value
        return None

    def _extract_currency(self, tokens: Sequence[str]) -> Optional[str]:
        codes = {"eur", "usd", "gbp", "inr", "brl"}
        for token in tokens:
            cleaned = token.strip().lower()
            if cleaned in codes:
                return cleaned.upper()
            if cleaned in {"€", "$", "£"}:
                mapping = {"€": "EUR", "$": "USD", "£": "GBP"}
                return mapping[cleaned]
        return None

    def _extract_amount(self, sentence: str, preferred_codes: Iterable[str]) -> Optional[str]:
        preferred = {code.lower() for code in preferred_codes}
        tokens = _tokenise(sentence)
        for idx, token in enumerate(tokens):
            lower = token.lower()
            if lower in preferred:
                amount = self._collect_numeric_phrase(tokens[idx + 1 :])
                if amount:
                    return f"{token} {amount}".strip()
            if token and token[0] in {"€", "$", "£"}:
                amount = self._collect_numeric_phrase([token[1:]] + list(tokens[idx + 1 :]))
                if amount:
                    symbol = token[0]
                    mapping = {"€": "EUR", "$": "USD", "£": "GBP"}
                    prefix = mapping.get(symbol, symbol)
                    return f"{prefix} {amount}".strip()
        return None

    def _collect_numeric_phrase(self, tokens: Sequence[str]) -> Optional[str]:
        parts: List[str] = []
        for token in tokens:
            cleaned = _clean_amount_token(token)
            if cleaned:
                parts.append(cleaned)
            elif parts:
                break
        return "".join(parts) if parts else None

    def _extract_date(self, sentence: str, keywords: Iterable[str]) -> Optional[str]:
        lowered = sentence.lower()
        if not any(keyword in lowered for keyword in keywords):
            return None
        tokens = _tokenise(sentence)
        best_candidate: Optional[str] = None
        for token in tokens:
            parsed = self._parse_date(token)
            if parsed:
                best_candidate = parsed
                break
        return best_candidate

    def _parse_date(self, token: str) -> Optional[str]:
        if dateparser is not None:
            settings = {"RETURN_AS_TIMEZONE_AWARE": False}
            dt = dateparser.parse(token, settings=settings)
            if dt:
                return datetime(dt.year, dt.month, dt.day).strftime("%Y-%m-%d")

        digits_only = "".join(ch for ch in token if ch.isdigit())
        if len(digits_only) == 8:
            candidate = self._build_date(digits_only[:4], digits_only[4:6], digits_only[6:])
            if candidate:
                return candidate
            candidate = self._build_date(digits_only[4:], digits_only[2:4], digits_only[:2])
            if candidate:
                return candidate
        if len(digits_only) == 6:
            candidate = self._build_date("20" + digits_only[:2], digits_only[2:4], digits_only[4:])
            if candidate:
                return candidate
        return None

    def _build_date(self, year: str, month: str, day: str) -> Optional[str]:
        try:
            y = int(year)
            m = int(month)
            d = int(day)
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None


def has_numeric_content(value: str) -> bool:
    """Return True when *value* contains at least one digit."""

    return any(ch.isdigit() for ch in value)


def parse_numeric_amount(value: str) -> Optional[float]:
    """Best-effort conversion of a numeric string to float without regex."""

    if not value:
        return None
    cleaned = _clean_amount_token(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
