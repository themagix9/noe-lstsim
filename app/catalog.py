"""Public setup catalog; zone boundaries/fleet outside 05 are not verified."""
CENTRES=['Mödling','St. Pölten','Stockerau','Zwettl']
ZONES=[{'id':f'{n:02}','name':f'Dispozone {n:02}'+(' · Bruck/Leitha (Startbestand)' if n==5 else ' · Bestand noch zu ergänzen')} for n in range(1,7)]
RULES=[
 {'code':'SIM-BEIST','title':'Beistellung / Absicherung (Übung)','kind':'emergency','priority':'mittel','needs':['RTW'],'signal':False},
 {'code':'SIM-ATEM','title':'Atemnot','kind':'emergency','priority':'hoch','needs':['RTW','NEF'],'signal':True},
 {'code':'SIM-STURZ','title':'Sturz in Wohnung','kind':'emergency','priority':'mittel','needs':['RTW'],'signal':False},
 {'code':'SIM-BEW','title':'Bewusstlose Person','kind':'emergency','priority':'hoch','needs':['RTW','NEF'],'signal':True},
 {'code':'SIM-VU','title':'Verkehrsunfall','kind':'emergency','priority':'mittel','needs':['RTW'],'signal':False},
 {'code':'SIM-KT','title':'Transportauftrag','kind':'transport','priority':'geplant','needs':['KTW'],'signal':False},
]

# Krankentransport-Codes aus der vom Nutzer bereitgestellten LstSim-Ablaufreferenz.
# Sie sind getrennt vom AMPDS-RD-Katalog, werden in der Oberfläche aber im selben
# Alarmierungsstichwort-Feld angeboten.
TRANSPORT_CODES=[
 ('KTR-90K2','Krankentransport – Tragstuhl',False),
 ('KTR-90K3','Krankentransport – liegend',False),
 ('KTR-93S1','Strahlentherapie – gehfähig',False),
 ('KTR-93S2','Strahlentherapie – Tragstuhl',False),
 ('KTR-93S3','Strahlentherapie – liegend',False),
 ('KTR-95S1','Strahlentherapie Heimtransport – gehfähig',False),
 ('KTR-95S2','Strahlentherapie Heimtransport – Tragstuhl',False),
 ('KTR-95S3','Strahlentherapie Heimtransport – liegend',False),
 ('KTR-95K2','Stationärer Heimtransport – Tragstuhl',False),
 ('KTR-95K3','Stationärer Heimtransport – liegend',False),
 ('KTR-95K2A','Ambulanter Heimtransport – Tragstuhl',False),
 ('KTR-95K3A','Ambulanter Heimtransport – liegend',False),
 ('KTR-93Y1','Dialyse – gehfähig',False),
 ('KTR-93Y2','Dialyse – Tragstuhl',False),
 ('KTR-95Y1','Dialyse Heimtransport – gehfähig',False),
 ('KTR-95Y2','Dialyse Heimtransport – Tragstuhl',False),
 ('KTR-96K2','Überstellung – Tragstuhl',False),
 ('KTR-96K3','Überstellung – liegend',False),
 ('KTR-96K2!','Überstellung – Tragstuhl SOFORT',False),
 ('KTR-96K3!','Überstellung – liegend SOFORT',False),
 ('KTR-90K2!','Einweisung – sitzend SOFORT',False),
 ('KTR-90K3!','Einweisung – liegend SOFORT',True),
 ('KTR-94B1','Bluttransport mit Sondersignal',True),
 ('KTR-94B4','Organtransport mit Sondersignal',True),
 ('KTR-94K1','Bluttransport',False),
 ('KTR-94K4','Organtransport',False),
 ('KTx-96K5','Überstellung mit RTW und Arzt (beigestellt)',True),
]
TRANSPORT_RULES=[{'code':code,'title':title,'kind':'transport','priority':'dringend' if signal else 'geplant','needs':['RTW'] if code=='KTx-96K5' else ['KTW'],'signal':signal,'category':'Krankentransport'} for code,title,signal in TRANSPORT_CODES]
