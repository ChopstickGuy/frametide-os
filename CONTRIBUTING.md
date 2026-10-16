# Contributing to Frametide OS

Thanks for helping! Frametide OS is a small community project, and every bug report, idea,
translation and pull request makes a difference.

## Reporting bugs

Please use the [bug report template](https://github.com/ChopstickGuy/frametide-os/issues/new?template=bug_report.yml)
and include:

- your hardware: CPU, GPU, laptop or desktop
- the output of `frametide-hwsetup` (it shows the detected hardware and planned steps)
- for driver problems, also `/var/log/frametide-hwsetup.log`

## Translations

The Store, Center, game check, Move from Windows and Bench are translated with gettext.

```bash
python3 tools/i18n.py extract                 # refresh po/frametide.pot
cp po/frametide.pot po/fr.po                  # start a new language (e.g. French)
python3 tools/i18n.py check                   # find missing strings and placeholder errors
```

Store descriptions live in `packages/frametide-tools/usr/share/frametide/store/catalog.json`
(`summary` in German, `summary_en` in English).

## Code

- **Shell:** `build.sh`, `scripts/`, package maintainer scripts. Check them with `bash -n`.
- **Python + GTK4/libadwaita:** `packages/frametide-tools/usr/lib/frametide/`
- **Package names:** `tools/check-packages.py` checks every name against the Ubuntu archive
  before a 30-minute build fails on a typo.
- Privileged actions go through `frametide-helper`. It only accepts a fixed set of validated
  commands, so please keep it that way.

The CI runs all checks on every pull request. To test a full ISO, see [docs/RELEASE.md](docs/RELEASE.md).

## Code of conduct

Be kind and patient. Many people here are brand new to Linux, and that's exactly who
Frametide is for.
