"""Original fictional MANV calls; actual patient counts remain hidden until assessment."""
from scenarios import scenario

MANV_SCENARIOS=[]
for id,title,caller,code,scores,report in [
 ('manv-bus','Busunfall','Hallo, Berger mein Name. Ein Bus ist gegen ein Auto gefahren. Mehrere Leute sitzen auf der Straße, zwei reagieren kaum. Ich kann nicht sagen, wie viele verletzt sind.','RD-29B1',[18,28,48,58,76,88], 'Busunfall: sechs verletzte Personen, davon zwei kritisch. Feuerwehr und Polizei zur Absicherung benötigt.'),
 ('manv-smoke','Rauchentwicklung im Wohnhaus','Gruber hier, bei uns hat es im Stiegenhaus stark geraucht. Wir sind jetzt draußen. Mehrere Nachbarn husten und einem Mann geht es sehr schlecht.','RD-8B0',[20,34,42,52,64,75,82,90], 'Acht betroffene Personen nach Rauchgasexposition, davon drei kritisch. Feuerwehr sichert das Gebäude, Versorgung außerhalb des Gefahrenbereichs.'),
 ('manv-pileup','Mehrere Fahrzeuge kollidiert','Ich heiße Novak. Hier sind mehrere Autos zusammengestoßen. Es laufen Leute herum, andere liegen noch in den Autos. Ich sehe bestimmt zehn Personen, aber Verletzungen kann ich schwer beurteilen.','RD-29B1',[12,25,38,46,54,63,72,78,84,92], 'Zehn verletzte Personen nach Verkehrsunfall, drei kritisch. Polizei und Feuerwehr sichern die Einsatzstelle; mehrere Transportmittel notwendig.'),
 ('manv-event','Verletzte bei Veranstaltung','Hier Leitner vom Veranstalter. Im Gedränge sind mehrere Leute gestürzt. Zwei liegen noch am Boden und viele klagen über Schmerzen. Wir haben den Zugang freigemacht.','RD-17B1',[22,35,50,56,62,68,73,78,82,86,90,94], 'Zwölf verletzte Personen nach Gedränge und Sturzereignis. Zwei kritisch, mehrere weitere transportbedürftig. Sichtung und koordinierte Nachforderung erforderlich.'),
]:
    item=scenario(id,title,caller,'Mehrere betroffene Personen, Ausmaß telefonisch noch unklar.',code,report,
        {'patient':'Mehrere Personen, ich kann die genaue Zahl noch nicht sicher nennen.','consciousness':'Einige sprechen mit mir, mindestens zwei reagieren kaum.','breathing':'Mehrere atmen auffällig, ich kann gerade nicht jede Person beurteilen.','access':'Der Zugang für die Rettung ist freigehalten. Ich bleibe unter dieser Nummer erreichbar.'},score=min(scores),trend=(-5,1),fire=id!='manv-event',police=id in ('manv-bus','manv-pileup'))
    item['_scenario'].update(manv=True,patient_count=len(scores),patient_scores=scores)
    MANV_SCENARIOS.append(item)
