"""Fictional automatically paced caller dialogue, not an AMPDS interrogation protocol."""
import random
import os
import time
import re

def line_seconds(text):
    return max(1.4,len(re.findall(r'\S+',text))/3.5+0.3)

class Calls:
    def prepare_call(self,j):
        if j['kind']!='emergency' or j.get('call'):return
        name=random.choice(['Anna Berger','Thomas Winter','Sabine Leitner','Markus Huber','Eva Wagner','Florian Gruber','Petra Bauer','Miriam Steiner','Lukas Hofer','Elisabeth Mayer','Daniel Fischer','Johanna Leitner','Michael Schwarz','Nora Huber','Andreas König','Claudia Reiter','Felix Schuster','Maria Winkler','Leon Auer','Theresa Pichler','Paul Brandl','Katharina Moser','Simon Eder','Verena Fuchs','Stefan Haider','Lisa Koller','Robert Brunner','Sarah Graf','Martin Schmid','Julia Reisinger'])
        event=j.get('event_title',j['title']);unconscious=event=='Bewusstlose Person';dyspnea=event=='Atemnot';fall=event=='Sturz in Wohnung'
        questions=[
            ('location','Adresse bestätigen','Zur Sicherheit: Wo genau sind Sie? Welche Hausnummer, welcher Stock und welche Tür?',f'Ja, {j["address"]}. '+('Erster Stock, Tür 3.' if fall or dyspnea else 'Ich stehe direkt davor, draußen.')),
            ('event','Was ist passiert?','Was ist passiert? Erzählen Sie mir kurz, was Sie sehen.',j['caller']),
            ('patient','Wer ist betroffen?','Wer braucht Hilfe und wie alt ist die Person ungefähr?','Mein Vater, er ist 68.' if dyspnea else 'Meine Mutter, sie ist 79 Jahre alt.' if fall else 'Ich kenne die Person nicht, erwachsen jedenfalls.' if unconscious else 'Ein Autofahrer, vielleicht Mitte vierzig. Es ist eine verletzte Person.'),
            ('consciousness','Ist die Person ansprechbar?','Ist die Person wach und reagiert sie, wenn Sie sie ansprechen?','Nein, ich spreche ihn an, aber da kommt gar nichts.' if unconscious else 'Ja, sie antwortet mir.' if fall else 'Ja, er ist wach und antwortet, aber er wirkt sehr beunruhigt.'),
            ('breathing','Wie atmet die Person?','Atmet die Person? Was fällt Ihnen an der Atmung auf?','Ich weiß es nicht genau, ich kann das gerade nicht sicher erkennen.' if unconscious else 'Er atmet, aber ganz schwer. Er kann kaum einen ganzen Satz sagen.' if dyspnea else 'Ja, die Atmung sieht für mich normal aus.'),
            ('access','Zugang und Rückruf klären','Wie finden unsere Kräfte Sie? Gibt es beim Zugang etwas zu beachten, und bleiben Sie unter dieser Nummer erreichbar?','Ich bin unter dieser Nummer erreichbar. '+('Ich öffne unten die Haustür, die Klingel ist beschriftet.' if dyspnea or fall else 'Ich mache mich am Straßenrand bemerkbar.')),
        ]
        answers=j.get('_scenario',{}).get('answers',{})
        questions=[(key,label,question,answers.get(key,answer)) for key,label,question,answer in questions]
        j['call']={'state':'ringing','caller_name':name,'questions':[{'key':key,'label':label,'question':question,'answer':answer} for key,label,question,answer in questions],'answered':[],'transcript':[],'model':'Fiktiver Anrufdialog; kein originales AMPDS-Abfrageprotokoll'}

    def phone_line(self,j,speaker,text):
        call=j['call'];call['transcript'].append({'speaker':speaker,'text':text,'time':self.state['clock']})
        self.log(speaker+': '+text,'Telefon')

    def automatic_calls_enabled(self):
        return os.environ.get('CALL_AUTO','1')!='0'

    def schedule_call(self,j,intro=None):
        call=j['call'];pending=[]
        if intro:pending.append({'speaker':'Anrufer','text':intro})
        groups=[(('location','event'),'Wo genau sind Sie, und was ist passiert?'),(('patient','consciousness','breathing'),'Wer ist betroffen? Sind die Personen ansprechbar, und wie atmen sie?'),(('access',),'Wie kommen wir zu Ihnen? Bleiben Sie unter dieser Nummer erreichbar?')]
        for keys,question in groups:
            batch=[q for q in call['questions'] if q['key'] in keys and q['key'] not in call['answered']]
            if batch:
                pending.append({'speaker':'LEO','text':question})
                pending.append({'speaker':'Anrufer','text':' '.join(q['answer'] for q in batch),'answered_keys':[q['key'] for q in batch]})
        pending.extend([{'speaker':'LEO','text':'Wir schicken jemanden zu Ihnen.'},{'speaker':'Anrufer','text':'Okay, danke! Bitte kommen Sie bald.','ends_call':True}])
        # Normalize the text-only pace to ~38 seconds. Audio completion controls
        # progression when speech is active; server deadlines recover lost clients.
        rows=call['transcript'][-1:]+pending
        total=sum(line_seconds(row['text']) for row in rows)
        for row in rows:row['seconds']=round(38*line_seconds(row['text'])/total,3)
        call.update(automatic=True,state='connected',pending=pending,next_line_at=time.time()+rows[0]['seconds'],paused=False)


    def resume_calls(self):
        if not self.automatic_calls_enabled():return
        for j in self.state['jobs']:
            call=j.get('call')
            if call and not call.get('automatic') and call['state'] in ('connected','ready') and j['status']!='done':self.schedule_call(j)

    def flush_calls(self):
        now=time.time();changed=False
        for j in self.state['jobs']:
            call=j.get('call')
            if not call or not call.get('automatic') or call['state']!='connected':continue
            if j['status']=='done':call.update(state='ended',pending=[]);changed=True;continue
            if call.get('finishing') and not call.get('paused') and now>=call.get('next_line_at',now+2):
                call.update(state='ended',ended_at=self.state['clock'],pending=[]);call.pop('next_line_at',None);changed=True;continue
            pending=call.get('pending',[])
            if call.get('paused') or not pending or now<call.get('next_line_at',now+2):continue
            row=pending.pop(0);self.phone_line(j,row['speaker'],row['text'])
            call['transcript'][-1].update(spoken_at=now,seconds=row.get('seconds',2))
            keys=row.get('answered_keys',[])
            if keys:
                call['transcript'][-1]['answered_keys']=keys
                call['answered'].extend(key for key in keys if key not in call['answered'])
                if len(call['answered'])==len(call['questions']):j['asked']=True;j['asked_at']=self.state['clock']
            call['next_line_at']=now+(25 if call.get('speech_active') else row.get('seconds',2))
            if row.get('ends_call'):
                call['finishing']=True
            changed=True
        return changed

    def accept_call(self,j):
        self.prepare_call(j);j['accepted']=True;j['call']['state']='connected'
        self.phone_line(j,'LEO','Rettungsleitstelle Niederösterreich, wo genau ist der Notfallort?')
        self_intro=f'Hallo, {j["call"]["caller_name"]} mein Name. Ich bin in {j["address"]}. Bitte schicken Sie jemanden, hier braucht jemand Hilfe!'
        if j.get('fire') and j.get('_scenario',{}).get('no_patient'):self_intro=f'Feuerwehr-Einsatzleitung hier, Einsatzadresse {j["address"]}. '+j['caller']
        if self.automatic_calls_enabled():
            if not (j.get('fire') and j.get('_scenario',{}).get('no_patient')):self_intro=f'Hallo, {j["call"]["caller_name"]} mein Name. Bitte helfen Sie uns!'
            j['call']['transcript'][-1]['spoken_at']=time.time();self.schedule_call(j,self_intro)
        else:
            j['call']['automatic']=False;self.phone_line(j,'Anrufer',self_intro)

    def call_playback(self,data):
        j=self.get('jobs',data['job']);call=j.get('call')
        if not call or not call.get('automatic') or call['state']!='connected':return
        now=time.time();action=data.get('mode')
        if action=='pause':
            if not call.get('paused'):call['remaining']=max(.1,call.get('next_line_at',now)-now)
            call['paused']=True;call['speech_active']=False
        elif action in ('resume','speech'):
            if call.get('paused'):
                call.update(paused=False,next_line_at=now+call.pop('remaining',2))
            if action=='resume' and call.get('speech_active'):call['next_line_at']=now+call['transcript'][-1].get('seconds',2)
            call['speech_active']=action=='speech'
            if action=='speech':
                call['next_line_at']=now+25
                from speech import speech
                speech.prepare(call['transcript'][-1:]+call.get('pending',[]))
        elif action=='done':
            if call.get('paused') or data.get('line')!=len(call['transcript'])-1:return
            if call.get('finishing'):
                call.update(state='ended',ended_at=self.state['clock'],pending=[]);call.pop('next_line_at',None)
            else:
                call['next_line_at']=now
                self.flush_calls()
        else:raise ValueError('Ungültige Anrufsteuerung.')

    def question_call(self,data):
        j=self.get('jobs',data['job']);self.prepare_call(j);call=j.get('call')
        if not j['accepted'] or not call or call['state'] not in ('connected','ready'):raise ValueError('Zuerst den Notruf annehmen; Gespräch muss offen sein.')
        if call.get('automatic'):raise ValueError('Die Anrufabfrage läuft automatisch. Bitte das Gespräch abwarten.')
        unanswered=[q for q in call['questions'] if q['key'] not in call['answered']]
        if not unanswered or data.get('question')!=unanswered[0]['key']:raise ValueError('Die nächste offene Abfrage auswählen.')
        q=unanswered[0]
        if data.get('combined') is True:
            groups=[(('location','event'),'Wo genau sind Sie, und was ist passiert?'),(('patient','consciousness','breathing'),'Wer ist betroffen? Sind die Personen ansprechbar, und wie atmen sie?'),(('access',),'Wie kommen wir zu Ihnen? Bleiben Sie unter dieser Nummer erreichbar?')]
            keys,question=next((keys,text) for keys,text in groups if q['key'] in keys)
            batch=[item for item in unanswered if item['key'] in keys]
            self.phone_line(j,'LEO',question)
            self.phone_line(j,'Anrufer',' '.join(item['answer'] for item in batch))
            call['transcript'][-1]['answered_keys']=[item['key'] for item in batch]
            call['answered'].extend(item['key'] for item in batch)
        else:
            self.phone_line(j,'LEO',q['question']);self.phone_line(j,'Anrufer',q['answer']);call['answered'].append(q['key'])
        if len(call['answered'])==len(call['questions']):call['state']='ready';j['asked']=True;j['asked_at']=self.state['clock']

    def finish_call(self,data):
        j=self.get('jobs',data['job']);self.prepare_call(j);call=j.get('call')
        if not call or call['state']!='ready':raise ValueError('Notruf zuerst vollständig abfragen.')
        self.phone_line(j,'LEO','Wir schicken jemanden zu Ihnen.')
        self.phone_line(j,'Anrufer','Okay, danke! Bitte kommen Sie bald.')
        call['state']='ended';call['ended_at']=self.state['clock'];self.log('Telefonat beendet.','Telefon')
