import os
import sys
import unittest

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.deduplication import compute_demande_fingerprint


class TestDeduplication(unittest.TestCase):
    def test_same_content_same_fingerprint(self):
        fp1 = compute_demande_fingerprint("Benali", "Ahmed", "Ma route est en mauvais état")
        fp2 = compute_demande_fingerprint("Benali", "Ahmed", "Ma route est en mauvais état")
        self.assertEqual(fp1, fp2)

    def test_case_insensitive(self):
        fp1 = compute_demande_fingerprint("BENALI", "AHMED", "Ma route est en mauvais état")
        fp2 = compute_demande_fingerprint("benali", "ahmed", "Ma route est en mauvais état")
        self.assertEqual(fp1, fp2)

    def test_different_message_different_fingerprint(self):
        fp1 = compute_demande_fingerprint("Benali", "Ahmed", "Ma route est en mauvais état")
        fp2 = compute_demande_fingerprint("Benali", "Ahmed", "Le bus ne passe plus")
        self.assertNotEqual(fp1, fp2)

    def test_different_nom_different_fingerprint(self):
        fp1 = compute_demande_fingerprint("Benali", "Ahmed", "Ma route est en mauvais état")
        fp2 = compute_demande_fingerprint("Mansouri", "Ahmed", "Ma route est en mauvais état")
        self.assertNotEqual(fp1, fp2)

    def test_extra_spaces_normalized(self):
        fp1 = compute_demande_fingerprint(" Benali ", " Ahmed ", "  Ma route est en mauvais état  ")
        fp2 = compute_demande_fingerprint("Benali", "Ahmed", "Ma route est en mauvais état")
        self.assertEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
