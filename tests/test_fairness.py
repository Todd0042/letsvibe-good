import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fairness import Chore, Person, balances, plan, record  # noqa: E402

DAY = date(2026, 3, 1)
DISHES, BATHROOM = Chore("d", "Dishes", 1), Chore("b", "Bathroom", 3)


def people(*names, away=None):
    return [Person(n.lower(), n, away_until=(away or {}).get(n)) for n in names]


class FairnessTest(unittest.TestCase):
    def test_doer_earns_and_house_shares_the_cost(self):
        house = people("Alex", "Sam")
        done = [record(house, BATHROOM, "alex", DAY)]
        self.assertEqual(balances(house, done), {"alex": 1.5, "sam": -1.5})
        self.assertEqual(plan(house, [DISHES], done, DAY)["d"], "sam")

    def test_time_away_pauses_your_share(self):
        house = people("Alex", "Sam", "Kim", away={"Kim": "2026-03-10"})
        done = [record(house, BATHROOM, "alex", DAY)]
        self.assertEqual(done[0].home, ["alex", "sam"])
        self.assertEqual(balances(house, done)["kim"], 0.0)
        self.assertNotIn("kim", plan(house, [DISHES, BATHROOM], done, DAY).values())

    def test_everyone_away_means_no_suggestion(self):
        house = people("Alex", "Sam", away={"Alex": "2026-03-02", "Sam": "2026-03-02"})
        self.assertEqual(plan(house, [DISHES], [], DAY), {"d": None})

    def test_suggestions_are_spread_out(self):
        house = people("Alex", "Sam")
        suggested = plan(house, [DISHES, Chore("t", "Trash", 1)], [], DAY)
        self.assertEqual(sorted(suggested.values()), ["alex", "sam"])

    def test_tie_goes_to_whoever_did_that_chore_least_recently(self):
        house = people("Alex", "Sam")
        done = [record(house, DISHES, "alex", DAY), record(house, DISHES, "sam", DAY)]
        self.assertEqual(plan(house, [DISHES], done, DAY)["d"], "alex")

    def test_removing_someone_keeps_balances_summing_to_zero(self):
        house = people("Alex", "Sam", "Kim")
        done = [record(house, BATHROOM, "kim", DAY), record(house, DISHES, "alex", DAY)]
        remaining = balances(house[:2], done)
        self.assertAlmostEqual(sum(remaining.values()), 0.0, places=2)
        self.assertGreater(remaining["alex"], remaining["sam"])

    def test_history_keeps_effort_after_a_chore_is_edited(self):
        house = people("Alex", "Sam")
        done = [record(house, BATHROOM, "alex", DAY)]
        self.assertEqual(done[0].effort, 3)
        self.assertEqual(balances(house, done)["alex"], 1.5)


if __name__ == "__main__":
    unittest.main()
