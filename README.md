# NÖ Dispo – Docker-Leitstellensimulator v0.1

Eigenständiger, spielbarer Prototyp für Niederösterreich, zunächst Raum Bruck/Leitha, Schwechat und Hainburg. Keine Kopie des LstSim-Quellcodes; keine Anbindung an echte Leitstellen.

## Start mit Docker Compose

ZIP entpacken, Terminal im Ordner `noe-dispo` öffnen:

```bash
docker compose up -d --build
```

Danach auf dem Rechner, auf dem Docker läuft: **http://localhost:8088**

Der Port ist standardmäßig nur lokal erreichbar. Für Zugriff über LAN ändere in `compose.yaml` die Portzeile zu `"8088:8080"` und starte erneut mit `docker compose up -d`. Verwende die Server-IP, z. B. `http://192.168.1.20:8088`. Der Prototyp hat keine Benutzeranmeldung: nicht ungeschützt öffentlich bereitstellen. Für einen entfernten Server ist alternativ ein SSH-Tunnel geeignet:

```bash
ssh -L 8088:127.0.0.1:8088 benutzer@server
```

Anschließend lokal `http://localhost:8088` öffnen. Es gibt keine kostenpflichtigen APIs und keine externen Frontend-Abhängigkeiten. Der erste Docker-Build benötigt Zugriff auf das Python-Basisimage.

## Portainer direkt aus GitHub

1. Unter GitHub **Actions** warten, bis `Test and publish Docker image` grün ist. Bei jedem Push auf `main` wird nach Tests ein Linux/amd64-Image veröffentlicht.
2. Das neue Container-Paket `noe-lstsim` unter dem GitHub-Profil öffnen. Neue Pakete können zunächst privat sein. Entweder Paket unter **Package settings → Change visibility → Public** öffentlich setzen oder in Portainer eine GHCR-Registry-Anmeldung mit einem GitHub-Token mit `read:packages` hinterlegen. Tokens nicht ins Repository oder in den Chat schreiben.
3. In Portainer **Stacks → Add stack → Repository** auswählen:
   - Name: `noe-lstsim`
   - Repository URL: `https://github.com/themagix9/noe-lstsim`
   - Repository reference: `refs/heads/main`
   - Compose path: `compose.portainer.yaml`
4. Für Zugriff im vertrauenswürdigen LAN in den Stack-Umgebungsvariablen `BIND_HOST=0.0.0.0` setzen. `PORT=8088` ist der Standard. Für ausschließlich lokalen Zugriff oder einen lokalen Reverse Proxy den Standard `127.0.0.1` behalten.
5. **Deploy the stack**, anschließend bei LAN-Freigabe `http://SERVER-IP:8088` öffnen.

Für spätere Updates zuerst den erfolgreichen GitHub-Build abwarten. Dann den Git-Stack aktualisieren und dabei **Re-pull image / Pull latest image** aktivieren (Bezeichnung je nach Portainer-Version). Nur Git abzufragen garantiert bei unverändertem Image-Tag `latest` noch keinen Austausch des Containers. Automatische Git-Updates sind optional; dabei muss die Option zum erneuten Laden des Images korrekt konfiguriert sein. Änderungen, die nur Quellcode betreffen, ändern die Compose-Datei nicht; daher manuelles Re-pull oder ein gezielter Webhook nach erfolgreichem Build verwenden.

Jeder Build besitzt zusätzlich einen unveränderlichen Tag `sha-<vollständige Commit-SHA>`. Über `IMAGE_TAG` kann eine konkrete Version gewählt werden. SQLite-Daten bleiben im bestehenden Stack-Volume erhalten. Stack-Namen bei Updates beibehalten, sonst erhält Docker ein anderes Volume. Der Simulator besitzt noch keine Anmeldung und darf nicht ungeschützt öffentlich zugänglich sein.

`compose.yaml` baut lokal aus dem Quellcode; `compose.portainer.yaml` verwendet das veröffentlichte Image. Für Portainer die zweite Datei wählen.

## Erste Übung

1. Die Simulation beginnt pausiert um 08:00. Starte sie oben rechts; zum Testen eignet sich 15×.
2. Über **+ Ereignis** kannst du sofort einen Notruf oder Transportauftrag erzeugen. Während der Übung treffen auch automatisch neue Ereignisse ein.
3. Notruf auswählen, annehmen und die zusätzliche Abfrage öffnen.
4. Transportziel auswählen, passende Ressourcen markieren und alarmieren. Bei Szenarien mit RTW + NEF beide auswählen; ein NEF kann später ergänzt werden.
5. Krankentransporte erscheinen direkt als elektronische Aufträge mit Abholzeit. Sie lösen keinen 144-Telefonanruf aus.
6. Fahrzeugstatus und Funkmeldungen folgen dem Simulationsablauf. Ein Fahrzeug bleibt bis zum Ende der Aufbereitung gebunden.

Die zusätzlichen Abfragen sind eine vereinfachte Spielmechanik und kein reales standardisiertes Abfragesystem oder medizinisches Schulungsprotokoll.

## Fahrzeuge und Dienststellen

Unter **Ressourcen** können Fahrzeuge und Dienststellen erstellt und bearbeitet werden. Für Fahrzeuge: Kennung, Typ (KTW, KTW-B, RTW, RTW-C, NEF, BEL), Stammdienststelle, Besetzung, Dienstbeginn und Dienstende sowie Datenquelle/Prüfvermerk. Gleicher Beginn und Ende bedeutet ganztägigen Dienst. Nacht-Dienstzeiten über Mitternacht werden unterstützt. Laufende Einsätze werden bei Dienstende abgeschlossen; danach geht das Fahrzeug außer Dienst. Unbesetzte Fahrzeuge sind nicht verfügbar.

Die 14 Kennungen und Fahrzeugtypen stammen aus den Nutzerfotos vom 11.10.2026: 53/002, 53/022, 53/601, 53/602, 53/699, 77/001, 77/002, 77/004, 77/006, 77/015, 77/030, 77/060, 77/099, 77/900. Die Fotos zeigen angemeldete Ressourcen zu einem Zeitpunkt, keine vollständige Flottenliste. **Stammdienststellen, Koordinaten und ganztägige Dienstzeiten sind ungeprüfte Startwerte**, abgeleitet aus den sichtbaren Ortsangaben und Kennungsgruppen. Kein aktueller vollständiger NÖ-Bestand wird behauptet. Die Live-Statuswerte, Einsatzcodes und etwaigen Patientendaten aus den Fotos werden nicht übernommen.

Stammdienststelle und aktueller Standort werden getrennt gespeichert. Die Zonenwahl filtert die Ressourcenübersicht; freie Fahrzeuge anderer Zonen bleiben in der Dispositionsauswahl verfügbar. Weitere Zonen und Dienststellen lassen sich anlegen, automatische Einsätze entstehen in v0.1 weiterhin im Raum Bruck/Leitha.

## Speicherung und Konfigurationsimport

SQLite speichert Stammdaten, Simulationsstand und das letzte Kommunikationsprotokoll im Docker-Volume `simulation-data`. `docker compose down` erhält dieses Volume; `docker compose down -v` entfernt es einschließlich aller gespeicherten Daten.

Unter **Konfiguration** lassen sich Dienststellen/Fahrzeuge als JSON exportieren und importieren. Ein Import ersetzt beide Stammdatenlisten und ist nur ohne laufende Einsätze erlaubt. Fehlerhafte Imports lassen die alte Konfiguration unverändert. Am einfachsten zunächst exportieren, die JSON-Datei bearbeiten und wieder importieren. IDs müssen eindeutig und aus Buchstaben, Zahlen, Bindestrichen oder Unterstrichen bestehen. Jeder Fahrzeugeintrag muss auf eine vorhandene Dienststellen-ID verweisen. Die Funktion **Übung zurücksetzen** leert Einsätze und Protokoll, erhält aber die eigenen Stammdaten.

Für eine vollständige Sicherung Container stoppen und das Docker-Volume sichern; ein JSON-Konfigurationsexport enthält keine laufenden Einsätze.

## Technischer Aufbau

- Python 3.12, Standardbibliothek, HTTP-Server und SQLite; keine Python-Pakete nötig.
- HTML/CSS/JavaScript ohne Buildschritt oder CDN.
- Hintergrunduhr, serverseitige Verfügbarkeitsprüfung und gesperrte Schreiboperationen.
- Eine gemeinsame Übung pro Installation; mehrere Browser sehen denselben Stand.
- Nicht privilegierter Container, Healthcheck, keine zusätzlichen Linux-Capabilities.

Für lokale Entwicklung ohne Docker:

```bash
DATA_DIR=./data python3 app/server.py
```

Dann `http://localhost:8080`. Unter PowerShell zuerst `$env:DATA_DIR="./data"` setzen und anschließend `python app/server.py` ausführen.

Tests:

```bash
python3 -m unittest discover -s tests -v
node --check app/static/app.js
```

## Bekannte Grenzen und nächste Schritte

Dies ist ein funktionierender Grundprototyp, kein vollständiger LstSim-Ersatz. Die Karte ist schematisch, keine navigierbare Straßenkarte. Fahrzeugpositionen springen zwischen Phasen; Fahrzeiten werden aus Luftlinie mit pauschalem Umwegfaktor berechnet. Beispieladressen, Anrufer und Szenarien sind erfunden. Die Abholzeit wird angezeigt; Verspätungen werden noch nicht bewertet. Keine Sprachsynthese, Spracherkennung oder KI-Anbindung.

Ressourcenanforderungen sind Szenariohinweise. Unvollständige Alarmierungen bleiben möglich, damit der Disponent nachalarmieren kann; der Ablauf wartet noch nicht zwingend auf den Notarzt. NEF fährt nach Versorgung ohne Begleitung zurück. Keine Rendezvous- oder Nachführungslogik, Vorhaltung, Pausen, dynamische Krankenhauskapazität oder echte AAO. BEL ist im Bestand pflegbar, aber noch ohne spielbare Führungsaufgaben. Krankenhäuser sind zunächst feste Ziele, Transportzieländerung nach Alarmierung ist gesperrt. Rückfahrende Fahrzeuge können noch nicht umdisponiert werden.

Sinnvolle nächste Ausbaustufen: geprüfter Fahrzeug-/Dienststellenimport für alle NÖ-Zonen, echte Straßenkarte und Routing, zusätzliche POIs und Transportziele, parametrisierte Funkdialoge, AAO/Qualifikationen, zeitabhängige Einsatzverteilung, Transportplanung und eigene Übungssitzungen mit Anmeldung.

## Prüfung dieser Ausgabe

Automatisierte Tests decken getrennten KT-Eingang, Notrufannahme, Doppelalarmierung, atomare Disposition, Nacht-/unbesetzte Dienste, kompletten Einsatzzyklus, Import-Rollback, Konfigurationsimport, Neustartpersistenz und Rücksetzung ab. HTTP-Smoke-Test prüft Oberfläche, API, Persistenz und Eingabevalidierung. JavaScript-Syntax geprüft. Docker ist in der Erstellungsumgebung nicht installiert; daher wurde kein Docker-Build ausgeführt. Eine visuelle Browserprüfung war dort nicht verfügbar.
