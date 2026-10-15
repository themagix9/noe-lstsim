"""Original fictional incidents. No imported LstSim dialogue or clinical instructions."""
from scenarios import scenario

# id, reported event, caller observation, age, on-scene finding, initial game score, code
CASES=[
 ('abdominal-elder','Bauchschmerzen','Meine Oma hat seit heute starke Bauchschmerzen und kann nicht mehr aufstehen.',78,'Patientin ansprechbar, ausgeprägte Bauchschmerzen. Transport zur Abklärung.',65,'RD-1A1'),
 ('abdominal-young','Bauchschmerzen','Mein Freund krümmt sich vor Bauchweh. Es wird seit einer Stunde schlimmer.',24,'Patient mit zunehmenden Bauchschmerzen, kreislaufstabil. Abklärung im Krankenhaus.',72,'RD-1A1'),
 ('allergy-rash','Allergische Reaktion','Nach dem Essen sind überall rote Flecken und es juckt ganz stark.',35,'Hautausschlag ohne Atemnot; aktuell stabil. Weitere Abklärung erforderlich.',82,'RD-2A1'),
 ('allergy-breath','Allergische Reaktion mit Atemnot','Nach einem Insektenstich bekommt meine Frau schlechter Luft und ihre Stimme klingt anders.',49,'Deutliche allergische Reaktion mit Atemproblemen. Notarztversorgung erforderlich.',28,'RD-6D2'),
 ('dog-bite','Hundebiss','Ein Hund hat mich am Unterarm gebissen. Die Besitzerin ist noch hier.',31,'Bissverletzung am Unterarm, keine starke Blutung. Transport zur Wundversorgung.',80,'RD-3A1'),
 ('assault','Verletzung nach Auseinandersetzung','Ein Mann wurde vor dem Lokal geschlagen. Er sitzt jetzt bei uns; die andere Person ist weg.',28,'Patient mit Gesichtsverletzung, wach. Polizeiliche Aufnahme und Abklärung im Krankenhaus.',66,'RD-4A1A'),
 ('back-pain','Akute Rückenschmerzen','Ich bin beim Aufstehen im Rücken eingeschossen und komme nicht mehr aus dem Bett.',56,'Akute Rückenschmerzen ohne Sturz; Patient ansprechbar und kreislaufstabil.',78,'RD-5A1'),
 ('asthma','Atemnot zu Hause','Meine Tochter bekommt schlecht Luft. Sie hat sonst auch Asthma, aber heute ist es stärker.',19,'Ausgeprägte Atemnot, Notarzt zur Versorgung erforderlich.',30,'RD-6D2'),
 ('breathing-night','Nächtliche Atemnot','Mein Mann musste sich aufsetzen, weil er im Liegen kaum Luft bekommt.',73,'Patient mit schwerer Atemnot; Notarztmittel erforderlich.',26,'RD-6D2'),
 ('respiratory-infection','Husten und Atemnot','Meine Mutter hustet seit Tagen, jetzt ist sie beim Sprechen ganz kurzatmig.',69,'Atembeschwerden und Fieber, Patientin wach. Notärztliche Versorgung erforderlich.',39,'RD-6C1'),
 ('burn-kitchen','Verbrennung in Küche','Mir ist heißes Wasser über den Arm gelaufen. Es tut stark weh, aber ich bin wach.',42,'Verbrennung am Unterarm, kreislaufstabil. Transport zur Versorgung.',75,'RD-7A1'),
 ('burn-work','Verbrennung am Arbeitsplatz','Ein Kollege hat sich an einer heißen Maschine verletzt, die Maschine steht jetzt.',37,'Lokale Verbrennung, keine weitere Gefährdung der Mannschaft. Klinische Versorgung.',74,'RD-7A1'),
 ('smoke-inhalation','Rauch eingeatmet','Mein Nachbar war kurz in der verrauchten Küche. Jetzt hustet er draußen stark.',61,'Rauchgasexposition mit Atemproblemen; Feuerwehr vor Ort, Notarzt erforderlich.',35,'RD-8B0'),
 ('co-alarm','CO-Warnung im Gebäude','Unser CO-Melder piepst und zwei Leuten ist schwindlig. Wir sind schon draußen.',46,'Verdacht auf CO-Exposition. Feuerwehr prüft das Gebäude, Patientenversorgung außerhalb.',34,'RD-8B0'),
 ('cardiac-arrest','Bewusstlose Person ohne erkennbare Atmung','Mein Vater reagiert gar nicht mehr, und ich sehe keine normale Atmung.',67,'Laufende Reanimation. Notarztmittel am Berufungsort erforderlich.',0,'RD-9E1'),
 ('chest-pain','Brustschmerz','Mein Papa hat plötzlich Druck auf der Brust und ist ganz verschwitzt.',64,'Anhaltender Brustschmerz und eingeschränkter Kreislauf. Notarztversorgung.',31,'RD-10C1'),
 ('chest-young','Brustschmerz bei junger Person','Ich habe seit einer halben Stunde Schmerzen im Brustkorb. Ich kann normal sprechen.',27,'Patient ansprechbar, Atmung unauffällig. Transport zur weiteren Abklärung.',76,'RD-10A1'),
 ('choking-resolved','Verschlucken','Meine Mutter hat sich beim Essen verschluckt. Jetzt spricht sie wieder, hustet aber noch.',81,'Kein anhaltender Erstickungsanfall, Patientin wach. Weitere Abklärung.',70,'RD-11A1C'),
 ('seizure-known','Krampfanfall beendet','Mein Freund hat Epilepsie. Er hat gezuckt und ist jetzt müde und verwirrt.',29,'Krampfanfall beendet, Patient noch desorientiert; weitere Versorgung und Abklärung.',52,'RD-12A1'),
 ('seizure-first','Erster Krampfanfall','Meine Frau ist umgefallen und hat am ganzen Körper gezuckt. So etwas hatte sie noch nie.',40,'Erstmaliger Krampfanfall, Bewusstsein noch eingeschränkt. Notarzt erforderlich.',36,'RD-12B0'),
 ('diabetes','Blutzuckerproblem','Mein Mann hat Diabetes und fühlt sich ganz zittrig, aber er antwortet mir normal.',58,'Patient mit auffälligem Blutzucker, wach und aktuell stabil. Klinische Abklärung.',58,'RD-13A1'),
 ('water-rescue','Person aus Wasser gerettet','Wir haben einen Mann aus dem Wasser geholt. Er sitzt hier und hustet.',33,'Patient nach Wasserunfall ansprechbar, auffällige Atmung. Notarzt erforderlich.',34,'RD-14C0'),
 ('electric-shock','Stromunfall','Ein Kollege hat einen Stromschlag bekommen. Die Anlage ist abgeschaltet; er ist wach.',44,'Patient nach Stromkontakt ansprechbar, normale Atmung. Transport zur Abklärung.',62,'RD-15C1E'),
 ('eye-injury','Augenverletzung','Beim Arbeiten ist mir etwas ins Auge gekommen. Ich sehe verschwommen.',39,'Fremdkörperverdacht am Auge, Patient ansonsten stabil. Fachärztliche Abklärung.',88,'RD-16A1'),
 ('fall-stairs','Sturz auf Stiege','Meine Mutter ist auf der Stiege gestürzt und hat starke Schmerzen im Bein.',82,'Patientin mit Verletzung der unteren Extremität. Liegendtransport.',65,'RD-17B1'),
 ('fall-ladder','Sturz von Leiter','Mein Nachbar ist von einer Leiter gefallen. Er spricht, aber er sagt, der Rücken tut weh.',57,'Sturz aus Höhe, starke Schmerzen. Notarzt zur Versorgung erforderlich.',37,'RD-17B1'),
 ('fall-shower','Sturz im Badezimmer','Mein Vater liegt in der Dusche und kommt alleine nicht mehr hoch.',86,'Patient nach Sturz wach, Hüftschmerz. Transport zur Abklärung.',66,'RD-17B1'),
 ('fall-ice','Sturz am Gehsteig','Eine Frau ist am Gehsteig ausgerutscht und kann nicht aufstehen.',71,'Patientin mit Schmerzen am Sprunggelenk, keine weiteren Beschwerden.',78,'RD-17A1'),
 ('headache','Starke Kopfschmerzen','Ich habe viel stärkere Kopfschmerzen als sonst und mir ist übel.',45,'Patient wach, starke Kopfschmerzen. Transport zur Abklärung.',61,'RD-18A1'),
 ('palpitations','Herzklopfen','Mein Herz schlägt so komisch und mir ist schwindlig, ich sitze schon.',53,'Patient mit Herzrhythmusbeschwerden und Kreislaufproblemen. Notarzt erforderlich.',40,'RD-19C0'),
 ('cold-person','Unterkühlte Person','Wir haben draußen einen Mann gefunden. Er ist ganz nass und zittert, spricht aber mit uns.',63,'Patient ausgekühlt, ansprechbar. Versorgung und Transport.',58,'RD-20A1C'),
 ('heat-person','Hitzeproblem','Meine Schwester ist nach längerem Aufenthalt in der Sonne ganz schwach geworden.',26,'Patientin mit Kreislaufbeschwerden nach Hitzeexposition, aktuell ansprechbar.',63,'RD-26B1'),
 ('nosebleed','Anhaltendes Nasenbluten','Bei meiner Mutter hört das Nasenbluten nicht auf. Sie ist wach.',75,'Anhaltende Blutung, Patientin kreislaufstabil. Klinische Abklärung.',69,'RD-21A1M'),
 ('cut-hand','Schnittverletzung','Ich habe mich beim Kochen in die Hand geschnitten. Es blutet und tut weh.',34,'Schnittverletzung der Hand, keine massive Blutung. Wundversorgung im Krankenhaus.',83,'RD-30A1'),
 ('trapped-hand','Hand eingeklemmt','Ein Kollege hat die Hand in einer Maschine eingeklemmt. Die Maschine ist aus.',47,'Mannschaft sichert Einsatzstelle; technische Befreiung durch Feuerwehr erforderlich.',54,'RD-22A1'),
 ('medication-error','Medikamente verwechselt','Mein Vater hat seine Tabletten doppelt genommen. Er fühlt sich müde.',79,'Verdacht auf versehentliche Medikamentenüberdosierung. Patient wach, weitere Abklärung.',48,'RD-23B0'),
 ('child-poison','Mögliche Vergiftung bei Kind','Mein Kind hat aus einer offenen Flasche getrunken, ich weiß nicht wie viel.',4,'Mögliche Vergiftung, Kind wach. Notarzt zur weiteren Beurteilung erforderlich.',38,'RD-23B0'),
 ('pregnancy-pain','Schwangerschaft mit Schmerzen','Meine Frau ist schwanger und hat plötzlich starke Schmerzen im Bauch.',30,'Schwangere Patientin ansprechbar, Schmerzen. Transport in geeignete geburtshilfliche Versorgung.',60,'RD-24B0'),
 ('birth-imminent','Geburt möglicherweise bevorstehend','Die Wehen kommen sehr schnell, wir schaffen es nicht mehr ins Krankenhaus.',32,'Geburt möglicherweise unmittelbar bevorstehend, Notarztversorgung erforderlich.',40,'RD-24B0'),
 ('mental-crisis','Psychische Krise','Mein Freund ist völlig verzweifelt und sagt, er hält es nicht mehr aus. Ich bin bei ihm.',23,'Patient in psychischer Krise, kooperativ. Weitere fachliche Versorgung erforderlich.',56,'RD-25A0'),
 ('panic','Panik und schnelle Atmung','Meine Tochter weint und atmet ganz schnell, nachdem sie eine schlimme Nachricht bekommen hat.',21,'Patientin wach, starke Angst. Körperliche Ursachen noch abzuklären; Transport.',64,'RD-6C1'),
 ('fever-child','Fieber bei Kind','Unser Sohn hat Fieber, trinkt wenig und ist viel müder als sonst.',5,'Kind mit Fieber und reduziertem Allgemeinzustand, ansprechbar. Klinische Abklärung.',57,'RD-26B1'),
 ('vomiting','Erbrechen und Schwäche','Meine Frau erbricht seit gestern und schafft es kaum noch aufzustehen.',55,'Patientin mit Flüssigkeitsverlust und Kreislaufbeschwerden. Klinische Abklärung.',50,'RD-26B1'),
 ('infection-elder','Schwäche und Fieber','Mein Opa hat hohes Fieber und redet heute ganz durcheinander.',84,'Patient mit Fieber und Bewusstseinsveränderung. Notarztversorgung erforderlich.',32,'RD-26B1'),
 ('stroke-speech','Plötzliche Sprachstörung','Meine Mutter kann plötzlich nicht richtig sprechen und ein Arm ist schwächer.',72,'Hinweise auf akutes neurologisches Ereignis. Weitere Abklärung in geeigneter Klinik.',38,'RD-28C1L'),
 ('stroke-uncertain','Neurologische Auffälligkeit','Mein Mann wirkt seit dem Aufstehen anders und sein Gesicht sieht schief aus.',68,'Neurologische Auffälligkeiten, Beginn unklar. Notarzt und klinische Abklärung.',40,'RD-28C1L'),
 ('crash-cyclist','Radunfall','Ein Radfahrer ist gestürzt und hält sich die Schulter. Er trägt einen Helm.',36,'Patient mit Schulterverletzung, wach. Transport zur Abklärung.',70,'RD-29A1'),
 ('crash-pedestrian','Fußgänger angefahren','Ein Auto hat einen Fußgänger erwischt. Er liegt auf der Straße und spricht mit uns.',62,'Patient mit mehreren Verletzungen. Notarztversorgung erforderlich, Polizei sichert.',28,'RD-29A1'),
 ('faint-school','Kollaps in Schule','Eine Schülerin ist kurz umgekippt. Jetzt ist sie wieder wach und sitzt bei uns.',16,'Patientin nach kurzer Bewusstlosigkeit wach. Transport zur Abklärung.',68,'RD-31A1'),
 ('helpless-home','Hilflose Person in Wohnung','Mein Nachbar ruft um Hilfe, aber die Tür ist versperrt. Ich weiß nicht, was passiert ist.',77,'Feuerwehr öffnet Zugang. Patient am Boden, ansprechbar und geschwächt. Transport.',52,'RD-32B1'),
]

CATALOG=[]
for id,title,caller,age,report,score,code in CASES:
    critical=score<45
    consciousness='Keine normale Reaktion erkennbar.' if code=='RD-9E1' else 'Wach, aber nicht wie sonst; antwortet nur kurz.' if critical else 'Ja, die Person ist wach und antwortet.'
    breathing='Ich sehe keine normale Atmung.' if code=='RD-9E1' else 'Die Atmung wirkt angestrengt.' if code.startswith(('RD-6','RD-8','RD-10C','RD-14')) else 'Die Person atmet; genauer kann ich es gerade nicht beurteilen.'
    observations={
        'seizure-known':('Er ist wach, aber noch müde und verwirrt.','Er atmet, soweit ich das sehe.'),
        'seizure-first':('Sie reagiert noch nicht richtig auf mich.','Sie atmet, genauer kann ich es gerade nicht beurteilen.'),
        'electric-shock':('Ja, er ist wach und antwortet.','Er atmet, soweit ich das sehe.'),
        'fall-ladder':('Ja, er spricht mit mir.','Er atmet, genauer kann ich es gerade nicht beurteilen.'),
        'water-rescue':('Ja, er sitzt hier und ist ansprechbar.','Er atmet und hustet.'),
        'child-poison':('Ja, mein Kind ist wach.','Es atmet, soweit ich das sehe.'),
        'helpless-home':('Ich höre ihn rufen, aber sehe ihn nicht.','Das kann ich durch die versperrte Tür nicht beurteilen.')}
    if id in observations:consciousness,breathing=observations[id]
    CATALOG.append(scenario(id,title,caller,'Telefonische Angaben: '+caller,code,report,
        {'patient':f'Eine Person, ungefähr {age} Jahre alt.','consciousness':consciousness,'breathing':breathing,
         'access':'Ich bin unter dieser Nummer erreichbar. Eine zweite Person erwartet euch beim Eingang.'},
        age=age,score=score,trend=(-9,2) if critical else (-5,4),fire=id in ('co-alarm','smoke-inhalation','trapped-hand','helpless-home'),police=id in ('assault','crash-pedestrian')))

for id,title,caller,report in [
    ('two-crash','Verkehrsunfall mit unklarer Personenlage','Zwei Autos sind zusammengestoßen. Ein Mann klagt über Schmerzen, bei der zweiten Person bin ich mir nicht sicher.','Vor Ort zwei verletzte, ansprechbare Personen. Für den zweiten Patienten benötigen wir ein weiteres transportierendes Rettungsmittel.'),
    ('two-fall','Sturz mit zweiter betroffener Person','Meine Eltern sind gemeinsam auf der Stiege gestürzt. Meine Mutter kann nicht aufstehen, mein Vater sitzt daneben.','Zwei Patienten nach Sturz, beide mit Schmerzen und transportbedürftig. Zweites Rettungsmittel erforderlich.')]:
    item=scenario(id,title,caller,'Personenlage telefonisch noch unklar.','RD-29A1' if id=='two-crash' else 'RD-17B1',report,
        {'patient':'Zwei erwachsene Personen; ich weiß noch nicht, ob beide verletzt sind.','consciousness':'Beide sprechen mit mir.','breathing':'Beide atmen, eine auffällige Atemnot sehe ich nicht.','access':'Ich erwarte euch beim Eingang und bleibe unter dieser Nummer erreichbar.'},score=70)
    item['_scenario'].update(patient_count=2,patient_scores=[70,80]);CATALOG.append(item)

# Further original everyday incidents and calls whose true cause only becomes
# clear after the crew arrives. No LstSim scenarios or dialogue are imported.
from scenario_zone5 import SCENARIOS as ZONE5_SCENARIOS
CATALOG.extend(ZONE5_SCENARIOS)
