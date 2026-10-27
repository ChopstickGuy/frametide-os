# Battle.net und WoW Forever auf Frametide OS

Battle.net läuft über **Proton**. Am einfachsten geht das mit dem **Faugus Launcher** aus dem
App Store (Gaming → „Faugus Launcher“). Alternativ funktioniert auch **Lutris** mit dessen
Battle.net-Installer.

## Einrichten (einmalig, ca. 10 Minuten)

1. `Battle.net-Setup.exe` von [blizzard.com](https://www.blizzard.com/apps/battle.net/desktop)
   herunterladen.
2. **Faugus Launcher** öffnen → **+**:
   - Name: `Battle.net`
   - Pfad: die heruntergeladene `Battle.net-Setup.exe`
   - Proton: **GE-Proton** (Faugus lädt es selbst herunter)
   - Umgebungsvariablen: `WINE_SIMULATE_WRITECOPY=1`
   - Startargumente: `--in-process-gpu`
3. Starten → Installer durchklicken. Öffnet sich Battle.net am Ende, **ohne Anmelden schließen**.
4. Den Eintrag bearbeiten: Pfad auf
   `…/drive_c/Program Files (x86)/Battle.net/Battle.net Launcher.exe` im gleichen Prefix setzen.
5. Battle.net über Faugus starten und anmelden.

Hängt die Anmeldung (Kreisel), in Battle.net unter *Einstellungen → App* die
**Hardwarebeschleunigung** ausschalten.

## WoW Forever

- Im Battle.net bei World of Warcraft die Version **„WoW: Forever“** auswählen (Beta: nur mit
  Zugang).
- Friert das Spiel beim Betreten der Welt ein: vorher im Spielmenü die **Grafikqualität auf 1**
  stellen, einloggen, danach wieder hochstellen. Hilft das nicht, unter *Grafik* auf **DirectX 11**
  wechseln oder *Sekundäre Beleuchtung* senken.
- Am Netzteil spielen bzw. oben rechts den Energiemodus **„Leistung“** wählen.

Spiele auf einer Linux-Partition (ext4) installieren, nicht auf einer NTFS-Platte.
