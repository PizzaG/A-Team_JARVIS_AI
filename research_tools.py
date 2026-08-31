#!/usr/bin/env python3
"""Local-first research and web tools for Jarvis."""
from __future__ import annotations
import fnmatch, hashlib, json, mimetypes, os, re, tarfile, zipfile
from pathlib import Path
from urllib.parse import urljoin
import requests

ROOT = Path(__file__).resolve().parent
TEXT_EXTENSIONS = {'.txt','.md','.markdown','.rst','.log','.csv','.tsv','.json','.jsonl','.xml','.yaml','.yml','.ini','.cfg','.conf','.properties','.toml','.py','.sh','.bash','.zsh','.fish','.js','.jsx','.ts','.tsx','.java','.kt','.kts','.c','.h','.cc','.cpp','.hpp','.mk','.bp','.gradle','.html','.htm','.css','.scss','.sql','.patch','.diff','.service','.rc','.prop','.xml','.cmake','.inc','.proto','.go','.rs','.rb','.php','.lua','.swift'}
SKIP_DIRS = {'.git','venv','.venv','__pycache__','node_modules','.cache','.mypy_cache','.pytest_cache'}
MAX_READ_BYTES = 4 * 1024 * 1024
MAX_SEARCH_BYTES = 8 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
TIMEOUT = 30

class ResearchError(Exception): pass

def set_root(value: str | None = None) -> Path:
    global ROOT
    if value:
        p = Path(value).expanduser()
        ROOT = (p if p.is_absolute() else ROOT / p).resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    return ROOT

def root_path() -> Path: return ROOT.resolve()

def safe_path(relative: str) -> Path:
    base = ROOT.resolve(); p = Path(relative).expanduser()
    candidate = (p if p.is_absolute() else base / p).resolve()
    try: candidate.relative_to(base)
    except ValueError: raise ResearchError(f"Path is outside the research root: {relative}")
    return candidate

def _iter_files(base=None):
    base = base or ROOT
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for name in filenames:
            p=Path(dirpath)/name
            try:
                if not p.is_symlink() and p.is_file(): yield p
            except OSError: pass

def list_files(path='.', pattern='*', limit=200):
    base=safe_path(path)
    if not base.is_dir(): raise ResearchError(f"Not a directory: {path}")
    rows=[]
    for p in sorted(base.rglob('*')):
        rel=p.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.startswith('.') for part in rel.parts): continue
        if p.is_file() and fnmatch.fnmatch(p.name, pattern):
            try: size=p.stat().st_size
            except OSError: size=-1
            rows.append(f"{rel}\t{size} bytes")
            if len(rows)>=max(1,min(int(limit),2000)): break
    return '\n'.join(rows) if rows else 'No matching files found.'

def read_file(path, start_line=1, end_line=None):
    p=safe_path(path)
    if not p.is_file(): raise ResearchError(f"File not found: {path}")
    if p.stat().st_size>MAX_READ_BYTES: raise ResearchError(f"File is too large ({p.stat().st_size} bytes). Use search_file or archive/file inspection first.")
    try: text=p.read_text(encoding='utf-8',errors='replace')
    except Exception as e: raise ResearchError(f"Could not read {path}: {e}")
    lines=text.splitlines(); s=max(1,int(start_line)); e=len(lines) if end_line is None else min(len(lines),int(end_line))
    return '\n'.join(f"{i}: {lines[i-1]}" for i in range(s,e+1)) if s<=e else ''

def search_files(query, path='.', case_sensitive=False, max_results=50):
    base=safe_path(path); needle=query if case_sensitive else query.lower(); results=[]
    if not base.exists(): raise ResearchError(f"Directory does not exist: {path}")
    for p in _iter_files(base):
        if p.suffix.lower() not in TEXT_EXTENSIONS: continue
        try:
            if p.stat().st_size>MAX_SEARCH_BYTES: continue
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception: continue
        hay=text if case_sensitive else text.lower()
        if needle not in hay: continue
        for i,line in enumerate(text.splitlines(),1):
            cmp=line if case_sensitive else line.lower()
            if needle in cmp:
                results.append(f"{p.relative_to(ROOT)}:{i}: {line[:700]}")
                if len(results)>=max_results: return '\n'.join(results)
    return '\n'.join(results) if results else 'No matches found.'

def file_info(path):
    p=safe_path(path)
    if not p.exists(): raise ResearchError(f"File not found: {path}")
    st=p.stat(); kind=mimetypes.guess_type(p.name)[0] or 'unknown'
    extra=[]
    if zipfile.is_zipfile(p): extra.append('ZIP archive')
    else:
        try:
            if tarfile.is_tarfile(p): extra.append('TAR archive')
        except OSError: pass
    return json.dumps({'path':str(p.relative_to(ROOT)),'size':st.st_size,'modified':st.st_mtime,'mime':kind,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if st.st_size<=128*1024*1024 else 'not calculated','type':', '.join(extra) or 'regular file'},indent=2)

def archive_list(path, limit=500):
    p=safe_path(path); names=[]
    try:
        if zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z: names=[f"{i.filename}\t{i.file_size} bytes" for i in z.infolist()[:limit]]
        elif tarfile.is_tarfile(p):
            with tarfile.open(p) as t: names=[f"{m.name}\t{m.size} bytes" for m in list(t)[:limit]]
        else: raise ResearchError(f"Not a supported archive: {path}")
    except Exception as e: raise ResearchError(str(e))
    return '\n'.join(names) or 'Archive is empty.'

def extract_archive(path, destination=None):
    p=safe_path(path); dest=safe_path(destination or (str(p.relative_to(ROOT)) + '.extracted'))
    dest.mkdir(parents=True,exist_ok=True); base=dest.resolve()
    def safe_member(name):
        out=(base/name).resolve()
        try: out.relative_to(base)
        except ValueError: raise ResearchError(f"Unsafe archive member: {name}")
        return out
    if zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            for info in z.infolist():
                if info.is_dir(): continue
                safe_member(info.filename)
            z.extractall(dest)
    elif tarfile.is_tarfile(p):
        with tarfile.open(p) as t:
            for m in t.getmembers(): safe_member(m.name)
            t.extractall(dest)
    else: raise ResearchError(f"Not a supported archive: {path}")
    return f"Extracted to {dest.relative_to(ROOT)}"

WEB_SEARCH_TIMEOUT = 15

def _web_search_worker(query, max_results, queue):
    try:
        from ddgs import DDGS
        # DDGS supports an HTTP-client timeout. Keep it deliberately short so
        # a dead/rate-limited search backend cannot stall the voice agent.
        results = DDGS(timeout=8).text(
            query,
            region="us-en",
            safesearch="moderate",
            max_results=max(1, min(int(max_results), 20)),
            backend="auto",
        )
        queue.put((True, results))
    except Exception as exc:
        queue.put((False, str(exc)))

def web_search(query, max_results=8):
    # Run DDGS in a separate process so we have a *real* upper bound. A
    # library/network call that gets stuck cannot freeze Jarvis's main voice
    # loop. The worker is killed if it exceeds WEB_SEARCH_TIMEOUT.
    import multiprocessing as mp
    queue = mp.Queue()
    proc = mp.Process(target=_web_search_worker, args=(query, max_results, queue), daemon=True)
    proc.start()
    proc.join(WEB_SEARCH_TIMEOUT)

    if proc.is_alive():
        proc.terminate()
        proc.join(2)
        raise ResearchError(
            f"Web search timed out after {WEB_SEARCH_TIMEOUT} seconds. "
            "The search provider may be slow or rate-limited; Jarvis is still running."
        )

    try:
        ok, payload = queue.get_nowait()
    except Exception:
        ok, payload = False, "search worker exited without returning a result"
    finally:
        queue.close()

    if not ok:
        raise ResearchError(f"Web search unavailable: {payload}")

    results = payload
    if not results:
        return 'No web results found.'
    return '\n'.join(
        f"{i}. {r.get('title','')}\n   {r.get('href','')}\n   {r.get('body','')}"
        for i, r in enumerate(results, 1)
    )

def open_url(url, max_chars=20000):
    if not re.match(r'^https?://',url,re.I): raise ResearchError('Only http:// and https:// URLs are allowed.')
    r=requests.get(url,headers={'User-Agent':'Local-Jarvis/1.4'},timeout=TIMEOUT,allow_redirects=True)
    r.raise_for_status(); c=r.text[:max_chars]
    c=re.sub(r'<script[^>]*>.*?</script>',' ',c,flags=re.I|re.S); c=re.sub(r'<style[^>]*>.*?</style>',' ',c,flags=re.I|re.S); c=re.sub(r'<[^>]+>',' ',c); c=re.sub(r'\s+',' ',c).strip()
    return f"URL: {r.url}\nStatus: {r.status_code}\nContent:\n{c[:max_chars]}"

def download_url(url, filename=None):
    if not re.match(r'^https?://',url,re.I): raise ResearchError('Only http:// and https:// URLs are allowed.')
    r=requests.get(url,headers={'User-Agent':'Local-Jarvis/1.4'},timeout=TIMEOUT,stream=True); r.raise_for_status()
    name=filename or Path(url.split('?',1)[0]).name or 'downloaded_file'
    name=Path(name).name
    dest=safe_path('downloads')/name; dest.parent.mkdir(parents=True,exist_ok=True)
    total=0
    with dest.open('wb') as f:
        for chunk in r.iter_content(1024*1024):
            if not chunk: continue
            total+=len(chunk)
            if total>MAX_DOWNLOAD_BYTES: raise ResearchError('Download exceeds 512 MiB safety limit.')
            f.write(chunk)
    return f"Downloaded {total} bytes to {dest.relative_to(ROOT)}"
