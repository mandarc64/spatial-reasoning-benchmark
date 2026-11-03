"""Meaningful scoring checks: order, duplicates, invalid schema, and prompt leakage."""
import unittest
from evaluate import correct,prompt

class EvaluationTests(unittest.TestCase):
    def test_sets_ignore_order_but_reject_duplicates(self):
        self.assertTrue(correct(['B','A'],['A','B'],'set'))
        self.assertFalse(correct(['A','A'],['A'],'set'))
    def test_ranked_lists_require_order(self):
        self.assertFalse(correct(['B','A'],['A','B'],'ordered'))
    def test_bool_is_not_integer_or_string(self):
        self.assertTrue(correct(True,True,'boolean'))
        self.assertFalse(correct(1,True,'boolean'))
        self.assertFalse(correct('true',True,'boolean'))
    def test_answer_key_never_enters_prompt(self):
        q={'question':'Question','context':{'point':[1,2]},'sql':'SECRET_SQL','fixture_expected':'SECRET_ANSWER'}
        self.assertNotIn('SECRET',prompt(q))

if __name__=='__main__': unittest.main()
