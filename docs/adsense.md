# AdSense auf der Startseite

Eingerichtet für den bereitgestellten Anzeigenblock „Startseite rechts“:

- Publisher: `ca-pub-2546389460875165`
- Slot: `7480335427`
- Desktop ab 1250 px: rechte Spalte mit 300 px Breite, vertikales Anzeigenformat.
- Kleinere Bildschirme: horizontaler Block unterhalb des Startformulars.
- Kennzeichnung als „Werbung“, Abstand vom Startformular und keine Überlagerung
  von Spielbuttons. Responsive Anzeigen werden weder abgeschnitten noch in
  eine feste maximale Höhe gezwängt.

## Einmalige Einrichtung im AdSense-Konto

1. Website-Freigabe für `stratosi.com` prüfen. Das Erstellen eines Anzeigenblocks
   allein ist noch keine Zusage von Google, tatsächlich Anzeigen auszuliefern.
2. **Datenschutz und Mitteilungen → Europäische Verordnungen** öffnen und eine
   Google-Einwilligungsnachricht für die Website veröffentlichen: Deutsch,
   Zustimmen, Ablehnen und Optionen, mit der tatsächlichen Datenschutzerklärung
   der Website. Google liefert diese CMP-Nachricht über den AdSense-Tag aus;
   kein selbst erfundener „Zustimmen“-Schalter ersetzt eine zertifizierte CMP.
3. **Anzeigen → Nach Website → stratosi.com bearbeiten → Ausgeschlossene Seiten**:
   `lstsim.stratosi.com/` einschließlich aller Unterseiten für automatische
   Anzeigen ausschließen. Der Simulator ist eine einzelne Browserseite mit
   wechselnder Ansicht; ein bloßes Ausblenden der Startseite würde automatisch
   eingefügte Anzeigen nicht zuverlässig aus dem laufenden Spiel entfernen.
   Der hier integrierte manuelle Anzeigenblock funktioniert weiterhin. Andere
   Seiten der Hauptdomain müssen nicht ausgeschlossen werden.
4. Den ads.txt-Status prüfen. Der Simulator stellt unter `/ads.txt` diese Zeile
   bereit:

   ```text
   google.com, pub-2546389460875165, DIRECT, f08c47fec0942fa0
   ```

   Die ads.txt der Hauptdomain liegt jetzt im selben Repository unter
   `main-site/public/ads.txt` und wird über Cloudflare Pages bereitgestellt.
   Die tatsächliche Erreichbarkeit unter `https://stratosi.com/ads.txt` prüfen.
5. Nach dem Deployment im Adminportal **Werbung → Startseitenwerbung aktivieren →
   Werbung speichern**. Anfangs ist die Funktion ausgeschaltet, damit die
   kontospezifischen Voraussetzungen zuerst eingerichtet werden können.

Die Publisher-Metadaten sind bereits im öffentlichen Seitenkopf hinterlegt:

```html
<meta name="google-adsense-account" content="ca-pub-2546389460875165">
```

In AdSense kann für die Inhaberschaftsprüfung **Meta-Tag** gewählt werden; diese
Bestätigung benötigt noch keine aktiven Anzeigen. Der Code dieses Repositorys
wird auf `lstsim.stratosi.com` ausgeliefert. Wenn Google die Hauptseite
`stratosi.com` prüft, muss derselbe Metatag auch in deren `<head>` stehen, sofern
sie nicht auf den Simulator weiterleitet. Eine separat gehostete Hauptseite
ändert dieser Simulator-Push nicht.
Das Adminportal enthält keinen Anzeigen-Loader. Lokal über HTTP lädt der
Simulator ebenfalls keinen Google-Anzeigen-Tag.

## Verhalten der Einbindung

Bei aktivierter Werbung und sichtbarer Startseite über HTTPS wird der originale
Google-AdSense-Loader einmal geladen. Zuvor wird `pauseAdRequests=1` gesetzt.
Der Loader kann damit die in AdSense veröffentlichte Google-CMP bereitstellen;
Anzeigenanfragen unseres Blocks bleiben zunächst pausiert.

Die Freigabe erfolgt über die IAB-TCF-Schnittstelle der CMP: nur nach erfolgreichem
`tcloaded`/`useractioncomplete` bei geladener CMP und entweder ausdrücklich
`gdprApplies=false` oder einem nichtleeren TC-String mit Zustimmung zur Speicherung
(Purpose 1) und Google (Vendor 755). Google wertet den vollständigen TC-String für
die tatsächlich zulässige Auslieferung weiter aus. Unbekannte, fehlende, fehlerhafte
oder ablehnende Signale geben keine Anzeigenanfrage frei. Eine Ablehnung wird
nicht als Zustimmung zu nicht personalisierten Anzeigen umgedeutet.

Der Anzeigenblock wird höchstens einmal je Seitenaufruf angefordert. Live-Daten,
Fenstergrößenänderungen und die Rückkehr zur Startseite lösen keine automatische
Anzeigenrotation aus. Während des Spiels, bei ausgeblendeter Browserseite oder
abgeschalteter Werbung werden weitere AdSense-Anfragen pausiert. Das ersetzt
**nicht** den oben beschriebenen Ausschluss automatischer Anzeigen im AdSense-Konto.

„Datenschutzeinstellungen“ ist sichtbar, sobald die Google-CMP ihre entsprechende
API bereitstellt, und öffnet deren Widerrufsdialog. Bei Widerruf wird ein vorhandener
Block entfernt; für eine erneute Auslieferung nach späterer Zustimmung die Seite
neu aufrufen. Einstellungen werden ausschließlich von der CMP gespeichert.

Bei fehlender CMP, Werbeblocker, verweigerter Einwilligung oder fehlender
Anzeigenfüllung kann die Fläche leer bleiben. Startformular und Simulation bleiben
benutzbar. Das Einfügen des Codes garantiert weder Freigabe noch Werbeeinnahmen.

## Kontrolle

- Privates Browserfenster: Einwilligungsdialog, Ablehnen, Zustimmen und spätere
  Änderung prüfen. Eigene Anzeigen nicht zu Testzwecken anklicken.
- Google-Vorschau nach Veröffentlichung der Nachricht:
  `https://lstsim.stratosi.com/?fc=alwaysshow&fctype=gdpr`.
- Desktop, Tablet und Handy prüfen; anschließend eine Simulation öffnen.
- Automatisierte Tests fangen alle Google-Anfragen ab und verwenden ausschließlich
  eine lokale CMP-/Anzeigenattrappe, keine echten Anzeigenaufrufe.

Offizielle Dokumentation:
- https://support.google.com/adsense/answer/9274025
- https://support.google.com/adsense/answer/10960768
- https://support.google.com/adsense/answer/9262311
- https://support.google.com/adsense/answer/9042142
- https://developers.google.com/funding-choices/fc-api-docs

## Datenschutzerklärung

Die ausgearbeitete Erklärung ist auf beiden Hosts unter `/datenschutz.html`
verfügbar. Für die CMP kann `https://lstsim.stratosi.com/datenschutz.html`
verwendet werden. Betriebsaufgaben und Quellen: [privacy-operations.md](privacy-operations.md).
