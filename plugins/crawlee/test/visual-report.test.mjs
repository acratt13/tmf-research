import test from 'node:test';
import assert from 'node:assert/strict';
import {validateManifest,galleryHTML,designMarkdown} from '../visual-report.mjs';
const target={id:'reference-a',url:'https://example.com/demo',allowed_domains:['example.com'],selector:'main'};
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
 assert.ok(html.includes('captured_unreviewed'));
});
test('handoff states evidence limits and keeps source provenance attached',()=>{
 const md=designMarkdown({...target,title:'A',source_uri:'motion://examples/react/drag',review_status:'captured_unreviewed',measurements:{desktop:{components:[],palette:[]}},motion:{desktop:{animations:[]}}});
 assert.ok(md.includes('motion://examples/react/drag'));
 assert.ok(md.includes('not a recreation or verification'));
 assert.ok(md.includes('Do not guess'));
});
