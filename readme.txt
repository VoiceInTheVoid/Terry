Proverbs CLI + TERRY (Mistral)

A tiny terminal app that shows random verses from Proverbs (KJV) and lets you chat with an LLM (Mistral) in a special /terry mode.
No virtual environment required.

1) Requirements

Python 3.10+

pip available on your system

Internet connection (for /terry mode)

A Mistral API key

2) Files & Layout

Place the script (e.g. proverbs_cli.py) anywhere. The app looks for the data file:

proverbs.txt next to the script (preferred), or

${XDG_DATA_HOME:-~/.local/share}/proverbs-cli/proverbs.txt

Expected file format (one verse per line):

Proverbs 1:1 The proverbs of Solomon the son of David, king of Israel;
Proverbs 1:2 To know wisdom and instruction; to perceive the words of understanding;
Proverbs 1:3 To receive the instruction of wisdom, justice, and judgment, and equity;


Favorites are saved to:
~/.local/share/proverbs-cli/favorites.txt

3) Install dependencies

The script only needs requests.

Linux/macOS:

python3 -m pip install --user requests


Windows (PowerShell):

py -m pip install --user requests

4) Set your Mistral API key (for /terry)

Linux/macOS (bash/zsh):

export MISTRAL_API_KEY='sk-...your-secret-key...'


Windows PowerShell:

$env:MISTRAL_API_KEY = 'sk-...your-secret-key...'


Optional tuning (defaults shown):

Linux/macOS:

export MISTRAL_MODEL='open-mixtral-8x7b'
export MISTRAL_TEMPERATURE='0.7'
export MISTRAL_MAX_TOKENS='256'
export PROVERBS_CTX_LIMIT='6000'


Windows PowerShell:

$env:MISTRAL_MODEL = 'open-mixtral-8x7b'
$env:MISTRAL_TEMPERATURE = '0.7'
$env:MISTRAL_MAX_TOKENS = '256'
$env:PROVERBS_CTX_LIMIT = '6000'

5) Run

Linux/macOS:

python3 proverbs_cli.py


Windows:

py proverbs_cli.py

6) Controls (main screen)

Enter → next random verse

s → save current verse to favorites

h → help

/terry → enter LLM chat mode

q → quit

7) TERRY mode

Type /terry from the main screen.
Prompt looks like:

TERRY[open-mixtral-8x7b|T=0.7|M=256]>


Ask questions normally

/model mistral-large-latest → change model

/temp 0.3 → adjust creativity

/max 512 → change answer length

/settings → show current values

b → back to Proverbs

q → quit