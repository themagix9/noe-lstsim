# NÖ Dispo – Docker-Leitstellensimulator v0.3

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

1. In der Lobby Spielernamen eingeben und eine Sitzung erstellen oder mit dem achtstelligen Code beitreten. Die Simulation beginnt pausiert um 08:00. Starte sie oben rechts; zum Testen eignet sich 15×.
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

AAO-Quelle: https://www.notrufnoe.at/ausrueckordnung-detail/, abgerufen 11.10.2026. Implementiert sind Kategoriezuordnung, KT-Typpräferenz und Organisation, BLS-rot-Präferenz mit 90 Sekunden, BLS/ALS-Typreihenfolge, bestätigter NFS bei ALS grün/gelb sowie bodengebundene Notarztmittel bei ALS orange/rot und ALS-gelb-Fallback. Telemedizin/Weitergabe erzeugen zunächst keinen automatischen Rettungsmittelvorschlag; bei markierter Nichtverfügbarkeit des Sekundärsystems greift der BLS-grün-Fallback. Fahrzeug-Ausrückzeiten sind manuell gepflegte Schätzwerte (Startwert 60 Sekunden); Eintreffzeiten bleiben Simulationsschätzungen. NFS ist im Ausgangsbestand **nicht bestätigt** und kann pro Ressource gepflegt werden. Es wird nicht aus einer Fahrzeugkennung abgeleitet.

Der Vorschlag bildet **nicht** die gesamte einsatztaktische AAO ab: ACN/Pilotregionen, NKV/NKI-Zusatzregeln, NAH-Zeitvergleiche, First Responder, Großeinsatzpläne und Sonderrettung fehlen. Die Oberfläche zeigt diese Lücken. Die Entscheidung über die tatsächliche Sondersignalverwendung liegt auch laut öffentlicher AAO beim Lenker; das Simulatorfeld ist ein Dringlichkeitshinweis im Trainingsablauf. Zusätzliche `SIM-…`-Regeln sind unter Konfiguration als JSON bearbeitbar, werden gespeichert und ändern keine originale AMPDS-Tabelle. Automatische Demoanrufe sind weiterhin fiktive Szenarien; es wird kein AMPDS-Abfrageprotokoll nachgebildet.

Leaflet-Lizenz liegt unter `app/static/vendor/Leaflet-LICENSE.txt`. OSM-Attribution bleibt sichtbar. Keine Karten-Vorabrufe, Offlinepakete oder serverseitigen Tile-Proxys. Browser-Tests ersetzen OSM-Kacheln lokal, damit die Tests keine öffentlichen Kartendienste belasten. Tile-Nutzungsregeln: https://operations.osmfoundation.org/policies/tiles/.
