import test from 'node:test';
import assert from 'node:assert/strict';
import {DOCUMENT_ACCEPT,extractSource} from '../extract.mjs';
test('Markdown is preserved without HTML parsing or link discovery',()=>{
 const body='# Webhooks\n\nUse `<signature>` and [SDK](https://example.com/sdk).\n```js\nif(a < b) {}\n```';
 const r=extractSource(Buffer.from(body),()=>{throw Error('Must not parse Markdown as HTML')},'text/markdown; charset=utf-8');
 assert.equal(r.text,body);assert.equal(r.title,'Webhooks');assert.equal(r.enqueueHTMLLinks,false);
 assert.ok(DOCUMENT_ACCEPT.startsWith('text/markdown,'));
});
test('Plain text remains inert and has no invented title',()=>{
 const r=extractSource(Buffer.from('Use <invoice> & keep tags.'),null,'text/plain');
 assert.equal(r.text,'Use <invoice> & keep tags.');assert.equal(r.title,'');
});
test('Unsupported MIME fails instead of treating arbitrary bytes as evidence',()=>{
 assert.throws(()=>extractSource(Buffer.from('binary'),null,'application/pdf'),/Unsupported/);
});
