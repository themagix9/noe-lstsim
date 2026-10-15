"""Consistent fictional caller perspective, facts and conversational wording."""
import re

FEMALE_NAMES={'Anna','Sabine','Eva','Petra','Miriam','Elisabeth','Johanna','Nora','Claudia','Maria','Theresa','Katharina','Verena','Lisa','Sarah','Julia'}
NAMES=['Anna Berger','Thomas Winter','Sabine Leitner','Markus Huber','Eva Wagner','Florian Gruber','Petra Bauer','Miriam Steiner','Lukas Hofer','Elisabeth Mayer','Daniel Fischer','Johanna Leitner','Michael Schwarz','Nora Huber','Andreas König','Claudia Reiter','Felix Schuster','Maria Winkler','Leon Auer','Theresa Pichler','Paul Brandl','Katharina Moser','Simon Eder','Verena Fuchs','Stefan Haider','Lisa Koller','Robert Brunner','Sarah Graf','Martin Schmid','Julia Reisinger']
SELF_IDS={'allergy-rash','dog-bite','back-pain','burn-kitchen','chest-young','eye-injury','headache','palpitations','cut-hand','birth-imminent'}
SELF_ZONE={1,5,6,7,8,9,10,11,15,16,17,18,24,25,26,27,34,35,43,45,49,51,52,54,55,58,60,62,63,65,66,71,72,75,77,79,85,90,91,94,95,97,98,102,105,107,108,109,110,111}
RELATIONS=[('mein Kind',None,r'mein(?:em|en|es)? kind|unser(?:em|en)? kind'),('meine Großmutter','female',r'meine(?:r)? (?:oma|großmutter)'),('mein Großvater','male',r'mein(?:em|en|es)? (?:opa|großvater)'),('meine Mutter','female',r'meine(?:r)? (?:ältere |alte )?(?:mutter|mama)'),('mein Vater','male',r'mein(?:em|en|es)? (?:vater|papa)'),('meine Frau','female',r'meine(?:r)? frau'),('mein Mann','male',r'mein(?:em|en|es)? mann'),('meine Tochter','female',r'meine(?:r)? tochter'),('mein Sohn','male',r'mein(?:em|en|es)? sohn(?:es)?|unser(?:em|en)? (?:sohn|kleiner)'),('meine Schwester','female',r'meine(?:r)? schwester'),('mein Bruder','male',r'mein(?:em|en|es)? bruder'),('meine Freundin','female',r'meine(?:r)? freundin'),('mein Freund','male',r'mein(?:em|en|es)? freund'),('meine Tante','female',r'meine(?:r)? tante'),('meine Nachbarin','female',r'meine(?:r)? nachbarin'),('mein Nachbar','male',r'mein(?:em|en|es)? nachbar')]

def gender_for_name(name):return 'female' if str(name).split(' ',1)[0] in FEMALE_NAMES else 'male'

def context_for(item,age=None,perspective=None):
    text=item.get('caller','');low=text.lower();id=item.get('scenario_id','')
    relation=next(((label,gender) for label,gender,pattern in RELATIONS if re.search(pattern,low)),None)
    agency=bool(re.search(r'feuerwehr|hier (?:rufhilfe|hausnotruf|notrufsystem)|automatischer alarm|notrufknopf|medizinischer notruf ist eingegangen',low)) and not relation
    self_call=id in SELF_IDS or id.startswith('zone5-') and id[6:].isdigit() and int(id[6:]) in SELF_ZONE
    if perspective:role=perspective
    elif agency:role='agency'
    elif self_call:role='self'
    elif id.startswith('manv-') or id in ('two-crash','two-fall','co-alarm','zone5-029'):role='group'
    elif relation:role='relative'
    else:role='witness'
    if age is None:
        match=re.search(r'\b(\d{1,3})\s*(?:Jahre|Jahr|jährig)',item.get('detail',''),re.I)
        age=int(match[1]) if match else None
    if age is None:
        answer=(item.get('_scenario',{}).get('answers') or {}).get('patient','')
        match=re.search(r'\b(\d{1,3})\b',answer);age=int(match[1]) if match else None
    return dict(role=role,age=age,relation=relation[0] if relation else None,patient_gender=relation[1] if relation else 'female' if 'schwanger' in low or id=='birth-imminent' else None,remote=bool(re.search(r'aus der entfernung|vom fenster|aus dem fenster|keinen sprechkontakt|nicht über die anlage|bekommen zunächst keinen|durch das fenster|erreiche .* nicht|nicht mehr an ihn heran|tür ist versperrt|öffnet die wohnungstür nicht|schafft es nicht zur tür|jetzt erreicht ihn keiner|noch weiter weg|näher kann ich nicht',low)))

def normalize_questions(job):
    call=job['call'];context=dict(job.get('_scenario',{}).get('call_context') or context_for(job));call['context']=context
    call['caller_gender']=context.get('patient_gender') if context['role']=='self' and context.get('patient_gender') else gender_for_name(call['caller_name'])
    role=context['role'];age=context.get('age');text=job.get('caller','');low=text.lower();answers={q['key']:q['answer'] for q in call['questions']}
    relation=context.get('relation');p='sie' if context.get('patient_gender')=='female' else 'er' if context.get('patient_gender')=='male' else 'die Person'
    if role=='self':
        answers['patient']='Ich bin '+str(age)+' Jahre alt.' if age is not None else 'Ich rufe für mich selbst an.'
        answers['consciousness']='Ja, ich kann mit Ihnen sprechen.'
        answers['breathing']='Ich bekomme schlecht Luft.' if re.search(r'bekomme.*(?:schlecht|kaum).*luft|schwer luft|luftnot|atemnot',low) and not re.search(r'keine (?:luftnot|atemnot)',low) else 'Ich bekomme Luft, ja.'
        from spoken_text import address_reply
        answers['location']=address_reply(job).replace('wir sind','ich bin')
        answers['access']='Sie erreichen mich unter dieser Nummer. Ich bleibe am Telefon.'
    elif role=='relative' and relation:
        answers['patient']=relation[0].upper()+relation[1:]+(f', {age} Jahre alt.' if age is not None else '.')
        # Keep hand-written clinical observations; generated templates use the actual relation.
        for key in ('consciousness','breathing'):
            answers[key]=re.sub(r'\b[Dd]ie Person\b',p.capitalize(),answers[key])
        answers['access']='Ich bleibe bei '+('ihr' if p=='sie' else 'ihm')+' und bin unter dieser Nummer erreichbar.' if not context['remote'] else 'Ich bin unter dieser Nummer erreichbar. Zur Person komme ich gerade nicht hin.'
    elif role=='witness' and age is not None:
        answers['patient']=f'Eine erwachsene Person, ich schätze ungefähr {age} Jahre.' if age>=18 else f'Ein Kind, ich schätze ungefähr {age} Jahre.'
    if role=='group' and re.match(r'Eine Person, ungefähr',answers['patient']):
        answers['patient']='Zwei Personen sind betroffen.' if job.get('scenario_id') in ('co-alarm','zone5-029') else 'Mehrere Personen sind betroffen, die genaue Zahl weiß ich noch nicht.'
    if role=='group' and job.get('scenario_id') in ('co-alarm','zone5-029'):
        answers['consciousness']='Wir können beide mit Ihnen sprechen.'
        answers['breathing']='Wir bekommen Luft, aber uns ist schwindlig.'
    if role=='agency' and 'Eine Person, ungefähr' in answers['patient']:
        answers['patient']='Uns liegt eine Meldung über eine betroffene Person vor. Genauere Angaben haben wir noch nicht.'
    if context['remote']:
        answers.update(consciousness='Das kann ich von hier aus nicht erkennen.',breathing='So weit sehe ich nicht hin. Das kann ich Ihnen nicht sagen.')
    if role!='self':
        # Do not invent a second helper at every door, nor a standing caller indoors.
        answers['location']=answers['location'].split(' Ich stehe direkt davor')[0]
        if 'Eine zweite Person erwartet' in answers['access']:answers['access']='Ich bin unter dieser Nummer erreichbar und beschreibe Ihnen den Zugang.'
    if role=='self' and context.get('patient_gender')=='female' and gender_for_name(call['caller_name'])!='female':
        import random
        call['caller_name']=random.choice([name for name in NAMES if gender_for_name(name)=='female'])
    for q in call['questions']:
        q['answer']=answers[q['key']]
        if role=='self':
            q['question']={'patient':'Wie alt sind Sie?','consciousness':'Können Sie mir gut folgen?','breathing':'Bekommen Sie normal Luft?','event':'Was ist Ihnen passiert?'}.get(q['key'],q['question'])
            q['label']={'patient':'Eigenes Alter','consciousness':'Ansprechbarkeit','breathing':'Ihre Atmung'}.get(q['key'],q['label'])
    call['context_version']=2
    return context

def groups_for(call):
    role=call.get('context',{}).get('role')
    if role=='self':
        return [(('location','event'),'Wo genau sind Sie, und was ist Ihnen passiert?'),(('patient','consciousness','breathing'),'Wie alt sind Sie, und bekommen Sie normal Luft?'),(('access',),'Bleiben Sie unter dieser Nummer erreichbar?')]
    if role=='agency':
        return [(('location','event'),'Wo ist der Einsatz, und welche Unterstützung benötigen Sie?'),(('patient','consciousness','breathing'),'Welche Angaben haben Sie zu betroffenen Personen?'),(('access',),'Wo sollen sich unsere Kräfte melden?')]
    return [(('location','event'),'Wo genau sind Sie, und was ist passiert?'),(('patient','consciousness','breathing'),'Wer ist betroffen? Ist die Person ansprechbar und atmet sie?' if role!='group' else 'Wie viele Personen sind betroffen? Reagieren sie und atmen sie?'),(('access',),'Bleiben Sie erreichbar? Wie finden wir Sie?')]

def answer_for(call,batch):
    context=call.get('context',{});role=context.get('role');keys={q['key'] for q in batch}
    if role=='self' and 'patient' in keys:return ' '.join(q['answer'] for q in batch if q['key']!='consciousness')
    if role=='group' and job.get('scenario_id') in ('co-alarm','zone5-029'):
        answers['consciousness']='Wir können beide mit Ihnen sprechen.'
        answers['breathing']='Wir bekommen Luft, aber uns ist schwindlig.'
    if role=='agency' and 'patient' in keys:return next(q['answer'] for q in batch if q['key']=='patient')
    return ' '.join(q['answer'] for q in batch)
