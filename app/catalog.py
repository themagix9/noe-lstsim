"""Public setup catalog; zone boundaries/fleet outside 05 are not verified."""
CENTRES=['Mödling','St. Pölten','Stockerau','Zwettl']
ZONES=[{'id':f'{n:02}','name':f'Dispozone {n:02}'+(' · Bruck/Leitha (Startbestand)' if n==5 else ' · Bestand noch zu ergänzen')} for n in range(1,7)]
RULES=[
 {'code':'SIM-ATEM','title':'Atemnot','kind':'emergency','priority':'hoch','needs':['RTW','NEF'],'signal':True},
 {'code':'SIM-STURZ','title':'Sturz in Wohnung','kind':'emergency','priority':'mittel','needs':['RTW'],'signal':False},
 {'code':'SIM-BEW','title':'Bewusstlose Person','kind':'emergency','priority':'hoch','needs':['RTW','NEF'],'signal':True},
 {'code':'SIM-VU','title':'Verkehrsunfall','kind':'emergency','priority':'mittel','needs':['RTW'],'signal':False},
 {'code':'SIM-KT','title':'Transportauftrag','kind':'transport','priority':'geplant','needs':['KTW'],'signal':False},
]
