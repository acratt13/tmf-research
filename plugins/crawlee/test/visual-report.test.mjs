import test from 'node:test';
import assert from 'node:assert/strict';
import {validateManifest,galleryHTML,designMarkdown,studyKind,selectTargets} from '../visual-report.mjs';
const target={id:'reference-a',url:'https://example.com/demo',allowed_domains:['example.com'],selector:'main'};
test('screen quota excludes motion studies and never recrawls attempted targets',()=>{
 const manifest={target_count:61,screen_target_count:2,targets:[target,{...target,id:'b'},{...target,id:'c'}]};
 const records=[{id:'motion-a',source_uri:'motion://examples/react/drag',state:'captured'},{id:'reference-a',kind:'site',state:'captured'},{id:'b',state:'unavailable'}];
 assert.deepEqual(selectTargets(manifest,records,5).map(r=>r.id),['c']);
 assert.equal(selectTargets(manifest,[...records,{id:'another',kind:'app-screen',state:'captured'}],5).length,0);
});
test('visual manifests reject duplicate URLs, unsafe URL schemes and missing scope',()=>{
 assert.throws(()=>validateManifest({target_count:40,targets:[target,{...target,id:'reference-b'}]}),/duplicate target URL/);
 assert.throws(()=>validateManifest({target_count:40,targets:[{...target,url:'http://example.com'}]}),/Invalid/);
 assert.throws(()=>validateManifest({target_count:40,targets:[{...target,allowed_domains:[]}]}),/allowed_domains/);
 assert.equal(validateManifest({target_count:40,targets:[target]}).targets.length,1);
});
test('untrusted titles and source descriptions stay text in the staging gallery',()=>{
 const r={...target,state:'captured',title:'<script>alert(1)</script>',description:'" onmouseover="bad',review_status:'captured_unreviewed',measurements:{desktop:{components:[],palette:[]}},motion:{desktop:{animations:[]}}};
 const html=galleryHTML([r]);
 assert.ok(!html.includes('<script>alert(1)</script>'));
 assert.ok(html.includes('&lt;script&gt;'));
 assert.ok(html.includes('captured, awaiting review'));
});
test('motion is separate from default screens and exposes real source playback',()=>{
 const motion={...target,url:'https://examples.motion.dev/react/gestures',source_uri:'motion://examples/react/gestures',state:'captured',title:'Gestures',measurements:{desktop:{components:[],palette:[]}},motion:{desktop:{animations:[]}}};
 assert.equal(studyKind(motion),'motion');
 const html=galleryHTML([motion]);
 assert.ok(html.includes('data-view="motion"'));
 assert.ok(html.includes('data-demo="https://examples.motion.dev/react/gestures"'));
 assert.ok(html.includes('No matching screen studies yet'));
 assert.ok(html.includes('Reference categories'));
});
test('handoff states evidence limits and keeps source provenance attached',()=>{
 const md=designMarkdown({...target,title:'A',source_uri:'motion://examples/react/drag',review_status:'captured_unreviewed',measurements:{desktop:{components:[],palette:[]}},motion:{desktop:{animations:[]}}});
 assert.ok(md.includes('motion://examples/react/drag'));
 assert.ok(md.includes('not a recreation or verification'));
 assert.ok(md.includes('Do not guess'));
});
