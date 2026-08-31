# Jarvis Research Engine

Jarvis is local-first. The configured research root defaults to `.` (the Jarvis folder) and can be changed in `config/jarvis.json`.

## Local tools

- `list_files` — inventory files.
- `search_files` — search text/code/config with file and line references.
- `read_file` — read bounded text ranges with line numbers.
- `file_info` — metadata and SHA-256 for manageable files.
- `archive_list` — inspect ZIP/TAR contents without extraction.
- `extract_archive` — safely extract archives inside the research root.

## Internet tools

- `web_search` — metasearch using the `ddgs` package.
- `open_url` — fetch readable text from HTTP/HTTPS pages.
- `download_url` — explicitly download a public URL into `downloads/`.

Internet access is controlled by:

```json
"research": {
  "Root": "Research_Folder",
  "internet": true,
  "max_results": 50,
  "max_web_results": 8
}
```

Set `internet` to `false` for offline-only operation.

## Research behavior

Jarvis should prefer local evidence for questions about the research folder, then use web research for verification/current information. It should distinguish local evidence, web evidence, and inference, and cite local file paths/line numbers whenever available.
