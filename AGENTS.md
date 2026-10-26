# Repository Guidelines

## Project Structure & Module Organization

PRSK_Editor is a Python 3.10+ desktop translation editor using PyQt5. Run commands from the repository root.

- `src/Main.pyw` starts the application and coordinates file operations and editor modes.
- `src/mainGUI.py` defines the Qt interface; `Editor.py` manages translation rows, editing, and text import/export.
- `src/JsonLoader.py` reads scenario JSON; `TranslationFormat.py` parses translation TXT v2.
- `src/ListManager.py`, `Flashback.py`, and `Dictionary.py` provide story catalogs, flashback analysis, and character names.
- `tests/` contains automated tests; `image/` contains icons and other bundled assets.
- `pyproject.toml` and `uv.lock` define reproducible dependencies. Platform packaging specifications are `Main.spec` and `Main_MacOS.spec`.

## Build, Test, and Development Commands

- `uv sync --locked`: install the committed dependency versions.
- `uv run python src/Main.pyw`: launch the desktop editor.
- `uv run python -m unittest discover -s tests -v`: run the automated suite, including Qt offscreen tests.
- `git diff --check`: check whitespace before submitting changes.
- `uv run pyinstaller --onefile --windowed --add-data "image:image" --icon image/icon/256.ico src/Main.pyw`: build a Windows executable into `dist/`.

The existing spec files contain developer-specific paths and older PyInstaller options; review them before using them for packaging.

## Coding Style & Naming Conventions

Use four spaces for Python indentation and UTF-8 for source and translation files. Follow nearby naming conventions: existing Qt handlers use camelCase, while newer standalone parsing functions use snake_case. Use descriptive class names and avoid unrelated renaming. No formatter or linter is currently configured.

Keep format parsing separate from widget updates. Preserve the distinction between unnamed dialogue and blank separator rows. Validate v2 imports completely before applying translations, and retain original JSON indices for entry matching.

## Testing Guidelines

Use standard-library `unittest`; name files `test_*.py` and methods `test_*`. No numeric coverage threshold is configured. Add regression tests for changed parsing and editing behavior, including malformed input and legacy compatibility. Report manual GUI checks separately from automated tests.

## Commit & Pull Request Guidelines

History mixes English and Chinese summaries, with recent fixes using `fix: <description>`. Prefer concise, action-oriented messages and focused commits. Pull requests should explain the behavior change, link relevant issues, list validation performed, and include screenshots for visible UI changes. Exclude downloaded data, local settings, logs, virtual environments, and build output.
