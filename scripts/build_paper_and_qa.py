import os
import re
import zipfile

PAPER_DIR = os.path.abspath("paper")
MAIN_MODULAR = os.path.join(PAPER_DIR, "main_modular.tex")
MAIN_OUTPUT = os.path.join(PAPER_DIR, "main.tex")
ZIP_OUTPUT = os.path.join(PAPER_DIR, "matibhrom_manuscript.zip")

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
        # Recursively resolve any nested inputs
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

def run_qa(full_content):
    errors = []
    warnings = []

    # 1. Check for lists in main body (sections 00-09)
    # Extract text between \input{sections/00_abstract.tex} equivalent and \appendix / references
    main_body_match = re.search(r'(\\begin\{abstract\}.*?)\\bibliographystyle', full_content, re.DOTALL)
    if main_body_match:
        main_body = main_body_match.group(1)
        enum_matches = re.findall(r'\\begin\{enumerate\}', main_body)
        item_matches = re.findall(r'\\begin\{itemize\}', main_body)
        if enum_matches:
            errors.append(f"Main body contains {len(enum_matches)} \\begin{{enumerate}} lists!")
        if item_matches:
            errors.append(f"Main body contains {len(item_matches)} \\begin{{itemize}} lists!")
        print(f"[QA] Main body lists: enumerate={len(enum_matches)}, itemize={len(item_matches)}")

    # 2. Check for placeholders
    placeholders = re.findall(r'\\fbox\{.*?\}', full_content)
    if placeholders:
        errors.append(f"Found {len(placeholders)} \\fbox placeholders: {placeholders}")
    
    todos = re.findall(r'\b(TODO|TBD|FIXME|XXX)\b', full_content)
    if todos:
        errors.append(f"Found placeholder tokens: {todos}")

    # 3. Check citations
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
        print(f"[QA] All {len(cited_keys)} cited keys exist in references.bib")

    # 4. Check included figures
    figs = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', full_content)
    for fig in figs:
        fig_path = os.path.join(PAPER_DIR, fig)
        if not os.path.isfile(fig_path):
            errors.append(f"Referenced figure does not exist: {fig_path}")
        else:
            print(f"[QA] Figure exists: {fig}")

    # 5. Check labels and refs
    labels = set(re.findall(r'\\label\{([^}]+)\}', full_content))
    refs = set(re.findall(r'\\(?:cref|ref)\{([^}]+)\}', full_content))
    missing_refs = refs - labels
    if missing_refs:
        errors.append(f"Undefined references: {missing_refs}")
    else:
        print(f"[QA] All {len(refs)} cross-references match defined labels ({len(labels)} labels defined)")

    # 6. Check font file
    font_path = os.path.join(PAPER_DIR, "fonts", "NotoSerifBengali.ttf")
    if not os.path.isfile(font_path):
        errors.append("NotoSerifBengali.ttf not found in paper/fonts/")
    else:
        print(f"[QA] Font file verified: {font_path} ({os.path.getsize(font_path)} bytes)")

    # 7. Check .latexmkrc
    latexmkrc_path = os.path.join(PAPER_DIR, ".latexmkrc")
    if not os.path.isfile(latexmkrc_path):
        errors.append(".latexmkrc missing!")
    else:
        print("[QA] .latexmkrc exists and configured for xelatex")

    if errors:
        print("\n--- QA ERRORS ---")
        for err in errors:
            print(f"ERROR: {err}")
        raise ValueError(f"QA Failed with {len(errors)} errors")
    else:
        print("\n[SUCCESS] ALL QA CHECKS PASSED PERFECTLY!")

def make_zip():
    # Files to include in zip for Overleaf
    include_exts = {".tex", ".bib", ".png", ".jpg", ".ttf", ".sty", ".bst"}
    include_names = {".latexmkrc", "README.txt"}
    
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(PAPER_DIR):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), PAPER_DIR)
                # Skip existing zip file or temp files
                if file.endswith(".zip") or file.endswith(".aux") or file.endswith(".log") or file.endswith(".out"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in include_exts or file in include_names:
                    z.write(os.path.join(root, file), arcname=rel)
                    print(f"  Added to zip: {rel}")
    
    zip_size = os.path.getsize(ZIP_OUTPUT)
    print(f"\n[OK] Packaged {ZIP_OUTPUT} ({zip_size:,} bytes)")

if __name__ == "__main__":
    content = build_main()
    run_qa(content)
    make_zip()
