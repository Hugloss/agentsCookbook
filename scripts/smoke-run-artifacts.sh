#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-artifacts.XXXXXX")"
cleanup() { rm -rf "$temp_root"; }
trap cleanup EXIT

run_dir="$temp_root/full"
mkdir -p "$run_dir/reviews" "$run_dir/receipts"
node - "$run_dir" <<'NODE'
const crypto=require('crypto'),fs=require('fs'),path=require('path');
const root=process.argv[2];
const reviewers=['plan-improver-model2','plan-improver-model3','plan-validation-designer','plan-coverage-reviewer','plan-red-team-gate','plan-implementation-simulator','plan-fact-auditor','plan-contract-checker'];
for(const reviewer of reviewers){
  const body=`# ${reviewer}\n\nMaterial finding for ${reviewer}.\n`;
  fs.writeFileSync(path.join(root,'reviews',`${reviewer}.md`),body);
  const receipt={schema_version:1,runtime:'opencode',run_id:'smoke',reviewer,artifact_id:reviewer,artifact:`reviews/${reviewer}.md`,sha256:crypto.createHash('sha256').update(body).digest('hex'),chars:body.length,summary:`${reviewer}: material finding.`};
  fs.writeFileSync(path.join(root,'receipts',`${reviewer}.json`),`${JSON.stringify(receipt,null,2)}\n`);
}
NODE

node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$run_dir" >/dev/null
printf 'SMOKE name=run_artifacts_complete status=pass\n'

node - "$run_dir/receipts/plan-fact-auditor.json" <<'NODE'
const fs=require('fs');const file=process.argv[2];const value=JSON.parse(fs.readFileSync(file,'utf8'));value.sha256='0'.repeat(64);fs.writeFileSync(file,`${JSON.stringify(value,null,2)}\n`);
NODE
if node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$run_dir" >/dev/null 2>&1; then
  printf 'SMOKE name=run_artifacts_tampered_hash status=fail\n' >&2; exit 1
fi
printf 'SMOKE name=run_artifacts_tampered_hash status=pass\n'

one_dir="$temp_root/one"
mkdir -p "$one_dir/reviews" "$one_dir/receipts"
node - "$one_dir" <<'NODE'
const crypto=require('crypto'),fs=require('fs'),path=require('path');const root=process.argv[2],reviewer='plan-coverage-reviewer';const body='# Coverage Design Review\n\nOne gap.\n';fs.writeFileSync(path.join(root,'reviews',`${reviewer}.md`),body);fs.writeFileSync(path.join(root,'receipts',`${reviewer}.json`),`${JSON.stringify({schema_version:1,runtime:'pi',run_id:'one',reviewer,artifact_id:reviewer,artifact:`reviews/${reviewer}.md`,sha256:crypto.createHash('sha256').update(body).digest('hex'),chars:body.length,summary:'One realistic coverage gap.'},null,2)}\n`);
NODE
node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$one_dir" --reviewer plan-coverage-reviewer >/dev/null
printf 'SMOKE name=run_artifacts_one_reviewer status=pass\n'
if node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$one_dir" >/dev/null 2>&1; then
  printf 'SMOKE name=run_artifacts_missing_reviewers status=fail\n' >&2; exit 1
fi
printf 'SMOKE name=run_artifacts_missing_reviewers status=pass\n'

# Pi session evidence must prove skill-first behavior, artifact persistence, and
# finite reviewer child tool use.
pi_good="$temp_root/pi-artifact-good.jsonl"
pi_missing="$temp_root/pi-artifact-missing.jsonl"
pi_unsafe="$temp_root/pi-artifact-unsafe-tool.jsonl"
node - "$pi_good" "$pi_missing" "$pi_unsafe" <<'NODE'
const fs=require('fs');
const [goodPath,missingPath,unsafePath]=process.argv.slice(2);
const reviewers=[
 ['plan-improver-model2','plan-gap-scout'],
 ['plan-improver-model3','alternative-route-challenge'],
 ['plan-validation-designer','validation-gap-finder'],
 ['plan-coverage-reviewer','coverage-design-review'],
 ['plan-red-team-gate','red-team-leftover-gate'],
 ['plan-implementation-simulator','implementation-dry-run'],
 ['plan-fact-auditor','fact-grounding-auditor'],
 ['plan-contract-checker','plan-contract-guard'],
];
function make(mode){
 const entries=[{type:'session',version:3,id:'session-artifact',cwd:'/repo'},{type:'message',id:'user',parentId:null,message:{role:'user',content:[{type:'text',text:'plan'}]}}];
 let parent='user';
 reviewers.forEach(([agent,skill],index)=>{
   const call=`call-${index}`,aid=`assistant-${index}`,rid=`result-${index}`;
   entries.push({type:'message',id:aid,parentId:parent,message:{role:'assistant',content:[{type:'toolCall',id:call,name:'subagent',arguments:{agent,task:'review'}}]}});
   const tools=[{name:'read',args:{path:`/skills/${skill}/SKILL.md`},status:'done'}];
   if(mode==='unsafe'&&index===0)tools.push({name:'bash',args:{command:'echo forbidden'},status:'done'});
   if(!(mode==='missing'&&index===0))tools.push({name:'review_artifact',args:{artifact_id:agent,summary:'material finding',content:'# Review'},status:'done'});
   entries.push({type:'message',id:rid,parentId:aid,message:{role:'toolResult',toolCallId:call,toolName:'subagent',isError:false,content:[{type:'text',text:'receipt'}],details:{agent,status:'done',output:JSON.stringify({artifact_id:agent,summary:'material finding'}),tools}}});
   parent=rid;
 });
 return `${entries.map(JSON.stringify).join('\n')}\n`;
}
fs.writeFileSync(goodPath,make('good'));fs.writeFileSync(missingPath,make('missing'));fs.writeFileSync(unsafePath,make('unsafe'));
NODE
AGENTS_COOKBOOK_RUN_DIR="$run_dir" node "$repo_root/scripts/check-pi-session.js" --scope session "$pi_good" >/dev/null
printf 'SMOKE name=pi_session_artifact_evidence status=pass\n'
if AGENTS_COOKBOOK_RUN_DIR="$run_dir" node "$repo_root/scripts/check-pi-session.js" --scope session "$pi_missing" >/dev/null 2>&1; then
  printf 'SMOKE name=pi_session_missing_artifact_call status=fail\n' >&2; exit 1
fi
printf 'SMOKE name=pi_session_missing_artifact_call status=pass\n'
if AGENTS_COOKBOOK_RUN_DIR="$run_dir" node "$repo_root/scripts/check-pi-session.js" --scope session "$pi_unsafe" >/dev/null 2>&1; then
  printf 'SMOKE name=pi_session_unsafe_child_tool status=fail\n' >&2; exit 1
fi
printf 'SMOKE name=pi_session_unsafe_child_tool status=pass\n'

printf 'SUMMARY status=pass\n'
