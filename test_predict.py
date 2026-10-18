"""
test_predict.py
---------------
Load the trained DGA detector and run predictions.

Usage:
    python test_predict.py                          # runs built-in test domains
    python test_predict.py google.com x9k2m8.net   # custom domains from CLI

Output per domain:
    domain | prediction | confidence | verdict
"""

import sys
import os
import joblib
import numpy as np

from dga_core import extract_features_batch


# ---------------------------------------------------------------------------
# Default test domains (used when no CLI args are given)
# ---------------------------------------------------------------------------
DEFAULT_DOMAINS = [
    # --- clearly benign ---
    "google.com",
    "youtube.com",
    "wikipedia.org",
    "github.com",
    "stackoverflow.com",
    "amazon.com",
    "microsoft.com",
    "openai.com",
    "cloudflare.com",
    "reddit.com",
    # --- clearly DGA-like ---
    "x9k2m8q1p4z7v3j.net",          # high entropy random
    "kqzxmvpnbwrtylsdfg.com",        # no vowels (Necurs-like)
    "3f8a1c2d9e4b7f6a0e5d2c1b8a3f.net",  # hex-like (Locky-like)
    "zyxwvutsrqponmlkj.biz",         # reverse alphabet
    "abc123def456ghi789.com",        # digit clusters (Zeus-like)
    # --- boundary / tricky ---
    "spokelight.net",                 # real-looking invented word
    "secure-login.net",               # legit-style phishing pattern
    "cdn.fastly.net",                 # CDN subdomain (benign)
    "update.windows.com",             # software update (benign)
    "d3f4ultcdn.net",                 # leet-speak CDN name
]


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_domains(domains: list[str], model_path: str = "dga_detector_pipeline.pkl") -> None:
    if not os.path.exists(model_path):
        print(f"[test_predict] ERROR: Model file '{model_path}' not found.")
        print("  Run:  python train_dga_detector.py --csv dga_data.csv")
        sys.exit(1)

    print(f"\n[test_predict] Loading model from '{model_path}' …")
    pipeline = joblib.load(model_path)

    # Report wordlist size if stored
    if hasattr(pipeline, "_dga_wordlist_size"):
        print(f"  Wordlist embedded: {pipeline._dga_wordlist_size:,} words")

    X = extract_features_batch(domains)
    probs  = pipeline.predict_proba(X)[:, 1]   # P(DGA)
    labels = pipeline.predict(X)               # 0=benign, 1=DGA

    # Pretty print
    header = f"\n{'Domain':<40} {'Pred':<8} {'P(DGA)':<10} {'Verdict'}"
    print(header)
    print("-" * len(header))

    for domain, label, prob in zip(domains, labels, probs):
        pred_str = "DGA" if label == 1 else "benign"
        verdict  = "⚠  LIKELY MALICIOUS" if label == 1 else "✓  safe"
        print(f"{domain:<40} {pred_str:<8} {prob:.4f}     {verdict}")

    # Summary
    n_dga    = int(labels.sum())
    n_benign = len(labels) - n_dga
    print(f"\n  Summary: {n_dga} DGA  |  {n_benign} benign  (out of {len(labels)} tested)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    model_path = "dga_detector_pipeline.pkl"
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model_path = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    if args:
        raw = " ".join(args)
        domains = [d.strip() for d in raw.replace(",", " ").split() if d.strip()]
    else:
        domains = DEFAULT_DOMAINS

    predict_domains(domains, model_path=model_path)


if __name__ == "__main__":
    main()

