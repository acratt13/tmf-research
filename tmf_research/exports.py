"""Presentation adapters for one accepted research revision; failures remain visible."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import subprocess
import textwrap
from .cli import dump, html_report, markdown, pdf_report, report_lines
from .processes import bounded_run


def designcraft_script(record, synthesis):
    """Editable vertical workflow; bounded text fails explicitly rather than clipping."""
    steps=synthesis.get('workflow_steps',[])
    if not 2 <= len(steps) <= 6:raise ValueError('Workflow needs two to six steps')
    commands=[]
    def add(command, **params):
        commands.append({'command':command,'params':params});return len(commands)-1
    add('file.new',intent='web',width=800,height=1060,pages=1,facingPages=False,margins=0,title='Proposed research workflow')
    for name,color in [('Ink','#142638'),('Muted','#486171'),('Teal','#087F82'),('Card','#EAF4F3')]:
        add('swatch.create',name=name,color=color)
    def text(rect,value,size,color):
        step=add('frame.create',rect=rect,content='text',text=value)
        add('text.select',story=f'${step}.story',anchor=0,focus=len(value.encode('utf-8')))
        add('type.char',attrs={'fontFamily':'Arial','size':size,'fill':color})
        add('type.para',attrs={'hyphenate':False})
    title=str(record['title'])
    if len(title)>220:raise ValueError('Diagram title exceeds template capacity')
    text([42,25,758,52],'TMF COUNCIL / PROPOSED WORKFLOW',12,'Teal')
    text([42,57,758,130],title,22,'Ink')
    for i,step in enumerate(steps):
        label=re.sub(r'^\s*\d+[.)]\s+','',str(step.get('label','')));detail=str(step.get('detail',''))
        if not label or len(label)>110 or len(detail)>420:raise ValueError('Workflow text exceeds template capacity')
        y=145+i*132
        box=add('frame.create',rect=[42,y,758,y+108],content='unassigned')
        add('object.fill',ids=[f'${box}.id'],swatch='Card')
        text([58,y+12,742,y+42],f'{i+1:02d}  '+label,16,'Ink')
        text([58,y+45,742,y+100],detail,12,'Muted')
        if i<len(steps)-1:
            line=add('path.create',anchors=[{'p':[400,y+110]},{'p':[400,y+130]}],closed=False)
            add('object.stroke',ids=[f'${line}.id'],swatch='Teal',weight=2,end='triangle')
    text([42,955,758,1025],'EVIDENCE BOUNDARY / Proposed analysis, not an observed runtime.\nRead the report and builder pack for sources, acceptance conditions and unresolved decisions.',12,'Muted')
    add('document.inspect');add('preflight.run')
    return commands


def export_run(directory, record, synthesis, formats, config, check_cancel=lambda:None):
    directory=Path(directory); out=directory/'outputs';out.mkdir(exist_ok=False)
    (directory/'published-analysis.json').write_text(dump(synthesis))
    outputs=[];errors=[]; receipts=[]
    lines=report_lines(record)
    # Synthesis sections are proposed analysis, separate from reviewed factual findings.
    insert=[]
    for section in synthesis.get('sections',[])[:12]:
        if isinstance(section,dict):
            insert.extend([('heading','Analysis / proposed design: '+str(section.get('heading',''))),('body',str(section.get('text','')))])
    council=synthesis.get('council_synthesis',{})
    if isinstance(council,dict) and any(council.values()):
        insert += [('heading','TMF Council — advisory synthesis')]
        insert += [('body',f'{key}: {value}') for key,value in council.items()]
        insert += [('body','Simulated perspectives from the same provider; confidence is not factual verification. Raw positions are retained in the builder pack and local run.')]
    lines += insert
    for table in synthesis.get('tables',[]):
        lines.append(('heading',table['title'] if re.match(r'^proposed\b',table['title'],re.I) else 'Proposed matrix / '+table['title']))
        for row in table['rows']:
            lines.append(('body',' · '.join(f'{column}: {cell}' for column,cell in zip(table['columns'],row))))
    if synthesis.get('coverage',{}).get('criteria'):
        lines.append(('heading','Question coverage — model assessment'))
        for item in synthesis['coverage']['criteria']:
            lines.append(('body',item['status'].upper()+': '+item['question']+' — '+item['reason']))
    md=markdown(lines)
    # Internal source for converters is retained in the run even if Markdown was not selected.
    source=directory/'presentation.md';source.write_text(md)
    def retain(name):
        path=out/name
        if not path.is_file() or path.stat().st_size==0: raise ValueError('Renderer produced no file')
        outputs.append(name);receipts.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'validation':'file exists; adapter-specific checks recorded separately'})
    command_number=0
    def run(cmd):
        nonlocal command_number
        command_number+=1
        p=bounded_run(cmd,timeout=120)
        (directory/f'export-{command_number:02}-stdout.txt').write_text(p.stdout)
        (directory/f'export-{command_number:02}-stderr.txt').write_text(p.stderr)
        if p.returncode: raise RuntimeError('Presentation engine returned nonzero exit')
        return p.stdout
    def command(name,params):return ['--cmd',name+'='+json.dumps(params)]
    craft=config.get('craft',{})
    for fmt in formats:
        check_cancel()
        try:
            if fmt=='md':(out/'report.md').write_text(md);retain('report.md')
            elif fmt=='html':(out/'report.html').write_text(html_report(lines));retain('report.html')
            elif fmt=='pdf':
                if craft.get('wordcraft'):
                    run([craft['wordcraft'],'convert',str(source),str(out/'report.pdf')])
                else:pdf_report(out/'report.pdf',lines)
                retain('report.pdf')
            elif fmt=='builder':
                bundle={'report':record,'analysis':synthesis,'kind':'Research blueprint; not implementation proof'}
                for key in ('plan','claims','council'):
                    path=directory/(key+'.json')
                    if path.exists():bundle[key]=json.loads(path.read_text())
                (out/'builder-pack.json').write_text(dump(bundle));retain('builder-pack.json')
            elif fmt=='docx':
                exe=craft['wordcraft'];run([exe,'convert',str(source),str(out/'report.docx')])
                saved=run([exe,'text',str(out/'report.docx')])
                if record['title'] not in saved or 'Unknowns and remaining work' not in saved:raise ValueError('Word saved-content check failed')
                retain('report.docx')
            elif fmt=='xlsx':
                exe=craft['gridcraft'];commands=[]
                rows=[['ID','Requirement (proposed)','Acceptance','Evidence basis','Status']]
                rows += [[r['id'],r['text'],r['acceptance'],', '.join(r.get('basis',[])),'Proposed; not implemented'] for r in record['requirements']]
                rows += [['','','','',''],['Evidence register','','','','']]
                rows += [[s['id'],s['title'],s.get('url',s.get('evidence_id','')),s['state'],s['limitations']] for s in record['sources']]
                rows += [['','','','',''],['Unknowns','','','','']]+[['',text,'','',''] for text in record['unknowns']]
                for table in synthesis.get('tables',[]):
                    title=table['title'] if re.match(r'^proposed\b',table['title'],re.I) else 'PROPOSED: '+table['title']
                    rows += [[],[title],table['columns'],*table['rows']]
                # Prevent research text from becoming spreadsheet formulas.
                for i,row in enumerate(rows,1):
                    for j,value in enumerate(row):
                        value=str(value)
                        if value.lstrip().startswith(('=','+','-','@')):value="'"+value
                        commands.append({'command':'cell.set','params':{'cell':f'{chr(65+j)}{i}','input':value}})
                commands += [{'command':'home.wrapText','params':{'range':f'A1:F{len(rows)}','on':True}},
                             {'command':'home.columnWidth','params':{'cols':'B:B,C:C,E:E,F:F','width':340}},
                             {'command':'view.freezeTopRow','params':{}}]
                script=directory/'grid-export.jsonl';script.write_text('\n'.join(json.dumps(x) for x in commands))
                run([exe,'run','--script',str(script),'--out',str(out/'requirements.xlsx'),'--quiet'])
                saved=run([exe,'cat',str(out/'requirements.xlsx'),'--range',f'A1:F{len(rows)}'])
                if 'Evidence register' not in saved or 'Unknowns' not in saved:raise ValueError('Workbook lost caveats/evidence')
                retain('requirements.xlsx')
            elif fmt=='pptx':
                exe=craft['deckcraft']
                slides=[('Research brief',record['question']),('Conclusion',record['summary'])]
                slides += [('Finding / '+f['label'],f['text']+'\nEvidence: '+', '.join(f['sources'])+'\n'+f.get('caveat','')) for f in record['findings'][:6]]
                slides += [('Unknowns and limits','\n'.join(record['unknowns'][:4]))]
                slides=[(title+(' · continued' if i else ''),chunk)
                        for title,body in slides for i,chunk in enumerate(textwrap.wrap(body,width=550,
                            replace_whitespace=False,drop_whitespace=True,break_long_words=True) or [''])]
                # Full source URLs and all caveats remain in speaker notes even in a short briefing.
                notes=md
                if len(notes)>100000:raise ValueError('Presentation notes exceed bounded export size')
                cmd=[exe,'run',*command('file.new',{'blank':True,'theme':'Nocturne'})]
                for title,body in slides:
                    cmd+=command('slide.new',{'layout':'blank'})+command('design.background',{'color':'#101A2C'})
                    for rect,text,size,color in [([55,40,850,90],title,30,'#FFFFFF'),([55,155,850,310],body,19,'#D7E3F0')]:
                        cmd+=command('insert.textBox',{'rect':rect,'text':text})+command('format.fontDialog',{'family':'Inter','size':size,'color':color})
                    cmd+=command('slide.notes',{'text':notes})
                run(cmd+['--save',str(out/'briefing.pptx')]);retain('briefing.pptx')
            elif fmt=='diagram' and craft.get('designcraft'):
                exe=craft['designcraft']
                script=out/'workflow-script.json'
                commands=designcraft_script(record,synthesis)
                script.write_text(dump(commands))
                version=run([exe,'--version']).strip()
                result=json.loads(run([exe,'script',str(script),'--save',str(out/'workflow.designcraft'),
                                       '--export',str(out/'workflow.pdf'),'--export',str(out/'workflow.png')]))
                (directory/'designcraft-delivery.json').write_text(dump({'renderer':version,'delivery':result}))
                inspection=result['results'][-2]
                preflight=result['results'][-1]
                # Persist diagnostics before withholding a failed presentation.
                stories=inspection.get('stories',[])
                expected=[c['params']['text'] for c in commands if c['command']=='frame.create' and 'text' in c['params']]
                if (len(stories)!=len(expected) or any(s.get('overset') is not False for s in stories)
                    or [s.get('length') for s in stories]!=[len(t.encode('utf-8')) for t in expected]
                    or preflight.get('issues')!=[] or preflight.get('errors')!=0 or preflight.get('warnings')!=0):
                    raise ValueError('DesignCraft preflight or saved-text check failed')
                for name in ('workflow-script.json','workflow.designcraft','workflow.pdf','workflow.png'):retain(name)
            elif fmt=='diagram':
                prefix=config['archify']
                if not isinstance(prefix,list) or not prefix or any(not isinstance(x,str) for x in prefix):raise ValueError('Invalid Archify command prefix')
                steps=synthesis.get('workflow_steps',[])[:6]
                if len(steps)<2:raise ValueError('Synthesis did not provide enough workflow steps')
                spec={'schema_version':2,'diagram_type':'workflow',
                      'meta':{'title':'Proposed workflow · '+record['title'][:70],'quality_profile':'showcase','animation':'none'},
                      'lanes':[{'id':'work','label':'Proposed workflow; verify before implementation'}],
                      'mainPath':[f'n{i}' for i in range(len(steps))],
                      'nodes':[{'id':f'n{i}','lane':'work','col':i,'type':'backend',
                                'label':textwrap.shorten(str(s.get('label','Step')),width=26,placeholder='…'),
                                'sublabel':textwrap.shorten(str(s.get('detail','')),width=30,placeholder='…'),'width':210} for i,s in enumerate(steps)],
                      'edges':[{'from':f'n{i}','to':f'n{i+1}'} for i in range(len(steps)-1)],
                      'cards':[{'dot':'cyan','title':'Evidence boundary','items':['Proposed analysis, not an observed runtime.','See the report and builder pack for evidence and unresolved decisions.']}]}
                specpath=out/'workflow.json';specpath.write_text(dump(spec))
                run(prefix+['validate','workflow',str(specpath),'--quality','showcase','--json'])
                delivery=run(prefix+['deliver','workflow',str(specpath),str(out/'workflow.html'),'--quality','showcase','--json'])
                (directory/'archify-delivery.json').write_text(delivery)
                retain('workflow.json');retain('workflow.html')
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError,RuntimeError) as exc:
            errors.append(f'Requested {fmt} export unavailable ({type(exc).__name__}); no successful export claimed')
    (out/'export-receipt.json').write_text(dump({'record_sha256':hashlib.sha256(dump(record).encode()).hexdigest(),
                                               'artifacts':receipts,'errors':errors,
                                               'limits':'Local adapter results; independent visual and format-interoperability review required.'}))
    outputs.append('export-receipt.json')
    return outputs,errors
