"""Sprache für Frametide-Werkzeuge: Texte im Code sind deutsch, alle anderen
Sprachen nutzen ihre Übersetzung (po/) oder fallen auf Englisch zurück."""
import gettext
import os

LOCALE_DIR = os.environ.get("FRAMETIDE_LOCALE", "/usr/share/locale")


def ui_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value and value not in ("C", "POSIX") and not value.startswith("C."):
            return value.split(":")[0].split(".")[0]
    return "en"


LANG = ui_language()
GERMAN = LANG.startswith("de")
_ = (lambda s: s) if GERMAN else gettext.translation(
    "frametide", LOCALE_DIR, languages=[LANG, LANG.split("_")[0], "en"], fallback=True).gettext


def localized(entry, key):
    """Feld aus dem Store-Katalog in der passenden Sprache (z. B. summary / summary_en)."""
    return entry[key] if GERMAN else entry.get(f"{key}_en", entry[key])
