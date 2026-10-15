"""Stable synthetic voice identities, independent of wording, status and callsign."""
import hashlib

def profile(identity):
    if identity=='LEO':return {'model':'leo','speaker_id':0,'identity':'LEO'}
    number=int.from_bytes(hashlib.sha256(str(identity).encode()).digest()[:8],'big')%236
    return {'model':'mls','speaker_id':number,'identity':str(identity)}

def caller_profile(job):
    return job['call'].setdefault('voice_profile',profile('caller:'+job['id']))

def resource_profile(vehicle):return profile('resource:'+vehicle['id'])
