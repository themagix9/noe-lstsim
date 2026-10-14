"""Stable simulated ground turnout times, not an operational/legal standard."""
import hashlib
import re

DAY_RANGES={'A':(85,120),'B':(60,84),'C':(40,59),'D':(25,39),'E':(15,24)}
NIGHT_RANGES={'A':(125,180),'B':(90,124),'C':(60,89),'D':(30,59),'E':(15,29)}

def seconds(engine,v,j):
    # Aircraft retain their separately configured start preparation.
    if v['type']=='NAH':return float(v.get('turnout',180))
    if v['status'] not in ('ready','radio','hospital','fr_ready','assigned','acknowledged','standby'):
        return float(v.get('turnout',60))
    night=not 21600<=engine.state['clock']%86400<64800
    code=j.get('code') or ''
    match=re.search(r'(?:^|-)\d+([ABCDE])\d',code)
    level=match.group(1) if match else 'A'
    low,high=(NIGHT_RANGES if night else DAY_RANGES)[level]
    if re.fullmatch(r'(?:RD-)?9E1',code):low,high=15,25
    origin=v.get('alarm_from') if v['status'] in ('assigned','acknowledged','standby') else v['status']
    if origin in ('radio','hospital'):low,high=5,15
    # Same estimate in AAO, modal and dispatch; never re-roll on live refresh.
    key=f'{j["id"]}:{v["id"]}:{code}:{int(engine.state["clock"]//86400)}:{night}'
    sample=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big')
    return low+sample%(high-low+1)

def preparation(engine,v,j):
    handover=max(0,(v.get('handover_due') or v.get('phase_due') or 0)-engine.state['clock']) if v['status']=='hospital' else 0
    return seconds(engine,v,j)+handover
