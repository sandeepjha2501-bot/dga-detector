"""
dga_core.py
-----------
Core feature engineering for DGA (Domain Generation Algorithm) detection.

A DGA is used by malware to automatically generate many candidate domain names
that the malware can use to find its C2 (command-and-control) server.
DGA domains look random / gibberish, while legitimate domains are human-readable.

This module extracts numerical features from a raw domain string so that a
machine-learning classifier can distinguish DGA from benign domains.
"""

import sys
import math
import re
import os
import string
from collections import Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np

# ---------------------------------------------------------------------------
# Optional: load a dictionary of real English words (used for one feature).
# If the file is missing, the feature falls back to a heuristic.
# ---------------------------------------------------------------------------
_WORD_SET: set[str] = set()

def _load_wordlist(path: str | None = None) -> None:
    """Load `words_alpha.txt` (or any newline-delimited word file) into _WORD_SET."""
    global _WORD_SET
    if path is None:
        path = os.environ.get("DGA_WORDLIST", "words_alpha.txt")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            _WORD_SET = {w.strip().lower() for w in fh if len(w.strip()) > 2}
        print(f"[dga_core] Wordlist loaded: {len(_WORD_SET):,} words from '{path}'")
    except FileNotFoundError:
        print(f"[dga_core] Wordlist not found at '{path}' — word-ratio feature will use heuristic.")

# load at import time
_load_wordlist()

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _shannon_entropy(s: str) -> float:
    """Compute Shannon entropy of a string (bits per character)."""
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _vowel_ratio(s: str) -> float:
    if not s:
        return 0.0
    vowels = sum(1 for ch in s if ch in "aeiou")
    return vowels / len(s)


def _consonant_ratio(s: str) -> float:
    if not s:
        return 0.0
    consonants = sum(1 for ch in s if ch in string.ascii_lowercase and ch not in "aeiou")
    return consonants / len(s)


def _digit_ratio(s: str) -> float:
    if not s:
        return 0.0
    return sum(1 for ch in s if ch.isdigit()) / len(s)


def _hyphen_ratio(s: str) -> float:
    if not s:
        return 0.0
    return s.count("-") / len(s)


def _max_consonant_run(s: str) -> int:
    """Length of the longest consecutive consonant block."""
    longest = 0
    run = 0
    for ch in s:
        if ch in string.ascii_lowercase and ch not in "aeiou":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def _max_digit_run(s: str) -> int:
    longest = 0
    run = 0
    for ch in s:
        if ch.isdigit():
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def _unique_char_ratio(s: str) -> float:
    if not s:
        return 0.0
    return len(set(s)) / len(s)


def _word_ratio(s: str) -> float:
    """
    Fraction of the domain that can be explained by real dictionary words.
    Uses a greedy longest-match approach.
    If no wordlist is loaded, falls back to vowel-ratio heuristic.
    """
    if not _WORD_SET:
        return _vowel_ratio(s)  # fallback heuristic
    remaining = s.replace("-", "").replace("_", "")
    covered = 0
    i = 0
    while i < len(remaining):
        matched = False
        for length in range(min(15, len(remaining) - i), 2, -1):
            candidate = remaining[i : i + length]
            if candidate in _WORD_SET:
                covered += length
                i += length
                matched = True
                break
        if not matched:
            i += 1
    return covered / len(remaining) if remaining else 0.0


def _ngram_frequency(s: str, n: int = 3) -> float:
    """
    Average frequency of character n-grams in the domain (self-referential).
    Higher → more repeated patterns (less random).
    """
    if len(s) < n:
        return 0.0
    grams = [s[i : i + n] for i in range(len(s) - n + 1)]
    counts = Counter(grams)
    return sum(counts.values()) / len(grams) if grams else 0.0


def _has_hex_pattern(s: str) -> int:
    """1 if a suspicious hex-looking block (8+ consecutive hex chars) is present."""
    return int(bool(re.search(r"[0-9a-f]{8,}", s)))


def _number_of_subdomains(domain: str) -> int:
    """Count labels separated by dots (rough subdomain depth)."""
    return len(domain.split("."))


# ---------------------------------------------------------------------------
# Public API: extract_features
# ---------------------------------------------------------------------------

FEATURE_NAMES = [
    "length",
    "entropy",
    "vowel_ratio",
    "consonant_ratio",
    "digit_ratio",
    "hyphen_ratio",
    "max_consonant_run",
    "max_digit_run",
    "unique_char_ratio",
    "word_ratio",
    "bigram_freq",
    "trigram_freq",
    "has_hex_pattern",
    "num_subdomains",
    "numeric_only_label",   # 1 if the SLD is all digits
]


def extract_features(domain: str) -> np.ndarray:
    """
    Extract a 1-D numeric feature vector from a raw domain string.

    Parameters
    ----------
    domain : str
        A bare domain such as 'google.com' or 'x9k2m8q1p4z7v.net'.
        The TLD is stripped before feature computation.

    Returns
    -------
    np.ndarray, shape (len(FEATURE_NAMES),), dtype float32
    """
    domain = domain.lower().strip()

    # Strip the TLD to focus on the second-level domain (SLD)
    parts = domain.split(".")
    sld = parts[-2] if len(parts) >= 2 else parts[0]

    length          = len(sld)
    entropy         = _shannon_entropy(sld)
    vowel_r         = _vowel_ratio(sld)
    consonant_r     = _consonant_ratio(sld)
    digit_r         = _digit_ratio(sld)
    hyphen_r        = _hyphen_ratio(sld)
    max_cons_run    = _max_consonant_run(sld)
    max_dig_run     = _max_digit_run(sld)
    unique_r        = _unique_char_ratio(sld)
    word_r          = _word_ratio(sld)
    bigram_f        = _ngram_frequency(sld, 2)
    trigram_f       = _ngram_frequency(sld, 3)
    hex_pat         = _has_hex_pattern(sld)
    n_sub           = _number_of_subdomains(domain)
    numeric_only    = int(sld.isdigit())

    return np.array([
        length, entropy, vowel_r, consonant_r, digit_r, hyphen_r,
        max_cons_run, max_dig_run, unique_r, word_r,
        bigram_f, trigram_f, hex_pat, n_sub, numeric_only,
    ], dtype=np.float32)


def extract_features_batch(domains: list[str]) -> np.ndarray:
    """Vectorised version of extract_features for a list of domains."""
    return np.vstack([extract_features(d) for d in domains])

