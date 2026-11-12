"""CSV runner for the browser video recorder."""
import csv
import os
from pathlib import Path 
import qscript

INPUT_CSV = "input.csv"
VIDEO_FOLDER = "./video"


def main():
    qscript.PATH_TO_VIDEO_FOLDER = VIDEO_FOLDER
    csv_path = Path(INPUT_CSV)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Input CSV not found: {csv_path.resolve()}")
    required_columns = [
        "URL", "Company Name", "Language", "Country",
        "Postcode", "City", "Street", "HouseNo",
    ]
   
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header.")
        missing = [column for column in required_columns if column not in reader.fieldnames]
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(missing))

        rows_processed = 0
        for row_number, row in enumerate(reader, start=2):
            values = [row.get(column, "") or "" for column in required_columns]
            print(f"[INFO] Processing CSV row {row_number}: {values[1]}")
            result = qscript.CaptureVideo_Magento(*values)
            rows_processed += 1
            if result:
                print(f"[OK] Video saved: {result}")
            else:
                print(f"[FAILED] No video created for CSV row {row_number}.")

        print(f"[DONE] Processed {rows_processed} CSV row(s).")


if __name__ == "__main__":
    main()
