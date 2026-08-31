"""B2-1 Reference의 핵심 동작을 자동으로 확인하는 단위 테스트입니다.

이 파일은 실제 프로그램 기능을 구현하는 곳이 아니라, 구현한 기능이 요구사항대로
동작하는지 반복해서 검증하는 곳입니다. ``unittest``는 Python 표준 라이브러리이므로
B2-1의 '외부 pip 패키지 사용 금지' 조건에도 맞습니다.

입문자가 테스트 코드를 읽을 때는 다음 흐름을 먼저 보면 됩니다.

1. ``setUp()``: 각 테스트 전에 깨끗한 임시 저장소 준비
2. ``self.service``: 실제 BudgetService 사용
3. ``self.assert...``: 기대 결과와 실제 결과 비교
4. ``tearDown()``: 임시 파일 정리

각 테스트는 서로 영향을 주지 않도록 새로운 임시 디렉터리에서 실행됩니다.
"""

from __future__ import annotations

import csv
import inspect
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from budget_app.cli import main
from budget_app.errors import AppError
from budget_app.services import BudgetService


class BudgetServiceTests(unittest.TestCase):
    """Service/Repository/CLI의 필수 요구사항을 검증하는 테스트 모음입니다."""

    def setUp(self) -> None:
        """각 테스트가 시작되기 전에 독립적인 임시 데이터 폴더를 만듭니다."""

        # TemporaryDirectory는 운영체제의 임시 위치에 테스트 전용 폴더를 만듭니다.
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"

        # 실제 애플리케이션과 같은 BudgetService를 테스트용 폴더에서 실행합니다.
        self.service = BudgetService(self.data_dir)

    def tearDown(self) -> None:
        """각 테스트가 끝난 뒤 임시 디렉터리를 삭제합니다."""

        self.temp.cleanup()

    def add_sample(self) -> None:
        """여러 테스트에서 재사용할 대표 거래 3건을 저장합니다.

        수입 1건, 지출 2건을 넣어 최신순, 검색, 요약, 예산 테스트에 사용합니다.
        숫자에서 ``3_000_000``처럼 밑줄은 사람이 읽기 쉽게 하는 Python 표기이며
        실제 값은 3000000과 같습니다.
        """

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
        """첫 실행에서 3개 JSONL 파일과 기본 카테고리가 만들어지는지 확인합니다."""

        self.assertTrue((self.data_dir / "transactions.jsonl").exists())
        self.assertTrue((self.data_dir / "categories.jsonl").exists())
        self.assertTrue((self.data_dir / "budgets.jsonl").exists())
        self.assertIn("food", self.service.list_categories())

    def test_transactions_categories_and_budget_survive_reopen(self) -> None:
        """Service 객체를 새로 만들어도 거래/카테고리/예산이 파일에 남는지 확인합니다."""

        self.service.add_category("health")
        transaction = self.service.add_transaction(
            date="2026-08-10", type="expense", category="health", amount=12_000, memo="약국"
        )
        self.service.set_budget("2026-08", 500_000)

        # 같은 data_dir으로 새 Service를 만드는 것은 프로그램을 종료했다가 다시
        # 실행하는 상황을 간단히 재현하는 방법입니다.
        reopened = BudgetService(self.data_dir)
        self.assertIsNotNone(reopened.transactions.find(transaction.id))
        self.assertIn("health", reopened.list_categories())

        budget = reopened.budgets.get("2026-08")
        self.assertIsNotNone(budget)
        self.assertEqual(budget.amount, 500_000)

    def test_add_list_search_and_persistence(self) -> None:
        """대표 거래 저장, 최신순 list, generator search, 재오픈 persistence를 확인합니다."""

        self.add_sample()

        # list_transactions()가 정말 generator인지 먼저 확인합니다.
        list_stream = self.service.list_transactions(limit=2)
        self.assertTrue(inspect.isgenerator(list_stream))

        # 테스트 비교를 위해 여기서만 generator를 list로 소비합니다.
        latest = list(list_stream)
        self.assertEqual([item.date for item in latest], ["2026-08-03", "2026-08-02"])

        search_stream = self.service.search_transactions(category="food", tag="meal")
        self.assertTrue(inspect.isgenerator(search_stream))
        search = list(search_stream)
        self.assertEqual(len(search), 1)
        self.assertEqual(search[0].memo, "점심")

        # 새 Service에서도 3건이 그대로 읽히면 거래 persistence가 유지된 것입니다.
        reopened = BudgetService(self.data_dir)
        self.assertEqual(len(list(reopened.transactions.iter_all())), 3)

    def test_search_all_core_filters_and_latest_order(self) -> None:
        """기간/category/type/메모/tag 검색 조건을 동시에 적용해 정확성을 확인합니다."""

        self.add_sample()
        result = list(
            self.service.search_transactions(
                date_from="2026-08-01",
                date_to="2026-08-31",
                type="expense",
                query="점심",
                tag="meal",
                category="food",
            )
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].date, "2026-08-02")

    def test_summary_budget_usage_and_over_budget(self) -> None:
        """월 집계, 예산 사용률, 예산 초과, 카테고리 순위를 확인합니다."""

        self.add_sample()
        self.service.set_budget("2026-08", 25_000)
        result = self.service.summary("2026-08", top=2)

        self.assertEqual(result["income"], 3_000_000)
        self.assertEqual(result["expense"], 30_000)
        self.assertEqual(result["balance"], 2_970_000)
        self.assertTrue(result["over_budget"])

        # 지출 30,000 / 예산 25,000 * 100 = 120.0%
        self.assertAlmostEqual(result["budget_usage"], 120.0)
        self.assertEqual(result["top"][0], ("food", 20_000))

    def test_summary_empty_month_is_explicit(self) -> None:
        """거래가 없는 달을 오류가 아닌 count=0 상태로 명확히 반환하는지 확인합니다."""

        result = self.service.summary("2026-12", top=3)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["income"], 0)
        self.assertEqual(result["expense"], 0)

    def test_update_and_delete_use_stable_ids_and_atomic_rewrite(self) -> None:
        """수정/삭제 후 ID·파일 상태·재오픈 결과가 안전하게 유지되는지 확인합니다."""

        self.add_sample()
        target = self.service.transactions.find("TX-000002")
        self.assertIsNotNone(target)

        # TX-000002의 ID는 유지하면서 금액과 메모만 바꿉니다.
        updated = self.service.update_transaction("TX-000002", amount=25_000, memo="저녁")
        self.assertEqual(updated.amount, 25_000)
        self.assertEqual(updated.memo, "저녁")

        # TX-000003만 삭제되고 다른 거래가 남는지 확인합니다.
        self.service.delete_transaction("TX-000003")
        self.assertIsNone(self.service.transactions.find("TX-000003"))
        self.assertIsNotNone(self.service.transactions.find("TX-000002"))

        # 원자적 재작성 helper가 같은 디렉터리에 만든 임시 파일을 남기지 않아야 합니다.
        leftovers = list(self.data_dir.glob(".transactions.jsonl.tmp-*"))
        self.assertEqual(leftovers, [])

        # 다시 열었을 때 JSONL을 정상 읽을 수 있어야 파일 재작성이 완성된 것입니다.
        reopened = BudgetService(self.data_dir)
        self.assertEqual(reopened.transactions.find("TX-000002").amount, 25_000)
        self.assertIsNone(reopened.transactions.find("TX-000003"))

    def test_missing_update_and_delete_are_errors(self) -> None:
        """존재하지 않는 ID를 수정/삭제할 때 AppError가 발생하는지 확인합니다."""

        # assertRaises는 괄호 안 코드가 지정한 예외를 발생시켜야 테스트를 통과시킵니다.
        with self.assertRaises(AppError):
            self.service.update_transaction("TX-999999", memo="none")
        with self.assertRaises(AppError):
            self.service.delete_transaction("TX-999999")

    def test_invalid_transaction_inputs_are_rejected(self) -> None:
        """잘못된 날짜/type/category/0·음수 금액을 모두 거부하는지 확인합니다."""

        bad_cases = (
            dict(date="2026-99-99", type="expense", category="food", amount=1000),
            dict(date="2026-08-01", type="other", category="food", amount=1000),
            dict(date="2026-08-01", type="expense", category="missing", amount=1000),
            dict(date="2026-08-01", type="expense", category="food", amount=0),
            dict(date="2026-08-01", type="expense", category="food", amount=-1),
        )

        # subTest를 사용하면 여러 bad_case 중 어느 입력에서 실패했는지 찾기 쉽습니다.
        for kwargs in bad_cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(AppError):
                self.service.add_transaction(**kwargs)

    def test_remove_category_is_blocked_when_in_use(self) -> None:
        """실제 거래가 참조하는 category를 삭제하지 못하게 하는지 확인합니다."""

        self.service.add_transaction(
            date="2026-08-01", type="expense", category="food", amount=1_000
        )
        with self.assertRaises(AppError):
            self.service.remove_category("food")

    def test_export_and_import_fixed_csv_schema(self) -> None:
        """공식 CSV 6개 컬럼으로 export하고 새 저장소에 다시 import되는지 확인합니다."""

        self.add_sample()
        output = Path(self.temp.name) / "export.csv"

        count = self.service.export_csv(output, month="2026-08")
        self.assertEqual(count, 3)

        # DictReader.fieldnames로 실제 CSV 헤더 순서를 확인합니다.
        with output.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, ["date", "type", "category", "amount", "memo", "tags"])

        # 완전히 다른 data_dir으로 import하여 원본 저장소와 분리된 복원을 검증합니다.
        second_data_dir = Path(self.temp.name) / "imported-data"
        second = BudgetService(second_data_dir)
        result = second.import_csv(output)

        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(len(list(second.transactions.iter_all())), 3)

    def test_export_date_range_and_required_condition(self) -> None:
        """날짜 범위 export와 export 필터 필수 규칙을 확인합니다."""

        self.add_sample()
        output = Path(self.temp.name) / "range.csv"

        count = self.service.export_csv(
            output,
            date_from="2026-08-02",
            date_to="2026-08-03",
        )
        self.assertEqual(count, 2)

        # month도 date range도 없으면 어떤 거래를 내보낼지 알 수 없으므로 오류가 정상입니다.
        with self.assertRaises(AppError):
            self.service.export_csv(Path(self.temp.name) / "bad.csv")

    def test_import_skips_broken_rows_and_reports_reason(self) -> None:
        """깨진 CSV 행을 건너뛰고 imported/skipped/행 번호를 기록하는지 확인합니다."""

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
        self.assertIn("row 3", result.errors[0])

    def test_cli_expected_error_has_nonzero_exit_without_traceback(self) -> None:
        """CLI 오류가 exit!=0, [오류]/[힌트], no Traceback 계약을 지키는지 확인합니다."""

        # 실제 터미널 대신 StringIO에 표준 오류(stderr)를 임시로 받아 내용을 검사합니다.
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["--data-dir", str(self.data_dir), "delete", "--id", "TX-999999"])

        self.assertNotEqual(exit_code, 0)
        self.assertIn("[오류]", stderr.getvalue())
        self.assertIn("[힌트]", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    # 이 파일을 직접 ``python test_budget_app.py``처럼 실행했을 때 테스트를 시작합니다.
    unittest.main()
