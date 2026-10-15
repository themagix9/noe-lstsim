"""Original scenario additions aligned with the bundled code catalogue.
Reported observations are deliberately separate from the finding at scene.
"""
import json,random
from pathlib import Path
from scenarios import scenario

ROWS=json.loads((Path(__file__).parent/'data'/'incidents-zone5.json').read_text())['incidents']
SCENARIOS=[]
for row in ROWS:
    code=row['code'];absent=row.get('no_patient',False);arrest=code=='RD-9E1'
    answers=dict(patient='Ich kann noch nicht sicher sagen, ob jemand betroffen ist.' if absent else f'Eine Person, ungefähr {row["age"]} Jahre alt.',
        consciousness='Ich kann keine Reaktion sicher erkennen.' if absent else 'Nein, keine Reaktion.' if arrest else 'Die Person ist wach und reagiert auf Ansprache.',
        breathing='Das kann ich aus der Entfernung nicht beurteilen.' if absent else 'Keine normale Atmung erkennbar.' if arrest else 'Die Person atmet deutlich angestrengt.' if code.startswith(('RD-6','RD-10C1')) else 'Die Person atmet regelmäßig, soweit ich das sehen kann.',
        access='Ich bleibe unter dieser Nummer erreichbar und mache mich beim Zugang bemerkbar.')
    item=scenario(row['id'],row['title'],row['caller'],'Telefonische Angaben: '+row['caller'],code,row['report'],answers,
        age=row['age'] if not absent or row['id']=='zone5-095' else None,score=row['percent'],trend=(-7,2) if row['percent']<45 else (-3,4),no_patient=absent,
        fire=row.get('fire',False) or code.startswith(('RD-8','RD-22A2')),police=row.get('police',False) or code.startswith(('RD-4','RD-29')))
    SCENARIOS.append(item)

def choose(engine,legacy):
    from scenario_catalog import CATALOG
    from scenarios import EXTRA_SCENARIOS
    from manv_scenarios import MANV_SCENARIOS
    pool={s.get('scenario_id','legacy-'+str(i)):s for i,s in enumerate(legacy+EXTRA_SCENARIOS+CATALOG+MANV_SCENARIOS)}
    signature='|'.join(sorted(pool));bag=engine.state.get('scenario_rotation',[])
    if engine.state.get('scenario_pool')!=signature or not bag:
        bag=list(pool);random.shuffle(bag)
        previous=engine.state.get('last_scenario')
        if len(bag)>1 and bag[-1]==previous:bag[0],bag[-1]=bag[-1],bag[0]
    id=bag.pop();engine.state.update(scenario_pool=signature,scenario_rotation=bag,last_scenario=id)
    return pool[id]
