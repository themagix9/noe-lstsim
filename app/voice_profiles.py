"""Stable identities using the intelligible single-speaker German model.

The former MLS pool is intentionally retired: arbitrary speaker IDs produced
unintelligible calls. Identity remains stable, but is not a promise of a unique
human voice for every resource. Telephone filtering distinguishes callers.
"""
def profile(identity):
    return {'model':'leo' if identity=='LEO' else 'clear','speaker_id':0,'identity':str(identity)}

def caller_profile(job):
    current=job['call'].get('voice_profile')
    if not current or current.get('model')!='clear' or current.get('speaker_id')!=0:
        job['call']['voice_profile']=profile('caller:'+job['id'])
    return job['call']['voice_profile']

def resource_profile(vehicle):return profile('resource:'+vehicle['id'])
