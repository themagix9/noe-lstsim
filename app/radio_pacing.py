"""Real-time speech pacing shared by every client, independent of simulation speed."""
import os
import time
import uuid

class RadioPacing:
    def flush_radio(self):
        pending=self.state.setdefault('radio_pending',[]);now=time.time();gap=max(0,float(os.environ.get('RADIO_INTERVAL','2')))
        if not pending or now<max(pending[0]['due'],self.state.get('radio_last_spoken',0)+gap):return False
        row=pending.pop(0);self.state['logs'].insert(0,dict(id=row['id'],time=self.state['clock'],text=self.radio_text(row['text']),channel='Funk',**{key:row[key] for key in ('vehicle','job','owner') if key in row}))
        self.state['logs']=self.state['logs'][:250];self.state['radio_last_spoken']=now
        for i,row in enumerate(pending):row['due']=now+(i+1)*gap
        return True

    def queue_radio(self,text):
        self.flush_radio();now=time.time();gap=max(0,float(os.environ.get('RADIO_INTERVAL','2')))
        pending=self.state.setdefault('radio_pending',[])
        if gap==0 or not pending and now>=self.state.get('radio_last_spoken',0)+gap:
            self.state['logs'].insert(0,dict(id=uuid.uuid4().hex[:12],time=self.state['clock'],text=text,channel='Funk',**self.radio_metadata(text)));self.state['radio_last_spoken']=now
        else:
            due=max(now,self.state.get('radio_last_spoken',0),pending[-1]['due'] if pending else 0)+gap
            pending.append(dict(id=uuid.uuid4().hex[:12],text=text,due=due,**self.radio_metadata(text)))
