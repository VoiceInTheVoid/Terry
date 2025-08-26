#!/usr/bin/env python3
import os
import sys
import re
import random
import shutil
import requests
from pathlib import Path
from textwrap import fill
from datetime import datetime
import time

# ---------- Paths (Linux-friendly) ----------
SCRIPT_DIR = Path(__file__).resolve().parent

# Prefer local proverbs.txt (your current workflow); else look in XDG data dir
PROVERBS_LOCAL = SCRIPT_DIR / "proverbs.txt"

XDG_DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
APP_DATA_DIR = XDG_DATA_HOME / "proverbs-cli"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

PROVERBS_XDG = APP_DATA_DIR / "proverbs.txt"
FAV_FILE = APP_DATA_DIR / "favorites.txt"

def resolve_proverbs_file() -> Path:
    """Use local proverbs.txt if present; otherwise use XDG location."""
    if PROVERBS_LOCAL.exists():
        return PROVERBS_LOCAL
    return PROVERBS_XDG

PROVERBS_FILE = resolve_proverbs_file()

# ---------- ANSI colors ----------
RESET = "\033[0m"
BOLD  = "\033[1m"

FG = {
    "default": "\033[39m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[97m",
    "bright_black": "\033[90m",
    "bright_blue": "\033[94m",
    "bright_cyan": "\033[96m",
    "bright_magenta": "\033[95m",
    "bright_yellow": "\033[93m",
    "bright_green": "\033[92m",
    "bright_white": "\033[97m",
    "bright_red": "\033[91m",
}

BOX = {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│"}

REF_RE = re.compile(r"^\s*(Proverbs\s+\d+:\d+)\s+(.*)$", re.IGNORECASE)

def term_width():
    try:
        return shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        return 80

def hr(char="─"):
    w = term_width()
    return char * max(20, min(w, 120))

def load_verses(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: '{path.resolve()}'. "
            f"Create it first or place 'proverbs.txt' next to this script."
        )
    verses = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            m = REF_RE.match(ln)
            if m:
                ref, txt = m.group(1), m.group(2)
            else:
                ref, txt = "Proverbs ?", ln
            verses.append((ref, txt))
    if not verses:
        raise ValueError(f"No verses found in '{path.resolve()}'.")
    return verses

def box_text(ref: str, text: str, pad=2, color_ref="bright_cyan", color_text="bright_white"):
    w = term_width()
    inner = max(20, min(w - 2 - pad*2, 120))
    wrapped = fill(text, width=inner)
    top = BOX["tl"] + BOX["h"] * (inner + pad*2) + BOX["tr"]
    bot = BOX["bl"] + BOX["h"] * (inner + pad*2) + BOX["br"]
    lines = [top]
    ref_clean = ref.strip()
    ref_line = ref_clean.center(inner + pad*2)
    lines.append(f'{BOX["v"]}{" " * pad}{BOLD}{FG[color_ref]}{ref_line}{RESET}{BOX["v"]}')
    sep = ("─" * (inner + pad*2))
    lines.append(f'{BOX["v"]}{" " * pad}{FG["bright_black"]}{sep}{RESET}{BOX["v"]}')
    for ln in wrapped.splitlines():
        padded = ln.ljust(inner)
        lines.append(f'{BOX["v"]}{" " * pad}{FG[color_text]}{padded}{RESET}{" " * pad}{BOX["v"]}')
    lines.append(bot)
    return "\n".join(lines)

def print_title():
    w = term_width()
    title = "PROVERBS (KJV, local)"
    subtitle = "Enter: random • 's': save • 'h': help • '/terry': Terry Mode • 'q': quit"
    print()
    print(FG["bright_magenta"] + BOLD + title.center(w) + RESET)
    print(FG["bright_black"] + subtitle.center(w) + RESET)
    print(FG["bright_black"] + hr() + RESET)

def save_favorite(ref: str, text: str):
    FAV_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {ref}  {text}\n"
    with FAV_FILE.open("a", encoding="utf-8") as f:
        f.write(line)

def show_help():
    w = term_width()
    help_lines = [
        ("Enter", "next random verse"),
        ("s", "save current verse to favorites"),
        ("h", "show this help"),
        ("q", "quit"),
        ("/terry", "enter Terry mode (Mistral)"),
    ]
    print(FG["bright_black"] + hr() + RESET)
    print((BOLD + "HELP".center(w) + RESET))
    for k, d in help_lines:
        print(f"{BOLD}{k:>8}{RESET}  {d}")
    print(FG["bright_black"] + hr() + RESET)

# ----- Globale Settings für TERRY (live tunable) -----
TERRY_SETTINGS = {
    "model": os.getenv("MISTRAL_MODEL", "open-mixtral-8x7b"),
    "temperature": float(os.getenv("MISTRAL_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("MISTRAL_MAX_TOKENS", "256")),
}

def terry_mode():
    """Enter Terry Mode — uses Mistral API for chat with live tuning."""
    w = term_width()
    title = "TERRY MODE — Mistral"
    subtitle = "Type query • '/model X' • '/temp 0.5' • '/max 128' • 'b' back • 'q' quit"
    print()
    print(FG["bright_red"] + BOLD + title.center(w) + RESET)
    print(FG["bright_black"] + subtitle.center(w) + RESET)
    print(FG["bright_black"] + hr("=") + RESET)

    try:
        while True:
            prompt = FG["bright_red"] + f"TERRY[{TERRY_SETTINGS['model']}|T={TERRY_SETTINGS['temperature']}|M={TERRY_SETTINGS['max_tokens']}]> " + RESET
            query = input(prompt)
            cmd = query.strip()

            if not cmd:
                continue
            if cmd.lower() == "q":
                sys.exit(0)
            if cmd.lower() == "b":
                print(FG["bright_black"] + "Returning to Proverbs..." + RESET)
                break

            # --- Live-Tuning ---
            if cmd.lower().startswith("/model "):
                TERRY_SETTINGS["model"] = cmd.split(maxsplit=1)[1]
                print(FG["green"] + f"[INFO] Model set to {TERRY_SETTINGS['model']}" + RESET)
                continue
            if cmd.lower().startswith("/temp "):
                try:
                    val = float(cmd.split(maxsplit=1)[1])
                    TERRY_SETTINGS["temperature"] = val
                    print(FG["green"] + f"[INFO] Temperature set to {val}" + RESET)
                except:
                    print(FG["red"] + "Invalid temp value." + RESET)
                continue
            if cmd.lower().startswith("/max "):
                try:
                    val = int(cmd.split(maxsplit=1)[1])
                    TERRY_SETTINGS["max_tokens"] = val
                    print(FG["green"] + f"[INFO] Max tokens set to {val}" + RESET)
                except:
                    print(FG["red"] + "Invalid max_tokens value." + RESET)
                continue
            if cmd.lower() in ("/settings", "/set", "/s"):
                print(FG["bright_black"] + f"[SETTINGS] model={TERRY_SETTINGS['model']}, temp={TERRY_SETTINGS['temperature']}, max={TERRY_SETTINGS['max_tokens']}" + RESET)
                continue

            # --- Normal Anfrage ---
            answer = query_llm(cmd)
            print(box_text("Your Answer:", answer, color_ref="bright_red", color_text="bright_white"))
            print()
    except KeyboardInterrupt:
        print(FG["bright_black"] + "\nReturning to Proverbs..." + RESET)

# ----- Mistral integration with cached Proverbs context -----
_PROVERBS_CONTEXT = None

def get_proverbs_context() -> str:
    """Load and cache proverbs.txt as context for LLM."""
    global _PROVERBS_CONTEXT
    if _PROVERBS_CONTEXT is not None:
        return _PROVERBS_CONTEXT

    try:
        verses = load_verses(PROVERBS_FILE)
        context = "\n".join([f"{ref} {txt}" for ref, txt in verses])
    except Exception as e:
        context = f"[Fehler beim Laden der Sprüche: {e}]"

    _PROVERBS_CONTEXT = context
    return context

def query_llm(prompt: str) -> str:
    """
    Mistral chat call mit:
    - Accept/Content-Type Headers, Timeout
    - Exponential Backoff bei 429/5xx (+ Retry-After)
    - Modell-Fallback (beginnend mit TERRY_SETTINGS['model'])
    - Kontextlimit via PROVERBS_CTX_LIMIT (Chars)
    - Steuerbar per Env: MISTRAL_MODEL, MISTRAL_MAX_TOKENS, MISTRAL_TEMPERATURE
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "[LLM ERROR] MISTRAL_API_KEY not set."

    base_url = "https://api.mistral.ai/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Modelle: starte mit live-gesetztem Modell, dann bewährte Alternativen
    model_candidates = [
        TERRY_SETTINGS.get("model") or os.getenv("MISTRAL_MODEL", "open-mixtral-8x7b"),
        "mistral-large-latest",
        "mistral-small-latest",
        "open-mixtral-8x7b",
    ]

    # --- Kontext limitieren (Kosten/Robustheit) ---
    raw_ctx = get_proverbs_context()
    MAX_CONTEXT_CHARS = int(os.getenv("PROVERBS_CTX_LIMIT", "6000"))
    ctx = (raw_ctx[:MAX_CONTEXT_CHARS] + " …") if len(raw_ctx) > MAX_CONTEXT_CHARS else raw_ctx

    system_prompt = (
        "You are given biblical proverbs as context. Use this mainly for guidance.\n"
        "Requirements:\n"
        "1) Advise the user as if spoken from Proverbs (quote a relevant proverb if suitable).\n"
        "2) Pay careful attention to the semantics and emotional tone of the user input.\n"
        "Style: a touch of biblical cadence, so the user feels addressed by ancient wisdom—while staying respectful and concise.\n\n"
        f"Context (Proverbs; possibly truncated):\n{ctx}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    max_tokens = int(TERRY_SETTINGS.get("max_tokens", 256))
    temperature = float(TERRY_SETTINGS.get("temperature", 0.7))

    def do_call(model: str):
        return requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
            timeout=30,
        )

    last_err = None
    for model in model_candidates:
        for attempt in range(5):
            try:
                resp = do_call(model)
            except requests.exceptions.Timeout:
                delay = min(1.0 * (2 ** attempt) + random.uniform(0, 0.3), 10)
                print(FG["bright_black"] + f"[WARN] Timeout. Retrying in {delay:.1f}s…" + RESET)
                time.sleep(delay)
                last_err = "timeout"
                continue
            except Exception as e:
                return f"[LLM ERROR] {e}"

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                except Exception as e:
                    return f"[LLM ERROR] Bad JSON: {e} | Raw: {resp.text[:300]}"

            if resp.status_code in (429, 502, 503, 504):
                ra = resp.headers.get("Retry-After")
                try:
                    delay = float(ra) if ra else 1.0 * (2 ** attempt) + random.uniform(0, 0.3)
                except Exception:
                    delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.3)
                delay = min(delay, 10)
                print(FG["bright_black"] + f"[WARN] {resp.status_code} on {model}. Retry in {delay:.1f}s…" + RESET)
                time.sleep(delay)
                last_err = resp.text
                continue

            if resp.status_code == 404:
                print(FG["bright_black"] + f"[INFO] Model not available: {model}" + RESET)
                last_err = resp.text
                break

            if resp.status_code == 401:
                return "[LLM ERROR] 401 Unauthorized — check MISTRAL_API_KEY / project."

            return f"[LLM ERROR {resp.status_code}] {resp.text[:400]}"

    return f"[FAILED] after retries & fallbacks. Last error: {last_err}"

def main():
    print(FG["bright_black"] + "Starting… initializing files & UI…" + RESET)
    try:
        verses = load_verses(PROVERBS_FILE)
    except Exception as e:
        print(FG["red"] + BOLD + "ERROR: " + RESET + str(e))
        try:
            input("Press Enter to exit…")
        finally:
            return

    print_title()

    current = None
    try:
        while True:
            if current is None:
                current = random.choice(verses)
                print(box_text(current[0], current[1]))
                print()

            s = input()
            cmd = s.strip().lower()

            if cmd == "q":
                break
            elif cmd == "h":
                show_help()
            elif cmd == "s":
                if current:
                    save_favorite(current[0], current[1])
                    print(FG["green"] + "Saved to favorites" + RESET)
            elif cmd == "/terry":
                terry_mode()
                current = None
                print_title()
            else:
                current = random.choice(verses)
                print(box_text(current[0], current[1]))
                print()
    except KeyboardInterrupt:
        pass
    finally:
        print(FG["bright_black"] + "Bye." + RESET)
        try:
            if not sys.stdin.isatty():
                input("Press Enter to exit…")
        except Exception:
            pass

if __name__ == "__main__":
    main()
