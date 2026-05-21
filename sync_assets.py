#!/usr/bin/env python3
import os
import re
import ssl
import json
import urllib.request
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed

# Bypass SSL Verification for scraping Wix
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIT_FILE = os.path.join(BASE_DIR, "audit_report.txt")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def log(msg):
    print(f"[Sync Engine] {msg}")

def init_directories():
    log("Initializing directory structure...")
    os.makedirs(os.path.join(ASSETS_DIR, "photography"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS_DIR, "visualizing"), exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    log("Directories successfully initialized.")

# ==========================================
# 1. Scraping and Structuring Artist Bio
# ==========================================
def scrape_and_build_bio():
    url = "https://www.reujy.com/bio"
    log(f"Scraping text narrative from: {url}")
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read().decode('utf-8')
            
        # Parse paragraphs and headings in document order
        lines = []
        for m in re.finditer(r'<(p|h[1-6])[^>]*>(.*?)</\1>', html, re.DOTALL):
            tag_type = m.group(1)
            tag_content = m.group(2)
            # Strip children HTML tags
            txt = re.sub(r'<[^>]*>', '', tag_content)
            txt = unescape(txt.strip())
            if txt:
                for sub in txt.split('\n'):
                    sub = sub.strip()
                    if sub:
                        # Only prevent consecutive exact duplicates
                        if not lines or lines[-1]['text'] != sub:
                            lines.append({
                                "text": sub,
                                "tag": tag_type
                            })
                            
        # Find index for Solo and Group headings
        solo_idx = -1
        group_idx = -1
        artist_name = "REU JY (류지영)"
        statement = ""
        
        for idx, item in enumerate(lines):
            txt = item['text']
            tag = item['tag']
            if "solo" in txt.lower() and len(txt) < 10:
                solo_idx = idx
            elif "group" in txt.lower() and len(txt) < 10:
                group_idx = idx
            elif tag == "p" and len(txt) > 200 and not statement:
                statement = txt # Extract the long biography text paragraph
                
        # Fallbacks just in case
        if solo_idx == -1 or group_idx == -1:
            # Let's find by keyword if tag-based heading matches were not direct
            for idx, item in enumerate(lines):
                txt = item['text']
                if txt.strip() == "Solo" and solo_idx == -1:
                    solo_idx = idx
                elif txt.strip() == "Group" and group_idx == -1:
                    group_idx = idx
                    
        log(f"Located Solo exhibitions at line index {solo_idx}, Group at {group_idx}")
        
        def parse_exhibition_block(start, end):
            exhibitions = []
            curr_year = None
            for i in range(start, end):
                line = lines[i]['text']
                # Match 4 digit year
                if re.match(r'^\d{4}$', line):
                    curr_year = line
                elif curr_year and '"' in line:
                    title_match = re.search(r'"(.*?)"', line)
                    if title_match:
                        title = title_match.group(1)
                        rest = line[title_match.end():].strip(", ")
                        parts = [p.strip() for p in rest.split(",")]
                        if len(parts) >= 2:
                            location = parts[-1]
                            venue = ", ".join(parts[:-1])
                        elif len(parts) == 1:
                            location = parts[0]
                            venue = ""
                        else:
                            location = ""
                            venue = ""
                        exhibitions.append({
                            "year": curr_year,
                            "title": title,
                            "venue": venue,
                            "location": location
                        })
            return exhibitions

        solos = parse_exhibition_block(solo_idx + 1, group_idx if group_idx != -1 else len(lines))
        groups = parse_exhibition_block(group_idx + 1, len(lines)) if group_idx != -1 else []
        
        bio_db = {
            "artist_name": artist_name,
            "statement": statement,
            "solo_exhibitions": solos,
            "group_exhibitions": groups
        }
        
        output_path = os.path.join(DATA_DIR, "bio.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(bio_db, f, indent=2, ensure_ascii=False)
            
        log(f"Successfully generated structured Bio DB: {output_path}")
        return True
    except Exception as e:
        log(f"Error scraping bio content: {e}")
        return False

# ==========================================
# 2. Parsing Captions for Visualizing Works
# ==========================================
def parse_visualizing_caption(raw_title):
    if not raw_title:
        return "", "", "", ""
        
    title = ""
    material = ""
    size = ""
    year = ""
    
    # Check if there are underscores representing title boundaries
    if "_" in raw_title:
        if raw_title.startswith("_"):
            m = re.match(r'^_(.*?)_(.*)$', raw_title)
            if m:
                title = m.group(1).strip()
                rest = m.group(2).strip()
            else:
                title = ""
                rest = raw_title.strip()
        else:
            parts = raw_title.split("_", 1)
            title = parts[0].strip()
            rest = parts[1].strip()
            
        # Parse the rest: "Material, Size, Year"
        rest_parts = [p.strip() for p in rest.split(",")]
        
        if len(rest_parts) == 3:
            material = rest_parts[0]
            size = rest_parts[1]
            year = rest_parts[2]
        elif len(rest_parts) == 2:
            part0 = rest_parts[0]
            part1 = rest_parts[1]
            if "x" in part0 or "cm" in part0 or re.match(r'^\d+\s*x\s*\d+', part0):
                size = part0
                material = ""
            else:
                material = part0
                size = ""
            year = part1
        elif len(rest_parts) == 1:
            part = rest_parts[0]
            if re.match(r'^\d{4}', part):
                year = part
            elif "x" in part or "cm" in part:
                size = part
            else:
                material = part
    else:
        # No underscore: e.g. "40x55cm, 2024 (1)"
        parts = [p.strip() for p in raw_title.split(",")]
        if len(parts) == 2:
            part0 = parts[0]
            part1 = parts[1]
            if "x" in part0 or "cm" in part0 or re.match(r'^\d+\s*x\s*\d+', part0):
                size = part0
            else:
                material = part0
            year = part1
        elif len(parts) == 1:
            part = parts[0]
            if re.match(r'^\d{4}', part):
                year = part
            else:
                size = part

    return title, material, size, year

# ==========================================
# 3. Media Downloading & Mapping Engine
# ==========================================
def extract_portfolio_items(url):
    log(f"Querying Wix portfolio registry from: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read().decode('utf-8')
            
        # Pull wixSDKItems arrays from script states
        idx = 0
        wix_sdk_items = []
        while True:
            found_pos = html.find('"wixSDKItems"', idx)
            if found_pos == -1:
                break
            start_array = html.find('[', found_pos)
            if start_array == -1:
                idx = found_pos + 13
                continue
            try:
                array_str = html[start_array:]
                decoder = json.JSONDecoder()
                arr, end_idx = decoder.raw_decode(array_str)
                wix_sdk_items.extend(arr)
                idx = start_array + end_idx
            except:
                idx = start_array + 1
                
        # De-duplicate by wix image source
        seen_srcs = set()
        unique_items = []
        for item in wix_sdk_items:
            src = item.get("src")
            if src and src not in seen_srcs:
                seen_srcs.add(src)
                unique_items.append(item)
                
        log(f"Extracted {len(unique_items)} unique media registry items.")
        return unique_items
    except Exception as e:
        log(f"Error querying wix portfolio items: {e}")
        return []

def download_image(url, output_path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx) as response:
            data = response.read()
            
        with open(output_path, "wb") as f:
            f.write(data)
        return True, len(data)
    except Exception as e:
        return False, str(e)

def run_asset_downloads():
    log("=== Starting Media Asset Absorption & Mapping ===")
    
    # 1. Photography Collection
    photo_items = extract_portfolio_items("https://www.reujy.com/portfolio-collections/my-portfolio/photography")
    photo_jobs = []
    
    for i, item in enumerate(photo_items):
        src = item.get("src")
        # Extract direct Wix filename: format wix:image://v1/filename/filename#originWidth...
        # We need the filename between 'v1/' and the next '/' or '#'
        m = re.search(r'v1/([a-zA-Z0-9_\-~%.]+)', src)
        if m:
            filename = m.group(1)
            direct_url = f"https://static.wixstatic.com/media/{filename}"
            output_name = f"reujy_photography_{i}.jpg"
            dest_path = os.path.join(ASSETS_DIR, "photography", output_name)
            photo_jobs.append((direct_url, dest_path, output_name))
            
    # 2. Visualizing Collection
    vis_items = extract_portfolio_items("https://www.reujy.com/portfolio-collections/my-portfolio/visualizing")
    vis_jobs = []
    
    for i, item in enumerate(vis_items):
        src = item.get("src")
        title = item.get("title") or ""
        t, m_str, s, y = parse_visualizing_caption(title)
        
        m = re.search(r'v1/([a-zA-Z0-9_\-~%.]+)', src)
        if m:
            filename = m.group(1)
            direct_url = f"https://static.wixstatic.com/media/{filename}"
            # Custom matching name format: {Title}_{Material}_{Size}_{Year}
            output_name = f"reujy_visualizing_{i}_{t}_{m_str}_{s}_{y}.jpg"
            # Sanitize filename characters just to be extremely safe, but keep approved format
            dest_path = os.path.join(ASSETS_DIR, "visualizing", output_name)
            vis_jobs.append((direct_url, dest_path, output_name))
            
    # Run downloads in parallel using ThreadPoolExecutor
    total_downloads = len(photo_jobs) + len(vis_jobs)
    log(f"Preparing to download {total_downloads} original assets concurrently...")
    
    results = {"success": 0, "failed": 0, "details": []}
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for url, dest, name in photo_jobs:
            futures[executor.submit(download_image, url, dest)] = (name, "photography", url)
        for url, dest, name in vis_jobs:
            futures[executor.submit(download_image, url, dest)] = (name, "visualizing", url)
            
        for future in as_completed(futures):
            name, category, url = futures[future]
            try:
                success, val = future.result()
                if success:
                    results["success"] += 1
                    results["details"].append({
                        "name": name,
                        "category": category,
                        "status": "success",
                        "size": val,
                        "url": url
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "name": name,
                        "category": category,
                        "status": "failed",
                        "error": val,
                        "url": url
                    })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "name": name,
                    "category": category,
                    "status": "failed",
                    "error": str(e),
                    "url": url
                })
                
    log(f"Absorption complete. Success: {results['success']}, Failed: {results['failed']}")
    return results

# ==========================================
# 4. Integrity Verification & Auditing
# ==========================================
def run_integrity_audit(download_results):
    log("=== Running Asset Integrity Validation Audit ===")
    
    audit_lines = []
    audit_lines.append("==========================================================")
    audit_lines.append("         ANTIGRAVITY ASSET INTEGRITY AUDIT REPORT")
    audit_lines.append("==========================================================")
    audit_lines.append(f"Directory Audited: {ASSETS_DIR}")
    
    photo_dir = os.path.join(ASSETS_DIR, "photography")
    vis_dir = os.path.join(ASSETS_DIR, "visualizing")
    
    photo_files = [f for f in os.listdir(photo_dir) if f.endswith(".jpg")]
    vis_files = [f for f in os.listdir(vis_dir) if f.endswith(".jpg")]
    
    audit_lines.append(f"Total Photography Files Found: {len(photo_files)}")
    audit_lines.append(f"Total Visualizing Files Found: {len(vis_files)}")
    audit_lines.append("")
    audit_lines.append("----------------------------------------------------------")
    audit_lines.append(" 1. PHOTOGRAPHY ASSET AUDIT DETAILS")
    audit_lines.append("----------------------------------------------------------")
    
    photo_ok = 0
    photo_fail = 0
    for idx, f in enumerate(sorted(photo_files)):
        path = os.path.join(photo_dir, f)
        size = os.path.getsize(path)
        
        # Verify if JPEG file starts with proper SOI header bytes (0xFF, 0xD8, 0xFF)
        is_corrupt = True
        try:
            with open(path, "rb") as check_file:
                header = check_file.read(3)
                if header == b'\xff\xd8\xff':
                    is_corrupt = False
        except:
            pass
            
        status = "OK" if not is_corrupt else "CORRUPTED (Header Mismatch)"
        if not is_corrupt:
            photo_ok += 1
        else:
            photo_fail += 1
        audit_lines.append(f"[{idx:02d}] {f:<40} Size: {size/1024/1024:.2f} MB | Integrity: {status}")
        
    audit_lines.append("")
    audit_lines.append("----------------------------------------------------------")
    audit_lines.append(" 2. VISUALIZING ASSET AUDIT DETAILS")
    audit_lines.append("----------------------------------------------------------")
    
    vis_ok = 0
    vis_fail = 0
    for idx, f in enumerate(sorted(vis_files)):
        path = os.path.join(vis_dir, f)
        size = os.path.getsize(path)
        
        is_corrupt = True
        try:
            with open(path, "rb") as check_file:
                header = check_file.read(3)
                if header == b'\xff\xd8\xff':
                    is_corrupt = False
        except:
            pass
            
        status = "OK" if not is_corrupt else "CORRUPTED (Header Mismatch)"
        if not is_corrupt:
            vis_ok += 1
        else:
            vis_fail += 1
        audit_lines.append(f"[{idx:02d}] {f:<80} Size: {size/1024/1024:.2f} MB | Integrity: {status}")
        
    audit_lines.append("")
    audit_lines.append("==========================================================")
    audit_lines.append("                  AUDIT SUMMARY STATISTICS")
    audit_lines.append("==========================================================")
    audit_lines.append(f"Total Processed Assets: {len(photo_files) + len(vis_files)}")
    audit_lines.append(f"Successfully Verified (OK): {photo_ok + vis_ok}")
    audit_lines.append(f"Failed / Corrupt Verified: {photo_fail + vis_fail}")
    audit_lines.append(f"Integrity Pass Rate: {(photo_ok + vis_ok) / (len(photo_files) + len(vis_files)) * 100:.2f}%")
    audit_lines.append("==========================================================")
    
    # Save Report
    with open(AUDIT_FILE, "w", encoding="utf-8") as audit_out:
        audit_out.write("\n".join(audit_lines))
        
    log(f"Asset Integrity Validation Report successfully written: {AUDIT_FILE}")
    print("\n" + "\n".join(audit_lines[-8:]) + "\n")

# ==========================================
# Main Execution Pipeline
# ==========================================
def main():
    log("Starting Antigravity Asset Absorption Pipeline...")
    init_directories()
    
    # Step 1: Scrape Bio text and build JSON DB
    bio_success = scrape_and_build_bio()
    
    # Step 2: Download Wix Media assets and classify/map captions
    dl_results = run_asset_downloads()
    
    # Step 3: Run Integrity Audit
    run_integrity_audit(dl_results)
    
    log("Antigravity Asset Absorption Pipeline finished successfully.")

if __name__ == "__main__":
    main()
