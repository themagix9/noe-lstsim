# NÖ Dispo – Docker-Leitstellensimulator v0.10

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

Anschließend lokal `http://localhost:8088` öffnen. Es gibt keine kostenpflichtigen APIs. Leaflet 1.9.4 wird lokal mitgeliefert; die Karte lädt nur die gerade benötigten OpenStreetMap-Kacheln im Browser. Der erste Docker-Build benötigt Zugriff auf das Python-Basisimage.

## Portainer direkt aus GitHub

1. Unter GitHub **Actions** warten, bis `Test and publish Docker image` grün ist. Bei jedem Push auf `main` wird nach Tests ein Linux/amd64-Image veröffentlicht.
2. Das neue Container-Paket `noe-lstsim` unter dem GitHub-Profil öffnen. Neue Pakete können zunächst privat sein. Entweder Paket unter **Package settings → Change visibility → Public** öffentlich setzen oder in Portainer eine GHCR-Registry-Anmeldung mit einem GitHub-Token mit `read:packages` hinterlegen. Tokens nicht ins Repository oder in den Chat schreiben.
3. In Portainer **Stacks → Add stack → Repository** auswählen:
   - Name: `noe-lstsim`
   - Repository URL: `https://github.com/themagix9/noe-lstsim`
   - Repository reference: `refs/heads/main`
   - Compose path: `compose.portainer.yaml`
4. In den Stack-Umgebungsvariablen `CLOUDFLARE_TUNNEL_TOKEN` auf den Token deines Cloudflare-Tunnels setzen. Keinen Token ins Repository schreiben. Ohne Token meldet Compose einen Fehler und deployt nicht.
5. Im Cloudflare-Tunnel einen veröffentlichten Hostnamen anlegen: Service-Typ **HTTP**, Service-URL **`noe-lstsim:8080`** (vollständiges Ziel: `http://noe-lstsim:8080`). Beide Services befinden sich im selben Docker-Netzwerk. `localhost` im Cloudflared-Container wäre der Tunnel-Container, nicht der Simulator.
6. **Deploy the stack**, anschließend den konfigurierten HTTPS-Hostnamen öffnen. Für eine private Testversion den Hostnamen über Cloudflare Access auf die gewünschten Benutzer beschränken.

Cloudflared wartet beim Start auf den gesunden Simulator. Der Tunnel stellt selbst ausgehende Verbindungen zu Cloudflare her; eingehende Ports/Portweiterleitungen sind dafür nicht nötig. Die lokale Debug-Schnittstelle bleibt standardmäßig auf `127.0.0.1:8088` begrenzt. `BIND_HOST=0.0.0.0` nur setzen, wenn zusätzlich LAN-Zugriff gewünscht ist.

Für spätere Updates zuerst den erfolgreichen GitHub-Build abwarten. Dann den Git-Stack aktualisieren und dabei **Re-pull image / Pull latest image** aktivieren (Bezeichnung je nach Portainer-Version). Nur Git abzufragen garantiert bei unverändertem Image-Tag `latest` noch keinen Austausch des Containers. Automatische Git-Updates sind optional; dabei muss die Option zum erneuten Laden des Images korrekt konfiguriert sein. Änderungen, die nur Quellcode betreffen, ändern die Compose-Datei nicht; daher manuelles Re-pull oder ein gezielter Webhook nach erfolgreichem Build verwenden.

Jeder Build besitzt zusätzlich einen unveränderlichen Tag `sha-<vollständige Commit-SHA>`. Über `IMAGE_TAG` kann eine konkrete Version gewählt werden. SQLite-Daten bleiben im bestehenden Stack-Volume erhalten. Stack-Namen bei Updates beibehalten, sonst erhält Docker ein anderes Volume. Der Simulator besitzt noch keine Anmeldung und darf nicht ungeschützt öffentlich zugänglich sein.

`compose.yaml` baut lokal aus dem Quellcode; `compose.portainer.yaml` verwendet das veröffentlichte Image. Für Portainer die zweite Datei wählen.

## Erste Übung

1. Spielmodus, Standort, Dispozone, Spielernamen und Startstunde wählen. Für den vorhandenen Bestand Dispo 05 verwenden. Multiplayer kann alternativ per Code beitreten. Die Simulation beginnt pausiert; zum Testen eignet sich 15×.
2. Über **+ Ereignis** kannst du sofort einen Notruf oder Transportauftrag erzeugen. Während der Übung treffen auch automatisch neue Ereignisse ein.
3. Notruf auswählen, annehmen und die zusätzliche Abfrage öffnen.
4. Im Einsatzmodal Abfrage abschließen, Stichwort prüfen, AAO-Vorschlag übernehmen oder passende Ressourcen manuell markieren und alarmieren. Transportziel wird bei RD-Einsätzen später von der Mannschaft gemeldet.
5. Krankentransporte erscheinen direkt als elektronische Aufträge mit Abholzeit. Sie lösen keinen 144-Telefonanruf aus.
6. Fahrzeugstatus und Funkmeldungen folgen dem Simulationsablauf. Nach Patientenübergabe wird die Ressource frei über Funk; bei Status 5 lassen sich bereits Folge-Transportaufträge senden.

Die zusätzlichen Abfragen sind eine vereinfachte Spielmechanik und kein reales standardisiertes Abfragesystem oder medizinisches Schulungsprotokoll.

## Fahrzeuge und Dienststellen

Unter **Ressourcen** können Fahrzeuge und Dienststellen erstellt und bearbeitet werden. Für Fahrzeuge: Kennung, Typ (KTW, KTW-B, RTW, RTW-C, NEF, BEL), Stammdienststelle, Besetzung, Dienstbeginn und Dienstende sowie Datenquelle/Prüfvermerk. Gleicher Beginn und Ende bedeutet ganztägigen Dienst. Nacht-Dienstzeiten über Mitternacht werden unterstützt. Laufende Einsätze werden bei Dienstende abgeschlossen; danach geht das Fahrzeug außer Dienst. Unbesetzte Fahrzeuge sind nicht verfügbar.

Die 14 Kennungen und Fahrzeugtypen stammen aus den Nutzerfotos vom 11.10.2026: 53/002, 53/022, 53/601, 53/602, 53/699, 77/001, 77/002, 77/004, 77/006, 77/015, 77/030, 77/060, 77/099, 77/900. Die Fotos zeigen angemeldete Ressourcen zu einem Zeitpunkt, keine vollständige Flottenliste. **Stammdienststellen, Koordinaten und ganztägige Dienstzeiten sind ungeprüfte Startwerte**, abgeleitet aus den sichtbaren Ortsangaben und Kennungsgruppen. Kein aktueller vollständiger NÖ-Bestand wird behauptet. Die Live-Statuswerte, Einsatzcodes und etwaigen Patientendaten aus den Fotos werden nicht übernommen.

Stammdienststelle und aktueller Standort werden getrennt gespeichert. Die Zonenwahl filtert die Ressourcenübersicht; freie Fahrzeuge anderer Zonen bleiben in der Dispositionsauswahl verfügbar. Weitere Zonen und Dienststellen lassen sich anlegen, automatische Einsätze entstehen derzeit nur bei Auswahl von Dispo 05 im Raum Bruck/Leitha.

## Speicherung und Konfigurationsimport

SQLite speichert Stammdaten, Simulationsstand und das letzte Kommunikationsprotokoll im Docker-Volume `simulation-data`. `docker compose down` erhält dieses Volume; `docker compose down -v` entfernt es einschließlich aller gespeicherten Daten.

Unter **Konfiguration** lassen sich Dienststellen/Fahrzeuge als JSON exportieren und importieren. Ein Import ersetzt beide Stammdatenlisten und ist nur ohne laufende Einsätze erlaubt. Fehlerhafte Imports lassen die alte Konfiguration unverändert. Am einfachsten zunächst exportieren, die JSON-Datei bearbeiten und wieder importieren. IDs müssen eindeutig und aus Buchstaben, Zahlen, Bindestrichen oder Unterstrichen bestehen. Jeder Fahrzeugeintrag muss auf eine vorhandene Dienststellen-ID verweisen. Die Funktion **Übung zurücksetzen** leert Einsätze und Protokoll, erhält aber die eigenen Stammdaten.

Für eine vollständige Sicherung Container stoppen und das Docker-Volume sichern; ein JSON-Konfigurationsexport enthält keine laufenden Einsätze.

## Multiplayer und Sitzungen

Multiplayer wählen, eine Sitzung erstellen und den achtstelligen Code über den Code-Button kopieren. Andere Spieler öffnen denselben Simulator, wählen **Mit Code beitreten** und geben Code und eigenen Namen ein. Bis zu 16 Spieleridentitäten sind pro Sitzung möglich; mehrere unabhängige Sitzungen laufen auf demselben Server. Am Start ausdrücklich **Singleplayer** oder **Multiplayer** wählen. Singleplayer-Sitzungen haben keinen nutzbaren Beitrittscode; Teamchat, Betreuungschips und Spielerliste sind dort ausgeblendet.

Alle Spieler einer Sitzung sehen dieselben Aufträge, Fahrzeugstatus, Simulationszeit und Funkmeldungen. Aktualisierung erfolgt durch HTTP-Polling etwa alle zwei Sekunden. Die Teamleiste zeigt Namen, Online-Status und Zahl der betreuten offenen Einsätze; der Stern markiert den Sitzungsleiter. Der Teamchat gehört ausschließlich zur Sitzung.

Ein Einsatz kann über **Einsatz übernehmen** reserviert werden. Notrufannahme, Abfrage oder Alarmierung übernehmen unbesetzte Einsätze automatisch. Die Betreuung steht direkt am Auftrag. Andere Spieler können den Einsatz beobachten, aber während der Betreuung nicht abfragen oder disponieren. **Zur Übergabe freigeben** macht ihn für Kollegen verfügbar; der Sitzungsleiter kann eine Betreuung ebenfalls freigeben. Wenn ein Spieler offline ist, ist die Übernahme nach spätestens 45 Sekunden möglich. Gleichzeitige Übernahmeversuche werden serverseitig gesperrt; genau ein Spieler erhält den Einsatz.

Pause/Geschwindigkeit und manuelle Ereignisse sind gemeinsame Steuerungen. Nur der Sitzungsleiter kann Stammdaten ändern, Grafiken importieren oder die Übung zurücksetzen. Alle können die Konfiguration exportieren. Der Beitrittscode erlaubt Zugriff auf die Runde; nicht öffentlich veröffentlichen, wenn sie privat bleiben soll. Der Simulator verwendet zufällige individuelle Zugangstoken und benötigt für `/api/state` nun einen Sitzungszugang. Das ersetzt noch keine dauerhaften Benutzerkonten oder Cloudflare Access.

Der Browser merkt sich den letzten Zugang; nach Reload bleibt die Identität erhalten. **Sitzung wechseln** öffnet die Lobby, wo die letzte Sitzung fortgesetzt werden kann. Ein gelöschter Browser-Speicher verliert diesen Zugang; ein erneuter Beitritt erzeugt eine neue Identität und stellt nicht automatisch Sitzungsleiterrechte wieder her. Namen sind pro Sitzung eindeutig. Wenn alle offline sind, friert die Simulationszeit nach Ablauf der Online-Frist ein. Es gibt bisher keine Raumlöschung oder Übertragung der Sitzungsleiterrolle; maximal 100 persistierte Sitzungen pro Installation.

### Bestehende Installation aktualisieren

Denselben Portainer-Stack und sein Volume behalten; Stack aktualisieren und das neue Image erneut ziehen. In der ersten Lobby kann der Sitzungsleiter **Bestehenden v0.1-Übungsstand übernehmen** wählen. Die alte SQLite-Tabelle wird bei der Migration erhalten. Ohne Auswahl startet eine neue Übung mit dem Ausgangsbestand. Kein `down -v` verwenden, wenn Daten erhalten bleiben sollen.

## Fahrzeuggrafiken

Vier eigene schematische SVG-Fahrzeugbilder (Kastenwagen, Kofferwagen, SUV und Führungsbus) sind enthalten. Sie sind keine exakten Abbildungen der realen NÖ-Flotte. In den Ressourcen kann pro Fahrzeug eine Grafik ausgewählt werden. Die Bilder erscheinen in den Fahrzeuglisten und als Fahrzeugmarker auf der Karte.

Der Sitzungsleiter kann unter **Ressourcen → Fahrzeuggrafiken → Eigene PNG-Grafik** PNG-Dateien bis 512 KiB und maximal 4096 × 4096 Pixel hinzufügen. Autor, Quelle und Lizenz/Freigabe werden mitgespeichert. Nur eigene oder für dieses separate Projekt freigegebene Dateien verwenden. Die Grafiken werden in SQLite gespeichert und bleiben beim Neustart erhalten. Die Metadaten sind Angaben des Hochladenden, keine automatisch geprüfte Lizenzbestätigung.

Die gewünschte LstSim-Sammlung wurde geprüft, aber es wurde keine ausreichende Freigabe für die Übernahme konkreter österreichischer Grafiken in dieses separate Projekt gefunden. Daher werden keine fremden LstSim-Dateien oder Blankos mitgeliefert. Recherchequellen:

- https://wiki.lstsim.de/Fahrzeuggrafiken
- https://forum.lstsim.de/thread/4749-lukas-fahrzeuggrafiken/ (österreichische Fahrzeuge, teils auf Blankos anderer Autoren)
- https://forum.lstsim.de/thread/3809-westf%C3%A4lische-grafiken/ (ausdrückliche Zustimmung für externe Verwendung erforderlich)

Ein JSON-Konfigurationsexport enthält Fahrzeug-Grafikzuordnungen, aber keine PNG-Dateien. Bei Import in eine andere Sitzung müssen eigene Grafiken dort vorher passend verfügbar sein; unbekannte Grafik-IDs werden zurückgewiesen. Eine vollständige Sicherung umfasst deshalb immer die SQLite-Datenbank, nicht nur den JSON-Export.

## Datenbank heute und später

**SQLite unter `/data/simulation.sqlite3`**, dauerhaft im Docker-Volume. Neu sind getrennte Tabellen für Sitzungen (`rooms`), Spielerzugänge (`members`), Grafikdateien (`graphics_files`) und den Simulationsstand pro Raum (`room_states`). Zugangstoken werden serverseitig nur als SHA-256-Hash gespeichert. Der vorhandene v0.1-Stand bleibt als Legacy-Datenbestand erhalten.

Der eigentliche Fahrzeug-/Einsatzbestand wird weiterhin gemeinsam als JSON-Simulationsstand pro Raum gespeichert. Für den späteren Ausbau sollten Dispozonen, Organisationen, Dienststellen, Schichtmodelle, POIs/Kliniken, Einsatzvorlagen, Transportaufträge und Funkdialoge in eigene Tabellen mit Migrationen aufgeteilt werden. PostgreSQL kann später für größere Installationen ergänzt werden; der jetzige Code nutzt weiterhin SQLite. Mehrere aktive App-Replikate auf demselben Volume werden nicht unterstützt.

## Technischer Aufbau

- Python 3.12, Standardbibliothek, HTTP-Server und SQLite; keine Python-Pakete nötig.
- HTML/CSS/JavaScript ohne Buildschritt oder CDN.
- Hintergrunduhr, serverseitige Verfügbarkeitsprüfung und gesperrte Schreiboperationen.
- Getrennte persistente Sitzungen; mehrere Browser einer Sitzung teilen denselben Stand.
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

Dies ist ein funktionierender Multiplayer-Grundprototyp, kein vollständiger LstSim-Ersatz. Die Karte nutzt OpenStreetMap und lässt sich verschieben/zoomen. Fahrzeugpositionen bewegen sich entlang einer Luftlinie; Fahrzeiten werden weiterhin aus Luftlinie mit pauschalem Umwegfaktor berechnet. Es gibt kein Straßenrouting. Beispieladressen, Anrufer und Szenarien sind erfunden. Die Abholzeit wird angezeigt; Verspätungen werden noch nicht bewertet. Keine Sprachsynthese, Spracherkennung oder KI-Anbindung.

Ressourcenanforderungen sind Szenariohinweise. Unvollständige Alarmierungen bleiben möglich, damit der Disponent nachalarmieren kann; der Ablauf wartet noch nicht zwingend auf den Notarzt. NEF fährt nach Versorgung ohne Begleitung zurück. Keine Rendezvous- oder Nachführungslogik, Vorhaltung, Pausen, dynamische Krankenhauskapazität oder echte AAO. BEL ist im Bestand pflegbar, aber noch ohne spielbare Führungsaufgaben. Bei Notfällen legt die simulierte Mannschaft vor Ort das Ziel fest. Frei über Funk zurückfahrende Ressourcen können erneut disponiert werden. Der Krankenhausbestand enthält zunächst nur drei Ziele.

Sinnvolle nächste Ausbaustufen: geprüfter Fahrzeug-/Dienststellenimport für alle NÖ-Zonen, Straßenrouting, zusätzliche POIs und Transportziele, parametrisierte Funkdialoge, AAO/Qualifikationen, zeitabhängige Einsatzverteilung, Transportplanung, Benutzerkonten, Rollenverwaltung und echte Sprachkommunikation.

## Prüfung dieser Ausgabe

Automatisierte Python-Tests decken Einsatzabläufe, Verfügbarkeit, atomare Disposition, Import-Rollback und Persistenz sowie Sitzungsisolation, konkurrierende Übernahmen, Betreuung, Übergabe, Offline-Übernahme, Teamchat, Rollenrechte, PNG-Import und Migration ab. API-Tests prüfen Beitritt und unberechtigte Zugriffe. Die GitHub-Pipeline prüft zusätzlich in zwei getrennten Browserkontexten: Erstellung/Beitritt, Spielerliste, Betreuung, Übergabe, Alarmierung, Chat, Reload, Grafikdarstellung und Simulationsstart. Desktop- und Mobilansichten werden als interne QA-Artefakte erstellt. Container-Build, Startprüfung und Portainer-Compose-Validierung laufen ebenfalls in GitHub Actions.

Für den Browser-Test separat Playwright installieren (`pip install playwright==1.58.0`, `python -m playwright install chromium`) und `python tests/browser_smoke.py` ausführen. Der Browser-Test verwendet Port 8080; dort darf kein weiterer Testserver laufen. Docker und ein lauffähiges Chromium waren in der lokalen Erstellungsumgebung nicht vorhanden; die tatsächliche Prüfung erfolgt durch die Pipeline. Cloudflare-Tunnelverbindung wird erst mit einem gültigen Token und Hostnamen auf deinem Server geprüft.

## v0.3: Einsatzmodal, Status, Zielkoordination und Vordisposition

Die Startseite bietet Singleplayer/Multiplayer, die Leitstellenstandorte Mödling, St. Pölten, Stockerau und Zwettl, die Dispozonen 01–06 und eine Startstunde. Notruf NÖ betreibt eine zentrale, standortübergreifende Leitstelle; die Standortwahl ist im Simulator Arbeitsplatzmetadatum, keine behauptete ausschließliche Bezirkszuständigkeit. Quelle: https://www.notrufnoe.at/unsere-standorte/. Die Zonennummern stammen aus der Nutzerabbildung; Grenzen/Zuständigkeiten sind nicht verifiziert. Nur Dispo 05 hat aktuell den Bruck/Leitha-Startbestand und automatischen Ereigniseingang. Andere Zonen sind zur Konfiguration auswählbar, ohne erfundene Fahrzeuge oder automatische Ereignisse aus fremden Gebieten. Pro Dienststelle ist die Zonennummer bearbeitbar.

Notrufe öffnen ein Einsatzmodal. Transportaufträge erscheinen elektronisch in der Liste. **Einsatz erstellen** öffnet das Formular für einen manuellen Auftrag; danach folgt das Dispositionsmodal mit Ressourcen. Adresse und Koordinaten sind manuell einzutragen; Kartenmitte dient als Koordinatenvorschlag, keine automatische Adressprüfung. Der Ressourcenbereich zeigt Typ, Status, Entfernung als Luftlinie und Dienstende, mit Filtern und einem AAO-Übernahmebutton. Er zeigt auch momentan nicht alarmierbare Ressourcen grau. Einsatzstichwort, Zusatztext, Dringlichkeit sowie simulierte Polizei-/Feuerwehranforderung können vor der ersten Alarmierung geändert werden. Diese Anforderungen werden protokolliert; es gibt noch keine spielbaren Polizei-/Feuerwehreinheiten.

| Status | Bedeutung |
|---|---|
| 1 | Frei auf Wache |
| 2 | Zum Berufungsort |
| 3 | Am Berufungsort |
| 4 | Zum Zielort |
| 5 | Am Zielort |
| 6 | Frei über Funk |
| 7 | Dienstfahrt |
| 8 | Bereitschaft, 10 Minuten Quittierungsfrist |
| 9 | Alarmiert und Quittiert |
| 0 | Außer Betrieb |

Vor Quittierung: **Alarmiert auf Wache** aus Status 1, andernfalls **Alarmiert über Funk**. Die simulierte Mannschaft setzt nach kurzer Zeit 9, danach 2; manche Alarmierungen gehen direkt auf 2. Bei Bereitschaft liegt eine 10-Minuten-Frist vor; Überschreitung erzeugt einen Hinweis ohne erfundene Quittierung. Über den Statusbutton lassen sich Mannschaftsmeldungen 9/2 zur offenen Alarmierung sowie 0/1/6/7/8 ohne laufende Versorgung simulieren. Status 0 bleibt bei manueller Abmeldung bestehen. Die tatsächliche Versorgung wird nicht durch freie Statusmeldungen abgebrochen.

Eine offene KT-Anforderung lässt sich auf eine Ressource **vordisponieren**, auch während eines anderen Einsatzes. Das reserviert sie, alarmiert sie aber nicht. Der Disponent sendet den Auftrag selbst, wenn Status **1, 5 oder 6** erreicht ist. Der Versand im Status 5 ist möglich; die bestehende Patientenübergabe endet trotzdem erst zu ihrer vorgesehenen Zeit, erst dann fährt die Mannschaft zum nächsten Auftrag. Reservierungen sind exklusiv, lösbar und persistent. Im Mehrspielermodus gelten die Betreuungsrechte auch für Reservierungen, Einsatzänderungen und Zielkoordination.

Bei einem RD-Einsatz ist zunächst kein Krankenhaus festgelegt. Nach Versorgung meldet die simulierte Mannschaft das Ziel. Für ein NÖ-Ziel folgt der Transport unmittelbar. Für ein Wiener Ziel bleibt sie am Berufungsort: Ziel-KH auswählen → **Bettenmann Wien kontaktieren** → nach simuliertem Telefonkontakt wird eine fiktive Kasusnummer `SIM-W-…` vergeben → **Per SDS** oder **Per ESApp senden** → Mannschaft bestätigt und fährt → bei Zielankunft wird die Kasusnummer bei der Aufnahme genannt. Der Ablauf verwendet Simulationszeit; bei Pause kommt keine Telefonantwort. Das ist ein simuliertes Gegenüber, keine echte Bettenanfrage, SDS-Verbindung oder ESApp-Anbindung. Elektronische Transportaufträge behalten ihr bereits beauftragtes Ziel. Unter **+ Ereignis** gibt es einen Notruf mit gezielter Wiener Zielanforderung, um diesen Ablauf auszuprobieren.

## AMPDS-Katalog und AAO-Stand

`app/data/ampds.json` enthält **2.650** Codes mit Beschreibung, Kategorie und PDF-Seite, aus dem vom Nutzer bereitgestellten `leoreport_ampds_codes_21022025.pdf`, Stand **21.02.2025**. Auslesen erfolgte aus den originalen PDF-Textobjekten, damit überlappende Tabellenzellen nicht vermischt werden. `scripts/import_ampds.py` reproduziert den Import mit pypdf (nur Entwicklung, keine Runtime-Abhängigkeit). Das vollständige PDF ist nicht Teil des Repositorys. Suche im Einsatzmodal nach Code, Stichwort oder Kategorie; die Auswahlliste zeigt höchstens 100 Treffer, die Suche erreicht den ganzen Katalog. Codezuordnung ist der PDF-Stand, keine Zusicherung einer tagesaktuellen Zuordnung.

AAO-Quelle: https://www.notrufnoe.at/ausrueckordnung-detail/, abgerufen 11.10.2026. Implementiert sind Kategoriezuordnung, KT-Typpräferenz und Organisation, BLS-rot-Präferenz mit 90 Sekunden, BLS/ALS-Typreihenfolge, bestätigter NFS bei ALS grün/gelb sowie NEF/NAH-Auswahl bei ALS orange/rot (NEF bei ALS orange bis 15 Minuten bevorzugt) und ALS-gelb-Fallback. Telemedizin/Weitergabe erzeugen zunächst keinen automatischen Rettungsmittelvorschlag; bei markierter Nichtverfügbarkeit des Sekundärsystems greift der BLS-grün-Fallback. Fahrzeug-Ausrückzeiten sind manuell gepflegte Schätzwerte (Startwert 60 Sekunden); Eintreffzeiten bleiben Simulationsschätzungen. Aktive RTW-C haben eine bestätigte NFS-Besetzung gemäß Nutzervorgabe; bei anderen Ressourcen ist NFS einzeln zu pflegen.

Der Vorschlag bildet **nicht** die gesamte einsatztaktische AAO ab: ACN/Pilotregionen, NKV/NKI-Zusatzregeln, Wetter-/Landeplatzprüfung, Großeinsatzpläne und Sonderrettung fehlen. Die Oberfläche zeigt diese Lücken. Die Entscheidung über die tatsächliche Sondersignalverwendung liegt auch laut öffentlicher AAO beim Lenker; das Simulatorfeld ist ein Dringlichkeitshinweis im Trainingsablauf. Zusätzliche `SIM-…`-Regeln sind unter Konfiguration als JSON bearbeitbar, werden gespeichert und ändern keine originale AMPDS-Tabelle. Automatische Demoanrufe sind weiterhin fiktive Szenarien; es wird kein AMPDS-Abfrageprotokoll nachgebildet.

Leaflet-Lizenz liegt unter `app/static/vendor/Leaflet-LICENSE.txt`. OSM-Attribution bleibt sichtbar. Keine Karten-Vorabrufe, Offlinepakete oder serverseitigen Tile-Proxys. Browser-Tests ersetzen OSM-Kacheln lokal, damit die Tests keine öffentlichen Kartendienste belasten. Tile-Nutzungsregeln: https://operations.osmfoundation.org/policies/tiles/.

## Fahrzeugkorrektur vom 11.10.2026

Die ausdrückliche Nutzerbestätigung ersetzt die veraltete Schwechat-LstSim-Liste. Schwechat: 77/001, 002 und 004 als RTW-C-fähige RTW (anfangs 001 aktiv); KTW 003, 005, 007, 008, 012, 013, 016, 031, 032; RTW 011 und 015; BKTW 020 (Nutzereingabe „BKWT“ normalisiert). Götzendorf: 77/030 dauerhaft RTW-C, 77/006 RTW. Leopoldsdorf: RTW 77/060. Himberg: RTW 77/050. NEF 77/099 und 53/699 bleiben; die im Screenshot ebenfalls bestätigten NEF 52/099 Baden und 64/099 Mödling sind als regionale externe Mittel ergänzt. Ihre genaue Stützpunktlage bleibt ausdrücklich zu prüfen. Der sonstige Bruck-/Hainburg-Bestand ist weiterhin ungeprüft; die alten Screenshotlisten werden nicht als aktuelle Fahrzeuge importiert. RTW-N und Martin 5 sind nicht im Startbestand.

RTW und KTW sind für Rettungs- und Transportaufträge verfügbar; der Typ bleibt für die AAO-Präferenz relevant. BKTW ist nur für Transport vorgesehen. RTW-C-Fähigkeit ist von der aktiven Besetzung getrennt. Unter Ressourcen lässt sich 001/002/004 als RTW-C besetzen. Die bisherige aktive Schwechat-Ressource wird RTW, das neue RTW-C erhält NFS. Serverprüfungen verhindern zwei RTW-C je Dienststelle, Wechsel im Einsatz oder während einer Reservierung sowie eine Herabstufung/Verlegung des festen 77/030. Beim Import gelten dieselben Regeln.

Zehn Schwechater First Responder haben fiktive Übungskennungen FR-SCH-01 bis 10; es sind keine echten Personal- oder Funkdaten. Ihr Kartenstartpunkt ist nur eine Übungsannahme. First Responder Fischamend ist eine eigene Organisation mit einem **unbesetzten Platzhalterpool**, weil die Anzahl nicht bekannt ist. Einzelne FR können manuell ergänzt werden. FR leisten Erstversorgung ohne Patiententransport, erfüllen keine RTW-/Notarzt-Anforderung und können als gesonderter optionaler Vorschlag mit geschätztem Zeitvorteil ergänzt werden.

C3 und C9 sind am Flugplatz Wiener Neustadt Ost bzw. Wien-Erdberg angelegt. Es gibt keine vermeintlich einsatzbereite Gesamtflotte Österreichs in Dispo 05. Die genannten beiden Stützpunkte werden als regionale externe Mittel nur während Bereitschaft oder ihres laufenden Einsatzes angezeigt. Der übrige Österreich-Screenshot dient als Referenz und wird nicht ungeprüft als aktuelle operative Flotte übernommen.

C3/C9: Sonnenaufgang bis Sonnenuntergang, bei frühem Sonnenaufgang frühestens 06:00; Tageslicht wird für das auswählbare Simulationsdatum anhand angenäherter NOAA-Gleichungen und Europe/Vienna (Sommer-/Winterzeit) berechnet. Außerhalb des Fensters Status 0; ein laufender Einsatz wird beendet. Flugzeit wird aus Luftlinie bei angenommenen 220 km/h plus 180 Sekunden Ausrückzeit berechnet. Aktuell arbeiten NAH als Notarztunterstützung ohne Hubschrauber-Patiententransport; Wetter, Landeplätze und Rendezvous sind noch nicht modelliert. Bodendienstzeiten sind in den neuen Anhängen nicht enthalten und bleiben explizit als unbestätigte 24h-Übungsannahme bearbeitbar.

Adressen: öffentliche Betreiberseiten des Roten Kreuzes und ÖAMTC; Kartenkoordinaten sind angenähert und bearbeitbar. Fischamend: https://www.fischamend.gv.at/Buergerservice/Gemeindeeinrichtungen/First_Responder. Flugdienst: https://www.oeamtc.at/thema/flugrettung/. Tageslichtberechnung: https://gml.noaa.gov/grad/solcalc/solareqns.PDF. Keine Echtzeitdatenanbindung.

Die Aktualisierung ergänzt bestehende Sitzungen ohne deren Einsätze zu löschen. Nur unveränderte Fahrzeuge aus der alten Foto-Startkonfiguration werden korrigiert; laufende Einsätze/Reservierungen werden abgewartet. Manuell gepflegte Datensätze werden nicht überschrieben. Die RTW-C-Besetzung wird dauerhaft gespeichert.

## v0.4: Tag-/Nachtbesetzung, FR-Wohnorte, NAH-Transport und 9E1

Nutzervorgaben: Tag 06:00–18:00, Nacht 18:00–06:00. Tagsüber sind alle besetzten Bodenressourcen verfügbar. RTW-C und NEF bleiben durchgehend besetzt mit Tag-/Nachtmannschaft; laufende Einsätze werden beim Schichtwechsel fertiggestellt. Andere RTW/KTW erhalten eine gespeicherte, pro Simulationsnacht zufällige Vorhaltung; einige zusätzliche Nacht-KTW sind möglich. Schwechat direkt hat mindestens drei eingeplante Wagen (FR/BEL zählen nicht). Götzendorf behält den festen RTW-C. Himberg und Leopoldsdorf können nachts unbesetzt sein. Keine erfundenen Reservefahrzeuge. Dies ist ein fiktiver Dienstplan; die Verfügbarkeit ist keine Garantie freier Fahrzeuge bei laufenden Einsätzen. Unter Ressourcen kann auf manuelle Dienstzeiten umgestellt werden.

FR: 10 Schwechat, 15 Fischamend mit zufällig gewählten, dauerhaft gespeicherten **fiktiven Wohnorten**, keine echten Privatadressen. Organisationszuordnung ersetzt keine FR-Wache. Freier Grundstatus ist „Bereitschaft zuhause“, ohne Status 1 und ohne 10-Minuten-Quittierungsfrist. Erst nach Alarmierung gelten die normalen Quittierungs-/Einsatzschritte. Rückkehr geht zum Wohnort. Bei 8 ohne Einsatz wird wieder FR-Bereitschaft hergestellt.

Patiententransport durch NAH ist möglich. Im Einsatzmodal lässt sich unter „Patiententransport“ die transportierende Mannschaft abstimmen; standardmäßig transportiert ein bodengebundener Wagen. Nur eine Mannschaft transportiert den simulierten Patienten. Unterstützungsressourcen kehren zurück, weitere verspätet eintreffende Wagen duplizieren den Patienten nicht. NAH nutzen Flugzeiten und Ziele mit konfiguriertem Landeplatz. Kein Wetter-/Landeplatzfreigabe- oder Rendezvousmodell.

**9E1 ist eine ausdrücklich vom Nutzer definierte Simulations-AAO**, nicht als vollständige amtliche oder medizinische eCPR-Disposition verifiziert: RTW-C + NEF + simulierte Polizeialarmierung; ein NAH ersetzt den NEF nicht. Wenn ein NAH vor Transportbeginn disponiert wird, wird er für den Patiententransport vorgesehen und eCPR Wien im Krankenhaus vorangemeldet. Das Team fährt nicht zur Einsatzstelle. Transportbereite Mannschaft meldet sich; der Disponent muss im Modal „Transport unter laufender Reanimation?“ per Funk fragen. Die Antwort kommt nach 30 Simulationssekunden. Der Szenarioausgang wird einmal zufällig gewählt (65 % fortlaufende Reanimation); Tests können den Ausgang deterministisch vorgeben. Keine medizinischen Auswahlkriterien nachgebildet.

Bei bestätigter laufender Reanimation wird ausschließlich das eCPR-Übungsziel AKH Wien mit Landeplatz zur Zielkoordination angeboten. Der abgestimmte NAH-Zielflug startet direkt ohne Bettenmann-Kasusnummer. Bodengebundene Fahrzeuge dürfen in dieser Simulation nicht unter laufender Reanimation transportieren; die Mannschaft fordert bei Bedarf einen NAH an. Ein RD-9-Code allein bedeutet noch keine laufende Reanimation. Ohne laufende Reanimation ist kein eCPR-Zielflug vorgesehen; reguläre Wiener Zielkoordination läuft weiter. Reales eCPR-Zentrum: https://notfallmedizin.meduniwien.ac.at/forschung/kooperationen-forschungsorganisationen/elso-membership/. Krankenhausannahme, Landeplatzverfügbarkeit, Polizeialarmierung und eCPR-Voranmeldung sind vollständig simuliert.

Bestehende Sitzungen erhalten die Besetzungs-/FR-Migration; laufende FR-Einsätze werden vor Änderung ihres Wohnorts beendet. Das Datenvolume bleibt erhalten. Neue Modi und Felder werden im JSON-Export gespeichert. v0.4 ersetzt die älteren README-Angaben zu 24h-Bodenannahmen, Fischamender Platzhalter und fehlendem NAH-Patiententransport.

Alarmierungsmodal: Geöffnete/fokussierte Auswahllisten bleiben trotz Hintergrundabfragen im DOM, damit AMPDS-Stichwörter ausgewählt werden können. Code und Beschreibung bilden das Alarmierungsstichwort. Generierte und manuelle Einsätze erhalten persistente, innerhalb ihrer Sitzung eindeutige Einsatznummern und fiktive Verrechnungsnummern; auch nach einem Reset werden Nummern nicht wiederverwendet. Alarmmeldungen enthalten Versorgungsstufe/AAO, Ressourcen, Patientenplatzhalter, Eventinfo, Abfragedetails, Einsatz-/Zieladresse und Zusatztext. Jede alarmierte Ressource erhält eine eigene Meldung im Simulationsprotokoll. Keine Übernahme personenbezogener Daten aus Referenzbildern; keine Verbindung zu realer Einsatzdokumentation.

Fensterlayout: Seite bleibt auf die Bildschirmhöhe begrenzt; Ressourcen, Aufträge, Kommunikation, Stammdaten und Dialoge scrollen innerhalb ihrer Bereiche. Größere Schrift, Desktop- und mobile Aufteilung. OSM-Zoom per Mausrad aktiv. Status 1 wird ausschließlich in der Heimatdienststelle zusammengefasst (Tooltip/Popup), andere Status erscheinen als Fahrzeugmarker; FR bleiben an ihren fiktiven Wohnorten sichtbar.

„Zur Startseite“ verlässt die Simulation, schließt offene Dialoge und ermöglicht die gespeicherte Sitzung fortzusetzen. Singleplayer wird beim Verlassen pausiert; Multiplayer läuft für die übrigen Disponenten weiter.

Dienststellenadressen Schwechat, Götzendorf, Himberg, Leopoldsdorf, Bruck und Hainburg anhand öffentlicher RK-Seiten geprüft (11.10.2026); Quellenlink im Datensatz. Kartenpunkte bleiben ausdrücklich angenähert und sind noch nicht gebäudegenau verifiziert. RK und NEF Mödling/Baden sind seit 15.10.2026 jeweils am gemeinsamen Betreiberstandort hinterlegt; Prüfhinweise wurden entfernt.

## v0.5: Straßenrouten, echte Adresspunkte, ETA und Funk-Nachforderungen

Neue Einsätze verwenden reale, öffentlich kartierte OSM-Adressen mit zugehörigem Adresspunkt; die dort simulierten Personen und Ereignisse sind vollständig fiktiv. Die Orte werden gleichmäßig über die vorhandenen Gemeinden verteilt. Im manuellen Einsatzformular bietet die lokale Adressliste passende Koordinaten; bei freier Adresse müssen Koordinaten weiterhin selbst geprüft werden. Kein öffentlicher Nominatim-Dienst wird als Suchfunktion eingebaut. Adressdaten: `app/data/addresses.json`, © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright. Auswahl aus Overpass, abgerufen am 11.10.2026; noch kein vollständiger NÖ-Adressbestand.

Krankenhausadressen nach offiziellen Betreiberseiten. Mödling und Hainburg verwenden die Kartenmarker der jeweiligen Betreiberseiten; Donaustadt/AKH nutzen die vom Nutzer bereitgestellten Kartenpunkte. Ein Marker bezeichnet das Krankenhausgelände, keinen abschließend geprüften Rettungseingang oder Hubschrauberlandeplatz. Dienststellen erhalten Haus-/Kreuzicons (grün bei eingeplanter Besetzung, grau ohne Besetzung); Krankenhäuser ein separates H-Icon. Frei auf Wache wird nur im Dienststellen-Popup gelistet. FR-Wohnorte bleiben fiktiv.

Bodenfahrzeuge erhalten OSRM-Straßenrouten, deren Geometrie für die Kartenbewegung verwendet wird. ETA und Straßenkilometer erscheinen im Ressourcenmodal; ETA enthält eine Ausrückzeit und gegebenenfalls die verbleibende Übergabezeit. Bereits fahrende Ressourcen zeigen ihre Restfahrzeit. NAH bleiben direkte Flugstrecken. Die AAO sortiert nach Routingzeit, sobald diese vorliegt; bis dahin ist der Vorschlag ausdrücklich vorläufig. Es gibt keine Live-Verkehrsdaten und keinen verifizierten Blaulicht-Fahrzeitfaktor.

Standard im Docker-/Portainer-Stack ist jetzt der eigene OSRM unter `http://osrm:5000`.
Der Österreich-Auszug von Geofabrik wird einmalig geladen und vorbereitet; Daten bleiben
im separaten Volume. Die App startet nach Abschluss der Datenvorbereitung und Start des
Routers. Dieser große Import wird in CI nicht vollständig ausgeführt; das echte OSRM-Profil
und die Fahrzeugbewegung werden dort auf einem kleinen Straßennetz geprüft.
`OSRM_IMAGE` wählt ein gemeinsames Image für Vorbereitung und Router.

Bei bewusst konfigurierten öffentlichen Diensten gelten deren Nutzungsbedingungen:
https://routing.openstreetmap.de/about.html und https://www.fossgis.de/ — maximal eine
Anfrage pro Sekunde, keine starke Nutzung. Öffentliche Router werden weiter auf mindestens
1,1 Sekunden Anfragenabstand begrenzt. Nur Koordinaten werden übermittelt. ETA-Abfragen
werden gebündelt; Straßenrouten werden sieben Tage in SQLite zwischengespeichert.
Die UI behält die OSM-/Routing-Hinweise. `ROUTING_ENABLED=0` ist ausschließlich ein
expliziter Übungs-/Testmodus mit schematischer Bewegung.

Funkdialog: Mannschaften können vor Ort NEF, RTW-C, weitere RTW, Polizei oder Feuerwehr nachfordern. „LEO von 77/001, kommen“ → „LEO hört“ → Nachforderung → falls nötig „Verstanden, Grund der Nachforderung? Kommen“ → Begründung → benötigte Ressource zum bestehenden Einsatz dazubuchen → Anfahrt bestätigen → Mannschaft quittiert → „LEO Ende“. Ohne verfügbares Rettungsmittel ist eine Zwischenmeldung möglich. Automatische NEF-Nachforderungen werden aus dem simulierten Zustand bzw. einer Verschlechterung ausgelöst; `REINFORCEMENTS_AUTO=0` deaktiviert nur diesen Zufallsteil. Offene Funkdialoge halten die Mannschaft am Berufungsort und werden gespeichert. Einsatzbetreuung schützt die Bedienung im Multiplayer. Kein Sprachmodell und kein medizinisches Entscheidungsmodell erzeugen die Funktexte; es sind nachvollziehbare Übungssituationen.

Referenz-JavaScript wurde als vom Nutzer bereitgestellte Ablaufreferenz gelesen. Es werden keine Implementierung, Fahrzeuggrafiken oder personenbezogenen Inhalte daraus übernommen; einzelne geografische Kartenpunkte sind als Nutzerreferenz gekennzeichnet.

## v0.6: Live-Verbindung, stabile Formulare und Meldekanäle

Die Oberfläche bezieht Zustandsänderungen über eine authentifizierte SSE-Verbindung (`/api/live`) mit automatischer Wiederverbindung. Es gibt keinen Zwei-Sekunden-Abruf von `/api/state` mehr. Serveränderungen werden unmittelbar angestoßen; der Simulationsmotor läuft weiterhin in Sekundenschritten. Die Uhr wird zwischen Serverständen lokal fortgeschrieben und beim nächsten Stand abgeglichen. Bei Verbindungsverlust wird die Fortschreibung begrenzt. Pausieren und Geschwindigkeitswechsel werden vom Server bestätigt.

Das Einsatzmodal gleicht HTML-Elemente ab, statt Formulare zu ersetzen: Texteingabe, Cursor, fokussierte Dropdowns und Ressourcenauswahl bleiben bestehen. Ressourcenfilter enthalten KTW inkl. KTW-B/BKTW, RTW inkl. RTW-C sowie einzelne RTW-C/NEF/NAH/FR. Sortiermöglichkeiten: Entfernung, ETA, Statusnummer, Kennung, Fahrzeugtyp und Dienststelle, jeweils auf-/absteigend. Entfernungen ohne berechnete Route bleiben als Luftlinie beschriftet. Unbekannte ETAs stehen bei aufsteigender ETA-Sortierung am Ende. Typ steht vor Funkkennung. Versteckte ausgewählte Ressourcen bleiben ausgewählt, Filter sind keine Abwahl.

Die manuelle Code-Auswahl startet leer und muss bestätigt werden; ein bereits vom Spieler ausgewählter Code wird bei der anschließenden Disposition übernommen. Die 27 KTR-/KTx-Transportcodes stammen aus der vom Nutzer gelieferten Ablaufreferenz; sie stehen nicht in der bereitgestellten 56-seitigen AMPDS-RD-Tabelle. Quellcodes werden nicht kopiert, nur die Code/Bezeichnungs-Zuordnung verwendet. Code `KTx-96K5` verlangt in der Simulation RTW/RTW-C; der beigestellte Arzt ist kein separat simulierter Fahrzeugbestand. Automatische Transporte nutzen passende KTR-Codes und erscheinen weiterhin elektronisch, nicht als 144-Anruf.

Einsatzmeldungen werden zur selben Simulationszeit über SDS und ESApp gespeichert und in den jeweiligen Kommunikationskanälen gezeigt, nicht als Funkansage. Nummerierte Statusmeldungen und Alarmierungs-/Quittierungszustände stehen im Kanal **Status**. Funk bleibt Mannschaftsgespräch, Rückmeldung und Nachforderung. Eine spätere Alarmansicht kann anhand des angekündigten Nutzer-Screenshots angepasst werden.

Jeder Patient besitzt einen gespeicherten fiktiven Stabilitäts-Spielwert zwischen 0 und 100. Er wird erst mit der Mannschaftsmeldung angezeigt. Die frei gewählte Spielschwelle von 45 löst im Szenario eine Notarztnachforderung aus; sie ist **kein medizinischer Score, keine Abfragerichtlinie und keine Versorgungsentscheidung**. Während der Versorgung am Berufungsort können sich Werte alle fünf Simulationsminuten ändern; während des Transports wird kein weiteres Verschlechterungs-/Rendezvousmodell vorgetäuscht. `PATIENT_EVOLUTION=0` deaktiviert diese zufällige Entwicklung; `REINFORCEMENTS_AUTO=0` unterdrückt automatische Nachforderungen für Tests. Laufende Transporte verwenden Krankenhauskoordinaten als Routenziel; verlorene Routen älterer gespeicherter Transporte werden rekonstruiert. Bei unerreichbarem Routenserver bleibt die Ressource mit sichtbarem Routinghinweis stehen.

## v0.7: Touch-Auswahl, Anrufdialog und verschiebbares Einsatzfenster

Fahrzeugzeilen behandeln Klicks und Berührungen explizit, ohne automatische Label-Weiterleitung; Kästchen, ganze Zeile sowie Leertaste/Enter unterstützen manuelle Auswahl. Die Auswahl bleibt während laufender ETA-/Status-Updates bestehen. Browserprüfungen verwenden Chromium und WebKit (Safari-Engine) mit Touch-Eingabe und laufendem Routing.

Das Einsatzfenster wird nichtmodal geöffnet, ohne verdunkelten oder unscharfen Hintergrund. Die Titelzeile lässt sich per Maus oder Touch ziehen; am Desktop unterstützt der Fensterrahmen Größenänderung. Andere Bereiche bleiben bedienbar. Neue eingehende Notrufe zentrieren die Karte mit Zoomstufe 13 auf den **simulierten** Anrufort. Echte AML-/GPS-Ortung wird nicht angebunden oder behauptet.

Automatische 144-Anrufe beginnen mit „Rettungsleitstelle Niederösterreich, wo genau ist der Notfallort?“ und einem fiktiven Anrufer mit Namen und Adresse. Per Button folgen Adresse, Ereignis, Person/Alter, Ansprechbarkeit, Atmung und Zugang/Rückruf. Antworten passen zu den vorhandenen Übungsszenarien. Der Verlauf wird sitzungsbezogen gespeichert und im Telefonkanal protokolliert. Dies ist keine originale AMPDS-Abfragesoftware und enthält keine medizinischen Handlungsanweisungen. Nach vollständiger Abfrage kann das Gespräch beendet werden; spätestens vor erfolgreicher Alarmierung sagt LEO „Wir schicken jemanden zu Ihnen“. Das Einsatzfenster schließt nach erfolgreichem Erstellen/Alarmieren; bei Fehlern bleibt es offen.

Neue Transportaufträge haben Abholzeiten nur auf :00 oder :30. Das Formular und die Einsatzbearbeitung erlauben diese Halbstundenschritte, der Server prüft sie ebenfalls. Im Auftragseingang und Einsatzfenster wird die Abholzeit rot, sobald höchstens 30 Simulationsminuten verbleiben; überfällige Aufträge bleiben rot. Bereits vorhandene Aufträge werden nicht ungefragt umterminiert.

Kartenmarker und Routen werden nach stabilen IDs abgeglichen. Bestehende Marker bleiben dieselben Leaflet-Objekte; nur Position, Icon oder Popup-Inhalt ändern sich bei Bedarf. Live-Stände löschen nicht mehr alle Kartenlayer. Offene Popups sowie vom Spieler gewählte Zoomstufe und Kartenausschnitt bleiben erhalten. Ein automatischer Wechsel erfolgt nur bei neuer Sitzung/Zonenwahl oder beim ausdrücklich gewünschten Fokus auf einen neuen Notruf. Die Nutzerreferenz wurde hinsichtlich Initialisierung und Positionsänderung bestehender Marker gelesen; die Leaflet-Umsetzung ist eigenständig.

## v0.10: Einsatzlagen, Klinikverzeichnis und Mannschaftsfunk

62 eigenständig geschriebene Einsatzlagen verwenden reale OSM-Adresspunkte des hinterlegten Bereichs und fiktive Personen. Zwei Patienten werden nach Erkundung getrennten Transportmitteln zugeordnet; ein fehlendes Fahrzeug kann per Funk nachgefordert werden. Tankwünsche im Status 6 benötigen eine Freigabe (simulierte Tankpause: fünf Minuten). Im Einsatzfenster können einzelne Ressourcen angefunkt und vor Patiententransport per Funk sowie SDS/ESApp storniert werden.

Das österreichweite Krankenhausverzeichnis enthält 304 Standorte von 254 Krankenanstalten aus dem amtlichen Verzeichnis vom 18.09.2026. Quelle: https://www.sozialministerium.gv.at/Themen/Gesundheit/Gesundheitssystem/Krankenanstalten/Krankenanstalten-und-selbststaendige-Ambulatorien-in-Oesterreich/Krankenanstalten-in-Oesterreich.html . Koordinaten stammen aus OpenStreetMap/Photon (© OpenStreetMap contributors, ODbL-1.0) oder den bereits hinterlegten Betreiberreferenzen. Gebäudezugänge und reale Annahmemöglichkeiten sind nicht bestätigt. Nicht eindeutig zuordenbare Kartenpositionen bleiben offen und lassen sich vom Sitzungsleiter in Konfiguration → Krankenhäuser bestätigen; diese Standorte werden bis dahin nicht geroutet. Automatische Notfallziele sind nahe Akutkliniken, nicht zufällige österreichweite Ziele. Geplante Transporte können zwischen Wien und NÖ sowie vom Wiener Krankenhaus zur realen Wohnadresse in NÖ führen.

Funkhinweise und Transport-Gong sind eigene synthetische Audiosignale. Eine eigene kurze Audiodatei (bis 1 MB) lässt sich browserlokal wählen; sie wird nicht auf den Server hochgeladen oder ins Repository übernommen. Der Zedge/Motorola-Ton ist nicht Bestandteil dieses Projekts.

### Unterstützungsanforderungen

Im Einsatzfenster unter **Disposition → Unterstützung** können externe KTW, RTW, RTW-C, NEF und NAH angefordert werden. Die simulierte fremde Leitstelle antwortet nach 45 Simulationssekunden; während Pause bleibt die Anfrage offen. Freie Ressourcen werden ausschließlich dem angefragten Einsatz zugebucht und über SDS/ESApp alarmiert. Gebundene, reservierte oder außerhalb der Dienstzeit befindliche Fahrzeuge werden abgelehnt. Offene Anfragen lassen sich zurückziehen; nach Zusage ist das bestehende Stornogespräch verfügbar. Die Ressource bleibt auf Karte und im eigenen Bestand sichtbar, bis sie nach Einsatzende ihren Heimatstützpunkt erreicht.

Christophorus 15 (Ybbsitz, Dispo 01) und Christophorus 16 (Oberwart, Burgenland) sind als externe Unterstützungsressourcen vorgegeben. Standortadressen: https://www.oeamtc.at/standorte/niederoesterreich/ und https://www.oeamtc.at/standorte/burgenland/. Kartenkoordinaten noch prüfen; C15 laut rth.info (https://www.rth.info/stationen.db/station.php?id=124), C16 angenähert. Für beide gilt im Simulator Tageslichtdienst frühestens ab 07:00; Verfügbarkeit, 45-Sekunden-Rückmeldung und Geschwindigkeit sind Simulationsannahmen, keine Live-Daten. Weitere externe Bodenfahrzeuge können unter Einstellungen mit tatsächlicher Kennung, Dienststelle, Dienstzeit, Bundesland und Dispozone ergänzt werden. Andere Dispozonen oder Dienststellen mit „Nur über Unterstützungsanforderung“ werden nicht automatisch in die lokale AAO aufgenommen. MTW und GSD-Fahrzeuge werden nicht als Einsatzmittel ergänzt; die beiden BEL aus dem ursprünglichen Fotobestand wurden aus freien Startkonfigurationen entfernt.


### Dispo 05: Fahrzeugrecherche und Bestandsmigration

Version 0.11 ergänzt 91 recherchierte Rettungs- und Transportfahrzeuge zu den 55 bestehenden Ressourcen. Enthalten sind die Bereiche Baden, Mödling und Bruck/Leitha sowie ASB Traiskirchen–Trumau, Steinfelden–Schönau–Leobersdorf, Ebreichsdorf und Gaaden–Wienerwald. MTW und GSD werden nicht importiert. Die bestätigte Schwechater Flotte und ihre RTW-C-Fähigkeiten bleiben unverändert.

Die [Rechercheliste](docs/dispo05-fahrzeugrecherche.csv) enthält jede ergänzte Kennung, den verwendeten Übungstyp, die Dienststellen-ID und einen Prüfvermerk. Betreiberseiten haben Vorrang; andere Kennungen stammen aus historischen Communitybeständen und den vom Nutzer bereitgestellten Bestandsfotos. Sie sind ausdrücklich **keine bestätigte aktuelle Dienstliste**. Unbestätigte frühere RTW-N werden als RTW geführt; eine NFS-Besetzung wird nicht behauptet. Nicht gebäudegenau bestätigte Dienststellenpunkte sind gekennzeichnet.

Die Ergänzung erfolgt beim nächsten Serverstart einmalig auch für gespeicherte Sitzungen. Bereits vorhandene oder manuell bearbeitete Fahrzeuge werden nicht überschrieben. Danach gelöschte Kandidaten bleiben auch nach Neustart und Übungsreset gelöscht. Dienstzeiten sind simuliert, keine Echtzeitdaten. Neu ergänzte Dienststellen halten nachts bis zu drei vorhandene Fahrzeuge vor; tagsüber sind alle besetzten Fahrzeuge verfügbar.

Das Einsatzfenster hat getrennte Reiter für Disposition, zugeordnete Kräfte, Unterstützung und Meldung. Nur die Ressourcenliste scrollt; längere Inhalte werden in Seiten aufgeteilt. Beim Öffnen und Tabwechsel startet die Liste oben; beim Öffnen ist Entfernung aufsteigend voreingestellt. Ausgewählte Zeilen sind grün.


Ressourcen-Icons können unter Konfiguration mit Vorschau einzeln zugeordnet werden; Änderungen betreffen ausschließlich die Grafik und lassen laufende Einsätze unverändert. PNG, JPEG und WebP bis 20 MB werden im Browser auf höchstens 512 × 256 Pixel und 512 KiB PNG verkleinert. Fahrzeuge am Berufungsort werden am Einsatzmarker nach Typfarbe gezählt und haben dort keinen separaten Fahrzeugmarker.

Beim Öffnen des Einsatzfensters steht Kommunikation zuerst, danach Disposition mit AMPDS-Auswahl, Einsatzdaten und getrennte Reiter für Nachforderung und externe Unterstützung. Noch nicht gewählte Alarmierungsstichwörter sperren die Ressourcenauswahl. Bei fehlenden Straßenroutendaten wird eine sofortige, ausdrücklich ungefähre ETA angezeigt. Offene Matrix-Anfragen werden nach zwölf Sekunden als Fehler markiert; später eintreffende Straßendaten ersetzen die Schätzung. Tatsächliche Straßenfahrten warten weiterhin auf Routengeometrie, damit Fahrzeuge bei ausgefallenem Routing nicht querfeldein fahren.


### Fachabteilungen und Mannschaftsziel

Betreiber-Abteilungsübersichten für 24 NÖ-Standorte sowie Klinik Landstraße und Donaustadt sind als datierte Profile hinterlegt. Zwei weitere recherchierte NÖ-Standorte bleiben ausdrücklich ungeprüft. Die Klinikliste und Karten-Popups zeigen die erfassten Abteilungen. Die Mannschaft wählt ihr Ziel nach dem vor Ort festgestellten Fachbedarf; ein ausdrücklich vorgegebenes Szenarioziel bleibt erhalten. Wiener Ziele werden weiterhin über den simulierten Bettenmann koordiniert.

Für Erwachsenen-Traumatologie wird Baden im regionalen Umfeld bevorzugt. Mödling gilt hierfür laut Betreiberhinweis Mo–Fr 08–13 Uhr als verfügbar; Kinder bis zehn Jahre bleiben dort durchgehend im Übungsmodell versorgbar. Bei stabilen dermatologischen Befunden wird im regionalen Umfeld Landstraße bevorzugt. Das sind Simulationsregeln, keine reale Zuweisungsanweisung und keine Echtzeit-Auskunft über Betten, Sperren oder Aufnahmefähigkeit. Ungeprüfte Profile werden nicht als verifiziert ausgegeben.

Die Nutzergrafiken vom 14.10.2026 sind Standard für RTW/RTW-C, NEF und Christophorus. Bereits individuell gewählte eigene Grafiken bleiben erhalten; explizite Icon-Zuordnungen sind auch beim RTW-C-Wechsel geschützt. Die Vordispositionsliste zeigt Heimatdienststelle und Entfernung zum Abholort, nach Entfernung aufsteigend.


Kartenansicht entsprechend der vom Nutzer bereitgestellten LstSim-JavaScript-Referenz: Startzoom 13, Maximalzoom 18, kleinere Fahrzeugicons unter Zoom 12. Die ausgewählte Leitstellenregion wird zentriert; Live-Updates verändern den gewählten Ausschnitt nicht. Sichtbare Fahrzeugbeschriftungen enthalten die aktuelle Statuszahl (S2, S4, S6 oder S7).

### Simulierte Ausrückzeit

Bodenfahrzeuge bekommen pro Auftrag eine stabile, gestaffelte Ausrückzeit. Tag ist 06:00–18:00, Nacht 18:00–06:00. Die Zeiten sind Übungsparameter nach Nutzerwunsch, keine Aussage über gesetzliche Vorgaben.

| AMPDS-Stufe | Tag | Nacht |
|---|---:|---:|
| A / regulärer Transport | 85–120 s | 125–180 s |
| B | 60–84 s | 90–124 s |
| C | 40–59 s | 60–89 s |
| D | 25–39 s | 30–59 s |
| E | 15–24 s | 15–29 s |
| 9E1 | 15–25 s | 15–25 s |

Frei über Funk: 5–15 Sekunden. AAO und ETA enthalten dieselbe Vorbereitung wie die automatische Alarmierung. Status 9 beendet die Vorbereitung nicht; manche Mannschaften fahren direkt mit Status 2 ab. Die Fahrzeugliste zeigt währenddessen einen Countdown. Eine manuell gesetzte Status-2-Meldung gilt als tatsächliche Abfahrt. Krankenhausübergabe wird zusätzlich abgewartet; bei Bereitschaft beginnt die Vorbereitung nach Quittierung. NAH behalten ihre konfigurierte Startvorbereitung. Bodenfahrzeuge verwenden automatisch diese Tabelle statt des früheren pauschalen Fahrzeug-Schätzwerts.

### MANV, Sichtung und Notarztbegleitung

Vier eigene fiktive MANV-Szenarien (Busunfall, Rauch im Wohnhaus, Mehrfachunfall, Veranstaltung) mit 6/8/10/12 Patienten können als Anruf über „Ereignis auslösen“ gestartet werden und sind Teil des automatischen Ereigniskatalogs. Die tatsächliche Lage wird erst nach der Erkundungszeit der Mannschaft sichtbar.

Der Reiter „Patienten / Sichtung“ führt jede Person getrennt: Zustand, Spiel-Sichtungskategorie, Transportfahrzeug und behandelndes Notarztmittel. SK I (<45 %), SK II (45–69 %) und SK III (ab 70 %) sind fiktive Spielkategorien, keine klinische Sichtungsanleitung. Freie Transportplätze werden zuerst den Patienten mit dem niedrigsten Zustand zugeordnet. NEF und NAH versorgen jeweils einen der kritischsten Patienten; die Zuordnung wird nach Zustandsänderungen neu geprüft. Ein Notarztmittel versorgt mehrere Patienten gemeinsam. Solange mindestens ein NEF oder NAH am BO ist, verschlechtert sich dort kein Patient. Nach der Erkundung steigen die Zustände mit einer nach Anzahl der Notarztmittel und Patienten skalierten Rate; zusätzliche Notarztmittel beschleunigen die Versorgung. Der Schwerpunkt wechselt etwa alle 30 Simulationssekunden zwischen ähnlich kritischen Patienten, deutlich kritischere Patienten haben Vorrang. Ohne Notarztmittel können sich Zustände verschlechtern. Die Spielwerte bleiben begrenzt auf 0–100.

Auch ein NEF kann weitere Notarzt- und Transportmittel über die interaktive Funkabfrage nachfordern. Bereits disponierte Notarztmittel zählen für die Deckung des Bedarfs; ein bestätigtes Funkgespräch kann nicht mehrfach dieselbe Ressource als neue Verstärkung verwenden. Die MANV-AAO berücksichtigt nach der Lagemeldung alle noch am BO befindlichen Patienten.

Ein NEF besitzt keine Patiententransportkapazität. Bei einem kritischen bodengebundenen Transport kann das behandelnde NEF ärztlich begleiten und ist dann bis zur Übergabe gebunden. Ein NAH kann zusätzlich selbst einen Patienten transportieren. Andere Notarztmittel bleiben bei verbleibenden Patienten am BO. Das beim Transportbeginn vereinbarte Ziel wird pro Fahrzeug gespeichert, damit spätere Zielmeldungen das laufende Ziel nicht ändern.

Nach Ankunft am Ziel sind Rettungsmittel für 180 Simulationssekunden in Status 5 zur Übergabe. Danach fahren sie selbstständig in Status 6 zur Heimatdienststelle zurück und können unterwegs erneut disponiert werden. Ein Einsatz wird erst abgeschlossen, wenn sämtliche Patienten übergeben und die verbliebenen Kräfte freigegeben sind. Sichtung, Behandlungszuordnung und Begleitung bleiben auch nach einem Serverneustart erhalten.

Die Anrufabfrage verwendet drei kompakte Buttons: „Ort und Ereignis“, „Patienten · Bewusstsein & Atmung“ und „Zugang und Rückruf“. Jeder Button erzeugt eine zusammengefasste Frage/Antwort. Alle sechs Themen und Antworten bleiben für die gemeinsame Disposition gespeichert; bereits laufende ältere Gespräche können mit der kürzeren Abfrage fortgesetzt werden.

### Flüssige Ressourcenbewegung, Signalfahrt und Auftragsübersicht

Die Karte zeichnet aktive Fahrzeugmarker über `requestAnimationFrame` zwischen den Live-Snapshots weiter. Bodenfahrzeuge folgen dabei der gelieferten Straßengeometrie einschließlich der kumulierten Streckenlängen; NAH folgen ihrem Flugweg. Nur Markerpositionen werden pro Bild aktualisiert, keine Formulare oder Popup-Inhalte. Die Simulation und Statuswechsel bleiben serverseitig verbindlich. Pausieren stoppt die Animation, bei Verbindungsunterbrechung wird höchstens drei Echtzeitsekunden vorausgerechnet. Veraltete Positionen auf derselben Fahrt setzen Marker nicht rückwärts; ausgeblendete Fahrzeuge werden aus der Animation entfernt.

Neue RD-Aufträge starten mit vorausgewählter Signalfahrt, KT-Aufträge ohne. Die Auswahl steht im Reiter „Disposition“ und bleibt beim Wechsel des AMPDS-Codes erhalten. Nach der ersten Alarmierung gilt diese Einstellung für weitere Alarmierungen; bereits alarmierte Fahrzeuge behalten ihre eigene Einstellung. Unter „Zugeordnet“ kann eine Bodenressource wegen benötigtem/nicht benötigtem Sondersignal angefunkt werden. Erst nach Mannschaftsantwort und bestätigter Anweisung wird umgestellt, mit Funkabschluss sowie SDS/ESApp-Nachricht. Der vorhandene Fahrweg bleibt erhalten, die Restfahrzeit wird angepasst; Blaulicht und ETA folgen dem neuen Modus. Ein NEF-Begleitverbund wechselt gemeinsam. Rückfahrten in Status 6 bleiben ohne Sondersignal. Das Flugzeitmodell der NAH bleibt unabhängig.

Aufträge sind anfangs eingeklappt. Der Pfeil blendet die zugeordneten Ressourcen und deren Status ein; höchstens ein Auftrag ist gleichzeitig ausgeklappt. Der Auftragstitel öffnet weiter das Einsatzfenster. Die Aufklappauswahl bleibt bei Live-Updates erhalten.

Im Mehrspielermodus schließt sich das offene Eingangsfenster bei anderen Spielern, sobald jemand den Anruf übernimmt. Sie erhalten „Benutzer XY hat den Einsatz übernommen“. Ein später bewusst zum Mitlesen geöffnetes Fenster wird nicht automatisch geschlossen.

MANV-Nachforderungen verwenden gemeinsame Versorgungskapazität statt eines NEF je kritischem Patienten: ein Notarztmittel kann im Spiel bis zu sechs Patienten gemeinsam betreuen; zusätzliche automatische Notarztnachforderungen entstehen nur bei einer größeren kritischen Lage. Vorhandene und anfahrende Notarztmittel zählen zusammen. Mehr freiwillig disponierte Notarztmittel beschleunigen die Besserung auch unterhalb dieser Schwelle.

Bei einer Nachforderung kann die Disposition nach der Abfrage „Negativ · keine Kräfte verfügbar“ antworten. Die Mannschaft bestätigt, das Gespräch endet und dieselbe Art automatischer Nachforderung bleibt für den Einsatz unterdrückt. Weitere Ressourcen können weiterhin manuell disponiert werden. Im Reiter „Nachforderung“ lässt sich die automatische Anforderung wieder freigeben. Bei abgelehntem Notarztmittel bleibt der Patiententransport mit den vorhandenen Mitteln möglich.


### Einsatzübersicht, Gemeindepools und Funkabschluss

- Links steht eine eigene, hohe Aufklapptaste. Es bleibt jeweils ein Auftrag ausgeklappt. Einsatzdauer (ab erster Alarmierung, davor ab Eingang) erscheint dort und im Modal; die Betreuung wird im Mehrspielerbetrieb deutlich hervorgehoben.
- Nach Freimeldung entfernt die Simulation die Ressource aus der aktuellen Einsatzzuordnung. Verlässt das letzte gebundene Rettungsmittel den Auftrag, wird er abgeschlossen und verschwindet aus den offenen Aufträgen – auch ohne Patiententransport und unabhängig von Polizei/Feuerwehr. Protokolle bleiben intern erhalten.
- Offene Nachforderungen lassen sich jederzeit über **LEO Ende** schließen, auch nach Abfahrt oder Freimeldung. Das Gespräch zu beenden alarmiert oder storniert keine Ressource. Automatische Lage-/Stabilitätsmeldungen werden mit „Hier LEO, verstanden, Ende“ quittiert.
- Ein vollständig erfasster Transport mit reservierter, verfügbarer Ressource erhält ab 30 Minuten vor Abholung eine grüne Kennzeichnung und die Taste **Alarmieren**. Diese sendet den vorhandenen Auftrag direkt per SDS und ESApp; Besitz- und Rollenrechte gelten weiter.
- BKTW/KTW-B sind nur bei ausdrücklich **gehfähigen** Transportpatienten auswählbar. Tragstuhl, liegend und RD sind gesperrt, auch in AAO, Vordisposition und direkter API-Disposition. Ohne eindeutigen Transportcode wird keine Gehfähigkeit angenommen. Status 7 für Dienstfahrten bleibt möglich.
- Bereitschafts-FR werden als Gemeindepool angeboten, nicht als einzelne fiktive Privatpersonen. Die Auswahl zieht den nächstgelegenen freien FR aus diesem Pool. FR quittieren nicht mit Status 9, sondern wechseln beim Ausrücken direkt auf Status 2 und erhalten dabei eine einsatzbezogene Nummer. Fiktive Übungsstärke: Schwechat 10, Fischamend 15, weitere im Bestand vertretene Gemeinden/Bereiche jeweils 5; keine Aussage über echte Personalbestände. Die Bereitschaftsorte liegen fiktiv im Umkreis der jeweiligen Dienststelle.
- Fahrtrouten erscheinen bei Fahrzeugauswahl oder für Ressourcen eines geöffneten/ausgeklappten Einsatzes. Standardmäßig bleiben sie ausgeblendet. Für 144-Anrufe gibt es einen lokal erzeugten Klingelton, bis der Anruf übernommen wird; in den Klangeinstellungen abschaltbar. Browser benötigen zuvor eine Benutzerinteraktion zur Audiofreigabe.


### Polizei, Feuerwehr, Einsatzupdates und Funkablauf

Polizei und Feuerwehr besitzen einen eigenen, **fiktiven Übungsbestand** in `agency_units`. Kennungen und Bereitschaftspunkte sind keine echten BOS-Bestands- oder Standortangaben. Je bereits positioniertem lokalen RD-Bereitstellungsbereich gibt es zunächst eine Polizeistreife und ein Feuerwehr-Rüstlöschfahrzeug. Die grafischen Fahrzeuge sind eigene SVG-Illustrationen. Die Disposition fordert Unterstützung bei einer simulierten Fremdleitstelle an; sie erhält die nächstgelegene freie Einheit. Bei ausgelastetem Bestand wartet die Anforderung auf eine freie Einheit.

Im Reiter **Polizei & Feuerwehr** lassen sich Unterstützung anfordern, Aufgaben ändern und Einheiten abbestellen. Einheiten durchlaufen Alarmierung, Ausrücken, Straßenanfahrt, Eintreffen, Aufgabe und Rückfahrt. Bei aktiviertem Routing warten sie auf eine echte Straßenroute; sie fahren bei einem Routerfehler nicht querfeldein. Bewegte Fahrzeuge erscheinen auf der Karte, vor Ort stehen P-/F-Zähler am Einsatzmarker. Routen erscheinen nur nach Auswahl. Aufgaben und Zeitansätze sind Spielregeln, keine realen Einsatzstandards: Polizei Absicherung/Erhebungen oder Gefahrenbereich sichern; Feuerwehr Tragehilfe, technische Menschenrettung oder Brandbekämpfung/Zugang.

Ein unsicherer Gefahrenbereich bzw. fehlender Zugang verschiebt die Lageaufnahme. Eine ausstehende technische Menschenrettung verhindert den Patiententransport. Einheitenabstellung allein hebt eine ungelöste Sperre nicht auf; eine passende Aufgabe muss durchgeführt werden. Nach Freigabe nimmt die Rettungsmannschaft ihre Arbeit wieder auf. Polizei und Feuerwehr halten einen sonst abgeschlossenen RD-Einsatz nicht offen und rücken nach Abschluss oder eigener Freigabe wieder ein. 9E1/gesetzte Unterstützungsfelder und bestätigte Funknachforderungen erzeugen tatsächliche simulierte Unterstützungsanforderungen.

**Zusatztexte** sind unabhängig von Code und Disposition jederzeit bearbeitbar. Optional gehen Änderungen gleichzeitig als Einsatzupdate über SDS und ESApp an die aktuell zugeordneten Rettungsmittel. Paralleländerungen werden über den vorherigen Text erkannt, damit ein anderer Benutzer nicht versehentlich überschrieben wird. Der Zusatztext steht auch im eingeklappten Auftrag direkt unter Code und Bezeichnung. Links teilen sich Aufklappen und Kartenfokus einen Tastenbereich; der Kartenfokus zentriert auf Zoom 14, ohne das Einsatzfenster zu öffnen. Aus Status 6 alarmierte Fahrzeuge bleiben während Alarmierung und Quittierung am aktuellen Standort sichtbar; ab Wache alarmierte Fahrzeuge bleiben ausgeblendet.

**Lagemeldungen** beginnen als Sprechwunsch. Nach „Hier LEO“ nennt die Mannschaft die simulierte Lage, tatsächlich vor Ort befindliche Kräfte und gegebenenfalls entbehrliche anfahrende Ressourcen. Die Disposition wählt zu stornierende Kräfte ausdrücklich aus; transportierende oder weiterhin benötigte Einheiten werden nicht storniert. Der Abschluss lautet „LEO verstanden, Ende“. Der frühere generische Satz „Notarztversorgung erforderlich, Notarztmittel bereits disponiert“ wird nicht mehr als Lagemeldung verwendet.

Funkmeldungen werden serverseitig in einer persistenten Warteschlange mit standardmäßig **2 echten Sekunden Abstand** freigegeben – unabhängig von Pause und Zeitraffer; alle Mitspieler sehen denselben Ablauf. Statusmeldungen, SDS/ESApp und Telefonprotokolle bleiben davon unabhängig. `RADIO_INTERVAL` erlaubt einen anderen Abstand; automatisierte Fachtests setzen ihn auf 0, der zusätzliche Browser- und Warteschlangentest prüft den tatsächlichen 2-Sekunden-Abstand. Nach einem Neustart wird eine überfällige Warteschlange weiter einzeln ausgespielt.

Statusfarben: 1 dunkelgrün, 6 hellgrün, 2 gelb, 3 rot, 4 rosa, 5 lila; Alarmierung und Quittierung rot auf Weiß.

Automatisch eingehende Krankentransporte tragen ihren Transportcode bereits bestätigt ein. Auftragstyp, Gehfähigkeit/Tragstuhl/Liegend und Code werden gemeinsam erzeugt; es werden nur vorhandene Katalogcodes verwendet. Die Disposition kann direkt vordisponieren. Manuelle Aufträge und Notrufe behalten die freie Codewahl ohne Vorauswahl. Noch unbearbeitete elektronische Altaufträge werden beim Laden entsprechend ergänzt.

Bei Alarmierung eines RD-9-Codes oder Reanimationsstichworts erscheint die virtuelle Ressource **eCPR AKH alarmiert** im Einsatz. Das gilt auch bei Umklassifizierung eines bereits laufenden Einsatzes. Ab Beginn des Patiententransports steht dort **eCPR AKH bereit**; nach Übergabe/Einsatzabschluss wird sie entfernt. Sie ist kein Fahrzeug, zählt nicht zur AAO-Besetzung und hält Einsätze nicht offen. Die Mannschaft bestätigt den Transport unter laufender Reanimation über Funk; der NAH fliegt dann direkt zum AKH ohne Kasusnummer. Für reguläre Wiener Ziele bleibt der Bettenmann-Ablauf erhalten. Laufende Alarmierungsstichwörter können über die Disposition geändert werden; dabei bleiben Patientenzustand, Fahrzeuge und aktive Routen erhalten, und die Mannschaft erhält ein SDS-/ESApp-Update.

### Straßenanschluss bei fehlender Route

Bei OSRM `NoRoute` / `NoSegment` fragt der Simulator an Start und Ziel jeweils bis zu vier nahe Straßenpunkte ab. Er prüft bis zu acht Kombinationen nach Abstand und verwendet die erste tatsächlich befahrbare Verbindung. Dabei darf ein Straßenpunkt höchstens 2 km vom ursprünglichen Punkt entfernt sein. Das Einsatzmittel wird einmalig an den Beginn dieser Straßengeometrie versetzt; der Vorgang steht im Systemprotokoll. Danach fährt es entlang der berechneten Straße, mit tatsächlicher Strecken-ETA und dem gewählten Signalfahrtfaktor. Auch Polizei-/Feuerwehrfahrten nutzen diesen Ablauf. Die Einsatzadresse bleibt unverändert. Ein Routenserver-Ausfall führt weiterhin zu sichtbarem Fehler und erneutem Versuch, nicht zu einer erfundenen Fahrt querfeldein.

### Einsatzvielfalt und zugeordnete Behörden

Der Katalog enthält zusätzlich 138 selbst verfasste fiktive Alltags-, Notfall- und Fehlfahrtvignetten in `app/data/incidents-zone5.json`. Codes werden gegen den vorhandenen NÖ-Codekatalog geprüft. Telefonische Beobachtungen und Feststellungen der Mannschaft bleiben getrennt: eine vermeintlich hilflose Person kann sich erst nach Erkundung als Fehlalarm herausstellen. Die Szenarien werden in zufällig gemischten Durchläufen ohne Wiederholung ausgewählt; die Reihenfolge überlebt einen Neustart. Ebenso werden die verfügbaren Gemeinden durchgemischt statt Einsätze auf wenige Orte zu beschränken. Es handelt sich um Spielvignetten, kein originales AMPDS-Abfrageprotokoll und keine echten Patientendaten.

Polizei und Feuerwehr stehen zusätzlich unter **Zugeordnet** und in den aufgeklappten Aufträgen, mit **Alarmiert / Ausrücken**, **Auf Anfahrt** oder **Am Einsatzort**. Ihre Einheiten bleiben von den nummerierten RD-Statuswerten getrennt. Abbestellte oder freigegebene Einheiten verschwinden aus dieser Zuordnung.

### Adressabdeckung und Einsatzfrequenz

Die gebündelte OSM-Adressauswahl enthält 2602 echte Adresspunkte bzw. Gebäudemittelpunkte aus 84 Gemeinden im Spielgebiet (Baden, Mödling, Bruck/Leitha und Ebenfurth). Sie ist eine Spielauswahl, kein vollständiges Adressregister und keine amtliche Abgrenzung der Dispozone. Straßen-/Ortsnamen und Hausnummern stammen aus OSM, pro Eintrag mit OSM-ID und Koordinaten. Ortsadressen wie „Furth 67“ sind ohne erfundene Straße enthalten. Die Gemeinde-Reihenfolge wird durchgemischt, sodass nicht nur Schwechat Einsätze erhält; nach einem vollständigen Durchlauf beginnt eine neue Mischung. Der Abruf läuft nur beim expliziten Recherche-Workflow; zur Laufzeit werden die mitgelieferten Daten verwendet. Quellen: © OpenStreetMap contributors, ODbL-1.0; Suchfenster über Wikipedia GeoData, Sommerein über die Kontaktkarte der Gemeinde.

Unter Einstellungen → Einsatzfrequenz können Gastgeber Notrufe und Transportaufträge unabhängig auf 0–120 pro Simulationsstunde einstellen. Die Abstände schwanken um den eingestellten Durchschnitt. **Nur 144-Anrufe** schaltet automatische Krankentransporte aus; vorhandene Aufträge bleiben erhalten und manuelle Transporte sind weiter möglich. Änderungen werden für die Sitzung gespeichert, mit Mitspielern geteilt und bei Pause nicht nachgeholt. Standard: gemeinsam 3 Notrufe/h und 4 Transporte/h, Calltaker/Disponent 6 und 6.

### MANV-Sichtungsfahrzeug

Das ersteintreffende RD-Fahrzeug bzw. der erste NAH übernimmt Sichtung und Koordination; FR übernehmen diese Funktion nicht. Während der ersten Sichtung übernimmt das Sichtungsfahrzeug noch keine Patientenversorgung. Sobald die Mannschaft die Lageaufnahme und Patientenliste abgeschlossen hat, kann es selbst versorgen und – als RTW/KTW/NAH – einen Patienten transportieren. Ein NEF kann nach Sichtung versorgen und begleiten, bleibt aber ohne eigene Transportkapazität. Das Fahrzeug zählt dann auch in AAO und Nachforderung zur verfügbaren Versorgung bzw. Transportkapazität; sechs Patienten benötigen somit insgesamt sechs Transportmittel. Die Funkkoordination geht bei Abfahrt an die frühest eingetroffene verbleibende Einheit über, ohne neue Sichtung. Bereits gesichtete laufende Einsätze werden beim Laden entsprechend freigegeben. Weitere Kräfte versorgen die Patienten wie bisher; Notarztmittel verteilen ihre Versorgung dynamisch. Nur das Sichtungsfahrzeug gibt die gebündelte MANV-Lagemeldung und Nachforderung ab. Bereits vor Ort und auf Anfahrt befindliche Kräfte werden für den Bedarf berücksichtigt. Die Disposition kann „Negativ · keine weiteren Kräfte verfügbar“ bestätigen und spätere Nachforderungen bei Bedarf wieder freigeben. Verlässt das Sichtungsfahrzeug den Einsatz, übernimmt die nächstfrüh eingetroffene verbleibende Einheit. Das sind Simulationsregeln, keine Darstellung einer verbindlichen realen MANV-Führungsorganisation.

### Hinweise auf Wiener Zielabklärung

Solange eine Mannschaft auf eine Wiener Ziel-/Kasusabklärung wartet, bleibt oberhalb der Aufträge eine Warnleiste sichtbar – unabhängig vom Notruf-/Transportfilter. Der eingeklappte Auftrag erhält eine gelbe Markierung und eine direkte Taste zum Reiter **Ziel & Transport**. Die Warnung unterscheidet **Kasusnummer erforderlich**, **Bettenmann angefragt** und **Kasusnummer liegt vor – an Mannschaft senden**. Nach zehn Simulationsminuten seit Zielanforderung wird sie rot.

Ein eigener lokal erzeugter Hinweiston ertönt beim erstmaligen offenen Bedarf, bei vorliegender Kasusnummer und einmal erneut nach zehn Minuten. Die Browser-Einstellung für diesen Ton ist unabhängig von Transportgong und Funkton; die gemeinsame Lautstärke gilt weiterhin. Hinweiszustände werden pro Spieler im Browser gespeichert, damit Live-Updates und Neuladen nicht fortlaufend denselben Ton auslösen. Schon beim Laden wartende Aufträge sind sichtbar und erhalten ihren ersten Hinweis; der Browser benötigt für Audio gegebenenfalls zunächst eine Benutzerinteraktion. Versand der Kasusnummer bzw. Einsatzabschluss entfernt die Warnung. Direkte eCPR-Flüge bleiben ohne Kasusnummer und erzeugen keine solche Warnung.

### Verfügbarkeit bei Vordisposition

Neue Vordispositionen sind nur für besetzte lokale Transportmittel in **Status 1, 5 oder 6** möglich. In der Auswahlliste bleiben Fahrzeuge mit Status 2/3/4/7/8/9/0 sowie noch nicht quittierter Alarmierung sichtbar, sind jedoch deaktiviert. Ein Statuswechsel während der Auswahl sperrt auch die Vordisponieren-Taste; der Server prüft die Verfügbarkeit vor einer Änderung erneut. Eine abgelehnte Auswahl löst keine bestehende gültige Reservierung. Status 5 bleibt zulässig, die laufende Patientenübergabe wird wie bisher vor Abfahrt beendet.

### Kartensymbole und schneller Straßen-Fallback

Bodenfahrzeuge erscheinen mit 64 × 32 Pixeln, NAH mit 84 × 48 Pixeln. Unter Zoom 12 bleiben mindestens 56 × 28 bzw. 74 × 42 Pixel erhalten; weiteres Herauszoomen verkleinert sie nicht mehr. Polizei und Feuerwehr verwenden dieselbe größere Bodendarstellung.

Routen für tatsächlich fahrende Ressourcen und ETA-Tabellen haben getrennte Hintergrundarbeiter. Eine langsame Tabelle blockiert damit keine Abfahrt; aktive Fahrten haben reservierten Platz in der Warteschlange. Beim Straßen-Fallback wird zuerst der nächste Start-Straßenpunkt gegen das unveränderte Ziel geprüft, bevor zusätzliche Zielpunkte und Kombinationen abgefragt werden. Straßenpunkte werden pro Router zwischengespeichert. Nach einer fehlgeschlagenen Fahrtroute wird nach fünf statt sechzig Sekunden erneut versucht; ein HTTP-Aufruf wartet höchstens vier Sekunden. Ein späterer Matrixfehler überschreibt keine bereits bestätigte Fahrtroute/ETA. Die Karte übernimmt den Straßenanschluss mit dem nächsten Live-Update, sobald die befahrbare Route bestätigt ist; Einsatzadresse und geometrische Begrenzung auf 2 km bleiben erhalten.

Die öffentliche FOSSGIS-Instanz behält mindestens 1,1 Sekunden zwischen HTTP-Anfragen, gemeinsam für beide Arbeiter. Für einen eigenen Router wie `http://osrm:5000` entfällt diese künstliche Pause. Eine sofortige Teleportation ohne Routerantwort wird nicht vorgetäuscht; bei Ausfall des Routers bleibt die Fahrt wartend. OSRM-API-Grundlage: https://project-osrm.org/docs/v5.24.0/api/ (Nearest, Route, Hints).

### Einheitlicher Sprechfunk

Rettungsfunk verwendet **LEO** und das Schema **gerufene Stelle von rufender Stelle, Nachricht, kommen**. Beispiel eCPR-Abfrage: „Christophorus 9 von LEO, kommen.“ → „LEO von Christophorus 9, hört, kommen.“ → „Christophorus 9 von LEO, transportiert ihr unter laufender Reanimation? Kommen.“ → „LEO von Christophorus 9, laufende Reanimation, Transport unter laufender Reanimation vorgesehen. Kommen.“ → „Christophorus 9 von LEO, verstanden. Ende.“ Derselbe Aufbau gilt für Nachforderungen, Lage-/Zielmeldungen, Transportabstimmung, Tankfreigaben, Sondersignal und Storno. Die zentrale Textaufbereitung ergänzt fehlendes „Kommen“ und vereinheitlicht NAH-Kurznamen. Ausstehende alte Funktexte werden beim Ausspielen ebenfalls aufbereitet.

SDS/ESApp bleiben Datenmeldungen, Statuswechsel eigene Statusmeldungen. Anruferdialoge und Telefonate mit anderen Organisationen bleiben getrennt vom Rettungsfunk. Die vorhandene Zwei-Sekunden-Warteschlange gilt weiter; die Simulation bildet keinen verbindlichen Echtfunk-Lehrgang ab.

### Fahrzeug-Kontextmenü

Klick/Rechtsklick auf eine Fahrzeugzeile oder Enter/Leertaste öffnet ein bei Live-Updates stabiles Menü. **Position auf Karte anzeigen** zentriert auf Zoom 14 und hebt den Ort fünf Sekunden hervor; stationäre Ressourcen erhalten dadurch keinen zusätzlichen Fahrzeugmarker. **Zur Wache einrücken** und **Standort halten** sind Funkaufträge für freie Ressourcen in Status 6 oder 7. Halten entfernt die aktive Fahrt und stoppt die Bewegung am aktuellen Standort; Zustand und Position bleiben über Neustarts erhalten. Einrücken bzw. eine neue Alarmierung hebt den Halt auf. Gebundene Fahrzeuge müssen zuerst über den Einsatz storniert werden; Patientenversorgung, Transporte und laufendes Tanken lassen sich damit nicht abbrechen. Im getrennten Mehrspielermodus darf nur der Disponent diese Bewegungsaufträge geben.

### Funkhäufigkeit nach Einsatzart

Routine-Krankentransporte erzeugen nur sehr selten eine automatische Lagemeldung (3 % Spielwahrscheinlichkeit pro Auftrag). Die Patientenaufnahme/Status 4 bleibt eine Statusmeldung, kein Funkgespräch. Einfache RD-Einsätze erzeugen weniger Routinefunk: A 10 %, B 25 %, C 60 %, D/E immer. Die Zufallsentscheidung bleibt pro Einsatz gespeichert und wird nicht bei jedem Update erneut gewürfelt. Bei mehreren gebundenen RD-/Unterstützungsressourcen, MANV oder kritischem Patientenzustand wird die Lagemeldung unabhängig davon angeboten. Notwendige Nachforderungen, Fehlfahrten, Wiener Zielabklärung und bewusst ausgelöste Funkaufträge bleiben erhalten. Stille Routine-Zielmeldungen aktualisieren das Transportziel weiterhin korrekt. Dies sind abstimmbare Spielwerte, keine empirischen Häufigkeiten.


### Straßengeschwindigkeiten und Abschnittsbewegung

Der optionale eigene OSRM-Dienst verwendet `routing/noe-car.lua`: Basis Autobahn
130 km/h, Schnellstraße (auch als Autobahn erfasste S-Referenzen) 100 km/h,
Ortsstraßen 50 km/h. Explizite OSM-Tempolimits wie 30 km/h, `AT:urban` und
`AT:rural` sowie langsamere Rampen, Zufahrten und Oberflächen berücksichtigt das
OSRM-Profil weiterhin. Nicht eindeutig gekennzeichnete normale Straßen fallen
auf 50 km/h zurück; dies ersetzt keine vollständige Ortsgebietsabgrenzung.
Abbiegezeiten kommen hinzu. Der vorhandene Blaulicht-Fahrzeitfaktor wird genau
einmal auf die normale Fahrzeit angewendet, nicht auf die Ausrückzeit; Faktor
0,85 bedeutet 15 % kürzere Fahrzeit. FR erhalten keinen Blaulichtbonus,
Hubschrauber behalten ihr Flugmodell.

Für dieses Profil beide Compose-Dateien verwenden. Der Profilhash löst auch bei
bestehenden Routing-Volumes einen erneuten Österreich-Import aus. Beim eigenen
Portainer-Git-Stack muss `routing/noe-car.lua` neben den Compose-Dateien verfügbar
sein. Ein öffentlicher OSRM-Server bleibt bei seinem Betreiberprofil; die
Simulation kann dessen Geschwindigkeiten nicht umkonfigurieren.

Routen fordern OSRM-Abschnittszeiten an. Kartenanimation und Serverposition
verwenden dieselbe zeitliche Verteilung statt gleichmäßiger Kilometer pro
Sekunde auf der gesamten Route. Ohne gültige Annotationen bleibt die bisherige
Interpolation erhalten. Alte Routen-Caches werden für neue Fahrten nicht
weiterverwendet; bereits laufende Fahrten bleiben erhalten. Es gibt keine
Live-Stau-, Ampel- oder Beschleunigungssimulation.


### Telenotarzt und Heli-Anfragen für lange Transporte

Pro Sitzung stehen zehn Telenotärzte in einem gemeinsamen Pool zur Verfügung.
Die Mannschaft fordert die Beratung per Sprechwunsch an; im Funkgespräch oder
unter **Nachforderung** kann der Disponent den Telenotarzt zubuchen. Die Nummer
wird gleichzeitig per SDS und ESApp an die anfordernde Mannschaft gesendet.
`SIM-000-000-01` bis `SIM-000-000-10` sind absichtlich nicht anwählbare
Simulationskennungen, keine echten Telefonnummern. Im Einsatz erscheint nur
**Telenotarzt** samt Nummer, ohne Fahrzeugstatus und ohne Kartenfahrzeug.

Nach 30 Simulationssekunden ruft die Mannschaft an. Telefonische Anleitung
verbessert den fiktiven Patienten-Spielwert anschließend alle 60 Sekunden um
3 Punkte bis maximal 85; ein Wert von 0 wird dadurch nicht angehoben. Dies ist
keine medizinische Versorgungsregel. Der Telenotarzt belegt keinen physischen
Notarztplatz, bietet keine Transportbegleitung und ersetzt kein NEF/NAH.
Eine anfänglich mäßige Einschränkung (45–60 Spielpunkte) kann bei der
fiktiven Telefonbeurteilung ebenfalls eine Vor-Ort-Nachforderung ergeben
(25 % Spielwahrscheinlichkeit, je Beratung einmal gespeichert). Die normale
Patientenentwicklung läuft weiter; telefonische Hilfe garantiert keine
Stabilisierung. Bei einem kritischen Spielwert fordert die Mannschaft nach telefonischer
Einschätzung ein Notarztmittel vor Ort oder bei langem Transport einen Heli an.
Beim Transportbeginn, Übergang zu einem Notarzt vor Ort, Storno oder Einsatzende
endet die Beratung und der Poolplatz wird frei. Ein manuelles Beenden ist unter
**Nachforderung** möglich. Auslastung, Verbindung und Zuordnung bleiben bei
Neuladen/Neustart erhalten. Pool und Zuweisung sind zwischen Mitspielern geteilt;
Betreuerrechte und die Calltaker-/Disponenten-Trennung gelten auch hier.

Bei kritischem fiktivem Zustand (1–44 Punkte) und mindestens 35 Minuten
Bodentransport zu einem geeigneten Akutkrankenhaus mit Heli-Landeplatz kann die
Mannschaft nach einem verfügbaren NAH fragen. Straßenrouting wird bevorzugt;
fehlende Routendaten werden durch eine ausdrücklich vorläufige Schätzung
ersetzt. Die 35 Minuten sind eine Spielannahme, keine medizinische Indikation.
Der Disponent bucht ein tatsächlich verfügbares Luftrettungsmittel zu und
bestätigt dessen Anfahrt mit ETA oder antwortet **Negativ – derzeit kein
Notarzthubschrauber verfügbar**. Es erscheint kein Phantom-Heli. Nach einer
Zusage wartet die Mannschaft; bei mehreren Patienten wird die Patientenzuordnung
erst nach Eintreffen des Helis geändert. Eine negative Antwort verhindert die
ständige Wiederholung derselben Anfrage; sie lässt sich unter Nachforderung
wieder freigeben. Laufende Reanimation und das bestehende eCPR-Verfahren bleiben
separat. Die Automatik beachtet `REINFORCEMENTS_AUTO=0`; `PATIENT_EVOLUTION=0`
unterdrückt auch die zusätzliche Verbesserung durch telefonische Anleitung.

### Anrufergespräch mit lokaler deutscher Sprachausgabe

Das Docker-Image enthält **Piper TTS 1.3.0** und die deutsche Stimme
**de_DE-thorsten-high** für LEO, Anrufer und Ressourcen. Der frühere MLS-Pool
wurde wegen unverständlicher Sprecherstimmen entfernt. Alle verwenden vorerst
dieselbe klare Grundstimme; der Telefonfilter unterscheidet den Anrufer akustisch. Kein API-Schlüssel und kein externer Sprachdienst sind
nötig. Sprache wird auf der CPU im Container erzeugt; begrenzter gemeinsamer
Audio-Cache und zwei ONNX-Rechenthreads begrenzen Speicher und CPU-Belastung.
Folgende Beiträge werden während des laufenden Gesprächs vorbereitet, damit
Wiedergabe nicht auf die Synthese der nächsten Zeile warten muss.
LEO hat eine feste eigene Stimme. Jeder Anrufer erhält einmal pro Telefonat eine
gespeicherte Identität; jede Ressource behält ihre feste Identität. Aktuell verwenden
alle Sprecher-ID 0 des klaren Modells, ohne zufällige Stimmvarianten. Alte MLS-Zuordnungen
werden auch in bestehenden Sitzungen ersetzt. Status- oder Funkkennungswechsel verändern sie nicht.
In den Ressourcen-Einstellungen kann die Stimme probegehört werden. Dies bereitet
die Funksprachausgabe vor; laufende Funkgespräche werden noch nicht vorgelesen.
Es gibt keine Tonhöhenverschiebung und keine zeitliche Anpassung einzelner Zeilen. Der Anrufer kann
zusätzlich einen Telefonfilter (300–3.400 Hz und Kompression) bekommen.
In den Einstellungen lassen sich Stimme, Telefonklang und Lautstärke ändern.
`TTS_ENABLED=0` schaltet die Synthese serverseitig ab; `TTS_MODEL` erlaubt einen
eigenen kompatiblen deutschen Einzelsprecher-Modellpfad. `TTS_CREW_MODEL` wird nicht mehr verwendet.

Für kurze Gespräche bleibt 30–45 Sekunden das Ziel. Die Dauer entsteht durch
kürzere, szenariogerechte Formulierungen, nicht durch Veränderung der
Wiedergabegeschwindigkeit. Jede WAV-Datei läuft mit Originaltempo und
Originaltonhöhe; natürlich längere Antworten dürfen länger dauern. Die
textbasierte Variante ohne Audio behält ihr 38-Sekunden-Ziel. Der nächste Beitrag erscheint nach Ende der gesprochenen Zeile;
eine kurze Sprechpause bleibt erhalten. Bei sehr langen Szenariotexten oder
langsamer Hardware kann ein Gespräch länger dauern. Fehlt Audio, läuft der
zeitgesteuerte Textdialog weiter. Browser erlauben Audio erst nach einem Klick;
„Annehmen“ gibt es normalerweise frei. Der Server erzeugt nur bereits sichtbare
Gesprächszeilen für angemeldete Mitglieder der jeweiligen Sitzung, keinen
öffentlichen beliebigen Text-zu-Sprache-Endpunkt.

**Fenster schließen pausiert Text und Audio**, Wiederöffnen setzt das Gespräch
fort. Ein laufender Audiobeitrag setzt am selben Zeitpunkt fort. Beim Wechsel
zu einem anderen Einsatz pausiert der bisherige Anruf. Der Reiter
**Disposition** bzw. **Weiter** ist bereits während des Telefonats verfügbar;
Fahrzeuge können nach manueller AMPDS-Auswahl alarmiert werden. Das Fenster
bleibt während des laufenden Gesprächs offen. Im getrennten Calltaker-Modus
bleibt die Übergabe an den Disponenten nach Gesprächsende. Alle Mitspieler
sehen denselben Verlauf, nur der betreuende Spieler steuert und hört den Anruf.

Quellen und Lizenzen: [Piper Quellcode, GPL-3.0](https://github.com/OHF-Voice/piper1-gpl/tree/v1.3.0)
, [Thorsten Modellkarte, CC0-Datensatz](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/high/MODEL_CARD)
Historische Quelle des inzwischen entfernten MLS-Modells:
[MLS-Modellkarte](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/mls/medium/MODEL_CARD).
MLS basiert auf Multilingual LibriSpeech von Vineel Pratap, Qiantong Xu, Anuroop
Sriram, Gabriel Synnaeve und Ronan Collobert (2020), LibriVox-Aufnahmen,
[OpenSLR 94](https://www.openslr.org/94/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Die Modelle bleiben unverändert; die App formuliert Texte für die Sprache und
legt bei Bedarf einen Telefonfilter auf erzeugtes Audio. Attribution ist auch
in den Einstellungen unter „Stimmen und Lizenzen“ erreichbar.
Piper und sein Modell bleiben als Drittkomponenten gekennzeichnet; die
Lizenzhinweise des installierten Pakets sind im Image enthalten. Die Stimme
spricht Deutsch, imitiert keine echte Anruferperson. Die fiktiven Texte sind
weiterhin kein originales AMPDS-Abfrageprotokoll.

### Straßenrouting mit Ersatzdienst und Storno-Rückfahrt

Bei nicht erreichbarem primärem Router oder fehlendem Straßenanschluss wird
für tatsächliche Fahrzeugfahrten ein unabhängiger zweiter OSRM-Router genutzt.
Standard: `https://router.project-osrm.org`; `ROUTING_BACKUP_URL` kann auf einen
eigenen zweiten Router zeigen oder im Container leer gesetzt werden.
Straßenanschlüsse, Hints und Cache sind pro Anbieter getrennt. Ein ausgefallener
primärer Dienst erhält 15 Sekunden Pause, statt jedes Fahrzeug erneut um einen
Timeout zu verzögern. Zwei Fahrt-Worker verhindern, dass eine einzelne schwierige
Adresse sämtliche anderen Fahrzeuge aufhält. Öffentliche Router bleiben pro
Anbieter auf höchstens eine Anfrage pro Sekunde begrenzt. Matrix-Abfragen
lösen keinen massenhaften Backup-Verkehr aus. Für größere Sitzungen eigene
OSRM-Instanzen verwenden; öffentliche Testdienste haben keine Verfügbarkeitsgarantie.

Ein Storno entfernt die Einsatzbindung, schaltet das Sondersignal aus und
berechnet eine neue, normale Straßenroute zur Heimatdienststelle. Falls die
Route zunächst fehlt, bleibt der Rückfahrauftrag erhalten und wird automatisch
erneut aufgelöst. Am Heimatstandort wird sofort korrekt eingerückt. Es werden
keine Straßen gegen die Einbahnrichtung rückwärts abgefahren und keine
Luftlinien als angebliche Straßenrouten ausgegeben. Sind beide Routendienste
ausgefallen und fehlt eine passende Cache-Route, bleibt die Fahrt bis zu einer
erreichbaren Straßenroute wartend. Bereits gespeicherte Routen funktionieren
weiter ohne Netz.


### Routing ab 15.10.2026: eigener Straßenrouter im Standard-Stack

`compose.portainer.yaml` und `compose.yaml` enthalten jetzt `osm-download`,
`osm-prepare` und `osrm`. Beim ersten Start wird der Österreich-OSM-Auszug von
Geofabrik geladen und mit dem österreichischen Geschwindigkeitsprofil vorbereitet.
Dieser einmalige Schritt benötigt Zeit, freien Speicher und RAM; die Daten bleiben
im Volume `routing-data` erhalten. Die Initialisierung steht in den Containerlogs.
`compose.routing.yaml` bleibt als kompatible Überschreibung bestehender Setups erhalten.

**In Portainer die Stack-Datei aus Git aktualisieren und den Stack neu bereitstellen.**
Ein reiner Austausch des App-Images legt die neuen Routing-Services nicht an.
Alte `ROUTING_URL`-Umgebungsvariablen gegebenenfalls auf `http://osrm:5000` ändern
oder entfernen. Der öffentliche Ersatzrouter bleibt ein Notbehelf für Ausfälle.

Vor einer manuellen Alarmierung berechnet der Server die vollständigen Straßenrouten
aller ausgewählten Bodenfahrzeuge parallel, ohne die Simulation oder andere Sitzungen
zu sperren. Erst dann werden Alarmierung und SDS/ESApp gemeinsam übernommen. Scheitert
die Berechnung, erscheint eine Fehlermeldung und es wird keine Alarmierung vorgetäuscht.
Die vorbereitete Route wird bei Quittierung/Ausrücken wiederverwendet. Bei Fahrzeugen
in Status 6 wird eine inzwischen fortgeschrittene Position auf derselben Route berücksichtigt;
eine nicht mehr passende Route wird vor der Alarmierung zurückgewiesen.

Startpunkte abseits der Straße werden auf einen erreichbaren Straßenanschluss gesetzt.
Status 9 kann bereits eine vorbereitete Fahrstrecke enthalten; die simulierte Ausrückzeit
und eine noch laufende Patientenübergabe bleiben berücksichtigt. Straßenbewegung wird
in 2/4/6/7/9 dargestellt. Standort halten, Tankvorgang und Spielpause bleiben absichtliche
Stopps. Verlorene Fahrstrecken alter Spielstände werden für Anfahrt, Transport und
freie Rückfahrt wiederhergestellt. Bekannte Ziel- und Rückfahrten werden während Versorgung
und Übergabe vorab angefragt. Es gibt weiterhin keine erfundene Querfeldein-Straßenroute.


### Portainer: fehlender Bind-Mount auf routing/noe-car.lua behoben

Die Stack-Dateien enthalten das Geschwindigkeitsprofil nun direkt im Startskript
von `osm-prepare`. Dieser schreibt `/data/noe-car.lua` ins benannte Volume
`routing-data`. Es gibt dafür keine `configs.file`- oder Hostpfad-Mounts mehr.
Dadurch funktioniert der Git-Stack auch, wenn Portainer und Docker-Daemon keinen
gemeinsamen Git-Checkout-Pfad besitzen. Der Fix benötigt nur eine aktualisierte
Compose-Datei; das zuletzt veröffentlichte App-Image bleibt kompatibel.

In Portainer **Pull and redeploy** verwenden; Stack und Volumes beibehalten.
Anschließend sind `osm-download` und `osm-prepare` nach erfolgreichem Abschluss
mit `Exited (0)` normal, während `osrm`, App und Tunnel dauerhaft laufen.
Der erste Österreich-Download und die Aufbereitung benötigen weiterhin Zeit.

`routing/noe-car.lua` bleibt die maßgebliche Quelldatei. Nach Profiländerungen
`python scripts/sync_routing_profile.py` ausführen; CI kontrolliert beide Kopien
mit `--check`. Zusätzlich startet CI die tatsächlichen Routing-Services aus
nur einer Compose-Datei in einem separaten Verzeichnis ohne `routing/` und
prüft eine echte Straßenroute auf einem kleinen Testnetz.
