# Adminportal, Benutzerkonten und Cloudflare

## Portainer einrichten

Das vorhandene `simulation-data`-Volume bleibt erhalten. Konten, Spielstände,
Statistiken, globale Einstellungen und das Änderungsprotokoll liegen gemeinsam
in `/data/simulation.sqlite3`. Der Stackname und das Volume dürfen beim Update
nicht geändert oder gelöscht werden.

Zusätzlich zum vorhandenen `CLOUDFLARE_TUNNEL_TOKEN` diese Stack-Variablen setzen:

| Variable | Wert |
| --- | --- |
| `ADMIN_USERNAME` | Ein eigener, noch nicht als Spieler registrierter Adminname, z. B. `julian-admin` |
| `ADMIN_PASSWORD` | Ein selbst gewähltes, einzigartiges Passwort mit 12–128 Zeichen |
| `PORT` | Host-Port des Simulators, z. B. `8091` (Standard `8088`) |
| `DASHBOARD_PORT` | Separater Host-Port des Dashboards, z. B. `8092` (Standard `8089`) |
| `DASHBOARD_BIND_HOST` | Bind-Adresse des Dashboard-Host-Ports (Standard `127.0.0.1`); unabhängig von `BIND_HOST` für das Spiel |
| `COOKIE_SECURE` | `1` für den HTTPS-Betrieb über Cloudflare (Standard) |

Das Administratorkonto wird nur angelegt, solange noch kein Administrator
existiert. Ein geändertes Bootstrap-Passwort überschreibt keine bestehende
Anmeldung. Spätere Passwortänderungen erfolgen im Adminportal. Einen schon
öffentlich registrierten Spielernamen macht der Bootstrap ausdrücklich **nicht**
zum Administrator. Stattdessen einen anderen Adminnamen verwenden.

Danach den Git-Stack aktualisieren und das neue Image erneut ziehen.
Der Simulator hört weiter auf Port **8080**, das Adminportal separat auf **8081**.
Die Host-Portbindungen sind unabhängig davon einstellbar: beispielsweise
`PORT=8091` und `DASHBOARD_PORT=8092`. Beide müssen verschiedene, freie Host-Ports
verwenden. Das Dashboard ist standardmäßig nur lokal unter `127.0.0.1:8089`
erreichbar. Für zusätzlichen LAN-Zugriff ausdrücklich `DASHBOARD_BIND_HOST=0.0.0.0`
setzen. `BIND_HOST` beeinflusst nur den Spielport.

Cloudflared verwendet im gemeinsamen Docker-Netzwerk weiterhin die internen
Ports **8080** und **8081**, auch wenn die Host-Ports auf 8091/8092 geändert werden.
Der Healthcheck prüft ebenfalls weiterhin den internen Spielport 8080.

## Cloudflare-Domain und Access

Im bereits verwendeten Tunnel eine zweite Published Application / einen zweiten
öffentlichen Hostnamen anlegen:

| Hostname | Zielservice |
| --- | --- |
| `lstsim.stratosi.com` | `http://noe-lstsim:8080` (vorhandener Simulator) |
| `dashboard-lstsim.stratosi.com` | `http://noe-lstsim:8081` (neues Adminportal) |

Keine zweite Tunnelinstanz und kein zweiter Token sind dafür erforderlich.
`localhost:8081` wäre aus dem Cloudflared-Container der falsche Container.

In Cloudflare Access eine **Self-hosted application** für ausschließlich
`dashboard-lstsim.stratosi.com` anlegen. Eine Allow-Regel nur für die eigene
E-Mail-Adresse beziehungsweise explizit zugelassene Administratoren erstellen,
keine Everyone- oder Bypass-Regel. Den Tunnel-Hostnamen mit dieser Anwendung über
**Protect with Access** verbinden. Anschließend im privaten Browserfenster prüfen,
dass zuerst Cloudflare Access und danach die Anmeldung des Adminportals erscheint.
Die bestehende Spieldomain bleibt separat konfiguriert.

Der Tunnel veröffentlicht die Domain; die Access-Regel steuert, wer den Zugang
überhaupt erreichen darf. Zusätzlich prüft der Simulator selbst ein eigenes
Administratorkonto. Cloudflare-Header allein erteilen keine Adminrechte.

Offizielle Dokumentation:
- https://developers.cloudflare.com/tunnel/concepts/routing/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/

Cloudflare-DNS und Access werden im Cloudflare-Konto eingerichtet. Das Repository
kann diese kontospezifischen Einstellungen ohne Cloudflare-Zugang nicht aktivieren.

## Funktionen

- Monitoring aktiver, laufender, pausierter und nur gespeicherter Sitzungen.
  „Aktiv“ bedeutet: mindestens ein Teilnehmer innerhalb von 45 Sekunden verbunden.
- Teilnehmer, Rollen, Konto-/Gaststatus, offene Aufträge und offene Funkaufgaben.
- Einzelne Simulationen administrativ pausieren oder fortsetzen.
- Sitzungen in Übersicht und Sitzungsliste endgültig löschen, mit Bestätigungsdialog
  und Hinweis auf verbundene Teilnehmer. Teilnehmer verlieren den Sitzungszugang
  und kehren zur Startseite zurück. Spielstand, Chat, Teilnehmerzugänge und eigene
  Fahrzeuggrafiken der Sitzung werden entfernt. Benutzerkonten und bisherige
  Statistiken bleiben erhalten; das Löschen erscheint im Änderungsprotokoll.
- Globale Statistiken, Prozesslaufzeit, SQLite-Größe und freier Datenträgerspeicher.
- Dauerhafte Zähler für erstellte und erstmals gestartete Simulationen, auch für
  Gäste. Fortsetzen, Pause/Weiter und weitere Multiplayer-Teilnehmer erhöhen die
  Startzahl nicht. Löschen einer Sitzung setzt diese Gesamtzähler nicht zurück.
- Laufzeit in Echtzeit und vergangene Simulationszeit mit Zeitfaktor: jede laufende
  Sitzung mit verbundenen Teilnehmern zählt einmal, unabhängig von Registrierung.
  Pausen und Offline-Zeiten zählen nicht. Gast-Spielzeit wird zusätzlich pro
  Gastidentität gezählt; die gesamte Teilnehmer-Spielzeit umfasst registrierte
  Spieler und Gäste zusammen. Mehrere Tabs derselben Identität zählen nicht mehrfach.
  Die bisherige registrierte Teilnehmer-Spielzeit bleibt separat erhalten.
- Das Dashboard nennt den Beginn der neuen Laufzeiterfassung. Vorhandene Sitzungen
  und im Löschprotokoll belegte Sitzungen werden in die Erstellungszahl übernommen;
  frühere Starts nur bei nachweisbarer Laufzeit oder laufendem Spielstand. Frühere
  Gastzeiten und nicht belegte Starts können nicht rückwirkend berechnet werden.
- Standards für neue Übungen: Standort, Zone, Startstunde, Geschwindigkeit,
  getrennte Notruf-/KT-Frequenzen für gemeinsam und Calltaker/Dispo, Transporte
  ein/aus, Signalfahrt- und Helikopterfaktor.
- Frequenzen und Fahrzeitfaktoren können optional auf bestehende Sitzungen
  übernommen werden. Startdatum, laufende Routen und deren aktuelle Geschwindigkeit
  werden dadurch nicht nachträglich verändert.
- Wartungshinweis auf der Startseite und im laufenden Spiel, ohne Zwangsabbruch.
  Startseiten prüfen den Hinweis alle 15 Sekunden; Sitzungen erhalten ihn live.
- Registrierung öffnen/schließen, Benutzer sperren/freigeben, Passwörter neu setzen.
- Die letzten 50 administrativen Änderungen als Protokoll. Passwörter und
  Anmeldetokens werden darin nicht gespeichert.

## Spielerkonten und Statistiken

Registrierung mit Benutzername, Anzeigename und Passwort; keine E-Mail-Adresse
und kein externer Identitätsdienst erforderlich. Als Gast spielen bleibt möglich.
Ein Konto kann neue und bereits beigetretene Sitzungen geräteübergreifend fortsetzen.
Bestehende Gastsitzungen lassen sich nach Anmeldung ausdrücklich mit dem Konto
verknüpfen. Die Teilnahmeidentität bleibt erhalten; der alte Sitzungstoken wird
beim Verknüpfen/Fortsetzen ersetzt.

Ein Benutzer kann nur eigene gespeicherte Mitgliedschaften laden. Ein gültiger
Sitzungscode erlaubt wie bisher den Beitritt zu einer Mehrspielerrunde. Der
Multiplayerchat ist sowohl lesend als auch schreibend auf angemeldete Konten
beschränkt; Gastclients erhalten keine Chatnachrichten in ihrer Zustandsantwort.

Persönliche Statistik: abgeschlossene RD-/KT-Einsätze, angenommene Notrufe,
Fahrzeug-Alarmierungen und aktive reale Spielzeit. Die Spielzeit zählt nur bei
laufender Simulation und aktiver Verbindung, unabhängig vom Simulationsfaktor.
Ein abgeschlossener Einsatz zählt für den letzten Betreuer. Notruf-/Alarmierungs-
und Spielzeitzähler starten ab Kontoverknüpfung. Noch im bisherigen Spielstand
enthaltene abgeschlossene Einsätze können übernommen werden; bereits zuvor
entfernte Historie lässt sich nicht rekonstruieren. Statistik bleibt nach
Zurücksetzen einer Übung und nach Entfernen abgeschlossener Aufträge erhalten.

Passwort vergessen: Die Administration kann ein neues Passwort setzen.
Ein automatischer E-Mail-Reset ist nicht Bestandteil dieser Version.
Spieler-Logins gelten maximal 30 Tage, Admin-Logins maximal 12 Stunden.
Abmelden, Sperren oder Passwortänderungen machen betroffene Logins ungültig.

## Lokale Entwicklung

Für HTTP-Entwicklung `COOKIE_SECURE=0` setzen. Das ist ausschließlich für lokale
Tests gedacht. Der lokale Adminzugang ist standardmäßig an Loopback gebunden
(`127.0.0.1:8089:8081`); `DASHBOARD_PORT` ändert den Host-Port auch in
`compose.yaml`. Im HTTPS-Betrieb über Cloudflare bleibt `COOKIE_SECURE=1`. Sichere Cookies verwenden hostgebundene `__Host-`-Namen, HttpOnly und
SameSite=Strict. Passwörter werden mit individuellem Salt und scrypt gespeichert;
Login-Tokens nur als SHA-256-Hash. Schreibende Konten-/Adminanfragen benötigen
zusätzlich einen CSRF-Nachweis; Login und Registrierung sind begrenzt.

SQLite-Backups müssen die laufende WAL-Schreibweise berücksichtigen. Ein Backup
über die SQLite-Backup-API erstellen oder den Container für eine Dateisicherung
geordnet stoppen; nicht nur die laufende Hauptdatei ohne WAL kopieren.
