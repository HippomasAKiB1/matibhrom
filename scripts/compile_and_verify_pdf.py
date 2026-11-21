import os
import sys
import shutil
import zipfile
import subprocess
import time

MIKTEX_BIN = r"D:\GG\MikTex\miktex\bin\x64"
WORKSPACE = os.path.abspath(".")
COMPILED_DIR = os.path.join(WORKSPACE, "revision_audit", "compiled")
BUILD_TREE = os.path.join(COMPILED_DIR, "build_tree")
PAGES_DIR = os.path.join(COMPILED_DIR, "pages")
ZIP_PATH = os.path.join(WORKSPACE, "paper", "matibhrom_manuscript.zip")

def prepare_clean_tree():
    if os.path.exists(BUILD_TREE):
        shutil.rmtree(BUILD_TREE)
    os.makedirs(BUILD_TREE, exist_ok=True)
    os.makedirs(PAGES_DIR, exist_ok=True)

    print(f"Extracting {ZIP_PATH} to {BUILD_TREE}...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(BUILD_TREE)
    print(f"Extracted {len(os.listdir(BUILD_TREE))} items to clean build tree.")

def run_cmd(args, cwd, log_file):
    env = os.environ.copy()
    env["PATH"] = MIKTEX_BIN + os.pathsep + env.get("PATH", "")
    print(f"Running: {' '.join(args)} in {cwd}")
    start = time.time()
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, errors="replace", timeout=120)
    duration = time.time() - start
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"COMMAND: {' '.join(args)}\n")
        f.write(f"EXIT CODE: {p.returncode}\n")
        f.write(f"DURATION: {duration:.2f}s\n\n")
        f.write("=== STDOUT ===\n")
        f.write(p.stdout)
        f.write("\n\n=== STDERR ===\n")
        f.write(p.stderr)
    print(f"Finished in {duration:.2f}s (Exit {p.returncode}). Output saved to {log_file}")
    return p.returncode, p.stdout, p.stderr

def compile_manuscript():
    xelatex = os.path.join(MIKTEX_BIN, "xelatex.exe")
    bibtex = os.path.join(MIKTEX_BIN, "bibtex.exe")

    # Pass 1: xelatex
    rc1, out1, err1 = run_cmd(
        [xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"],
        cwd=BUILD_TREE,
        log_file=os.path.join(COMPILED_DIR, "pass1_xelatex.log")
    )

    # Pass 2: bibtex
    rc2, out2, err2 = run_cmd(
        [bibtex, "main"],
        cwd=BUILD_TREE,
        log_file=os.path.join(COMPILED_DIR, "pass2_bibtex.log")
    )

    # Pass 3: xelatex
    rc3, out3, err3 = run_cmd(
        [xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"],
        cwd=BUILD_TREE,
        log_file=os.path.join(COMPILED_DIR, "pass3_xelatex.log")
    )

    # Pass 4: xelatex
    rc4, out4, err4 = run_cmd(
        [xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"],
        cwd=BUILD_TREE,
        log_file=os.path.join(COMPILED_DIR, "pass4_xelatex.log")
    )

    pdf_path = os.path.join(BUILD_TREE, "main.pdf")
    if os.path.isfile(pdf_path):
        target_pdf = os.path.join(COMPILED_DIR, "matibhrom_tacl_compiled.pdf")
        shutil.copy2(pdf_path, target_pdf)
        size = os.path.getsize(target_pdf)
        print(f"[SUCCESS] PDF Generated: {target_pdf} ({size:,} bytes)")
        return target_pdf
    else:
        print("[FAIL] PDF was not generated!")
        return None

def render_pages(pdf_path):
    import pypdfium2 as pdfium
    print(f"Rendering pages of {pdf_path}...")
    doc = pdfium.PdfDocument(pdf_path)
    n_pages = len(doc)
    print(f"Total pages: {n_pages}")
    
    rendered_images = []
    for i in range(n_pages):
        page = doc[i]
        width, height = page.get_size()
        image = page.render(scale=2.0).to_pil()
        out_img = os.path.join(PAGES_DIR, f"page_{i+1:02d}.png")
        image.save(out_img)
        rendered_images.append((out_img, width, height))
        print(f"  Saved page {i+1:02d} -> {out_img} ({width:.1f} x {height:.1f} pt)")
    
    return n_pages, rendered_images

if __name__ == "__main__":
    prepare_clean_tree()
    pdf = compile_manuscript()
    if pdf:
        n, imgs = render_pages(pdf)
        print(f"\n[DONE] Successfully compiled {n} pages and rendered all page images!")
    else:
        sys.exit(1)
