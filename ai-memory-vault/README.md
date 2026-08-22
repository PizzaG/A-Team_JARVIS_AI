# AI Memory Vault

> **Never used Claude Code?** Start at [jaredrhod.com](https://jaredrhod.com): pick your situation and it routes you to the right path.

**Runs on:** built and tested on Claude Code; any terminal AI that reads and writes files works with rough edges. The $20 Pro plan is enough.

Give your AI a real, persistent memory. This is the free, open system that turns an Obsidian vault into your AI's working memory, so it remembers everything across sessions, lives outside the model with no size ceiling, and pulls back exactly what it needs in one step. Free to use, share, and build on, including commercially inside your own business (see LICENSE).

**It also ships with my actual agent.** People kept asking whether they could just download my Jarvis instead of inventing an assistant from scratch, so now the boot config arrives with him already in it: the name, the personality, the way he talks, and the rules he runs on. Keep him as-is, keep him and change the name, or replace him with your own. Your call, and it's one section of one file either way.

## The build

- **[ai-memory-vault.md](ai-memory-vault.md):** the build script. Run it inside Claude and it checks whether Obsidian is even installed yet (and installs it for you if not), interviews you, then builds a complete, self-maintaining system: a boot config, a folder structure around your real projects, daily notes that write themselves, a profile that updates as the AI learns about you, and "Jobs" that teach it to do your recurring tasks your way. Your vault becomes the AI's memory, so it lives outside the model with no size ceiling, and the AI holds only what the current task needs while reaching anything else in one step. Watch the walkthrough: [https://www.youtube.com/playlist?list=PLN7lTYpeRLOc](https://www.youtube.com/playlist?list=PLN7lTYpeRLOc)

**Already inside a Claude Code session?** Paste this and it builds the whole system with you: *"I'd like to set this up, please: https://github.com/jaredrhod/ai-memory-vault.git"*

## AI Priming

AI Priming is having your AI read a specific set of your notes before it gives you the answer or output you want. For example, before my agent writes a marketing email, it reads my copywriting notes, my email marketing notes, my customer avatar, and my company knowledge base. Then it writes. This is extremely powerful because, with AI, context is king. When you "prime" your AI with the knowledge and skills it needs prior to its output, your results will always be better and more accurate.

Every job gets its own set of notes. An email needs different notes than a Facebook ad. The vault keeps all of your notes organized in one place and tells your AI which notes to read for which job. You set that up once, and your AI primes itself on every task after that.

Full definition and examples: https://jaredrhod.com/ai-priming

## Templates

Starter files for the system. Every spot that needs your information is marked `[FILL IN: ...]`. Drop a template in and tell your AI "fill this in for me," and it will interview you and write it in your voice (each template carries that instruction for the AI). Or fill them out by hand if you prefer.

- **[CLAUDE.md](templates/CLAUDE.md):** the boot config. Goes in the folder you run Claude Code from (your **working directory**), kept **out of your vault** so the vault stays pure notes and doesn't get tangled once you have more than one project. Claude Code auto-loads it every session and points the AI to your vault. Holds your agent's identity (its name, role, and personality) plus your startup sequence and the rules that can't lapse. **This one arrives working:** my own agent's identity is already filled in, clearly marked as the one section to swap if you'd rather have your own.
- **[VAULT-INDEX.md](templates/VAULT-INDEX.md):** the operating manual. This one lives **inside your vault** (it's a note, not config). Your profile, your projects, the full vault rules, and how you like to work with the AI.
- **[DAILY-NOTE.md](templates/DAILY-NOTE.md):** the daily-note template. Goes **inside your vault** at `01 - Daily Notes/Daily Note Template.md`. Every daily note gets created from it, so the log keeps one consistent, scannable shape.
- **[MEMORY.md](templates/MEMORY.md):** the pointer for Claude Code's own memory. Goes in **Claude Code's project folder** (`~/.claude/projects/...`, not your vault). It redirects the native memory back into the vault so you never end up with two memory layers that drift apart.

## Updating

The build script, the templates, and the wizard improve continuously. If you keep a copy of this repo on disk, say to your agent: **"pull the latest ai-memory-vault and tell me what changed."** Updates only ever touch the repo's own files. Your vault, your notes, and your CLAUDE.md are yours and are never inside this repo, so nothing you built can be overwritten. Installed through fullstack-agent? `./fullstack-agent/update.sh` updates every piece at once and prints what changed.

## The rest of it

A mind is better with a mouth, a face, and hands. Once your agent remembers you, the natural next steps are talking to it out loud, giving it a face on screen, and moving your notes around with your bare hands.

- **The whole stack, one command.** [fullstack-agent](https://github.com/jaredrhod/fullstack-agent) installs the memory, the voice, the face, and the hands, and wires them together for you. Pick only the pieces you want: https://jaredrhod.com
- **The videos.** Free series on all of it: https://youtube.com/@jaredrhod
- **The Discord.** Thousands of builders, and the fastest place to get unstuck: https://discord.gg/YSdsqMv3V8
- **Everything else,** free and open: https://jaredrhod.com

## Support

Free to use, and always will be. If this helped you out, you can buy me a coffee:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jaredrhod)

## License

Copyright (c) 2026 Jared Rhodenizer.

Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). **Use it in your business, commercially, for free.** Copy it, adapt it, and build your own system on it. Two rules: credit me, and license your own adapted version the same way so the next person gets what you got. Full terms are in the LICENSE file and at https://creativecommons.org/licenses/by-sa/4.0/
