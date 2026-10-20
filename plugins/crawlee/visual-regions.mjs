// Runs in the source page. Regions remain observations linked to the parent screen.
export function extractRegions(rootSelector) {
 const root=document.querySelector(rootSelector);
 if(!root)throw Error('Missing screen root');
 function path(el){
  if(el.id)return '#'+CSS.escape(el.id);
  const segments=[];
  while(el&&el!==document.body){
   const tag=el.tagName.toLowerCase(),siblings=[...(el.parentElement?.children||[])].filter(x=>x.tagName===el.tagName);
   segments.unshift(tag+':nth-of-type('+(siblings.indexOf(el)+1)+')');el=el.parentElement;
  }
  return 'body > '+segments.join(' > ');
 }
 const groups=[
  ['Navigation','navigation','header,nav,aside,[role="navigation"],[role="toolbar"]'],
  ['Section','section','main section,main article,section,article'],
  ['Card','card','[class*="card" i],[data-slot="card"],[role="dialog"]'],
  ['Form','form','form,fieldset,[data-slot="field-set"]'],
  ['Data display','data','table,[role="grid"],[data-chart]'],
  ['Control','control','button,[role="button"],input,select,[role="tablist"]'],
 ];
 const regions=[],seen=new Set(),boxes=[];
 for(const [fallback,kind,selector]of groups){
  let perKind=0;
  for(const el of root.querySelectorAll(selector)){
   if(perKind>=2||regions.length>=12)break;
   const b=el.getBoundingClientRect(),s=getComputedStyle(el);
   if(b.width<35||b.height<20||b.width>1600||b.height>1600||s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0)continue;
   if(kind==='section'&&(b.width<240||b.height<150))continue;
   const selector=path(el),box=[Math.round(b.x+scrollX),Math.round(b.y+scrollY),Math.round(b.width),Math.round(b.height)].join(',');
   if(seen.has(selector)||boxes.includes(box))continue;
   seen.add(selector);boxes.push(box);perKind++;
   const label=(el.getAttribute('aria-label')||el.querySelector('h1,h2,h3,[data-slot="card-title"]')?.textContent||(kind==='control'?el.textContent:el.querySelector('label,p,button')?.textContent)||fallback).trim().replace(/\s+/g,' ').slice(0,100);
   const styles={};for(const k of ['backgroundColor','color','borderRadius','boxShadow','fontFamily','fontSize','fontWeight','padding','gap','display','gridTemplateColumns'])styles[k]=s[k];
   const anatomy=[...el.querySelectorAll('h1,h2,h3,p,a,button,input,svg,img')].slice(0,12).map(x=>({tag:x.tagName.toLowerCase(),role:x.getAttribute('role'),text:(x.getAttribute('aria-label')||x.getAttribute('alt')||x.textContent||'').trim().replace(/\s+/g,' ').slice(0,100)}));
   regions.push({id:'R'+String(regions.length+1).padStart(3,'0'),kind,label,source_selector:selector,bounds:{x:Math.round(b.x+scrollX),y:Math.round(b.y+scrollY),width:Math.round(b.width),height:Math.round(b.height)},styles,anatomy,evidence_basis:'DOM/computed styles; semantic grouping inferred from element roles and headings'});
  }
 }
 return regions;
}
