from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from benchmarks.harness.identity import digest, trial_id
from benchmarks.harness.model import TrialStatus
from benchmarks.harness.receipt import ReceiptExistsError, write_receipt

class FoundationTests(unittest.TestCase):
    def test_identity_mapping_order(self):
        self.assertEqual(digest({"b":2,"a":1}),digest({"a":1,"b":2}))
    def test_trial_identity_binds_condition(self):
        base=dict(experiment={"id":"e","version":1},task={"id":"t","version":1},trial=0,seed=7)
        self.assertNotEqual(trial_id(condition={"id":"bare"},**base),trial_id(condition={"id":"hashmarks"},**base))
    def test_receipt_create_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path,checksum=write_receipt(root,{"status":TrialStatus.PASS.value})
            self.assertEqual(json.loads(path.read_text())["status"],"PASS"); self.assertTrue(checksum)
            with self.assertRaises(ReceiptExistsError): write_receipt(root,{"status":TrialStatus.FAIL.value})
    def test_non_product_failure_states_exist(self):
        self.assertEqual(TrialStatus.INCOMPLETE.value,"INCOMPLETE")
        self.assertEqual(TrialStatus.INVALID.value,"INVALID")
        self.assertEqual(TrialStatus.CONTAMINATED.value,"CONTAMINATED")
if __name__=="__main__": unittest.main()
