"""Stable, single-speaker German voices; no random speaker or pitch changes."""
def profile(identity,gender=None):
    return {'model':'leo' if identity=='LEO' else 'female' if gender=='female' else 'clear','speaker_id':0,'identity':str(identity)}

def caller_profile(job):
    from caller_context import gender_for_name
    call=job['call'];gender=call.get('caller_gender') or gender_for_name(call.get('caller_name',''))
    expected=profile('caller:'+job['id'],gender)
    if call.get('voice_profile')!=expected:call['voice_profile']=expected
    return call['voice_profile']

def resource_profile(vehicle):return profile('resource:'+vehicle['id'])
