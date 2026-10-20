/** Prefer compact document representations; preserve Markdown as evidence text. */
export const DOCUMENT_ACCEPT='text/markdown,text/html;q=0.9,text/plain;q=0.8,application/xhtml+xml;q=0.7';
export function extractSource(body,$,contentType=''){
 const mime=String(contentType).split(';')[0].trim().toLowerCase();
 if(mime==='text/markdown'||mime==='text/plain'){
  const text=(Buffer.isBuffer(body)?body.toString('utf8'):String(body)).trim();
  const title=mime==='text/markdown'?(text.match(/^#\s+(.+)$/m)?.[1]??''):'';
  return {text,title,enqueueHTMLLinks:false,extraction:'Crawlee retained '+mime+' text; no HTML interpretation or browser rendering'};
 }
 if(mime!=='text/html'&&mime!=='application/xhtml+xml')throw Error('Unsupported document content type');
 const title=$('title').text().trim();$('script,style,noscript,nav,footer,header').remove();
 const chosen=$('main').length?$('main'):$('article').length?$('article'):$('body');
 return {title,text:chosen.text().replace(/[ \t]+/g,' ').replace(/\n\s*\n/g,'\n\n').trim(),
  enqueueHTMLLinks:true,extraction:'Crawlee Cheerio HTML text; retained body may be decoded/decompressed, not raw wire bytes'};
}
