# Stratosi-Hauptseite

Eigenständige statische Website für https://stratosi.com. Kein neues Repository,
keine Node-Pakete, kein Docker-Service und kein Build erforderlich. `public/`
ist das vollständige Cloudflare-Pages-Ausgabeverzeichnis. Änderungen hier haben
keinen Einfluss auf den Simulator und die geschützte Admin-Subdomain.

## Vor dem öffentlichen Livegang

- `public/impressum.html`: Betreiberanschrift und Kontakt-E-Mail sind mit den
  ausdrücklich zur Veröffentlichung freigegebenen Angaben hinterlegt.
- `public/datenschutz.html`: Betreiberkontakt ist hinterlegt; konkretes Cloudflare-Setup und
  Verarbeitungshinweise vollständig ergänzen/prüfen. Aktuell ausdrücklich nur
  Entwurf für die Hauptseite, NICHT für Simulator/AdSense-CMP verwenden.
- Betreiberanschrift und E-Mail wurden vom Betreiber ausdrücklich freigegeben.
- Die Hauptseite lädt keine Werbung, keine Google-Skripte, keine Analyse und keine
  externen Fonts. Der Metatag ist bereits im HTML; er löst keine Anzeigen aus.

## Cloudflare Pages mit GitHub verbinden (empfohlen)

1. Cloudflare → Workers & Pages → Anwendung erstellen → Pages → Git-Repository verbinden.
2. GitHub-Repository `themagix9/noe-lstsim` freigeben und auswählen.
3. Projektname z.B. `stratosi-main`, Produktionsbranch `main`.
4. Framework-Voreinstellung **None/Keine**; Build-Befehl **leer** lassen;
   Build-Ausgabeverzeichnis **main-site/public**; Root-Verzeichnis Repository-Root.
5. Speichern und bereitstellen. Erst die `*.pages.dev`-Vorschau prüfen.
6. Im Pages-Projekt → Benutzerdefinierte Domains → Domain einrichten →
   **stratosi.com** verbinden. Cloudflare lässt den nötigen DNS-Eintrag bestätigen.
   Einen vorhandenen Eintrag für exakt `stratosi.com` vorab auf Konflikte prüfen.
   Keine Wildcard-Änderung und keine Änderungen an lstsim/dashboard vornehmen.
7. Optional unter Build-Watch-Paths nur `main-site/*` einschließen, damit reine
   Simulator-Commits kein erneutes Deployment der Hauptseite anstoßen.

Spätere Änderungen in `main-site/public` werden automatisch aus Git bereitgestellt.
Alternativ Direct Upload: kompletten Inhalt von `public/` hochladen. Bei dieser
Variante gibt es keine automatische Git-Synchronisierung.

## AdSense

Im Kopf von `index.html` steht bereits:

```html
<meta name="google-adsense-account" content="ca-pub-2546389460875165">
```

`https://stratosi.com/ads.txt` muss nach Domain-Verbindung genau Folgendes liefern:

```text
google.com, pub-2546389460875165, DIRECT, f08c47fec0942fa0
```

In AdSense `stratosi.com` als Website auswählen, Metatag-Verifizierung durchführen
und Überprüfung beantragen. Die Seite ist keine Garantie auf AdSense-Freigabe.
Google bewertet Inhalt und Einhaltung seiner Richtlinien.
Die weiteren Schritte für die Werbung im Simulator stehen in `../docs/adsense.md`.
Auf der Hauptseite ist aktuell absichtlich kein AdSense-Loader: CSP lässt ausschließlich lokale
Skripte zu. Soll hier später Werbung erscheinen, muss das inklusive CMP/Datenschutz
und passender CSP gesondert implementiert werden.

## Lokal prüfen

```sh
python -m http.server 8000 --directory main-site/public
```

Dann http://localhost:8000 öffnen. Nur ein lokales Skript für den Datenschutzhinweis; keine Abhängigkeiten.

## Cookie- und Datenschutzhinweis

Der untere Hinweis merkt das Schließen pro Tab in sessionStorage. Er ist eine
Information mit „Verstanden“, keine Einwilligung für Werbung. Die Hauptseite
lädt weiterhin keine Google- oder Analyse-Skripte. Im Simulator bleibt der
bestehende Google-CMP-Dialog für optionale Werbung zuständig.
