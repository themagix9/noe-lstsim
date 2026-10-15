"""Deterministic spoken formulations; never invent or alter an incident address."""
import re

_UNITS=['null','eins','zwei','drei','vier','fünf','sechs','sieben','acht','neun','zehn','elf','zwölf','dreizehn','vierzehn','fünfzehn','sechzehn','siebzehn','achtzehn','neunzehn']
_TENS={20:'zwanzig',30:'dreißig',40:'vierzig',50:'fünfzig',60:'sechzig',70:'siebzig',80:'achtzig',90:'neunzig'}
def number(value):
    n=int(value)
    if n<20:return _UNITS[n]
    if n<100:return (('ein' if n%10==1 else _UNITS[n%10])+'und' if n%10 else '')+_TENS[n//10*10]
    if n<1000:return ('ein' if n//100==1 else _UNITS[n//100])+'hundert'+(number(n%100) if n%100 else '')
    if n<10000:return ('ein' if n//1000==1 else number(n//1000))+'tausend'+(number(n%1000) if n%1000 else '')
    return ' '.join(_UNITS[int(c)] for c in str(value))

def address_reply(job):
    p=job.get('address_point') or {}
    street,house,postcode,city=(str(p.get(k) or '') for k in ('street','house_number','postcode','city'))
    if not (street and house and city):
        match=re.fullmatch(r'(.+?)\s+(\d+[\w/\-]*),\s*(\d{4})\s+(.+)',job['address'])
        if not match:return 'Ja, die Adresse ist '+job['address']+'.'
        street,house,postcode,city=match.groups()
    prep='am' if re.search(r'(platz|weg|ring|gürtel|damm|markt)$',street,re.I) else 'in der' if re.search(r'(straße|strasse|gasse|allee|zeile)$',street,re.I) else 'bei der Adresse'
    return f'Ja, wir sind {prep} {street} Nummer {house} in {postcode} {city}.'.replace('  ',' ')

def speech_text(text):
    text=re.sub(r'\b(\d{2})(\d{2})(?=\s+[A-ZÄÖÜ])',lambda m:number(m[1])+' '+number(m[2]),text)
    text=re.sub(r'\b(\d{2})/(\d{3})\b',lambda m:number(m[1])+' '+' '.join(number(c) for c in m[2]),text)
    text=re.sub(r'\b(\d+)([a-zA-Z]?)\b',lambda m:number(m[1])+(' '+m[2] if m[2] else ''),text)
    for key,value in {'NEF':'Notarzteinsatzfahrzeug','RTW':'Rettungswagen','KTW':'Krankentransportwagen','CPR':'Reanimation','NÖ':'Niederösterreich','KH':'Krankenhaus','SDS':'Es De Es','ESApp':'Es App'}.items():text=re.sub(r'\b'+key+r'\b',value,text)
    return text
