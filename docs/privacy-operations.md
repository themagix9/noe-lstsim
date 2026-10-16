# Datenschutz: Betriebsaufgaben und Quellen

Die veröffentlichte Erklärung gilt für stratosi.com und lstsim.stratosi.com.
Identische HTML-Fassungen: main-site/public/datenschutz.html und
app/static/datenschutz.html. Das Impressum ist ebenfalls auf beiden Hosts
vorhanden; neue Seiten müssen Links zu beiden Dokumenten behalten.

Die Erklärung beruht auf der Implementierung in accounts.py, portal_http.py,
sessions.py, session_portal.py, routing.py, speech.py und den Browsermodulen.
IONOS als aktueller Hoster wurde vom Betreiber bestätigt. Sie behauptet keine
nicht implementierte automatische Löschung und keinen bereits abgeschlossenen
Auftragsverarbeitungsvertrag. Die folgenden Konto-/Betriebsaufgaben sind durch
Dateiänderungen allein nicht erledigt:

- IONOS-Vertragspartner und Serverstandort im Kundenkonto gegenprüfen (Text:
  IONOS SE, Deutschland). AVV im IONOS-Konto prüfen/abschließen und dokumentieren.
- Cloudflare-DPA, aktivierte Sicherheits-/Protokollierungsfunktionen und konkrete
  Aufbewahrung gegenprüfen; Analytics/Zaraz sind nicht Bestandteil dieser
  Implementierung. Werden sie zugeschaltet, Erklärung und Einwilligung anpassen.
- Google-CMP für Europäische Verordnungen veröffentlichen, als Datenschutz-URL
  https://lstsim.stratosi.com/datenschutz.html hinterlegen. Zustimmen/Ablehnen/
  Einstellungen und erneutes Öffnen der Datenschutzeinstellungen testen.
- Automatische Anzeigen auf lstsim.stratosi.com inklusive Unterseiten ausschließen;
  unser manueller Anzeigenblock bleibt über den eigenen Schalter steuerbar.
- Manuelle Auskunfts-/Löschungsanfragen tatsächlich bearbeiten: nicht nur die
  Sitzung löschen. Konto, account_sessions, members/user_id, archived_member_users,
  player_usage, account_events, completed_incidents-Zuordnungen, Chat, Uploads und
  personenbezogene Auditdetails berücksichtigen. Es gibt derzeit KEINE pauschale
  automatische Inaktivitätslöschung. Keine ungeprüften SQL-Löschbefehle ausführen;
  gemeinsame Sitzungen anderer Teilnehmer schützen. Statistiken sind erst nach
  ausreichender Entfernung der Zuordnungen anonym, nicht schon durch UUIDs.
- Gespeicherte personenbezogene Daten regelmäßig auf Erforderlichkeit prüfen.
  Falls Backups/Serverlogs eingerichtet werden oder existieren, deren tatsächliche
  Fristen und Löschverfahren zusätzlich dokumentieren und die Erklärung anpassen.
- Die Hauptseite lädt keinen Google-Code. Der Simulator lädt bei aktivierter
  Werbung den Google-Tag bereits für die CMP; die Erklärung benennt auch diesen
  technischen Kontakt vor einer optionalen Anzeigenfreigabe.

## Primärquellen

- DSGVO, insbesondere Art. 6, 12–22, 28 und 44 ff.:
  https://eur-lex.europa.eu/eli/reg/2016/679
- Betroffenenrechte und Beschwerde, österreichische Datenschutzbehörde:
  https://dsb.gv.at/rechte-pflichten/ihre-rechte-als-betroffene-person
  https://dsb.gv.at/eingabe-an-die-dsb/beschwerde
- Google Publisher Privacy Disclosures:
  https://support.google.com/publisherpolicies/answer/10437794?hl=de
- Google-CMP-Anforderungen:
  https://support.google.com/adsense/answer/13554116?hl=de
- Google-Datenverwendung auf Partnerseiten:
  https://policies.google.com/technologies/partner-sites?hl=de
- IONOS-Auftragsverarbeitung:
  https://www.ionos.de/hilfe/datenschutz/allgemeine-informationen-zur-datenschutz-grundverordnung-dsgvo/vereinbarung-zur-auftragsverarbeitung-avv-mit-ionos-abschliessen/
- Cloudflare-DPA und Privacy Policy:
  https://www.cloudflare.com/cloudflare-customer-dpa/
  https://www.cloudflare.com/de-de/privacypolicy/
- OpenStreetMap Privacy Policy:
  https://osmfoundation.org/wiki/Privacy_Policy

Keine Zusicherung einer behördlichen oder AdSense-Freigabe. Bei abweichender
Betriebskonfiguration muss der Text entsprechend angepasst werden.
