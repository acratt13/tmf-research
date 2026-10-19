const $=id=>document.getElementById(id);let settings,runId,polling,reviewed;
const names={understand:'Understand',compare:'Compare',build:'Build',audit:'Audit',offer:'Offer a service',md:'Markdown',html:'Web report',pdf:'PDF',docx:'Word document',xlsx:'Workbook',pptx:'Slides',diagram:'Diagram',builder:'Builder package'};
async function api(path,body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-TMF-Token':settings.token},body:JSON.stringify(body)}:{});const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data}
function choices(target,values,defaults){for(const value of values){const label=document.createElement('label');label.className='choice';const input=document.createElement('input');input.type='checkbox';input.value=value;input.checked=defaults.includes(value);label.append(input,document.createTextNode(names[value]||value));$(target).append(label)}}
function selected(id){return [...$(id).querySelectorAll('input:checked')].map(i=>i.value)}
function input(){return {question:$('question').value,context:$('context').value,lenses:selected('lenses'),formats:selected('formats'),depth:$('depth').value,council:$('council').checked,urls:$('urls').value.split('\n').map(x=>x.trim()).filter(Boolean),inspections:selected('inspections')}}
function fail(error){$('error').textContent=error.message}
function invalidate(){reviewed=null;$('brief-panel').hidden=true}
async function history(){try{const runs=await api('/api/runs');$('history').replaceChildren();if(!runs.length)$('history').textContent='No saved investigations yet.';for(const run of runs){const b=document.createElement('button');b.textContent=`${run.status} · ${run.question}`;b.onclick=()=>{runId=run.id;localStorage.setItem('tmf-last-run',runId);$('setup').open=false;watch()};$('history').append(b)}}catch(e){$('history').textContent='Saved runs could not be read.'}}
async function watch(){clearTimeout(polling);if(!runId)return;const watching=runId;try{const state=await api('/api/runs/'+watching);if(watching!==runId)return;$('research').hidden=false;$('workspace').classList.add('has-run');document.body.classList.add('has-research');$('status').textContent=state.status;$('run-question').textContent=(state.question||'')+(state.lenses?' · '+state.lenses.map(x=>names[x]).join(' + '):'');$('stage').textContent=state.stage;$('events').replaceChildren();for(const event of state.events.slice(-10)){const li=document.createElement('li'),time=document.createElement('time');time.textContent=new Date(event.at).toLocaleTimeString();li.append(time,document.createTextNode(event.text));$('events').append(li)}$('counts').textContent=state.findings===undefined?'':`${state.findings} reviewed findings · ${state.requirements} proposed requirements${state.withheld_claims?' · '+state.withheld_claims+' claims held back':''}`;$('outputs').replaceChildren();for(const file of state.outputs){const a=document.createElement('a');a.href='/outputs/'+runId+'/'+encodeURIComponent(file);a.textContent=file;a.download=file;$('outputs').append(a)}$('run-errors').textContent=[...new Set(state.errors)].join(' · ');const active=['queued','running','reviewing','cancelling'].includes(state.status);$('timeline').open=active;$('cancel').hidden=!active;$('reexport').hidden=active||!state.outputs.length;$('cancel').disabled=state.status==='cancelling';if(active){$('result').replaceChildren();polling=setTimeout(watch,2000);}else {history();await showResult(watching)}}catch(e){if(watching!==runId)return;$('status').textContent='unavailable';$('counts').textContent='';$('result').replaceChildren();$('outputs').replaceChildren();$('cancel').disabled=true;$('stage').textContent='Connection lost; run state is unavailable. Reconnect to read its saved status.';polling=setTimeout(watch,5000)}}
$('preview').onclick=async()=>{try{$('error').textContent='';const data=await api('/api/brief',input());reviewed=JSON.stringify(input());$('brief').textContent=`QUESTION\n${data.question}\n\nLENSES\n${data.lenses.map(x=>names[x]).join(' + ')}\n\nDEPTH / OUTPUTS\n${data.depth} · ${data.formats.map(x=>names[x]).join(', ')}\n\nCONTEXT\n${data.context||'None supplied; consequential gaps will remain explicit.'}\n\nTEAM\nLead → source scout → specialists + selected REA → evidence review${data.council?' → Council challenge':''} → follow-up → synthesis → exports\n\n${data.privacy}`;$('brief-panel').hidden=false}catch(e){fail(e)}};
$('start').onclick=async()=>{if(reviewed!==JSON.stringify(input()))return invalidate();$('start').disabled=true;try{const data=await api('/api/runs',input());runId=data.id;$('setup').open=false;localStorage.setItem('tmf-last-run',runId);watch();history()}catch(e){fail(e)}finally{$('start').disabled=false}};
$('cancel').onclick=async()=>{try{await api('/api/cancel',{id:runId});watch()}catch(e){fail(e)}};
$('preset').onclick=()=>{const preset=settings.presets['tmf-service-blueprint'];for(const id of ['lenses','formats'])for(const box of $(id).querySelectorAll('input'))box.checked=preset[id].includes(box.value);$('depth').value=preset.depth;$('council').checked=true;invalidate()};
(async()=>{try{settings=await api('/api/config');choices('lenses',Object.keys(settings.lenses),['understand','build']);choices('formats',settings.formats,['md','html','builder']);choices('export-formats',settings.formats,['md','html','builder']);choices('inspections',settings.inspections.map(x=>x.id),[]);if(!settings.inspections.length)$('inspections').textContent='No software targets configured. Research can run without REA.';for(const id of ['question','context','urls','depth','council','lenses','formats','inspections'])$(id).addEventListener('input',invalidate);await history();runId=localStorage.getItem('tmf-last-run');if(runId){$('setup').open=false;watch()}}catch(e){fail(e)}})();

function element(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node}
function sourceLink(source){
 let label=source.id+' · '+source.title;
 let url;try{url=new URL(source.url)}catch{return element('span',label)}
 if(source.title===source.url)label=source.id+' · '+url.hostname;
 if(!['https:','http:'].includes(url.protocol))return element('span',label);
 const a=element('a',label);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';return a;
}
async function showResult(id){
 $('result').replaceChildren();
 try{
  const result=await api('/api/result/'+id);if(id!==runId)return;
  const report=result.report,article=element('article',undefined,'research-report');
  article.append(element('div','RESEARCH BRIEF','eyebrow'),element('h1',report.title),element('p','The conclusion','section-label'),element('p',report.summary,'conclusion'));
  const nav=element('nav',undefined,'report-nav');nav.setAttribute('aria-label','Research sections');
  for(const [anchor,label] of [['analysis','Analysis'],['coverage','Question coverage'],['findings','Findings'],['requirements','Build plan'],['unknowns','Open questions'],['evidence','Evidence']]){const a=element('a',label);a.href='#research-'+anchor;nav.append(a)}article.append(nav);
  function section(anchor,title,note){const section=element('section',undefined,'report-section');section.id='research-'+anchor;section.append(element('h2',title));if(note)section.append(element('p',note,'section-note'));article.append(section);return section}
  function citations(ids){const row=element('div',undefined,'citations');for(const id of ids||[]){const a=element('a',id);a.href='#source-'+id;a.setAttribute('aria-label','Read evidence '+id);row.append(a)}return row}
  const analysis=section('analysis','Analysis and proposed approach','Accepted analysis from the same revision used for exports. Recommendations remain proposals.');
  for(const item of result.analysis?.sections||[])analysis.append(element('h3',item.heading),element('p',item.text));
  if(!result.analysis?.sections?.length)analysis.append(element('p','No accepted analysis sections are available for this revision.'));
  const decision=result.analysis?.council_synthesis;
  if(decision?.strongest_dissent)analysis.append(element('h3','Strongest dissent'),element('p',decision.strongest_dissent));
  const coverage=section('coverage','How well the question was answered','Model-assessed coverage against the original goals; not factual certification.');
  for(const item of result.analysis?.coverage?.criteria||[]){const row=element('div',undefined,'coverage-item');row.append(element('span',item.status,'evidence-label'),element('h3',item.question),element('p',item.reason));coverage.append(row)}
  if(!result.analysis?.coverage?.criteria?.length)coverage.append(element('p','This older investigation has no explicit question-coverage assessment.'));
  const findings=section('findings','What the research found',report.findings.length+' accepted findings. Labels distinguish documented facts, observations, inferences and proposals.');
  for(const [index,finding] of report.findings.entries()){
   const card=element('div',undefined,'finding');card.append(element('span',String(index+1).padStart(2,'0'),'finding-number'));
   const content=element('div');content.append(element('span',finding.label,'evidence-label'),element('p',finding.text));if(finding.caveat)content.append(element('p',finding.caveat,'caveat'));content.append(citations(finding.sources));card.append(content);findings.append(card);
  }
  const requirements=section('requirements','The proposed build plan',report.requirements.length+' requirements to scope and verify. These are proposals, not delivered capabilities.');
  for(const requirement of report.requirements){const card=element('details',undefined,'requirement'),title=element('summary',requirement.id+' · '+requirement.text);card.append(title,element('p','Acceptance condition','section-label'),element('p',requirement.acceptance),citations(requirement.basis));requirements.append(card)}
  if(!report.requirements.length)requirements.append(element('p','No build requirements were published.'));
  const unknowns=section('unknowns','What we still need to learn','Latest entries in the saved uncertainty ledger. Earlier planning limits and role objections remain available below.');
  const latest=report.unknowns.slice(-12),earlier=report.unknowns.slice(0,-12);
  const list=element('ul');for(const unknown of latest)list.append(element('li',unknown));unknowns.append(list);
  if(earlier.length){const detail=element('details');detail.append(element('summary','Earlier uncertainty entries ('+earlier.length+')'));const previous=element('ul');for(const unknown of earlier)previous.append(element('li',unknown));detail.append(previous);unknowns.append(detail)}
  const evidence=section('evidence','Evidence register','Source availability describes the saved research snapshot, not a fresh live check.');
  for(const source of report.sources){const card=element('div',undefined,'source');card.id='source-'+source.id;card.append(sourceLink(source),element('span',source.state,'evidence-label'),element('p',source.scope),element('p',source.limitations,'caveat'));if(source.retrieved_at)card.append(element('small','Retrieved '+new Date(source.retrieved_at).toLocaleString()));evidence.append(card)}
  if(result.council){const details=element('details',undefined,'council');details.append(element('summary','How the Council challenged this research'),element('p','Simulated perspectives from the same provider. These opinions do not establish factual support.','section-note'));for(const member of result.council.positions){details.append(element('h3',member.role),element('p',member.position||member.status),element('p','Risk: '+(member.underweighted_risk||member.reason||'Unavailable'),'caveat'))}article.append(details)}
  $('result').replaceChildren(article);
 }catch(e){if(id===runId)$('result').textContent='The saved report could not be read. Select this investigation from Recent research to retry.'}
}
$('new-research').onclick=()=>{$('setup').open=true;$('setup').scrollIntoView({behavior:'smooth',block:'start'});$('question').focus({preventScroll:true})};

$('reexport').onclick=async()=>{try{await api('/api/export',{id:runId,formats:selected('export-formats')});watch()}catch(e){fail(e)}};
