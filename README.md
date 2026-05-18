# DDTC Notification Extractor

Pulls Congressional Notification letters from [federalregister.gov](https://www.federalregister.gov) pages published by the State Department's Directorate of Defense Trade Controls (DDTC) and saves them as a structured spreadsheet — one row per letter.

## What you get

Each letter on a Federal Register page becomes one row in `ddtc_extracted.xlsx` with these columns:

| Column | Source | Example |
|---|---|---|
| Notification date | Date heading above the letter | 7/2/2025 |
| Notification number | The "Department Notification Number" line | 25-039 |
| Section | The AECA section cited | Section 36(c) of the Arms Export Control Act |
| Notification type | What's being proposed | proposed license amendment for the export of defense articles, including technical data, and defense services |
| Amount | The dollar threshold | amount of $100,000,000 or more |
| Description | The "The transaction involves..." paragraph | The transaction contained in... |
| Source URL | The Federal Register page the row came from | https://www.federalregister.gov/... |

## Files in this folder

- `extract_data.py` — the Python script that does the work
- `compile.bat` — One-time helper batch script that builds a standalone `extract_data.exe` (no Python install needed on target machines)
- `README.md` — this file

## How to use it

There are two ways to run it. Pick whichever fits.

### Option A: Run the Python script directly

1. Make sure Python 3.9+ is installed and on PATH.
2. Install the required packages once:
   ```
   pip install requests beautifulsoup4 pandas openpyxl
   ```
3. From this folder, run:
   ```
   python extract_ddtc.py
   ```
4. Paste one or more Federal Register URLs (separated by spaces or newlines), then press Enter on a blank line.
5. The results land in `ddtc_extracted.xlsx` next to the script.

You can also pass URLs as arguments and skip the prompt:
```
python extract_ddtc.py https://www.federalregister.gov/documents/... https://www.federalregister.gov/documents/...
```

### Option B: Build a standalone .exe (Windows, no Python needed afterward)

1. Download the latest release.
2. Run the `extract_data.exe`

## How append-and-merge works

Each run **adds new rows** to `ddtc_extracted.xlsx`. If a Notification number in the new run is already in the spreadsheet, the row gets **merged**:

- **New value wins** when the new run has data in a cell.
- **Existing value is kept** when the new run's cell is blank.

This means manually-entered data survives reruns. Example: if a letter on the page has no date heading, the extracted row will have a blank date. Type the date in by hand. On the next run the script will see the new row has a blank date, leave your value alone, and keep going.

Rows whose Notification numbers aren't in the new run are left completely untouched. You can also add your own columns (e.g. "Notes", "Status") and they'll survive reruns since the script only touches the columns it writes.

A summary at the end of each run tells you what changed: *"Added 12 new row(s), updated 2 existing row(s). Total now: 63."*

## Edge cases worth knowing

**Letters without a date heading.** Most letters on a page have a `<h2>` date heading above them, but occasionally one doesn't (it visually inherits the date from the previous letter). The script still extracts these — the Notification number, Section, Type, Amount, and Description all populate — but the date cell is left blank for you to fill in by hand. The dedup logic above ensures your manual entry survives future reruns.

**Excel file locks.** If `data_extracted.xlsx` is open in Excel when you run the script, Windows won't let it read or write the file. You'll see a clear message: *"Can't write to data_extracted.xlsx — is it open in Excel?"* Close the file and run again.

**Duplicate key.** Rows are matched on Notification number alone. If two different DDTC numbers are the same, the newer one would overwrite the other. You will get a message in the summary of this behavior.

**Rate limiting.** The script pauses 1 second between URLs as to not stress the government servers that host the notifications for the Federal Register. For best results, don't attempt to extract data from more than 50 notifications in a single instance.

**Page structure changes.** The parser depends on Federal Register pages following their current layout (date in `<h2>`, "Pursuant to..." sentence with predictable phrasing, etc.).

## Troubleshooting

**Antivirus flags the .exe** — Right-click → Properties → "Unblock" fixes it temporarily. Otherwise, may have create a rule exception in Windows Defender.

**A row's Section / Type / Amount columns are blank** — the "Pursuant to..." sentence on that letter didn't match the expected pattern. This means the data will have to be entered manually since the notification doesn't for the expected format.
