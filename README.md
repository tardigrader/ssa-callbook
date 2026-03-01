# SSA Callbook

A CLI tool and TUI (textual user interface) for searching the Swedish amateur radio callbook (SSA SM-Callbook).

## Features

- Search by callsign, first name, last name, or city
- Display member information including address and contact details
- OpenStreetMap links for addresses (approximate location)
- QTH locator support for precise coordinates (when available)
- Distance calculation between two callsigns or Maidenhead locators
- Interactive TUI with keyboard shortcuts

## Installation

### Using uv (recommended)

```bash
# Create virtual environment and install dependencies (includes editable install)
uv sync
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies and CLI
pip install -e .
```

## Usage

The CLI can be run with `uv run ssacall` (without activating) or after activating the environment:

```bash
# Without activating (using uv run)
uv run ssacall -c SA2NTA

# Or after activating
source .venv/bin/activate
ssacall -c SA2NTA
```

### CLI Examples

```bash
# Search by callsign
uv run ssacall -c SA2NTA

# Search by first name
uv run ssacall -f Krister

# Search by last name  
uv run ssacall -l Löfgren

# Search by city
uv run ssacall -y Holmsund

# Use wildcard (asterisk) in callsign
uv run ssacall -c SM7*

# Combined search
uv run ssacall -f Krister -l Löfgren

# Show full search URL
uv run ssacall -c SA2NTA -v

# Calculate distance between two callsigns
uv run ssacall -d SA2NTA SM5DYQ

# Calculate distance between two Maidenhead locators
uv run ssacall -d JP94vc KP03er

# Launch interactive TUI
uv run ssacall -t
```

### Interactive TUI

Launch the TUI with `ssacall -t` or `ssacall-tui`.

**Keyboard shortcuts:**
- `c` - Switch to callsign search
- `f` - Switch to first name search
- `l` - Switch to last name search
- `y` - Switch to city search
- `Enter` - Perform search
- `q` - Quit

## Options

```
-c, --call CALL       Callsign to search for
-f, --first FIRST    First name to search for
-l, --last LAST      Last name to search for
-y, --city CITY      Location/city to search for
-v, --verbose        Show full search URL used
-d, --distance       Calculate distance between two callsigns or locators
-t, --tui            Launch interactive TUI
```

## Troubleshooting

### Result limit

SSA limits search results to 50 entries. If there are more results, the CLI and TUI will show a warning message. Use more specific search criteria to narrow down results.

### "Could not find QTH locator" error

The SSA callbook does not return QTH locators for all entries. Distance calculation requires QTH locators to be available in the callbook for the callsigns being queried. You can:

1. Use Maidenhead locators directly: `ssacall -d JP94vc KP03er`
2. Wait for the callsign to have their QTH locator registered in the SSA callbook

### Network errors

- Check your internet connection
- The SSA website may be temporarily unavailable
- Try again later

## Potential Improvements

The SSA callbook website returns additional data that could be supported in future versions:

### Special Callsigns (Specialsignaler)

SSA issues special callsigns (e.g., SM50, SM100, etc.) for events and celebrations. These are currently not parsed by this tool.

### Recreational Callsigns (Fritidssignaler)

When searching, SSA also returns "fritidssignaler" - temporary callsigns used at summer houses or other secondary locations. These have a different format and could be displayed separately.

### License

MIT License

## Author

Built for the Swedish amateur radio community.
