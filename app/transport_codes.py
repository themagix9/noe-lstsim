"""Consistent automatic transport orders using only existing catalogue codes."""
import random

CODES={
 'Entlassung':{'tragstuhl':'KTR-95K2','liegend':'KTR-95K3'},
 'Ambulanztermin':{'tragstuhl':'KTR-90K2','liegend':'KTR-90K3'},
 'Dialysefahrt':{'gehfaehig':'KTR-93Y1','tragstuhl':'KTR-93Y2'},
 'Überstellung':{'tragstuhl':'KTR-96K2','liegend':'KTR-96K3'},
 'Strahlentherapie':{'gehfaehig':'KTR-93S1','tragstuhl':'KTR-93S2','liegend':'KTR-93S3'},
}
DETAILS={'gehfaehig':'Gehfähiger Patient, selbstständig mobil.','tragstuhl':'Tragstuhltransport, Unterstützung beim Umsetzen erforderlich.','liegend':'Liegendtransport, zwei Sanitäter erforderlich.'}

def assign(engine,j,preserve_mode=False):
    purpose=j.get('transport_purpose') or j.get('event_title') or j['title']
    if j.get('origin_hospital') and not j.get('transport_destination'):purpose='Überstellung'
    if purpose not in CODES:purpose='Ambulanztermin'
    modes=CODES[purpose];text=j.get('detail','').lower()
    mode=('liegend' if 'liegend' in text else 'gehfaehig' if 'gehfähig' in text else 'tragstuhl') if preserve_mode else random.choice(list(modes))
    # Existing lying dialysis orders use the catalogue's general lying code;
    # never invent an unverified dialysis suffix.
    code=modes.get(mode,'KTR-90K3' if mode=='liegend' else 'KTR-90K2')
    rule=engine.rule(code)
    j.update(code=code,code_confirmed=True,code_source='Elektronischer Transportauftrag',transport_purpose=purpose,transport_mode=mode,detail=DETAILS[mode]+' Keine akute Verschlechterung gemeldet.',title=rule['title'],category=rule['category'],needs=rule['needs'][:],priority=rule['priority'])
    return code
