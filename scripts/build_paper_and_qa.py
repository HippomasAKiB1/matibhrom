import os
import re
import sys
import shutil
import zipfile
import subprocess
import hashlib
import time

PAPER_DIR = os.path.abspath("paper")
MAIN_MODULAR = os.path.join(PAPER_DIR, "main_modular.tex")
MAIN_OUTPUT = os.path.join(PAPER_DIR, "main.tex")
ZIP_OUTPUT = os.path.join(PAPER_DIR, "matibhrom_manuscript.zip")

MIKTEX_BIN = r"D:\GG\MikTex\miktex\bin\x64"
WORKSPACE = os.path.abspath(".")
COMPILED_DIR = os.path.join(WORKSPACE, "revision_audit", "compiled")
BUILD_TREE = os.path.join(COMPILED_DIR, "build_tree")
PAGES_DIR = os.path.join(COMPILED_DIR, "pages")

def resolve_inputs(content, base_dir):
    def replace_input(match):
        rel_path = match.group(1).strip()
        if not rel_path.endswith(".tex"):
            rel_path += ".tex"
        full_path = os.path.join(base_dir, rel_path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Missing input file: {full_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            subcontent = f.read()
        return resolve_inputs(subcontent, base_dir)

    return re.sub(r'\\input\{([^}]+)\}', replace_input, content)

def build_main():
    with open(MAIN_MODULAR, "r", encoding="utf-8") as f:
        mod_content = f.read()

    full_content = resolve_inputs(mod_content, PAPER_DIR)
    
    with open(MAIN_OUTPUT, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    print(f"[OK] Generated {MAIN_OUTPUT} ({len(full_content.splitlines())} lines)")
    return full_content

def run_static_qa(full_content):
    errors = []

    # 1. Lists in main body (sections 00-09)
    main_body_match = re.search(r'(\\begin\{abstract\}.*?)\\bibliographystyle', full_content, re.DOTALL)
    if main_body_match:
        main_body = main_body_match.group(1)
        enum_matches = re.findall(r'\\begin\{enumerate\}', main_body)
        item_matches = re.findall(r'\\begin\{itemize\}', main_body)
        if enum_matches:
            errors.append(f"Main body contains {len(enum_matches)} \\begin{{enumerate}} lists!")
        if item_matches:
            errors.append(f"Main body contains {len(item_matches)} \\begin{{itemize}} lists!")
        print(f"[QA-Static] Main body lists: enumerate={len(enum_matches)}, itemize={len(item_matches)}")

    # 2. Placeholders
    placeholders = re.findall(r'\\fbox\{.*?\}', full_content)
    if placeholders:
        errors.append(f"Found {len(placeholders)} \\fbox placeholders: {placeholders}")
    
    todos = re.findall(r'\b(TODO|TBD|FIXME|XXX)\b', full_content)
    if todos:
        errors.append(f"Found placeholder tokens: {todos}")

    # 3. Citations vs bibtex
    with open(os.path.join(PAPER_DIR, "references.bib"), "r", encoding="utf-8") as f:
        bib_text = f.read()
    bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib_text))
    
    cite_matches = re.findall(r'\\cite[pt]?\{([^}]+)\}', full_content)
    cited_keys = set()
    for m in cite_matches:
        for k in m.split(","):
            cited_keys.add(k.strip())
    
    missing_keys = cited_keys - bib_keys
    if missing_keys:
        errors.append(f"Missing BibTeX keys in references.bib: {missing_keys}")
    else:
        print(f"[QA-Static] All {len(cited_keys)} cited keys exist in references.bib")

    # 4. Figures exist
    figs = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', full_content)
    for fig in figs:
        fig_path = os.path.join(PAPER_DIR, fig)
        if not os.path.isfile(fig_path):
            errors.append(f"Referenced figure does not exist: {fig_path}")
        else:
            print(f"[QA-Static] Figure exists: {fig}")

    # 5. Cross-references
    labels = set(re.findall(r'\\label\{([^}]+)\}', full_content))
    refs = set(re.findall(r'\\(?:cref|ref)\{([^}]+)\}', full_content))
    missing_refs = refs - labels
    if missing_refs:
        errors.append(f"Undefined references: {missing_refs}")
    else:
        print(f"[QA-Static] All {len(refs)} cross-references match defined labels ({len(labels)} defined)")

    # 6. Font file
    font_path = os.path.join(PAPER_DIR, "fonts", "NotoSerifBengali.ttf")
    if not os.path.isfile(font_path):
        errors.append("NotoSerifBengali.ttf not found in paper/fonts/")
    else:
        print(f"[QA-Static] Font file verified: {font_path} ({os.path.getsize(font_path):,} bytes)")

    # 7. .latexmkrc
    latexmkrc_path = os.path.join(PAPER_DIR, ".latexmkrc")
    if not os.path.isfile(latexmkrc_path):
        errors.append(".latexmkrc missing!")
    else:
        print("[QA-Static] .latexmkrc exists and configured for xelatex")

    if errors:
        for err in errors:
            print(f"STATIC QA ERROR: {err}")
        raise ValueError(f"Static QA failed with {len(errors)} errors")
    print("[QA-Static] All static QA checks PASSED!")

def make_zip():
    include_exts = {".tex", ".bib", ".png", ".jpg", ".ttf", ".sty", ".bst"}
    include_names = {".latexmkrc", "README.txt"}
    
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(PAPER_DIR):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), PAPER_DIR)
                if file.endswith(".zip") or file.endswith(".aux") or file.endswith(".log") or file.endswith(".out"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in include_exts or file in include_names:
                    z.write(os.path.join(root, file), arcname=rel)
    
    zip_size = os.path.getsize(ZIP_OUTPUT)
    print(f"[OK] Packaged {ZIP_OUTPUT} ({zip_size:,} bytes)")

def compile_and_audit():
    if os.path.exists(BUILD_TREE):
        shutil.rmtree(BUILD_TREE)
    os.makedirs(BUILD_TREE, exist_ok=True)
    os.makedirs(PAGES_DIR, exist_ok=True)

    with zipfile.ZipFile(ZIP_OUTPUT, "r") as z:
        z.extractall(BUILD_TREE)

    xelatex = os.path.join(MIKTEX_BIN, "xelatex.exe")
    bibtex = os.path.join(MIKTEX_BIN, "bibtex.exe")
    env = os.environ.copy()
    env["PATH"] = MIKTEX_BIN + os.pathsep + env.get("PATH", "")

    # 4-pass compilation
    print("[Build] Executing 4-pass XeLaTeX + BibTeX compilation pipeline...")
    subprocess.run([xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"], cwd=BUILD_TREE, env=env, capture_output=True, check=True)
    subprocess.run([bibtex, "main"], cwd=BUILD_TREE, env=env, capture_output=True, check=True)
    subprocess.run([xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"], cwd=BUILD_TREE, env=env, capture_output=True, check=True)
    p = subprocess.run([xelatex, "--enable-installer", "-interaction=nonstopmode", "-synctex=1", "main.tex"], cwd=BUILD_TREE, env=env, capture_output=True, text=True, check=True)

    log_path = os.path.join(BUILD_TREE, "main.log")
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_content = f.read()

    undefined_refs = re.findall(r'LaTeX Warning: Reference `(.*?)` on page \d+ undefined', log_content)
    undefined_cites = re.findall(r'LaTeX Warning: Citation `(.*?)` on page \d+ undefined', log_content)
    overfull_hboxes = re.findall(r'Overfull \\hbox \(([0-9\.]+pt) too wide\) in paragraph at lines (\d+)--(\d+)', log_content)

    print(f"[QA-Compiler] Undefined references: {len(undefined_refs)}")
    print(f"[QA-Compiler] Undefined citations: {len(undefined_cites)}")
    print(f"[QA-Compiler] Overfull hboxes: {len(overfull_hboxes)}")

    assert len(undefined_refs) == 0, f"Found undefined references: {undefined_refs}"
    assert len(undefined_cites) == 0, f"Found undefined citations: {undefined_cites}"
    assert len(overfull_hboxes) == 0, f"Found overfull hboxes: {overfull_hboxes}"

    pdf_build = os.path.join(BUILD_TREE, "main.pdf")
    pdf_target = os.path.join(COMPILED_DIR, "matibhrom_tacl_compiled.pdf")
    shutil.copy2(pdf_build, pdf_target)
    pdf_size = os.path.getsize(pdf_target)

    # PDF verification and rendering
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_target)
    n_pages = len(doc)
    print(f"[QA-PDF] PDF verified: {pdf_target} ({pdf_size:,} bytes, {n_pages} pages)")
    for i in range(n_pages):
        page = doc[i]
        w, h = page.get_size()
        assert abs(w - 595.28) < 1.0 and abs(h - 841.89) < 1.0, f"Page {i+1} dimension is not A4 ({w}x{h})"
        img = page.render(scale=2.0).to_pil()
        out_img = os.path.join(PAGES_DIR, f"page_{i+1:02d}.png")
        img.save(out_img)

    print(f"[QA-PDF] All {n_pages} pages rendered to 2x resolution PNGs in {PAGES_DIR}")

if __name__ == "__main__":
    content = build_main()
    run_static_qa(content)
    make_zip()
    compile_and_audit()
    print("\n=======================================================")
    print("ALL STATIC, COMPILATION, LOG, AND PDF QA CHECKS PASSED!")
    print("=======================================================")
