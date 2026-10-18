# DGA Domain Detector

A machine-learning tool that detects **Domain Generation Algorithm (DGA)** domains — the kind used by malware to hide communication with hacker-controlled servers.

## What is a DGA?

Malware (botnets, ransomware) uses algorithms to auto-generate thousands of random domain names. The attacker registers just one. Traditional blocklists can't keep up. ML can.

| Domain | Verdict | P(DGA) |
|--------|---------|--------|
| `google.com` | ✓ Safe | 0.004 |
| `x9k2m8q1p4z7v3j.net` | ⚠ Malicious | 1.000 |
| `kqzxmvpnbwrtylsdfg.com` | ⚠ Malicious | 1.000 |
| `spokelight.net` | ✓ Safe | 0.007 |

## Results

- **Test Accuracy**: 99%
- **ROC-AUC**: 0.9998
- **Family Hold-out AUC**: 0.9999 (generalises to unseen DGA families)

## How It Works

```
Domain String
     ↓
Feature Extraction (15 features)
  • Shannon entropy     • Vowel/consonant ratio
  • Dictionary coverage • Max consonant run
  • Hex pattern check   • N-gram frequency
  • Digit ratio         • Unique char ratio
     ↓
StandardScaler → LightGBM (400 trees)
     ↓
P(DGA) score [0.0 – 1.0]
```

## Project Structure

```
├── dga_core.py             # Feature engineering (15 features)
├── train_dga_detector.py   # Training + evaluation + model save
├── test_predict.py         # CLI predictor for any domain
├── fetch_live_data.py      # Live data: Tranco + threat feeds
├── generate_dga_data.py    # Synthetic dataset generator (10 families)
├── make_wordlist.py        # Downloads English wordlist (370k words)
├── requirements.txt        # Python dependencies
└── DGA_Detector_Colab.ipynb  # Google Colab runner notebook
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2a. Use live data (recommended)
```bash
# Downloads Tranco Top-1M (benign) + public DGA threat feeds
python fetch_live_data.py --benign 5000 --dga 5000 --output live_data.csv
python make_wordlist.py
python train_dga_detector.py --csv live_data.csv
```

### 2b. Use synthetic demo data
```bash
python generate_dga_data.py          # creates dga_data.csv
python make_wordlist.py              # downloads words_alpha.txt
python train_dga_detector.py --csv dga_data.csv
```

### 3. Classify domains
```bash
# Built-in test set (20 domains)
python test_predict.py

# Your own domains
python test_predict.py google.com x9k2m8.net spokelight.net evil-botnet.ru
```

## DGA Families Covered

| Family | Pattern |
|--------|---------|
| Conficker | Random lowercase letters |
| CryptoLocker | Letters + digits, high entropy |
| Zeus | Short + digit clusters |
| Necurs | Long consonant-only strings |
| Locky | 16-32 hex characters |
| Dridex | Word + long digit suffix |
| Mirai | IP octets encoded as string |
| Ramdo | Short pseudo-random |
| Suppobox | Dictionary word + random suffix |
| Banjori | Rotated-alphabet mutation |

## Features

| Feature | Description |
|---------|-------------|
| `entropy` | Shannon entropy — random strings peak at ~3.5 bits/char |
| `word_ratio` | Dictionary coverage via greedy longest-match |
| `vowel_ratio` | English words ~40% vowels; DGA strings ~0-10% |
| `max_consonant_run` | `kqzxmvp` → 7; impossible in real English |
| `has_hex_pattern` | Detects `[0-9a-f]{8,}` blocks (Locky-style) |
| + 10 more | see `dga_core.FEATURE_NAMES` |

## Requirements

- Python 3.10+
- `pandas`, `numpy`, `scikit-learn`, `lightgbm`, `joblib`, `scipy`, `tldextract`, `requests`

## License

MIT

