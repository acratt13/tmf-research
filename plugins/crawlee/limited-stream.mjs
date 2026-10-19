import {Transform} from 'node:stream';
// pipeline consumers see the same error; upstream is stopped before buffering more.
export function limitedStream(upstream, maximum) {
 let bytes=0;
 const limited=new Transform({transform(chunk,encoding,done){
  bytes+=chunk.length;
  done(bytes>maximum?Error('Page exceeds response byte limit'):null,bytes>maximum?undefined:chunk);
 }});
 upstream.on('error',error=>limited.destroy(error));
 limited.on('close',()=>{if(!upstream.destroyed)upstream.destroy()});
 return upstream.pipe(limited);
}
