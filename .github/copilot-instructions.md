# GitHub Copilot Agent Instructions

## MCP Tools — When and How to Use Them

### Serena (`mcp_oraios_serena_*`)
**Use for: reading and understanding code — always prefer over reading raw files.**
- `activate_project` — call once at the start of any coding session to enable semantic indexing
- `find_symbol` — find classes, functions, methods by name across the entire codebase
- `get_symbols_overview` — get a structural overview of a file (classes, methods, variables)
- `find_referencing_symbols` — find all places where a symbol is used (safe refactoring)
- `replace_symbol_body` — replace an entire function/class body precisely by name
- `search_for_pattern` — regex search scoped to a file or directory
- **Context:** running in `ide-assistant` mode — file editing tools are intentionally disabled (VS Code handles edits)

### Database — DBHub Dev (`dbhub-dev`) / DBHub Prod (`dbhub-prod`)
**Use for: running SQL queries, inspecting schema, debugging data issues.**
- `dbhub-dev` connects to: `news_aggregator_dev` on `localhost:5432`
- `dbhub-prod` connects to: `news_prod` on Neon cloud
- Use dev for exploration and debugging; only use prod when explicitly asked
- Can list tables, describe schema, run SELECT queries, check row counts

### GitHub MCP (`mcp_io_github_git_*`)
**Use for: GitHub operations — PRs, issues, branches, commits.**
- Creating/reviewing pull requests
- Reading/writing GitHub issues
- Listing branches and commits
- Authenticated via Copilot OAuth — no manual token needed

### Context7 (`mcp_io_github_ups_*`)
**Use for: looking up current documentation for any library or framework.**
- When the user asks about a library API, use `resolve-library-id` then `get-library-docs`
- Always prefer this over guessing API signatures from training data
- Covers npm, PyPI, and most popular libraries

### Playwright MCP (`mcp_microsoft_pla_browser_*`)
**Use for: browser automation, UI testing, scraping behind JavaScript.**
- Navigate pages, click elements, fill forms, take screenshots
- Use when Chrome DevTools MCP is not sufficient (e.g., need full interaction)

### Chrome DevTools MCP (`mcp_io_github_chr_*`)
**Use for: inspecting running Chrome — network requests, console logs, performance.**
- Requires Chrome running with `--remote-debugging-port=9222`
- Use for debugging frontend issues in the fastnews Cloudflare Worker site

### MarkItDown (`mcp_microsoft_mar_*`)
**Use for: converting documents (PDF, DOCX, XLSX, images) to Markdown.**
- When the user provides a non-text file and wants its content analyzed

### Desktop Commander (`mcp_io_github_won_*`)
**Use for: shell commands and file operations when run_in_terminal is not available.**
- File read/write, directory listing, running processes
- Secondary option — prefer native VS Code tools first

---

## Project Context

- **Language:** Python
- **Database:** PostgreSQL 16 (dev: localhost, prod: Neon cloud)
- **Virtual environment:** `C:\Users\Korisnik\Documents\fast_news\.venv`
- **Run scripts from:** `news_aggregator/` directory with the venv python interpreter
- **News portals:** `portals/pt_*` (BBC, Reuters, NYT, Guardian, Fox, ABC, Al Jazeera) + `portals/py_cnn/`
- **NLP/Summarizer:** `news_aggregator/nlp/summarizer/main.py` — use `--backend copilot --model gpt-5-mini`
- **Migrations:** `alembic` with `alembic.ini` in `news_aggregator/`
- **Frontend:** Cloudflare Worker in `news_aggregator/frontend/fastnews/`
