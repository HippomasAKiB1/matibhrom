"""
Resumable downloader for BGE-M3 model weights.
"""
import os
import sys
import time
from pathlib import Path
import requests

TARGET_DIR = Path(r"C:\Users\AKiB\.cache\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181")
BLOBS_DIR = Path(r"C:\Users\AKiB\.cache\huggingface\hub\models--BAAI--bge-m3\blobs")
URL = "https://huggingface.co/BAAI/bge-m3/resolve/main/pytorch_model.bin"
TOTAL_SIZE = 2271145830

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    target_file = TARGET_DIR / "pytorch_model.bin"
    part_file = TARGET_DIR / "pytorch_model.bin.part"

    if target_file.exists() and target_file.stat().st_size == TOTAL_SIZE:
        print(f"Target already complete: {target_file} ({TOTAL_SIZE} bytes)")
        return

    # Adopt existing incomplete download if present
    if not part_file.exists() and BLOBS_DIR.exists():
        incompletes = list(BLOBS_DIR.glob("*.incomplete"))
        if incompletes:
            inc = incompletes[0]
            print(f"Adopting incomplete download from blobs: {inc.name} ({inc.stat().st_size} bytes)")
            import shutil
            shutil.move(str(inc), str(part_file))

    current_size = part_file.stat().st_size if part_file.exists() else 0
    print(f"Current downloaded size: {current_size / (1024*1024):.1f} MB / {TOTAL_SIZE / (1024*1024):.1f} MB")

    if current_size >= TOTAL_SIZE:
        part_file.rename(target_file)
        print("Completed!")
        return

    headers = {"Range": f"bytes={current_size}-{TOTAL_SIZE - 1}"}
    print(f"Requesting bytes {current_size} to {TOTAL_SIZE - 1}...")

    resp = requests.get(URL, headers=headers, stream=True, timeout=30)
    if resp.status_code not in (200, 206):
        print(f"Error: unexpected status code {resp.status_code}")
        sys.exit(1)

    chunk_size = 2 * 1024 * 1024  # 2MB chunks
    last_print = time.time()
    downloaded_session = 0

    with open(part_file, "ab") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            downloaded_session += len(chunk)
            total_now = current_size + downloaded_session

            if time.time() - last_print > 3:
                mb_now = total_now / (1024 * 1024)
                mb_tot = TOTAL_SIZE / (1024 * 1024)
                speed_mb = (downloaded_session / (1024 * 1024)) / (time.time() - (last_print - 3))
                pct = (total_now / TOTAL_SIZE) * 100
                print(f"  [Progress] {mb_now:.1f} / {mb_tot:.1f} MB ({pct:.1f}%)")
                last_print = time.time()

    if part_file.stat().st_size == TOTAL_SIZE:
        if target_file.exists():
            target_file.unlink()
        part_file.rename(target_file)
        print(f"Successfully downloaded and finalized: {target_file}")
    else:
        print(f"Partial download saved: {part_file.stat().st_size} bytes")

if __name__ == "__main__":
    main()
