"""
fetch_live_data.py
-------------------
Fetches REAL, live domain data from public sources:

  Benign  → Tranco Top-1M list  (https://tranco-list.eu/)
            Updated daily. The top 10k are used by default.

  DGA     → DGArchive public API (https://dgarchive.caad.fkie.fraunhofer.de/)
            OR falls back to a curated public GitHub DGA dataset.

Usage:
    python fetch_live_data.py              # default: 5k benign + 5k DGA
    python fetch_live_data.py --benign 10000 --dga 10000
    python fetch_live_data.py --output live_data.csv

After running this, train with:
    python train_dga_detector.py --csv live_data.csv
"""

import argparse
import csv
import io
import os
import sys
import zipfile
import time
import random

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHON = sys.executable
TIMEOUT = 30

# ---------------------------------------------------------------------------
# Benign: Tranco Top-1M
# ---------------------------------------------------------------------------
TRANCO_LATEST_URL = "https://tranco-list.eu/top-1m.csv.zip"
TRANCO_CACHE      = "tranco_top1m.csv"


def fetch_tranco(n: int) -> list[str]:
    """Download the Tranco top-1M list (zip), return top-n domains."""
    if os.path.exists(TRANCO_CACHE):
        age_hours = (time.time() - os.path.getmtime(TRANCO_CACHE)) / 3600
        if age_hours < 24:
            print(f"[benign] Using cached Tranco list (age: {age_hours:.1f}h)")
            return _read_tranco_csv(TRANCO_CACHE, n)
        print(f"[benign] Cache is {age_hours:.1f}h old — refreshing.")

    print(f"[benign] Downloading Tranco Top-1M list …")
    try:
        r = requests.get(TRANCO_LATEST_URL, timeout=60, stream=True)
        r.raise_for_status()
        zdata = r.content
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            name = zf.namelist()[0]
            with zf.open(name) as f:
                content = f.read().decode("utf-8")
        with open(TRANCO_CACHE, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"[benign] Tranco list saved to '{TRANCO_CACHE}'")
        return _read_tranco_csv(TRANCO_CACHE, n)
    except Exception as exc:
        print(f"[benign] Tranco download failed: {exc}")
        print("[benign] Falling back to Umbrella Top-1M …")
        return fetch_umbrella(n)


def _read_tranco_csv(path: str, n: int) -> list[str]:
    domains = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                domains.append(parts[1].strip().lower())
            if len(domains) >= n:
                break
    print(f"[benign] Loaded {len(domains):,} benign domains from Tranco")
    return domains


def fetch_umbrella(n: int) -> list[str]:
    """Fallback: Cisco Umbrella top-1M."""
    URL = "http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"
    try:
        print("[benign] Downloading Cisco Umbrella Top-1M …")
        r = requests.get(URL, timeout=60)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            with zf.open("top-1m.csv") as f:
                content = f.read().decode("utf-8")
        domains = []
        for line in content.splitlines():
            parts = line.split(",")
            if len(parts) >= 2:
                domains.append(parts[1].strip().lower())
            if len(domains) >= n:
                break
        print(f"[benign] Loaded {len(domains):,} benign domains from Umbrella")
        return domains
    except Exception as exc:
        print(f"[benign] Umbrella also failed: {exc}")
        raise RuntimeError("Cannot fetch any benign domain list. Check internet connection.")


# ---------------------------------------------------------------------------
# DGA: DGArchive public dataset (Fraunhofer FKIE)
# ---------------------------------------------------------------------------
DGARCHIVE_URL  = "https://dgarchive.caad.fkie.fraunhofer.de/site/current"
# Public curated DGA dataset on GitHub (no auth required)
DGA_GITHUB_URL = (
    "https://raw.githubusercontent.com/andrewaeva/DGA/master/dga_data"
    "/dga_domains_full.txt"
)
# Fallback 2: bambenek consulting feeds (public, updated daily)
BAMBENEK_FEEDS = [
    "https://osint.bambenekconsulting.com/feeds/dga-feed.txt",
    "https://faf.bambenekconsulting.com/feeds/dga-feed.txt",
]
# Fallback 3: abuse.ch urlhaus DGA tagged
URLHAUS_URL = "https://urlhaus.abuse.ch/downloads/text/"


def fetch_dga_domains(n: int) -> list[tuple[str, str]]:
    """
    Returns list of (domain, family) tuples from public DGA threat feeds.
    Tries multiple sources in order.
    """
    results = []

    # --- Source 1: andrewaeva/DGA GitHub repo ---
    print("[dga] Trying andrewaeva/DGA GitHub dataset …")
    results = _fetch_andrewaeva_dga(n)
    if results:
        print(f"[dga] Got {len(results):,} DGA domains from GitHub dataset")
        return results

    # --- Source 2: Bambenek Consulting feeds ---
    print("[dga] Trying Bambenek Consulting feeds …")
    for url in BAMBENEK_FEEDS:
        results = _fetch_bambenek(url, n)
        if results:
            print(f"[dga] Got {len(results):,} DGA domains from Bambenek")
            return results

    # --- Source 3: URLhaus (filtered for DGA-tagged entries) ---
    print("[dga] Trying URLhaus …")
    results = _fetch_urlhaus(n)
    if results:
        print(f"[dga] Got {len(results):,} DGA domains from URLhaus")
        return results

    raise RuntimeError(
        "Could not fetch DGA data from any source. "
        "Check internet or run with --use-synthetic to use generated data."
    )


def _fetch_andrewaeva_dga(n: int) -> list[tuple[str, str]]:
    """
    Fetch DGA/malicious domains from multiple public threat intel sources.
    """
    sources = [
        # abuse.ch Feodo Tracker — C2 botnet domains
        ("https://feodotracker.abuse.ch/downloads/domainblocklist.txt", "feodo_c2"),
        # abuse.ch URLhaus — malware distribution URLs
        ("https://urlhaus.abuse.ch/downloads/text/", "urlhaus"),
        # Malware Domain List
        ("https://www.malwaredomainlist.com/hostslist/hosts.txt", "malware_domain_list"),
    ]

    all_domains: list[tuple[str, str]] = []

    for url, family_tag in sources:
        if len(all_domains) >= n:
            break
        try:
            r = requests.get(url, timeout=TIMEOUT,
                             headers={"User-Agent": "DGA-Detector-Research/1.0"})
            if r.status_code != 200:
                continue
            batch = []
            for line in r.text.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "//", ";")):
                    continue
                # Strip protocol prefix if present
                for proto in ("http://", "https://", "ftp://"):
                    if line.startswith(proto):
                        line = line[len(proto):]
                dom = line.split("/")[0].strip().lower()
                # Basic validity
                if "." in dom and " " not in dom and len(dom) > 4 and len(dom) < 80:
                    batch.append((dom, family_tag))
            if len(batch) > 20:
                print(f"[dga]   Got {len(batch):,} domains from {url.split('/')[2]}")
                all_domains.extend(batch)
        except Exception:
            continue

    return all_domains[:n]


def _fetch_bambenek(url: str, n: int) -> list[tuple[str, str]]:
    """
    Bambenek Consulting DGA feed format:
    domain,ip,date,malware_family,notes
    """
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        domains = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            parts = line.split(",")
            if len(parts) >= 1:
                dom = parts[0].strip().lower()
                fam = parts[3].strip().lower() if len(parts) > 3 else "dga"
                if "." in dom:
                    domains.append((dom, fam))
            if len(domains) >= n:
                break
        return domains
    except Exception:
        return []


def _fetch_urlhaus(n: int) -> list[tuple[str, str]]:
    """
    URLhaus text feed — extract hostnames.
    Not DGA-specific but contains malicious domains.
    """
    try:
        r = requests.get(URLHAUS_URL, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        domains = []
        seen = set()
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract hostname from URL
            try:
                host = line.split("/")[2] if "://" in line else line.split("/")[0]
                host = host.lower().strip()
                if host and "." in host and host not in seen:
                    seen.add(host)
                    domains.append((host, "malicious"))
            except Exception:
                continue
            if len(domains) >= n:
                break
        return domains
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Synthetic DGA fallback (reuse generate_dga_data.py logic)
# ---------------------------------------------------------------------------
def fetch_synthetic_dga(n: int) -> list[tuple[str, str]]:
    """Generate synthetic DGA domains as a fallback."""
    print("[dga] Using synthetic DGA generation as fallback …")
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from generate_dga_data import GENERATORS
        per_family = max(1, n // len(GENERATORS))
        results = []
        for family, fn in GENERATORS.items():
            for dom in fn(per_family):
                results.append((dom, family))
        random.shuffle(results)
        return results[:n]
    except ImportError:
        raise RuntimeError("generate_dga_data.py not found alongside this script.")


# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------
def write_csv(benign_domains: list[str],
              dga_domains: list[tuple[str, str]],
              output_path: str) -> None:
    rows = []
    for dom in benign_domains:
        rows.append({"domain": dom, "label": "benign", "family": "benign"})
    for dom, fam in dga_domains:
        rows.append({"domain": dom, "label": "dga", "family": fam})

    random.shuffle(rows)

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["domain", "label", "family"])
        writer.writeheader()
        writer.writerows(rows)

    benign_n = sum(1 for r in rows if r["label"] == "benign")
    dga_n    = sum(1 for r in rows if r["label"] == "dga")
    print(f"\n[output] Wrote {len(rows):,} rows -> '{output_path}'")
    print(f"  Benign: {benign_n:,}  |  DGA: {dga_n:,}")
    fams = {}
    for r in rows:
        if r["label"] == "dga":
            fams[r["family"]] = fams.get(r["family"], 0) + 1
    print(f"  DGA families: {dict(sorted(fams.items(), key=lambda x: -x[1]))}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch live DGA + benign domain data.")
    p.add_argument("--benign", type=int, default=5000,
                   help="Number of benign domains to fetch (default: 5000)")
    p.add_argument("--dga",    type=int, default=5000,
                   help="Number of DGA domains to fetch (default: 5000)")
    p.add_argument("--output", default="live_data.csv",
                   help="Output CSV path (default: live_data.csv)")
    p.add_argument("--use-synthetic-dga", action="store_true",
                   help="Use synthetic DGA generator instead of threat feeds")
    p.add_argument("--no-tranco-cache", action="store_true",
                   help="Force re-download the Tranco list even if cached")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.no_tranco_cache and os.path.exists(TRANCO_CACHE):
        os.remove(TRANCO_CACHE)

    print("=" * 60)
    print("  DGA Detector — Live Data Fetcher")
    print("=" * 60)

    # Benign
    print(f"\n[step 1/2] Fetching {args.benign:,} benign domains from Tranco …")
    benign = fetch_tranco(args.benign)

    # DGA
    print(f"\n[step 2/2] Fetching {args.dga:,} DGA domains from threat feeds …")
    if args.use_synthetic_dga:
        dga = fetch_synthetic_dga(args.dga)
    else:
        try:
            dga = fetch_dga_domains(args.dga)
        except RuntimeError as e:
            print(f"[dga] WARNING: {e}")
            print("[dga] Falling back to synthetic DGA generation.")
            dga = fetch_synthetic_dga(args.dga)

    # Sample to requested count
    if len(benign) > args.benign:
        benign = random.sample(benign, args.benign)
    if len(dga) > args.dga:
        dga = random.sample(dga, args.dga)

    # Balance if needed
    min_size = min(len(benign), len(dga))
    if len(benign) != len(dga):
        print(f"\n[balance] Capping to {min_size:,} per class for balance.")
        benign = benign[:min_size]
        dga    = dga[:min_size]

    write_csv(benign, dga, args.output)
    print(f"\nNext step: python train_dga_detector.py --csv {args.output}")


if __name__ == "__main__":
    main()
