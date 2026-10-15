"""Original fictional NÖ incidents; caller observations are separate from scene truth."""

def scenario(id,title,caller,detail,code,report,answers,score=70,trend=(-5,3),no_patient=False,fire=False,police=False,hold=120,age=None,perspective=None):
    from caller_context import context_for
    context=context_for({'scenario_id':id,'caller':caller,'detail':detail,'_scenario':{'answers':answers}},age,perspective)
    return {'scenario_id':id,'title':title,'caller':caller,'detail':detail,'suggested_code':code,
            'priority':'mittel','needs':['RTW'],'scene':report,'fire':fire,'police':police,
            '_scenario':{'call_context':context,'report':report,'answers':answers,'initial_percent':score,'trend':list(trend),
                         'no_patient':no_patient,'hold_seconds':hold,'source':'Eigene fiktive NÖ-Übung'}}

EXTRA_SCENARIOS=[
    scenario('garage-smoke','Beistellung Garagenbrand',
        'Hier Feuerwehr, wir fahren zu einer Rauchentwicklung bei einer Garage. Bitte ein Rettungsmittel zur Beistellung; Verletzte sind uns derzeit nicht bekannt.',
        'Feuerwehrmeldung: Rauchentwicklung, Personenlage noch unklar.', 'SIM-BEIST',
        'Erkundung mit der Feuerwehr abgeschlossen: Rauch von einem Ofen, kein Brand und keine betroffenen Personen. Keine rettungsdienstliche Versorgung erforderlich.',
        {'patient':'Wir haben bisher keine verletzten Personen gemeldet bekommen.','consciousness':'Das ist noch nicht erhoben; wir fahren gerade zu.','breathing':'Dazu haben wir keine Angaben.','access':'Die Feuerwehr weist euch bei der Zufahrt ein.'},no_patient=True,fire=True),
    scenario('fire-standby','Beistellung Wohnhausbrand',
        'Feuerwehr-Einsatzleitung hier. Wir löschen einen Brand in einem leerstehenden Haus. Bitte ein Fahrzeug zur Absicherung der eingesetzten Kräfte.',
        'Feuerwehr fordert eine Beistellung; aktuell keine Verletzten bekannt.', 'SIM-BEIST',
        'Mit der Einsatzleitung Rücksprache gehalten: Alle Personen außerhalb des Gefahrenbereichs, niemand verletzt. Wir bleiben vorerst zur Absicherung vor Ort.',
        {'patient':'Aktuell niemand verletzt. Es geht um die Absicherung unserer Mannschaft.','consciousness':'Keine betroffene Person bekannt.','breathing':'Keine Beschwerden gemeldet.','access':'Bereitstellungsraum vor dem Gebäude, Zufahrt von der Feuerwehr freigehalten.'},no_patient=True,fire=True,hold=600),
    scenario('seizure-mistaken-stroke','Verdacht auf Schlaganfall',
        'Mein Bruder ist plötzlich umgefallen! Sein Arm hat so komisch gezuckt. Ich glaube, das ist ein Schlaganfall. Jetzt sagt er gar nichts mehr.',
        'Angehörige meldet Kollaps, Zuckungen und eingeschränkte Reaktion.', 'RD-31D3',
        'Vor Ort Hinweise auf einen Krampfanfall. Patient jetzt ansprechbar, aber noch deutlich verwirrt. Die telefonische Schlaganfallvermutung hat sich bisher nicht bestätigt; weitere Abklärung erforderlich.',
        {'patient':'Mein Bruder, 42 Jahre.','consciousness':'Er macht die Augen auf, aber antwortet nicht richtig.','breathing':'Er atmet hörbar; ich bin ziemlich aufgeregt und kann das schwer beschreiben.','access':'Erdgeschoß, die Haustür ist offen. Ich warte bei ihm.'},score=38,trend=(-8,2)),
    scenario('collapse-low-sugar','Kollaps im Geschäft',
        'Eine Kundin sitzt hier am Boden und ist ganz neben sich. Sie schaut mich an, aber spricht kaum. Vielleicht hat sie etwas getrunken?',
        'Verkäufer meldet verwirrte Person; Ursache telefonisch unklar.', 'RD-31D3',
        'Patientin mit deutlich erniedrigtem Blutzucker, keine Hinweise auf eine Alkoholisierung. Notarzt zur weiteren Versorgung erforderlich.',
        {'patient':'Eine Kundin, ich schätze sie auf ungefähr fünfzig.','consciousness':'Sie hat die Augen offen, reagiert aber nur langsam.','breathing':'Sie atmet, eine auffällige Atemnot sehe ich nicht.','access':'Eingang beim Parkplatz. Mein Kollege erwartet euch dort.'},score=32,trend=(-10,1)),
    scenario('crash-uninjured','Verkehrsunfall unklare Verletzung',
        'Bei uns sind zwei Autos zusammengestoßen. Beide Fahrer stehen draußen, einer hält sich den Arm. Ob jemand verletzt ist, weiß ich nicht.',
        'Zwei Fahrzeuge, beide Fahrer ausgestiegen, Verletzungen unklar.', 'RD-29A1',
        'Beide Beteiligten untersucht, keine Verletzung und keine Beschwerden festgestellt. Kein Patiententransport erforderlich; Polizei übernimmt die Unfallaufnahme.',
        {'patient':'Zwei Fahrer, beide erwachsen.','consciousness':'Beide sind wach und reden miteinander.','breathing':'Beide atmen normal, soweit ich sehe.','access':'Wir stehen am Gehsteig neben den Fahrzeugen; die Fahrbahn ist teilweise blockiert.'},no_patient=True,police=True),
    scenario('fall-underestimated','Sturz im Garten',
        'Mein Papa ist im Garten ausgerutscht. Er sagt, es ist eh nichts, aber er kommt nicht auf und ist jetzt ganz blass.',
        'Angehörige meldet Sturz, Schmerzen und auffällige Blässe.', 'RD-17B1',
        'Patient mit starken Schmerzen nach Sturz und zunehmender Kreislaufinstabilität. Notarzt am Berufungsort erforderlich.',
        {'patient':'Mein Vater, 76.','consciousness':'Ja, er antwortet, aber er wirkt schwächer als vorhin.','breathing':'Er atmet schneller und sagt, dass ihm schwindlig ist.','access':'Durch das offene Gartentor, hinter dem Haus. Ich bin unter dieser Nummer erreichbar.'},score=40,trend=(-9,1)),
]
