import {lookup} from 'node:dns';
import {isIP} from 'node:net';
export const USER_AGENT='TMFCrawlee/0.1 (+https://github.com/acratt13/tmf-research)';
export function publicV4(ip){
 if(isIP(ip)!==4)return false;
 const [a,b,c]=ip.split('.').map(Number);
 return !(a===0||a===10||a===127||a>=224||(a===100&&b>=64&&b<=127)||(a===169&&b===254)||(a===172&&b>=16&&b<=31)||(a===192&&(b===168||b===0||b===2))||(a===198&&(b===18||b===19||(b===51&&c===100)))||(a===203&&b===0&&c===113));
}
export function checkedURL(value,domains){
 const u=new URL(value);
 if(u.protocol!=='https:'||u.username||u.password||(u.port&&u.port!=='443')||isIP(u.hostname)||u.hostname.endsWith('.')||!u.hostname.includes('.'))throw Error('Only public HTTPS domain URLs on port 443 are supported');
 if(!domains.includes(u.hostname))throw Error('URL outside explicit allowed domains');
 u.hash='';return u;
}
export function publicLookup(host,options,callback){
 lookup(host,{all:true,family:4,verbatim:true},(error,addresses)=>{
  if(error)return callback(error);
  if(!addresses.length||addresses.some(a=>!publicV4(a.address)))return callback(Error('DNS returned a non-public or unsupported address'));
  if(options?.all)callback(null,addresses);else callback(null,addresses[0].address,4);
 });
}
export function brief(input){
 const urls=input.urls;
 if(!Array.isArray(urls)||urls.length<1||urls.length>5)throw Error('Supply one to five starting URLs');
 const domains=input.allowed_domains??[...new Set(urls.map(s=>new URL(s).hostname))];
 if(!Array.isArray(domains)||!domains.length||domains.length>10||domains.some(x=>typeof x!=='string'||!/^([a-z0-9-]+\.)+[a-z]{2,}$/i.test(x)))throw Error('Invalid allowed_domains');
 const normalized=urls.map(x=>checkedURL(x,domains).href);
 function bound(key,fallback,max){const v=input[key]??fallback;if(!Number.isInteger(v)||v<1||v>max)throw Error('Invalid '+key);return v;}
 return {urls:[...new Set(normalized)],allowed_domains:domains,max_pages:bound('max_pages',5,20),max_depth:bound('max_depth',1,3),topic:String(input.topic??'Public web collection').slice(0,200),tags:Array.isArray(input.tags)?input.tags.slice(0,12).map(x=>String(x).slice(0,60)):[],limits:{page_bytes:1000000,job_seconds:120,concurrency:1,robots:'required; unavailable policy fails closed',redirects:'refused'}};
}
