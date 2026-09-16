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

# Hash tampering must fail closed.
node - "$run_dir/receipts/plan-fact-auditor.json" <<'NODE'
const fs=require('fs');const file=process.argv[2];const value=JSON.parse(fs.readFileSync(file,'utf8'));value.sha256='0'.repeat(64);fs.writeFileSync(file,`${JSON.stringify(value,null,2)}\n`);
NODE
if node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$run_dir" >/dev/null 2>&1; then
  printf 'SMOKE name=run_artifacts_tampered_hash status=fail\n' >&2
  exit 1
fi
printf 'SMOKE name=run_artifacts_tampered_hash status=pass\n'

# One-reviewer mode supports routed/standalone runs without weakening full-flow exactness.
one_dir="$temp_root/one"
mkdir -p "$one_dir/reviews" "$one_dir/receipts"
node - "$one_dir" <<'NODE'
const crypto=require('crypto'),fs=require('fs'),path=require('path');const root=process.argv[2],reviewer='plan-coverage-reviewer';const body='# Coverage Design Review\n\nOne gap.\n';fs.writeFileSync(path.join(root,'reviews',`${reviewer}.md`),body);fs.writeFileSync(path.join(root,'receipts',`${reviewer}.json`),`${JSON.stringify({schema_version:1,runtime:'pi',run_id:'one',reviewer,artifact_id:reviewer,artifact:`reviews/${reviewer}.md`,sha256:crypto.createHash('sha256').update(body).digest('hex'),chars:body.length,summary:'One realistic coverage gap.'},null,2)}\n`);
NODE
node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$one_dir" --reviewer plan-coverage-reviewer >/dev/null
printf 'SMOKE name=run_artifacts_one_reviewer status=pass\n'

# Full-flow mode must reject the same incomplete run.
if node "$repo_root/scripts/check-run-artifacts.js" --run-dir "$one_dir" >/dev/null 2>&1; then
  printf 'SMOKE name=run_artifacts_missing_reviewers status=fail\n' >&2
  exit 1
fi
printf 'SMOKE name=run_artifacts_missing_reviewers status=pass\n'

printf 'SUMMARY status=pass\n'
