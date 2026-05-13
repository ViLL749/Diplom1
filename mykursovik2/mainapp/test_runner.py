from django.test.runner import DiscoverRunner
from unittest import TextTestResult
from unittest.runner import _WritelnDecorator
import sys
from termcolor import colored


class CustomTestResult(TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0
        self.total_count = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        self.total_count += 1
        self.stream.write(colored(f"✓ {test._testMethodName} - Успех\n", "green"))
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.total_count += 1
        self.stream.write(colored(f"✗ {test._testMethodName} - Неудача\n", "red"))
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.total_count += 1
        self.stream.write(colored(f"! {test._testMethodName} - Ошибка\n", "yellow"))
        self.stream.flush()

    def print_summary(self):
        color = "green" if self.wasSuccessful() else "red"
        self.stream.write(colored(f"\nРезультат: {self.success_count}/{self.total_count} тестов успешно\n", color))
        self.stream.flush()

    def wasSuccessful(self):
        return self.success_count == self.total_count


class CustomTestRunner(DiscoverRunner):
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        self.setup_test_environment()
        suite = self.build_suite(test_labels)
        old_config = self.setup_databases()

        result = CustomTestResult(
            stream=_WritelnDecorator(sys.stdout),
            descriptions=self.descriptions if hasattr(self, 'descriptions') else True,
            verbosity=self.verbosity if hasattr(self, 'verbosity') else 1
        )
        suite.run(result)
        result.print_summary()

        self.teardown_databases(old_config)
        self.teardown_test_environment()
        return self.suite_result(suite, result)