from __future__ import annotations

import csv
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from budget_app.cli import build_parser
from budget_app.models import Transaction
from budget_app.services import BudgetService, CSV_FIELDS


class BudgetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.service = BudgetService(self.data_dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_initializes_three_persistent_files_and_defaults(self) -> None:
        self.assertTrue((self.data_dir / "transactions.jsonl").exists())
        self.assertTrue((self.data_dir / "categories.jsonl").exists())
        self.assertTrue((self.data_dir / "budgets.jsonl").exists())
        self.assertIn("food", self.service.categories.list())

    def test_add_list_newest_first_and_generator(self) -> None:
        self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1000)
        self.service.add_transaction(date="2026-08-03", type_="income", category="salary", amount=5000)
        iterator = self.service.transactions.iter_transactions()
        self.assertTrue(hasattr(iterator, "__next__"))
        rows = list(self.service.list_transactions(10))
        self.assertEqual([tx.date for tx in rows], ["2026-08-03", "2026-08-01"])

    def test_search_filters_and_streams(self) -> None:
        self.service.add_transaction(date="2026-08-02", type_="expense", category="food", amount=1200, memo="lunch", tags="meal,work")
        self.service.add_transaction(date="2026-08-01", type_="expense", category="transport", amount=800, memo="bus", tags="commute")
        rows = list(self.service.search_transactions(category="food", query="LUNCH", tag="meal"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].category, "food")

    def test_update_delete_and_missing_id(self) -> None:
        tx = self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1000)
        updated = self.service.update_transaction(tx.id, {"amount": "1500", "memo": "changed"})
        self.assertEqual(updated.amount, 1500)
        self.service.delete_transaction(tx.id)
        self.assertIsNone(self.service.transactions.find(tx.id))
        with self.assertRaises(Exception):
            self.service.delete_transaction(tx.id)

    def test_category_in_use_guard(self) -> None:
        self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1000)
        with self.assertRaises(Exception):
            self.service.remove_category("food")

    def test_budget_summary_usage_and_overrun(self) -> None:
        self.service.set_budget("2026-08", 1000)
        self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1200)
        result = self.service.summary("2026-08", 3)
        self.assertEqual(result["expense"], 1200)
        self.assertEqual(result["usage"], 120.0)
        self.assertTrue(result["over_budget"])

    def test_export_import_round_trip_utf8_schema(self) -> None:
        self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1200, memo="점심", tags="식사")
        output = Path(self.tmp.name) / "export.csv"
        self.assertEqual(self.service.export_csv(output, month="2026-08"), 1)
        with output.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(tuple(reader.fieldnames or ()), CSV_FIELDS)
            row = next(reader)
            self.assertEqual(row["memo"], "점심")
        other = BudgetService(Path(self.tmp.name) / "other")
        self.assertEqual(other.import_csv(output), 1)
        self.assertEqual(len(list(other.transactions.iter_transactions())), 1)

    def test_broken_import_rolls_back_all_rows(self) -> None:
        self.service.add_transaction(date="2026-08-01", type_="expense", category="food", amount=1000)
        source = Path(self.tmp.name) / "bad.csv"
        source.write_text(
            "date,type,category,amount,memo,tags\n"
            "2026-08-02,expense,food,500,ok,meal\n"
            "2026-99-99,expense,food,600,bad,meal\n",
            encoding="utf-8",
        )
        with self.assertRaises(Exception):
            self.service.import_csv(source)
        rows = list(self.service.transactions.iter_transactions())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].amount, 1000)

    def test_transaction_validation(self) -> None:
        with self.assertRaises(Exception):
            Transaction(id="TX-1", type="expense", date="bad", amount=1, category="food")
        with self.assertRaises(Exception):
            Transaction(id="TX-1", type="other", date="2026-08-01", amount=1, category="food")
        with self.assertRaises(Exception):
            Transaction(id="TX-1", type="expense", date="2026-08-01", amount=0, category="food")


class BudgetCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.env = os.environ.copy()
        package_root = Path(__file__).resolve().parents[1]
        self.env["PYTHONPATH"] = str(package_root) + os.pathsep + self.env.get("PYTHONPATH", "")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "budget_app", "--data-dir", str(self.data), *args]
        return subprocess.run(command, input=input_text, text=True, capture_output=True, env=self.env, check=False)

    def test_help_works(self) -> None:
        result = subprocess.run([sys.executable, "-m", "budget_app", "--help"], text=True, capture_output=True, env=self.env, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)

    def test_all_command_help_paths_work(self) -> None:
        help_paths = [
            ("add",), ("list",), ("search",), ("summary",), ("update",), ("delete",),
            ("category",), ("category", "add"), ("category", "list"), ("category", "remove"),
            ("budget",), ("budget", "set"), ("import",), ("export",),
        ]
        for path in help_paths:
            with self.subTest(path=path):
                parser = build_parser()
                output = io.StringIO()
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
                    parser.parse_args([*path, "--help"])
                self.assertEqual(raised.exception.code, 0)
                self.assertIn("usage:", output.getvalue())

    def test_export_requires_source_filter(self) -> None:
        output = self.root / "no-filter.csv"
        result = self.run_cli("export", "--out", str(output))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[힌트]", result.stderr)
        self.assertFalse(output.exists())

    def test_interactive_add_persists_across_processes(self) -> None:
        add = self.run_cli("add", input_text="2026-08-08\nexpense\nfood\n15000\n점심\nmeal\n")
        self.assertEqual(add.returncode, 0, add.stderr)
        self.assertIn("id=TX-000001", add.stdout)
        listed = self.run_cli("list", "--limit", "3")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("TX-000001", listed.stdout)
        self.assertIn("점심", listed.stdout)

    def test_cli_category_budget_summary(self) -> None:
        add_category = self.run_cli("category", "add", "--name", "study")
        self.assertEqual(add_category.returncode, 0, add_category.stderr)
        add = self.run_cli("add", input_text="2026-08-08\nexpense\nstudy\n12000\nbook\nlearning\n")
        self.assertEqual(add.returncode, 0, add.stderr)
        budget = self.run_cli("budget", "set", "--month", "2026-08", "--amount", "10000")
        self.assertEqual(budget.returncode, 0, budget.stderr)
        summary = self.run_cli("summary", "--month", "2026-08", "--top", "3")
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertIn("사용률 120.0%", summary.stdout)
        self.assertIn("예산을 초과", summary.stdout)

    def test_cli_search_update_delete(self) -> None:
        self.run_cli("add", input_text="2026-08-07\nexpense\nfood\n1000\ncoffee\ndrink\n")
        searched = self.run_cli("search", "--q", "coffee", "--tag", "drink")
        self.assertEqual(searched.returncode, 0, searched.stderr)
        self.assertIn("TX-000001", searched.stdout)
        updated = self.run_cli("update", "--id", "TX-000001", "--amount", "2000", "--memo", "coffee2")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        listed = self.run_cli("list")
        self.assertIn("2000", listed.stdout)
        deleted = self.run_cli("delete", "--id", "TX-000001")
        self.assertEqual(deleted.returncode, 0, deleted.stderr)
        empty = self.run_cli("list")
        self.assertIn("데이터 없음", empty.stdout)

    def test_error_is_nonzero_without_traceback_and_has_hint(self) -> None:
        result = self.run_cli("delete", "--id", "TX-999999")
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("[오류]", combined)
        self.assertIn("[힌트]", combined)
        self.assertNotIn("Traceback", combined)

    def test_invalid_add_is_nonzero_without_traceback(self) -> None:
        result = self.run_cli("add", input_text="2026-99-99\nexpense\nfood\n1000\nbad\n\n")
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertNotIn("Traceback", combined)
        self.assertIn("YYYY-MM-DD", combined)

    def test_csv_cli_round_trip(self) -> None:
        self.run_cli("add", input_text="2026-08-08\nexpense\nfood\n5000\n한글메모\nmeal\n")
        output = self.root / "out.csv"
        exported = self.run_cli("export", "--out", str(output), "--month", "2026-08")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertTrue(output.exists())
        other_data = self.root / "other"
        command = [sys.executable, "-m", "budget_app", "--data-dir", str(other_data), "import", "--from", str(output)]
        imported = subprocess.run(command, text=True, capture_output=True, env=self.env, check=False)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertIn("imported=1", imported.stdout)


if __name__ == "__main__":
    unittest.main()
