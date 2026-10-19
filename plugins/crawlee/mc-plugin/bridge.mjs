/** Deployment config is instance-local; the shipped plugin contains no host identity or credentials. */
import {readFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
const config=JSON.parse(await readFile(process.env.CRAWLEE_CONFIG,'utf8'));
if(typeof config.ssh_host!=='string'||!/^([a-zA-Z0-9][a-zA-Z0-9._-]*)$/.test(config.ssh_host))throw Error('Configure a valid SSH host alias');
const child=spawn('ssh',['-T','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2',config.ssh_host,'docker exec -i tmf-crawlee-worker node /app/mcp.mjs'],{stdio:'inherit'});
child.on('error',()=>{process.stderr.write('Remote Crawlee transport unavailable\n');process.exitCode=1});child.on('exit',(code)=>{process.exitCode=code??1});
for(const sig of ['SIGTERM','SIGINT'])process.on(sig,()=>child.kill(sig));
