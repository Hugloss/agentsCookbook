from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

from .probe_contract import validate_probe_contract
from .quality_debt import QualityDebtError, baseline_document, quality_debt_audit


def _fake_ruff(path: Path) -> None:
    path.write_text("""#!/usr/bin/env python3
import json, os, sys, time
if '--version' in sys.argv:
    print('ruff 9.9.9'); raise SystemExit(0)
mode=os.environ.get('AE_RUFF_MODE','base')
if mode == 'timeout': time.sleep(2)
if mode == 'badjson': print('{'); raise SystemExit(1)
root=os.getcwd()
limit=6 if mode == 'limit6' else 5\nvalue=9 if mode != 'reduced' else 7
rows=[{'code':'C901','filename':os.path.join(root,'src','a.py'),'location':{'row':1},'message':f'complexity ({value} > {limit})'}]
if mode == 'new':
    rows.append({'code':'C901','filename':os.path.join(root,'src','b.py'),'location':{'row':1},'message':f'complexity (8 > {limit})'})
print(json.dumps(rows)); raise SystemExit(1)
""", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp).resolve()
        (root/"src").mkdir()
        (root/"src/a.py").write_text("def a():\n    pass\n", encoding="utf-8")
        (root/"src/b.py").write_text("def b():\n    pass\n", encoding="utf-8")
        fake=root/"ruff"; _fake_ruff(fake)
        old_path=os.environ["PATH"]; os.environ["PATH"]=str(root)+os.pathsep+old_path
        try:
            base=quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5})
            assert validate_probe_contract(base)==[]
            assert base["derived"]["summary"]["excess"]==4
            baseline=root/"baseline.json"
            baseline.write_text(json.dumps(baseline_document(base)), encoding="utf-8")
            same=quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5}, baseline_path=baseline)
            assert same["derived"]["baseline_comparison"]["state"]=="UNCHANGED"
            os.environ["AE_RUFF_MODE"]="new"
            grown=quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5}, baseline_path=baseline)
            assert grown["derived"]["baseline_comparison"]["state"]=="INCREASED"
            assert grown["derived"]["baseline_comparison"]["files"]["src/b.py"]["state"]=="NEW"
            os.environ["AE_RUFF_MODE"]="reduced"
            reduced=quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5}, baseline_path=baseline)
            assert reduced["derived"]["baseline_comparison"]["state"]=="REDUCED"
            os.environ["AE_RUFF_MODE"]="limit6"\n            changed_limit=quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":6}, baseline_path=baseline)
            assert changed_limit["derived"]["baseline_comparison"]["state"]=="INCOMPARABLE_BASELINE"
            os.environ["AE_RUFF_MODE"]="badjson"
            try: quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5})
            except QualityDebtError: pass
            else: raise AssertionError("bad analyzer JSON must fail closed")
            os.environ["AE_RUFF_MODE"]="timeout"
            try: quality_debt_audit(repository_root=root, roots=("src",), limits={"C901":5}, timeout_seconds=.05)
            except QualityDebtError: pass
            else: raise AssertionError("analyzer timeout must fail closed")
        finally:
            os.environ.pop("AE_RUFF_MODE", None); os.environ["PATH"]=old_path
    print(json.dumps({"status":"PASS","cases":7,"tool":"quality-debt"},sort_keys=True))


if __name__=="__main__":
    main()
