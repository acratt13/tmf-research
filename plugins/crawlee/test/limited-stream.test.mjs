import test from 'node:test';
import assert from 'node:assert/strict';
import {Readable} from 'node:stream';
import {limitedStream} from '../limited-stream.mjs';
test('retains bytes within cap',async()=>{
 const chunks=[];for await(const chunk of limitedStream(Readable.from([Buffer.from('abc')]),3))chunks.push(chunk);
 assert.equal(Buffer.concat(chunks).toString(),'abc');
});
test('oversized stream fails and stops upstream',async()=>{
 const source=Readable.from([Buffer.alloc(5),Buffer.alloc(5)]);
 await assert.rejects(async()=>{for await(const chunk of limitedStream(source,6)){}},/byte limit/);
 assert.equal(source.destroyed,true);
});
