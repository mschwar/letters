# DOC_AGENT.md

Doc agent runs post-commit to keep docs aligned with code changes.

## Usage
- Manual: `python3 infra/scripts/doc_agent.py --mode manual`
- Install post-commit hook: `bash infra/scripts/install_doc_agent_hook.sh`

## Behavior
- Appends to `progress.txt` feature log
- Refreshes schema and dependency sections
- Updates cross-references and index
- Optionally auto-commits doc updates

## Configuration
- Defaults are read from this file when the environment variable is unset.
- `DOC_AGENT_AUTOCOMMIT=1` to auto-commit
- `DOC_AGENT_COMMIT_MSG="Auto-doc: ..."`
- `DOC_AGENT_SUMMARY_CMD="..."` to generate summaries (stdin diff)
