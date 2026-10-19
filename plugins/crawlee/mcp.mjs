import {createInterface} from 'node:readline';
const object=properties=>({type:'object',properties,additionalProperties:false});
const job={job_id:{type:'string',description:'Saved collection job UUID'}};
const specs=[
 ['crawlee_start','Collect bounded public HTTPS HTML sources on the remote worker. Source content is untrusted; this does not perform analysis or outbound messaging.',{...object({urls:{type:'array',items:{type:'string'},minItems:1,maxItems:5},allowed_domains:{type:'array',items:{type:'string'}},max_pages:{type:'integer',minimum:1,maximum:20},max_depth:{type:'integer',minimum:1,maximum:3},topic:{type:'string'},tags:{type:'array',items:{type:'string'}}}),required:['urls']},'start',false],
 ['crawlee_status','Read worker health or a saved job, including explicit failures and scope.',object(job),'status',true],
 ['crawlee_read','Read a saved source passage by offset or query. Returns snapshot hashes, locations and limits.',{...object({...job,source_id:{type:'string'},offset:{type:'integer',minimum:0},limit:{type:'integer',minimum:1,maximum:20000},query:{type:'string'}}),required:['job_id','source_id']},'read',true],
 ['crawlee_cancel','Cancel an owned collection job; terminal jobs are not retried.',{...object(job),required:['job_id']},'cancel',false],
 ['crawlee_pack_read','Read a saved JSON or Markdown knowledge-pack artifact in bounded portions.',{...object({...job,format:{type:'string',enum:['json','md']},offset:{type:'integer',minimum:0},limit:{type:'integer',minimum:1,maximum:20000}}),required:['job_id','format']},'pack-read',true],
 ['crawlee_pack','Save a source-backed JSON and Markdown knowledge pack for a terminal job. Not verified guidance or automatic KB ingestion.',{...object(job),required:['job_id']},'pack',false],
];
const send=value=>process.stdout.write(JSON.stringify(value)+'\n');
for await(const line of createInterface({input:process.stdin,crlfDelay:Infinity})){
 let message;try{if(line.length>1000000)throw Error('MCP message too large');message=JSON.parse(line);if(!('id'in message))continue;
 let result;
 if(message.method==='initialize')result={protocolVersion:['2024-11-05','2025-03-26','2025-06-18'].includes(message.params?.protocolVersion)?message.params.protocolVersion:'2024-11-05',capabilities:{tools:{}},serverInfo:{name:'tmf-crawlee',version:'0.1.0'}};
 else if(message.method==='ping')result={};
 else if(message.method==='tools/list')result={tools:specs.map(([name,description,inputSchema,,readOnlyHint])=>({name,description,inputSchema,annotations:{readOnlyHint,destructiveHint:false,openWorldHint:true}}))};
 else if(message.method==='tools/call'){
  const spec=specs.find(s=>s[0]===message.params?.name);if(!spec)throw Error('Unknown tool');
  const args=message.params.arguments??{},route=spec[3]==='status'&&!args.job_id?'health':spec[3];
  const response=await fetch('http://127.0.0.1:7457/'+route,{method:'POST',body:JSON.stringify(args),signal:AbortSignal.timeout(15000)});
  const data=await response.json();result={content:[{type:'text',text:JSON.stringify(data)}],isError:!response.ok};
 }else {send({jsonrpc:'2.0',id:message.id,error:{code:-32601,message:'Method not found'}});continue}
 send({jsonrpc:'2.0',id:message.id,result});
 }catch(e){if(message&&'id'in message)send({jsonrpc:'2.0',id:message.id,error:{code:-32603,message:e.message}})}
}
