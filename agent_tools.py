from __future__ import annotations
import json, os, shlex, shutil, subprocess
from pathlib import Path
from research_tools import (
    ResearchError, list_files, read_file, search_files, file_info,
    archive_list, extract_archive, web_search, open_url, download_url, safe_path,
)

class JarvisTools:
    def __init__(self, project_root: Path, memory):
        self.root = Path(project_root).resolve()
        self.memory = memory

    def _tool_candidates(self, query: str = ""):
        tools = self.root / "Tools"
        if not tools.exists():
            return "No Tools directory exists under Project_Folder."
        q = query.lower().strip()
        rows=[]
        for p in sorted(tools.rglob('*')):
            if not p.is_file() or any(x in {'.git','venv','.venv','__pycache__'} for x in p.parts):
                continue
            if p.suffix.lower() not in {'.sh','.bash','.py','.pl','.rb','.js','.exe','.bin'} and p.name.lower() not in {'lpunpack','simg2img'}:
                continue
            text=''
            try:
                if p.suffix.lower() in {'.sh','.bash','.py','.pl','.rb','.js'} and p.stat().st_size <= 512*1024:
                    text=p.read_text(encoding='utf-8',errors='replace')[:20000]
            except Exception:
                pass
            hay=(str(p.relative_to(self.root))+' '+text).lower()
            if q and q not in hay:
                continue
            rows.append(str(p.relative_to(self.root)))
            if len(rows)>=100:
                break
        return '\n'.join(rows) if rows else 'No matching tools found.'

    def _run_project_command(self, command: str, cwd: str = ".", timeout: int = 1800, show_output: bool = False):
        work=safe_path(cwd)
        if not work.is_dir(): raise ResearchError(f"Working directory does not exist: {cwd}")
        # Commands execute from the project sandbox. The shell cannot escape via cwd,
        # but Jarvis still gives Qwen the responsibility to choose the command.
        # Project tools are non-interactive by default. Never inherit Jarvis's
        # terminal stdin: scripts that end with `read`, `read -p`, `pause`, etc.
        # would otherwise steal the user's Jarvis input and can make the main
        # conversation appear to hang or loop.
        proc=subprocess.Popen(command, shell=True, cwd=str(work), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, bufsize=1, executable='/bin/bash')
        lines=[]
        try:
            for line in proc.stdout:
                line=line.rstrip()
                if line:
                    # Keep command output internal. Qwen receives it for reasoning;
                    # raw script banners must never leak into Jarvis's terminal.
                    lines.append(line)
                    if len(lines)>400:
                        lines=lines[-400:]
            rc=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
            raise ResearchError(f"Command timed out after {timeout} seconds")
        result={'exit_code':rc,'cwd':str(work.relative_to(self.root)),'output':'\n'.join(lines[-200:])}
        return json.dumps(result, indent=2)

    def _copy_path(self, source: str, destination: str):
        src=safe_path(source); dst=safe_path(destination)
        if not src.exists(): raise ResearchError(f"Source not found: {source}")
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
        else: shutil.copy2(src,dst)
        return f"Copied {src.relative_to(self.root)} to {dst.relative_to(self.root)}"

    def _move_path(self, source: str, destination: str):
        src=safe_path(source); dst=safe_path(destination)
        if not src.exists(): raise ResearchError(f"Source not found: {source}")
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(src),str(dst))
        return f"Moved {src.name} to {dst.relative_to(self.root)}"

    def _delete_path(self, path: str, confirm: bool = False):
        if not confirm:
            return "Deletion not performed. Ask the user for confirmation before deleting files or directories."
        p=safe_path(path)
        if not p.exists(): raise ResearchError(f"Path not found: {path}")
        if p.is_dir(): shutil.rmtree(p)
        else: p.unlink()
        return f"Deleted {path}"

    def remember(self, fact: str):
        return self.memory.remember(fact)

    def search_memory(self, query: str):
        return self.memory.search(query, limit=10) or "No matching persistent memory found."

    def definitions(self):
        def fn(name, desc, props, required=None):
            return {'type':'function','function':{'name':name,'description':desc,'parameters':{'type':'object','properties':props,'required':required or []}}}
        return [
            fn('list_project_files','List files in the local Project_Folder. Use this to inspect the workspace before acting.',
               {'path':{'type':'string','description':'Relative directory inside Project_Folder, default .'},'pattern':{'type':'string','description':'Filename glob, default *'},'limit':{'type':'integer','description':'Maximum results, default 100'}}),
            fn('read_project_file','Read a text file from Project_Folder with line numbers.',
               {'path':{'type':'string'},'start_line':{'type':'integer'},'end_line':{'type':'integer'}} ,['path']),
            fn('search_project_files','Search text files recursively inside Project_Folder.',
               {'query':{'type':'string'},'path':{'type':'string','description':'Relative directory, default .'},'case_sensitive':{'type':'boolean'},'max_results':{'type':'integer'}},['query']),
            fn('inspect_file','Inspect a project file: size, type, modified time and hash when practical.',{'path':{'type':'string'}},['path']),
            fn('list_archive','List the contents of a ZIP/TAR archive.',{'path':{'type':'string'},'limit':{'type':'integer'}},['path']),
            fn('extract_archive','Extract a ZIP/TAR archive safely inside Project_Folder.',{'path':{'type':'string'},'destination':{'type':'string'}},['path']),
            fn('find_project_tools','Discover scripts/binaries under Project_Folder/Tools. Search their filenames and readable source for a term.',{'query':{'type':'string'}}),
            fn('run_project_command','Run a shell command from a directory inside Project_Folder and return its exit code and output. Use this for project tools after inspecting them.',{'command':{'type':'string'},'cwd':{'type':'string','description':'Relative working directory, default .'},'timeout':{'type':'integer','description':'Timeout in seconds, default 1800'},'show_output':{'type':'boolean','description':'Show raw command output in the Jarvis terminal. Default false.'}},['command']),
            fn('copy_project_path','Copy a file or directory inside Project_Folder.',{'source':{'type':'string'},'destination':{'type':'string'}},['source','destination']),
            fn('move_project_path','Move a file or directory inside Project_Folder.',{'source':{'type':'string'},'destination':{'type':'string'}},['source','destination']),
            fn('delete_project_path','Delete a file or directory inside Project_Folder. Requires confirm=true; ask the user before destructive deletion.',{'path':{'type':'string'},'confirm':{'type':'boolean'}},['path','confirm']),
            fn('web_search','Search the Internet using the local DDGS backend.',{'query':{'type':'string'},'max_results':{'type':'integer'}},['query']),
            fn('open_web_page','Fetch and extract readable text from a web page.',{'url':{'type':'string'},'max_chars':{'type':'integer'}},['url']),
            fn('download_web_file','Download a web file into Project_Folder/downloads.',{'url':{'type':'string'},'filename':{'type':'string'}},['url']),
            fn('remember','Save a fact or decision to persistent Jarvis memory.',{'fact':{'type':'string'}},['fact']),
            fn('search_memory','Search persistent Jarvis memory for relevant information.',{'query':{'type':'string'}},['query']),
        ]

    def call(self, name, args):
        args=args or {}
        try:
            if name=='list_project_files': return list_files(args.get('path','.'),args.get('pattern','*'),args.get('limit',100))
            if name=='read_project_file': return read_file(args['path'],args.get('start_line',1),args.get('end_line'))
            if name=='search_project_files': return search_files(args['query'],args.get('path','.'),args.get('case_sensitive',False),args.get('max_results',50))
            if name=='inspect_file': return file_info(args['path'])
            if name=='list_archive': return archive_list(args['path'],args.get('limit',500))
            if name=='extract_archive': return extract_archive(args['path'],args.get('destination'))
            if name=='find_project_tools': return self._tool_candidates(args.get('query',''))
            if name=='run_project_command': return self._run_project_command(args['command'],args.get('cwd','.'),args.get('timeout',1800),args.get('show_output',False))
            if name=='copy_project_path': return self._copy_path(args['source'],args['destination'])
            if name=='move_project_path': return self._move_path(args['source'],args['destination'])
            if name=='delete_project_path': return self._delete_path(args['path'],args.get('confirm',False))
            if name=='web_search': return web_search(args['query'],args.get('max_results',8))
            if name=='open_web_page': return open_url(args['url'],args.get('max_chars',20000))
            if name=='download_web_file': return download_url(args['url'],args.get('filename'))
            if name=='remember': return self.remember(args['fact']) or 'Memory saved.'
            if name=='search_memory': return self.search_memory(args['query'])
            return f"Unknown tool: {name}"
        except Exception as e:
            return f"TOOL ERROR: {type(e).__name__}: {e}"
