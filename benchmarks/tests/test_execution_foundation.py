from __future__ import annotations
import subprocess, tempfile, unittest
from pathlib import Path
from benchmarks.adapters.oracles import CommandOracle
from benchmarks.harness.campaign import TrialSpec,pending
from benchmarks.harness.workspace import snapshot,diff_snapshots,materialize_git

class ExecutionFoundationTests(unittest.TestCase):
    def test_snapshot_detects_ignored_path_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/".ignored").mkdir(); before=snapshot(root)
            (root/".ignored"/"side-effect").write_text("x")
            self.assertEqual(diff_snapshots(before,snapshot(root))["added"],[".ignored/side-effect"])
    def test_oracle_requires_positive_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            oracle=CommandOracle("o","1",("sh","-c","exit 7"),("sh","-c","exit 0"))
            self.assertFalse(oracle.healthcheck(tmp).payload["healthy"])
    def test_materialization_binds_exact_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/"source"; source.mkdir()
            subprocess.run(("git","init"),cwd=source,check=True,capture_output=True)
            subprocess.run(("git","config","user.email","bench@example.invalid"),cwd=source,check=True)
            subprocess.run(("git","config","user.name","Bench"),cwd=source,check=True)
            (source/"a").write_text("a"); subprocess.run(("git","add","a"),cwd=source,check=True)
            subprocess.run(("git","commit","-m","a"),cwd=source,check=True,capture_output=True)
            sha=subprocess.run(("git","rev-parse","HEAD"),cwd=source,check=True,capture_output=True,text=True).stdout.strip()
            self.assertEqual(materialize_git(source=source,commit=sha,destination=root/"trial"),sha)
    def test_completed_receipt_is_not_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=TrialSpec({"id":"e"},{"id":"t"},{"id":"c"},0,1); root=Path(tmp); (root/s.id).mkdir()
            self.assertEqual(pending([s],root),[s]); (root/s.id/"result.json").write_text("{}")
            self.assertEqual(pending([s],root),[])
if __name__=="__main__": unittest.main()
