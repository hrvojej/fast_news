"""
Fix relative paths in all article HTML files after directory restructure.
Articles were generated with flat paths (../static) but are now in subdirectories.
This script:
1. Fixes relative_static_path, relative_root_path, relative_categories_path
2. Injects proper header categories into the nav
"""
import os
import re
import sys
from pathlib import Path

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'web', 'articles')
CATEGORIES_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'web', 'categories')

# Build header categories from existing category files
category_files = [f for f in os.listdir(CATEGORIES_DIR) if f.startswith("category_") and f.endswith(".html")]
header_categories = []
for f in sorted(category_files):
    slug = f.replace("category_", "").replace(".html", "")
    if slug.lower() in ("espanol", "uncategorized"):
        continue
    display_name = "NY" if slug.lower() == "nyregion" else slug.title()
    header_categories.append({"slug": slug, "name": display_name})

# Build nav HTML for categories
def build_nav_li_items():
    items = []
    for cat in header_categories:
        items.append(f'          <li>\n            <a href="/categories/category_{cat["slug"]}.html">{cat["name"]}</a>\n          </li>')
    return "\n".join(items)

nav_items_html = build_nav_li_items()

fixed = 0
errors = 0

for root, dirs, files in os.walk(ARTICLES_DIR):
    for fname in files:
        if not fname.endswith('.html'):
            continue
        filepath = os.path.join(root, fname)
        rel_path = os.path.relpath(filepath, ARTICLES_DIR).replace("\\", "/")
        depth = rel_path.count("/")  # 0 = flat, 1 = articles/cat/file, 2 = articles/cat/sub/file
        
        # Correct paths: from articles/[cat/[sub/]]file.html, need to go up (depth+1) to reach web/
        prefix = "../" * (depth + 1)
        correct_static = prefix + "static"
        correct_root = prefix.rstrip("/") if prefix else "."
        correct_categories = prefix + "categories"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # Fix static paths: ../static -> ../../static etc.
            # Be careful not to double-fix. Match patterns like href="../static or src="../static
            content = re.sub(
                r'(href|src)="(\.\./)+static/',
                f'\\1="{correct_static}/',
                content
            )
            # Fix the debug line: <p>Relative static path: ../static</p>
            content = re.sub(
                r'Relative static path: (\.\./)+static',
                f'Relative static path: {correct_static}',
                content
            )
            # Fix manifest href
            content = re.sub(
                r'href="(\.\./)+static/',
                f'href="{correct_static}/',
                content
            )
            
            # Fix root paths (for Home, About links) - currently href="/homepage.html" which is absolute, should be fine
            # But also fix relative patterns like href="../homepage.html" if any
            content = re.sub(
                r'href="(\.\./)+homepage\.html"',
                f'href="{correct_root}/homepage.html"',
                content
            )
            content = re.sub(
                r'href="(\.\./)+about\.html"',
                f'href="{correct_root}/about.html"',
                content
            )
            
            # Fix header: inject category nav items into the empty nav
            # Pattern: between <ul class="nav-left"> ... Home li ... empty space ... </ul>
            # We need to find the nav-left ul and inject categories after the Home li
            nav_left_pattern = re.compile(
                r'(<ul class="nav-left">\s*<li>\s*<a href="[^"]*">Home</a>\s*</li>)(.*?)(</ul>\s*<!-- Right-aligned)',
                re.DOTALL
            )
            
            def inject_categories(m):
                return m.group(1) + "\n" + nav_items_html + "\n      " + m.group(3)
            
            content = nav_left_pattern.sub(inject_categories, content)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  FIXED: {rel_path} (depth={depth}, static={correct_static})")
                fixed += 1
            else:
                print(f"  SKIP (no changes): {rel_path}")
                
        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")
            errors += 1

print(f"\nDone: {fixed} fixed, {errors} errors")
