from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from budget_app.cli import main
from budget_app.errors import AppError
from budget_app.services import BudgetService


class BudgetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.service = BudgetService(self.data_dir)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_sample(self) -> None:
        self.service.add_transaction(
            date="2026-08-01", type="income", category="salary", amount=3_000_000, memo="월급"
        )
        self.service.add_transaction(
            date="2026-08-02", type="expense", category="food", amount=20_000, memo="점심", tags="meal"
        )
        self.service.add_transaction(
            date="2026-08-03", type="expense", category="transport", amount=10_000, memo="버스"
        )

    def test_three_persistent_files_and_default_categories(self) -> None:
        self.assertTrue((self.data_dir / "transactions.jsonl").exists())
        self.assertTrue((self.data_dir / "categories.jsonl").exists())
        self.assertTrue((self.data_dir / "budgets.jsonl").exists())
        self.assertIn("food", self.service.list_categories())

    def test_add_list_search_and_persistence(self) -> None:
        self.add_sample()
        latest = list(self.service.list_transactions(limit=2))
        self.assertEqual([item.date for item in latest], ["2026-08-03", "2026-08-02"])

        search = list(self.service.search_transactions(category="food", tag="meal"))
        self.assertEqual(len(search), 1)
        self.assertEqual(search[0].memo, "점심")

        reopened = BudgetService(self.data_dir)
        self.assertEqual(len(list(reopened.transactions.iter_all())), 3)

    def test_summary_budget_usage_and_over_budget(self) -> None:
        self.add_sample()
        self.service.set_budget("2026-08", 25_000)
        result = self.service.summary("2026-08", top=2)
        self.assertEqual(result["income"], 3_000_000)
        self.assertEqual(result["expense"], 30_000)
        self.assertEqual(result["balance"], 2_970_000)
        self.assertTrue(result["over_budget"])
        self.assertAlmostEqual(result["budget_usage"], 120.0)

    def test_update_and_delete_use_stable_ids(self) -> None:
        self.add_sample()
        target = self.service.transactions.find("TX-000002")
        self.assertIsNotNone(target)

        updated = self.service.update_transaction("TX-000002", amount=25_000, memo="저녁")
        self.assertEqual(updated.amount, 25_000)
        self.assertEqual(updated.memo, "저녁")

        self.service.delete_transaction("TX-000003")
        self.assertIsNone(self.service.transactions.find("TX-000003"))
        self.assertIsNotNone(self.service.transactions.find("TX-000002"))

    def test_remove_category_is_blocked_when_in_use(self) -> None:
        self.service.add_transaction(
            date="2026-08-01", type="expense", category="food", amount=1_000
        )
        with self.assertRaises(AppError):
            self.service.remove_category("food")

    def test_export_and_import_fixed_csv_schema(self) -> None:
        self.add_sample()
        output = Path(self.temp.name) / "export.csv"
        count = self.service.export_csv(output, month="2026-08")
        self.assertEqual(count, 3)

        with output.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, ["date", "type", "category", "amount", "memo", "tags"])

        second_data_dir = Path(self.temp.name) / "imported-data"
        second = BudgetService(second_data_dir)
        result = second.import_csv(output)
        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(len(list(second.transactions.iter_all())), 3)

    def test_import_skips_broken_rows_and_reports_reason(self) -> None:
        source = Path(self.temp.name) / "broken.csv"
        source.write_text(
            "date,type,category,amount,memo,tags\n"
            "2026-08-01,expense,food,1000,ok,meal\n"
            "2026-99-99,expense,food,1000,bad,meal\n",
            encoding="utf-8",
        )
        result = self.service.import_csv(source)
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped, 1)
        self.assertTrue(result.errors)

    def test_cli_expected_error_has_nonzero_exit_without_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["--data-dir", str(self.data_dir), "delete", "--id", "TX-999999"])
        self.assertNotEqual(exit_code, 0)
        self.assertIn("[오류]", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
