# Eine Version veröffentlichen

## Ablauf

1. Auf `main` committen und pushen. GitHub Actions prüft den Code und baut die ISO.
   Die ISO liegt danach 30 Tage lang unter *Actions → ISO bauen → Artifacts*.
2. Die ISO in einer VM testen (siehe README).
3. Wenn alles passt, einen Tag setzen:
   ```bash
   git tag v1.0.0-alpha1 && git push origin v1.0.0-alpha1
   ```
   Die Pipeline baut dann erneut, lädt die ISO auf SourceForge hoch und legt ein
   GitHub-Release (Vorabversion) mit Prüfsumme und Download-Link an.

## Warum SourceForge?

GitHub-Releases erlauben höchstens **2 GB pro Datei**, unsere ISO ist größer.
SourceForge ist kostenlos, hat ein weltweites Spiegelnetz und wird von vielen
Distributionen genutzt, zum Beispiel Manjaro, MX Linux und Nobara.

## SourceForge einmalig einrichten

1. Ein Konto auf <https://sourceforge.net/user/registration> anlegen.
2. Ein Projekt anlegen: <https://sourceforge.net/create/>, Name z. B. `frametide-os`.
   Die Projekt-ID (Unix-Name) steht dann in der Adresse
   `sourceforge.net/projects/<projekt-id>/`.
3. Den SSH-Schlüssel hinterlegen: <https://sourceforge.net/auth/shell_services>.
   Dort den **öffentlichen** Schlüssel einfügen, der in der Einrichtung genannt wurde
   (Zeile beginnt mit `ssh-ed25519`).
4. Benutzername und Projekt-ID als GitHub-Secrets eintragen. Das geht im Repo unter
   *Settings → Secrets and variables → Actions* oder so:
   ```bash
   gh secret set SF_USER --body "<sourceforge-benutzername>"
   gh secret set SF_PROJECT --body "<projekt-id>"
   ```
   Der private Schlüssel `SF_SSH_KEY` ist bereits eingetragen.

Solange `SF_USER` fehlt, wird der Upload übersprungen und die ISO bleibt nur als
Actions-Artefakt verfügbar.
