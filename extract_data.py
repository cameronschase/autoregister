"""
@author Cameron Chase
May 18, 2026
cameron.chase@gmail.com

Extract DDTC Congressional Notification letters from Federal Register pages into a structured spreadsheet with one row per letter.

Output columns:
    Notification date, Notification number, Section, Notification type, Amount, Description

Common User Usage:
    Use the .exe file provided

Advanced User Usage:
    python extract_data.py <url1> [url2 ...]
or edit URLS list at the bottom.
"""

import os
import re
import sys
import time
from datetime import datetime
 
import requests
from bs4 import BeautifulSoup
import pandas as pd
 
 
DATE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}$"
)
 
# Sentence that starts every letter's body:
#   "Pursuant to <SECTION>, please find enclosed a certification of a
#    <NOTIFICATION TYPE> in the <AMOUNT>."
# It varies slightly ("a certificate" vs "a certification", "and" vs ","
# between sections, the amount sometimes uses [$] etc), so we keep it loose.
PURSUANT_RE = re.compile(
    r"Pursuant to\s+(?P<section>.+?)\s*,\s*"
    r"please find enclosed\s+(?:a certification|a certificate)\s+of\s+a\s+"
    r"(?P<ntype>.+?)\s+in the\s+"
    r"(?P<amount>amount of[^.]+?)\.",
    re.IGNORECASE | re.DOTALL,
)
 
DDTC_RE = re.compile(r"DDTC\s*(\d+[-–]\d+)")
 
 
def parse_page_html(html: str, source_url: str) -> list[dict]:
    """Parse the HTML of a single Federal Register notice page."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("div.body") or soup
 
    # Pull every heading and paragraph in document order.
    blocks = []
    for element in body.find_all(["h2", "h3", "h4", "p"]):
        text = element.get_text(" ", strip=True)
        if text:
            blocks.append((element.name, text))
 
    return parse_blocks(blocks, source_url)
 
 
def parse_blocks(blocks: list[tuple[str, str]], source_url: str) -> list[dict]:
    """Walk the (tag, text) blocks and emit one row per letter."""
    rows = []
    current = None  # the letter currently being built
 
    for tag, text in blocks:
        # A date heading begins a new letter
        if tag == "h2" and DATE_RE.match(text):
            if current:
                rows.append(finalize(current))
            current = {"source_url": source_url, "date": text,
                       "ddtc": "", "pursuant_text": "", "description": ""}
            continue
 
        # A "Congressional Notification Transmittal Letter" heading WITHOUT a
        # preceding date heading still starts a new letter — we just leave the
        # date blank for the user to fill in manually.
        if (tag == "h2"
                and text.startswith("Congressional Notification Transmittal Letter")
                and current is not None
                and current["ddtc"]):  # only after we've finished the previous row
            rows.append(finalize(current))
            current = {"source_url": source_url, "date": "",
                       "ddtc": "", "pursuant_text": "", "description": ""}
            continue
        if current is None:
            continue
        # DDTC number (might be in same line as "Department Notification Number" or alone)
        if not current["ddtc"]:
            m = DDTC_RE.search(text)
            if m:
                current["ddtc"] = m.group(1)
                # don't `continue` — same paragraph might also start "Pursuant to"

        # The Pursuant-to paragraph
        if not current["pursuant_text"] and text.startswith("Pursuant to"):
            current["pursuant_text"] = text
            continue

        # The transaction-description paragraph (first one we hit after Pursuant)
        if (current["pursuant_text"]
                and not current["description"]
                and text.startswith("The transaction")):
            current["description"] = text
            continue
    if current:
        rows.append(finalize(current))
    return rows
 
 
def finalize(r: dict) -> dict:
    """Turn the in-progress dict into the final flat row."""
    # Date -> real date object, or None if missing (gives a blank cell in Excel)
    if not r["date"]:
        d = None
    else:
        try:
            d = datetime.strptime(r["date"], "%B %d, %Y").date()
        except ValueError:
            d = r["date"]
 
    # Parse Pursuant-to sentence into three fields
    section = ntype = amount = ""
    m = PURSUANT_RE.search(r["pursuant_text"])
    if m:
        section = m.group("section").strip()
        ntype = m.group("ntype").strip()
        amount = m.group("amount").strip()
 
    return {
        "Notification date": d,
        "Notification number": r["ddtc"],
        "Section": section,
        "Notification type": ntype,
        "Amount": amount,
        "Description": r["description"],
        "Source URL": r["source_url"],
    }
 
def fetch_and_extract(url: str) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return parse_page_html(resp.text, url)
 
 
def prompt_for_urls() -> list[str]:
    """Ask the user to paste URLs.  Accepts one or many, separated by any
    whitespace (spaces, tabs, newlines).  Finish with a blank line."""
    print("Paste one or more Federal Register URLs below.")
    print("They can be on one line or many.  Press Enter on an empty line when done.\n")
 
    pasted_lines = []
    while True:
        try:
            line = input()
        except EOFError:  # Ctrl-D / Ctrl-Z also ends input
            break
        if line.strip() == "":
            if pasted_lines:  # blank line after content = done
                break
            else:  # blank line before any content = keep waiting
                continue
        pasted_lines.append(line)
 
    # Split everything on whitespace and keep only http(s) URLs
    raw_tokens = " ".join(pasted_lines).split()
    urls = [t for t in raw_tokens if t.startswith("http://") or t.startswith("https://")]
    return urls
 
 
def main(urls):
    if not urls:
        print("No URLs provided.  Exiting.")
        return
 
    print(f"\nProcessing {len(urls)} URL(s)...\n")
    all_rows = []
    for url in urls:
        print(f"Fetching: {url}")
        try:
            rows = fetch_and_extract(url)
            print(f"  -> {len(rows)} letters")
            all_rows.extend(rows)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1)  # be polite to the server
 
    if not all_rows:
        print("\nNo letters were extracted.")
        return
 
    new_df = pd.DataFrame(all_rows)
    out = "ddtc_extracted.xlsx"
 
    # If the file already exists, merge with what's there.
    # "Replace on match" = if a Notification number appears in both the
    # existing file and the new data, the new row wins per-cell, BUT
    # blank cells in the new row fall back to the old row's value.
    # That way manually-entered data (e.g. a date you filled in) is
    # preserved across reruns.
    if os.path.exists(out):
        try:
            existing_df = pd.read_excel(out)
        except PermissionError:
            print(f"\nERROR: Can't read {out} — is it open in Excel?")
            print("Close the file and run the program again.")
            return
        except Exception as e:
            print(f"\nWARNING: Could not read existing {out} ({e}).")
            print("The new rows will be written, but old rows may be lost.")
            existing_df = pd.DataFrame()
 
        if not existing_df.empty and "Notification number" in existing_df.columns:
            # Build a lookup of existing rows by notification number
            existing_by_num = {
                row["Notification number"]: row.to_dict()
                for _, row in existing_df.iterrows()
            }
 
            # For each row in the new data: if its number matches an existing
            # row, fill in any blank cells from the existing row.
            merged_rows = []
            replaced = 0
            for _, new_row in new_df.iterrows():
                num = new_row["Notification number"]
                if num in existing_by_num:
                    replaced += 1
                    old_row = existing_by_num[num]
                    merged = dict(new_row)
                    for col, new_val in merged.items():
                        if _is_blank(new_val) and col in old_row \
                                and not _is_blank(old_row[col]):
                            merged[col] = old_row[col]
                    merged_rows.append(merged)
                else:
                    merged_rows.append(dict(new_row))
 
            # Keep existing rows that aren't being replaced
            new_numbers = set(new_df["Notification number"])
            untouched = existing_df[
                ~existing_df["Notification number"].isin(new_numbers)
            ]
            combined = pd.concat(
                [untouched, pd.DataFrame(merged_rows)],
                ignore_index=True,
            )
            added = len(new_df) - replaced
        else:
            combined = new_df
            added = len(new_df)
            replaced = 0
 
        msg = f"Added {added} new row(s)"
        if replaced:
            msg += f", updated {replaced} existing row(s)"
        msg += f". Total now: {len(combined)}."
    else:
        combined = new_df
        msg = f"Created new file with {len(combined)} row(s)."
 
    try:
        combined.to_excel(out, index=False)
    except PermissionError:
        print(f"\nERROR: Can't write to {out} — is it open in Excel?")
        print("Close the file and run the program again.")
        return
 
    print(f"\nDone. {msg}")
    print(f"Output: {out}")
 
 
def _is_blank(v) -> bool:
    """True if a value is empty / NaN / None / whitespace-only string."""
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return False
    print(f"Output: {out}")
 
 
def _pause_before_exit():
    """Keep the console window open when run as a standalone .exe so the
    user can see the results.  Does nothing if no console is attached."""
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
 
 
if __name__ == "__main__":
    # URLs may also be passed on the command line; if none given, prompt.
    cli_urls = sys.argv[1:]
    try:
        if cli_urls:
            main(cli_urls)
        else:
            main(prompt_for_urls())
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    _pause_before_exit()