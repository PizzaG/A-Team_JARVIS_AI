## v2.6
- Updated the top agent status to always use the currently configured active Agent Name.
- Added explicit Stopped, Starting.., Running, and Working status states for the active agent.
- Kept the configured Agent Name intact during automatic release updates instead of replacing it with the JARVIS default.
- Runtime stop messages now use the active Agent Name instead of a hard-coded JARVIS label.
- Public Release v2.6

## v2.5
- Added White as an Outline Color option.
- Renamed the Tool Activity checkbox to Activity.
- Reorganized the feature checkboxes into a two-column layout for a cleaner options bar.
- Added a configurable Agent Name field that saves to config/jarvis.json and updates GUI branding and the live runtime without requiring a restart.
- Applied the configured Agent Name to the window title, options/chat labels, start/stop/status text, prompt placeholder, desktop launcher branding, runtime identity, and system prompt.
- Strengthened persistent-memory guidance so JARVIS saves concise project continuity checkpoints for durable decisions, requirements, discoveries, blockers, implementation state, and next steps during ongoing work.
- Updated README and Updates/version.json for the v2.5 release.
- Public Release v2.5

## v2.4
- Added automatic update installation with archive validation, extraction, restart, and cleanup.
- Protected Memory_Vault from being overwritten during application updates.
- Removed the downloaded-archive location prompt because updates now install automatically.
- Updated the Outline Color selector to show all available colors without the unnecessary scrolling list.
- Moved the top-bar option toggles beside the Run Setup, Start JARVIS, and Stop JARVIS controls and centered the action controls.
- Added Memory and Tool Activity controls wired to config/jarvis.json, with live runtime updates.
- Moved the existing face and voice selectors into the centered JARVIS Options control area.
- Updated config/VERSION for the v2.4 release and synchronized updater metadata.
- Public Release v2.4

## v2.3
- Expanded JARVIS agent research budgets for longer multi-step investigations.
- Increased tool rounds, continuation phases, tool-call allowance, and maximum agent runtime.
- Increased retained agent context and tool-result limits for deeper research tasks.
- Extended finalization timeout and context budget for large research sessions.
- Improved continuation checkpoints so JARVIS reviews unresolved questions and verification steps before continuing.
- Added multi-line updater changelog support through Updates/version.json.
- Moved the application VERSION source into config/VERSION and updated the GUI lookup path.
- Simplified and redesigned the main README for a cleaner repository presentation.
- Public Release v2.3

## v2.2
- Initial GTK3 GUI App Code Refactor
- Public Release v2.2
