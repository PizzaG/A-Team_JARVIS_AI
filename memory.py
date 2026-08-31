from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path

class MemoryVault:
    """Local, markdown-first persistent memory inspired by Jared Rhodenizer's AI Memory Vault.

    The vault is external to the model. Jarvis loads only the relevant notes and writes
    durable memories back to markdown so they survive restarts and model changes.
    """
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.daily = self.root / "01 - Daily Notes"
        self.profile = self.root / "02 - Profile"
        self.projects = self.root / "03 - Projects"
        self.knowledge = self.root / "04 - Knowledge"
        self.jobs = self.root / "05 - Jobs"
        for p in (self.daily, self.profile, self.projects, self.knowledge, self.jobs):
            p.mkdir(parents=True, exist_ok=True)
        self.index = self.root / "VAULT-INDEX.md"
        self.priorities = self.root / "Active Priorities.md"
        self._bootstrap()

    def _bootstrap(self):
        if not self.index.exists():
            self.index.write_text("""---\nstatus: active\nproject: meta\ntype: index\n---\n# VAULT INDEX\n\nThis vault is JARVIS's persistent external memory. Load only the notes relevant to the current task.\n\n## Memory rules\n- This vault is the long-term source of truth for durable Jarvis memory.\n- Do not invent memories.\n- Prefer updating an existing note over creating duplicates.\n- Important project findings belong in the relevant project note.\n- Daily activity belongs in the current daily note.\n- User-requested memories should be written immediately.\n\n## Vault structure\n- `01 - Daily Notes/` — chronological session/activity log\n- `02 - Profile/` — durable information about the user and working preferences\n- `03 - Projects/` — persistent project knowledge and findings\n- `04 - Knowledge/` — reusable technical/reference knowledge\n- `05 - Jobs/` — task-specific procedures and priming notes\n\n## Project workspace\nThe active local project workspace is separate from this vault. Jarvis may use it for files, tools, firmware, source, extraction output, and experiments.\n""", encoding="utf-8")
        if not self.priorities.exists():
            self.priorities.write_text("# Active Priorities\n\n", encoding="utf-8")
        profile = self.profile / "Profile.md"
        if not profile.exists():
            profile.write_text("---\ntype: reference\nstatus: active\n---\n# Profile\n\nDurable information Jarvis should remember about the user.\n", encoding="utf-8")

    @property
    def today_path(self):
        return self.daily / f"{datetime.now():%Y-%m-%d}.md"

    def load_boot_context(self, max_chars=18000):
        parts=[]
        for p in (self.index, self.priorities, self.profile / "Profile.md", self.today_path):
            if p.exists():
                txt=p.read_text(encoding="utf-8", errors="replace")
                parts.append(f"MEMORY FILE: {p.relative_to(self.root)}\n{txt[:max_chars]}")
        return "\n\n".join(parts)[:max_chars]

    def search(self, query: str, limit=8):
        terms=[x.lower() for x in re.findall(r"[A-Za-z0-9_./-]+", query) if len(x)>2]
        hits=[]
        for p in self.root.rglob("*.md"):
            try: txt=p.read_text(encoding="utf-8", errors="replace")
            except Exception: continue
            low=txt.lower(); score=sum(low.count(t) for t in terms)
            if score:
                hits.append((score,p,txt))
        hits.sort(key=lambda x:(-x[0], str(x[1])))
        out=[]
        for score,p,txt in hits[:limit]:
            lines=txt.splitlines()
            matched=[]
            for i,line in enumerate(lines,1):
                if any(t in line.lower() for t in terms): matched.append(f"{i}: {line[:300]}")
            out.append(f"{p.relative_to(self.root)}\n"+"\n".join(matched[:8]))
        return "\n\n".join(out)

    def remember(self, text: str, category="Knowledge"):
        now=datetime.now()
        safe=re.sub(r"[^A-Za-z0-9 _-]+", "", text).strip()
        title="Memory - "+(safe[:60] if safe else now.strftime("%Y-%m-%d %H%M"))
        target_dir=self.knowledge if category.lower() != "profile" else self.profile
        target=target_dir/(re.sub(r"\s+"," ",title).replace("/","-")+".md")
        if target.exists():
            target=target.with_name(target.stem+f" {now:%H%M%S}.md")
        target.write_text(f"---\ntype: reference\nstatus: active\ncreated: {now:%Y-%m-%d}\n---\n# {title}\n\n{text.strip()}\n", encoding="utf-8")
        self.append_daily("Memory", text.strip())
        return target

    def append_daily(self, section: str, text: str):
        p=self.today_path
        if not p.exists():
            p.write_text(f"---\ntype: log\nstatus: active\ndate: {datetime.now():%Y-%m-%d}\n---\n# Daily Note — {datetime.now():%Y-%m-%d}\n", encoding="utf-8")
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n## {section}\n{datetime.now():%H:%M} — {text.strip()}\n")

    def record_interaction(self, user: str, answer: str):
        # Keep daily notes useful without dumping giant transcripts into memory.
        u=re.sub(r"\s+", " ", user).strip()[:500]
        a=re.sub(r"\s+", " ", answer).strip()[:800]
        self.append_daily("Session", f"User: {u}\nJarvis: {a}")
