"""
make_wordlist.py
----------------
Downloads the dwyl/english-words words_alpha.txt from GitHub (or generates
a compact built-in word list if internet is unavailable).

Run:  python make_wordlist.py
"""

import urllib.request
import os
import sys

URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
OUTPUT = "words_alpha.txt"

# Compact fallback list (common English words, ~2 000 words)
FALLBACK_WORDS = """
the and for are but not you all can had her was one our out day get has him his how man new now old see two way who boy did its let put say she too use
able about above across after again against age ago agree ahead air all allow almost alone along already also although always among another any anyone anything appear
area around ask away back bad ball bank base basic be bear beat become been before begin behind being below best better between big bit black blue body book both
box boy break bring build burn buy call came care carry case cause change check child city class clear close cold come common company complete consider control
cool cost could country cover create cut dark data dead deal deep describe detail develop difference different difficult do does done door down draw drive drop dry
due during each early earth easy eat else end enough enter even every example fall family far fast feel few field fight find fire first five floor follow food
force form found free friend from front full fun give glad go good great green group grow hand hard have head hear heart heat heavy help here high history
hold home hope house human important include increase inside interest into issue just keep kind know large last later learn leave less let life light like line
list live local long look love low make many may mean meet might mind miss model move much must name national need never next nice night no not note nothing
notice number object often oil only open other outside own part pay people period picture place plan play point poor possible power press probably problem provide
public put question quickly quite rather reach ready real reason receive remember result return right river road room run same say school second seem seen send set
short show side since size small so social some something sometimes sound south space special start state stay step still stop student study subject such sure
system table take talk tell than that their them then there these they thing think those though thought three through time together today too top toward town true
try turn two under until up use used usually very view voice want water way week well went what when where while white who why wide will window with within
without woman work world would write year yes yet you young your
about above across after again against age agree ahead air all allow almost alone along already also although always among another any anyone anything appear
area around ask away back ball bank base basic bear beat become before begin behind below best better between big bit black blue body book both
box break bring build burn buy call came care carry case cause change check child city class clear close cold come common company complete consider control
cool cost could country cover create cut dark data dead deal deep describe detail develop difference different difficult does done door down draw drive drop dry
due during each early earth easy eat else end enough enter even every example fall family far fast feel few field fight find fire first five floor follow food
force form found free friend from front full fun give glad good great green group grow hand hard have head hear heart heat heavy help high history
hold home hope house human important include increase inside interest issue just keep kind know large last later learn leave less life light like line
list live local long look love low make many mean meet might mind miss model move much must name national need never next nice night note nothing
notice number object often oil open other outside own part pay people period picture place plan play point poor possible power press probably problem provide
public question quickly quite rather reach ready real reason receive remember result return right river road room run same school second seem seen send
short show side since size small social some something sometimes sound south space special start state stay step still stop student study subject such sure
system table take talk tell than their them then there these they thing think those though thought three through time together today toward town true
turn under until used usually very view voice want water way week well went what when where while white who why wide will window with within
without woman work world would write year young your
"""

def make_fallback(output: str) -> None:
    words = sorted(set(w.strip() for w in FALLBACK_WORDS.split() if len(w.strip()) > 2))
    with open(output, "w", encoding="utf-8") as fh:
        fh.write("\n".join(words))
    print(f"[make_wordlist] Wrote {len(words):,} fallback words → '{output}'")


def download(url: str, output: str) -> bool:
    try:
        print(f"[make_wordlist] Downloading from {url} …")
        urllib.request.urlretrieve(url, output)
        lines = sum(1 for _ in open(output, encoding="utf-8"))
        print(f"[make_wordlist] Downloaded {lines:,} words → '{output}'")
        return True
    except Exception as exc:
        print(f"[make_wordlist] Download failed: {exc}")
        return False


if __name__ == "__main__":
    if os.path.exists(OUTPUT):
        lines = sum(1 for _ in open(OUTPUT, encoding="utf-8"))
        print(f"[make_wordlist] '{OUTPUT}' already exists ({lines:,} words). Skipping.")
    else:
        if not download(URL, OUTPUT):
            print("[make_wordlist] Using built-in fallback word list.")
            make_fallback(OUTPUT)

