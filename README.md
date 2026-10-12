# NÖ Dispo – Docker-Leitstellensimulator v0.7

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

Bei bestätigter laufender Reanimation wird ausschließlich das eCPR-Übungsziel AKH Wien mit Landeplatz zur Zielkoordination angeboten. Erst nach Bettenmann-Antwort, Kasusnummer und SDS/ESApp startet der Zielflug. Ohne laufende Reanimation ist kein eCPR-Zielflug vorgesehen; reguläre Wiener Zielkoordination läuft weiter. Reales eCPR-Zentrum: https://notfallmedizin.meduniwien.ac.at/forschung/kooperationen-forschungsorganisationen/elso-membership/. Krankenhausannahme, Landeplatzverfügbarkeit, Polizeialarmierung und eCPR-Voranmeldung sind vollständig simuliert.

Bestehende Sitzungen erhalten die Besetzungs-/FR-Migration; laufende FR-Einsätze werden vor Änderung ihres Wohnorts beendet. Das Datenvolume bleibt erhalten. Neue Modi und Felder werden im JSON-Export gespeichert. v0.4 ersetzt die älteren README-Angaben zu 24h-Bodenannahmen, Fischamender Platzhalter und fehlendem NAH-Patiententransport.

Alarmierungsmodal: Geöffnete/fokussierte Auswahllisten bleiben trotz Hintergrundabfragen im DOM, damit AMPDS-Stichwörter ausgewählt werden können. Code und Beschreibung bilden das Alarmierungsstichwort. Generierte und manuelle Einsätze erhalten persistente, innerhalb ihrer Sitzung eindeutige Einsatznummern und fiktive Verrechnungsnummern; auch nach einem Reset werden Nummern nicht wiederverwendet. Alarmmeldungen enthalten Versorgungsstufe/AAO, Ressourcen, Patientenplatzhalter, Eventinfo, Abfragedetails, Einsatz-/Zieladresse und Zusatztext. Jede alarmierte Ressource erhält eine eigene Meldung im Simulationsprotokoll. Keine Übernahme personenbezogener Daten aus Referenzbildern; keine Verbindung zu realer Einsatzdokumentation.

Fensterlayout: Seite bleibt auf die Bildschirmhöhe begrenzt; Ressourcen, Aufträge, Kommunikation, Stammdaten und Dialoge scrollen innerhalb ihrer Bereiche. Größere Schrift, Desktop- und mobile Aufteilung. OSM-Zoom per Mausrad aktiv. Status 1 wird ausschließlich in der Heimatdienststelle zusammengefasst (Tooltip/Popup), andere Status erscheinen als Fahrzeugmarker; FR bleiben an ihren fiktiven Wohnorten sichtbar.

„Zur Startseite“ verlässt die Simulation, schließt offene Dialoge und ermöglicht die gespeicherte Sitzung fortzusetzen. Singleplayer wird beim Verlassen pausiert; Multiplayer läuft für die übrigen Disponenten weiter.

Dienststellenadressen Schwechat, Götzendorf, Himberg, Leopoldsdorf, Bruck und Hainburg anhand öffentlicher RK-Seiten geprüft (11.10.2026); Quellenlink im Datensatz. Kartenpunkte bleiben ausdrücklich angenähert und sind noch nicht gebäudegenau verifiziert. NEF Baden/Mödling weiterhin als ungeprüfte Stützpunktlage markiert.

## v0.5: Straßenrouten, echte Adresspunkte, ETA und Funk-Nachforderungen

Neue Einsätze verwenden reale, öffentlich kartierte OSM-Adressen mit zugehörigem Adresspunkt; die dort simulierten Personen und Ereignisse sind vollständig fiktiv. Die Orte werden gleichmäßig über die vorhandenen Gemeinden verteilt. Im manuellen Einsatzformular bietet die lokale Adressliste passende Koordinaten; bei freier Adresse müssen Koordinaten weiterhin selbst geprüft werden. Kein öffentlicher Nominatim-Dienst wird als Suchfunktion eingebaut. Adressdaten: `app/data/addresses.json`, © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright. Auswahl aus Overpass, abgerufen am 11.10.2026; noch kein vollständiger NÖ-Adressbestand.

Krankenhausadressen nach offiziellen Betreiberseiten. Mödling und Hainburg verwenden die Kartenmarker der jeweiligen Betreiberseiten; Donaustadt/AKH nutzen die vom Nutzer bereitgestellten Kartenpunkte. Ein Marker bezeichnet das Krankenhausgelände, keinen abschließend geprüften Rettungseingang oder Hubschrauberlandeplatz. Dienststellen erhalten Haus-/Kreuzicons (grün bei eingeplanter Besetzung, grau ohne Besetzung); Krankenhäuser ein separates H-Icon. Frei auf Wache wird nur im Dienststellen-Popup gelistet. FR-Wohnorte bleiben fiktiv.

Bodenfahrzeuge erhalten OSRM-Straßenrouten, deren Geometrie für die Kartenbewegung verwendet wird. ETA und Straßenkilometer erscheinen im Ressourcenmodal; ETA enthält eine Ausrückzeit und gegebenenfalls die verbleibende Übergabezeit. Bereits fahrende Ressourcen zeigen ihre Restfahrzeit. NAH bleiben direkte Flugstrecken. Die AAO sortiert nach Routingzeit, sobald diese vorliegt; bis dahin ist der Vorschlag ausdrücklich vorläufig. Es gibt keine Live-Verkehrsdaten und keinen verifizierten Blaulicht-Fahrzeitfaktor.

Standard für kleine private Übungen: `ROUTING_URL=https://routing.openstreetmap.de/routed-car`. Nutzungsbedingungen: https://routing.openstreetmap.de/about.html und https://www.fossgis.de/ — maximal eine Anfrage pro Sekunde, keine starke Nutzung. Der Server bündelt ETA-Abfragen über die Table-API, nutzt einen gemeinsamen Hintergrundworker und persistente SQLite-Caches (7 Tage) und hält mindestens 1,1 Sekunden zwischen Anfragen. Nur Koordinaten werden übermittelt, keine Patientendaten. Die UI enthält OSM-/Routing-Hinweise und „Karte verbessern“. Für dauerhafte oder größere Multiplayer-Nutzung den eigenen OSRM-Dienst verwenden. Wenn Routing nicht erreichbar ist, wartet die Ressource sichtbar; keine unmarkierte Fahrt querfeldein. `ROUTING_ENABLED=0` ist ausschließlich ein ausdrücklich deaktivierter Übungs-/Testmodus mit bisheriger schematischer Bewegung.

Eigener OSRM: `compose.routing.yaml` zusätzlich zu `compose.portainer.yaml` verwenden. Download-, Vorbereitung- und Routingdienste sind enthalten; `ROUTING_URL` wird intern auf `http://osrm:5000` gesetzt. Einmalige Österreich-PBF-Datei von Geofabrik und OSRM-Vorbereitung können lange dauern und benötigen mehrere GB Speicher/RAM. Der Simulator startet bereits und meldet wartendes Routing, bis OSRM bereit ist. Routingdaten bleiben im separaten Volume. `OSRM_IMAGE` kann auf einen festen OSRM-Tag gesetzt werden; Vorbereitung und Server müssen dasselbe Image verwenden. Dieser optionale große Österreich-Import wird in CI nur als Compose-Konfiguration geprüft, nicht vollständig ausgeführt.

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
