'use strict';
// Derive attention from open conversations; closing one clears its marker on all clients.
window.RadioUI={
 attention(state,job){return (state.radio_calls||[]).filter(c=>c.job===job.id&&c.state!=='closed')},
 owner(state,row){const job=state.jobs.find(j=>j.id===row.job);return job?.owner||row.owner||null},
 ownerLabel(state,row){const id=this.owner(state,row);return id?(state.session.players.find(p=>p.id===id)?.name||'Abgemeldeter Disponent'):'Noch nicht zugeordnet'}
};
