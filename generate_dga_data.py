"""
generate_dga_data.py
---------------------
Generates a synthetic `dga_data.csv` training dataset.

Columns:
  domain  — raw domain string (no protocol, no path)
  label   — 'dga' or 'benign'
  family  — DGA family name (or 'benign')

Run once:  python generate_dga_data.py
"""

import random
import string
import csv
import os

random.seed(42)

# ---------------------------------------------------------------------------
# Benign domains  (well-known real-world domains)
# ---------------------------------------------------------------------------
BENIGN_DOMAINS = [
    "google.com", "youtube.com", "facebook.com", "twitter.com", "amazon.com",
    "wikipedia.org", "reddit.com", "instagram.com", "linkedin.com", "netflix.com",
    "apple.com", "microsoft.com", "github.com", "stackoverflow.com", "openai.com",
    "cloudflare.com", "dropbox.com", "spotify.com", "zoom.us", "slack.com",
    "adobe.com", "salesforce.com", "shopify.com", "stripe.com", "twilio.com",
    "wordpress.com", "medium.com", "quora.com", "tumblr.com", "pinterest.com",
    "bbc.com", "cnn.com", "nytimes.com", "theguardian.com", "reuters.com",
    "weather.com", "espn.com", "nbcnews.com", "foxnews.com", "abcnews.go.com",
    "bing.com", "duckduckgo.com", "yahoo.com", "aol.com", "ask.com",
    "ebay.com", "etsy.com", "alibaba.com", "aliexpress.com", "walmart.com",
    "target.com", "bestbuy.com", "homedepot.com", "costco.com", "ikea.com",
    "paypal.com", "venmo.com", "wise.com", "revolut.com", "coinbase.com",
    "chase.com", "bankofamerica.com", "wellsfargo.com", "citibank.com", "hsbc.com",
    "docker.com", "kubernetes.io", "nginx.com", "apache.org", "python.org",
    "nodejs.org", "reactjs.org", "vuejs.org", "angular.io", "typescript.org",
    "postgresql.org", "mysql.com", "mongodb.com", "redis.io", "elastic.co",
    "aws.amazon.com", "azure.microsoft.com", "cloud.google.com", "heroku.com", "vercel.com",
    "twitch.tv", "tiktok.com", "snapchat.com", "discord.com", "telegram.org",
    "whatsapp.com", "signal.org", "skype.com", "zoom.us", "meet.google.com",
    "outlook.com", "gmail.com", "protonmail.com", "fastmail.com", "zoho.com",
    "harvard.edu", "mit.edu", "stanford.edu", "cambridge.ac.uk", "oxford.ac.uk",
    "nasa.gov", "nih.gov", "cdc.gov", "who.int", "un.org",
    "techcrunch.com", "wired.com", "theverge.com", "arstechnica.com", "engadget.com",
    "imdb.com", "rottentomatoes.com", "metacritic.com", "goodreads.com", "audible.com",
    "airbnb.com", "booking.com", "expedia.com", "hotels.com", "tripadvisor.com",
    "uber.com", "lyft.com", "doordash.com", "grubhub.com", "instacart.com",
]

# ---------------------------------------------------------------------------
# DGA family generators
# ---------------------------------------------------------------------------

FAMILIES = ["conficker", "cryptolocker", "zeus", "necurs", "locky",
            "dridex", "mirai", "ramdo", "suppobox", "banjori"]


def _conficker_like(n: int) -> list[str]:
    """Conficker: pseudo-random lowercase letters, length 8-15."""
    domains = []
    chars = string.ascii_lowercase
    for _ in range(n):
        length = random.randint(8, 15)
        sld = "".join(random.choices(chars, k=length))
        tld = random.choice(["com", "net", "org", "biz", "info"])
        domains.append(f"{sld}.{tld}")
    return domains


def _cryptolocker_like(n: int) -> list[str]:
    """CryptoLocker: mix of letters and digits, higher entropy."""
    domains = []
    chars = string.ascii_lowercase + string.digits
    for _ in range(n):
        length = random.randint(10, 20)
        sld = "".join(random.choices(chars, k=length))
        tld = random.choice(["com", "ru", "cc"])
        domains.append(f"{sld}.{tld}")
    return domains


def _zeus_like(n: int) -> list[str]:
    """Zeus: shorter, sometimes has digit clusters."""
    domains = []
    for _ in range(n):
        length = random.randint(6, 12)
        sld = "".join(random.choices(string.ascii_lowercase, k=length))
        # insert 1-3 digits at random positions
        sld_list = list(sld)
        for _ in range(random.randint(1, 3)):
            pos = random.randint(0, len(sld_list))
            sld_list.insert(pos, str(random.randint(0, 9)))
        sld = "".join(sld_list)
        tld = random.choice(["net", "org", "com"])
        domains.append(f"{sld}.{tld}")
    return domains


def _necurs_like(n: int) -> list[str]:
    """Necurs: very long, low vowel ratio."""
    consonants = "bcdfghjklmnpqrstvwxyz"
    domains = []
    for _ in range(n):
        length = random.randint(18, 30)
        sld = "".join(random.choices(consonants, k=length))
        tld = random.choice(["com", "top", "xyz"])
        domains.append(f"{sld}.{tld}")
    return domains


def _locky_like(n: int) -> list[str]:
    """Locky: hex-like, 16-32 hex chars."""
    domains = []
    hex_chars = "0123456789abcdef"
    for _ in range(n):
        length = random.randint(16, 32)
        sld = "".join(random.choices(hex_chars, k=length))
        tld = random.choice(["com", "net"])
        domains.append(f"{sld}.{tld}")
    return domains


def _dridex_like(n: int) -> list[str]:
    """Dridex: word + numbers hybrid."""
    domains = []
    for _ in range(n):
        word_len = random.randint(4, 8)
        sld = "".join(random.choices(string.ascii_lowercase, k=word_len))
        digits = "".join(random.choices(string.digits, k=random.randint(3, 8)))
        sld = sld + digits
        tld = random.choice(["com", "info", "net"])
        domains.append(f"{sld}.{tld}")
    return domains


def _mirai_like(n: int) -> list[str]:
    """Mirai-style: IP-like patterns encoded as strings."""
    domains = []
    for _ in range(n):
        octets = [random.randint(1, 255) for _ in range(4)]
        sld = "".join(f"{o:03d}" for o in octets)
        tld = random.choice(["com", "net", "org"])
        domains.append(f"{sld}.{tld}")
    return domains


def _ramdo_like(n: int) -> list[str]:
    """Ramdo: short pseudorandom."""
    domains = []
    for _ in range(n):
        length = random.randint(5, 9)
        sld = "".join(random.choices(string.ascii_lowercase, k=length))
        tld = random.choice(["com", "net", "ru"])
        domains.append(f"{sld}.{tld}")
    return domains


def _suppobox_like(n: int) -> list[str]:
    """Suppobox: dictionary-word + random suffix."""
    words = ["super", "cloud", "data", "info", "secure", "safe", "best", "top",
             "fast", "web", "net", "global", "smart", "pro", "max", "ultra"]
    domains = []
    for _ in range(n):
        word = random.choice(words)
        suffix = "".join(random.choices(string.ascii_lowercase, k=random.randint(4, 8)))
        sld = word + suffix
        tld = random.choice(["com", "net", "org"])
        domains.append(f"{sld}.{tld}")
    return domains


def _banjori_like(n: int) -> list[str]:
    """Banjori: based on character rotation mutation."""
    seed_words = ["earlybird", "football", "sunshine", "baseball", "rainbow"]
    domains = []
    for _ in range(n):
        base = random.choice(seed_words)
        shift = random.randint(1, 5)
        sld = "".join(chr((ord(c) - ord('a') + shift) % 26 + ord('a')) if c.isalpha() else c for c in base)
        noise = "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 7)))
        sld = sld + noise
        tld = random.choice(["com", "net"])
        domains.append(f"{sld}.{tld}")
    return domains


GENERATORS = {
    "conficker":    _conficker_like,
    "cryptolocker": _cryptolocker_like,
    "zeus":         _zeus_like,
    "necurs":       _necurs_like,
    "locky":        _locky_like,
    "dridex":       _dridex_like,
    "mirai":        _mirai_like,
    "ramdo":        _ramdo_like,
    "suppobox":     _suppobox_like,
    "banjori":      _banjori_like,
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(output_path: str = "dga_data.csv",
             benign_per_class: int = 400,
             dga_per_family: int = 400) -> str:
    rows = []

    # Benign: replicate + small random variations to reach desired count
    benign_base = BENIGN_DOMAINS.copy()
    while len(benign_base) < benign_per_class * len(FAMILIES):
        # create variations: prepend random word
        prefix = "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 6)))
        original = random.choice(BENIGN_DOMAINS)
        parts = original.split(".", 1)
        if len(parts) == 2:
            benign_base.append(f"{prefix}.{parts[0]}.{parts[1]}")
        else:
            benign_base.append(f"{prefix}{original}")

    random.shuffle(benign_base)
    total_benign = benign_per_class * len(FAMILIES)
    for domain in benign_base[:total_benign]:
        rows.append({"domain": domain, "label": "benign", "family": "benign"})

    # DGA
    for family, gen_fn in GENERATORS.items():
        for domain in gen_fn(dga_per_family):
            rows.append({"domain": domain, "label": "dga", "family": family})

    random.shuffle(rows)

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["domain", "label", "family"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[generate] Wrote {len(rows):,} rows -> '{output_path}'")
    benign_count = sum(1 for r in rows if r["label"] == "benign")
    dga_count    = sum(1 for r in rows if r["label"] == "dga")
    print(f"  Benign: {benign_count:,}  |  DGA: {dga_count:,}")
    return output_path


if __name__ == "__main__":
    generate()
