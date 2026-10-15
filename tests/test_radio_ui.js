const assert=require('assert');global.window={};require('../app/static/radio-ui.js');const ui=window.RadioUI;
const job={id:'j',owner:'dispo-a'},state={jobs:[job],radio_calls:[{job:'j',vehicle:'v',state:'calling',owner:'old'},{job:'other',state:'calling'},{job:'j',state:'closed'}],session:{mode:'multi',players:[{id:'dispo-a',name:'Julian'},{id:'dispo-b',name:'Anna'}]}};
assert.equal(ui.attention(state,job).length,1);assert.equal(ui.ownerLabel(state,state.radio_calls[0]),'Julian');
job.owner='dispo-b';assert.equal(ui.ownerLabel(state,state.radio_calls[0]),'Anna','Follow actual incident ownership after handover');
state.radio_calls[0].state='closed';assert.equal(ui.attention(state,job).length,0,'End clears actionable marker');
assert.equal(ui.ownerLabel(state,{}),'Noch nicht zugeordnet');
state.jobs=[];assert.equal(ui.ownerLabel(state,{owner:'dispo-a'}),'Julian','Historical attribution survives incident cleanup');
console.log('Radio attention and multiplayer ownership passed.');
