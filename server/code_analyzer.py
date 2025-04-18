import os
import subprocess
import json
from datetime import datetime
import concurrent.futures
from pathlib import Path
from typing import Dict, List
import logging
import tempfile
from openai import OpenAI
from dotenv import load_dotenv
from code_parser import ParserService

load_dotenv()

# Импорт ParserService из code_parser.py

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Конфигурация инструментов для Python
LANGUAGE_TOOLS = {
    "python": {
        "linter": {
            "cmd": ["pylint", "{file}", "--output-format=json"],
            "ignore": [
                "missing-module-docstring",
                "missing-function-docstring",
                "invalid-name",
            ],
        },
        "security": {"cmd": ["bandit", "-r", "{dir}", "-f", "json"], "ignore": []},
        "type_checker": {
            "cmd": [
                "mypy",
                "--strict",
                "{file}",
                "--show-error-codes",
                "--no-color-output",
            ],
            "ignore": ["import-untyped", "no-redef"],
        },
    },
}

# Конфигурация GPT-промптов
GPT_CONFIG = {
    "code_analysis": """
Вы — эксперт по {language}. Проанализируйте код, представляющий изменения пользователя в GitHub merge, и выявите ошибки в категориях: безопасность, линтинг, типизация, сложность. Игнорируйте незначительные ошибки (документация, стиль, например, {doc_ignore}, {style_ignore}). Верните не более 5 ошибок.

1. **Анализ кода**:
   - Безопасность: Проверьте уязвимости (инъекции, небезопасные функции).
   - Линтинг: Найдите логические ошибки, влияющие на функциональность.
   - Типизация: Проверьте несоответствия типов.
   - Сложность: Оцените читаемость и поддерживаемость.
2. **Формат ответа**:
```
Issues:
- Тип: [security/lint/type_error/complexity]
  Сообщение: [Описание ошибки]
  Место: [Файл:строка]
  Код: [Фрагмент кода]
  Рекомендация: [Исправление]
  Серьезность: [critical/non-critical]
```

**Код**: 
{code}
""",
    "prioritize_issues": """
Вы — старший разработчик для {language}. Проанализируйте код и список ошибок, выберите **3 самые важные ошибки**, влияющие на безопасность, функциональность или читаемость. Игнорируйте незначительные ошибки (документация, стиль: {doc_ignore}, {style_ignore}).

1. **Формат ответа**:
```
Selected Issues:
- Тип: [security/lint/type_error/complexity]
  Сообщение: [Сообщение об ошибки]
  Место: [Файл:строка]
  Код: [Фрагмент кода]
  Проблема: [Описание проблемы]
  Рекомендация: [Исправление]
  Обоснование: [Почему ошибка важна]
```

**Код**: 
{code}
**Ошибки**: 
{issues}
""",
    "analyze_patterns": """
Вы — архитектор ПО для {language}. Проанализируйте код и выявите шаблоны проектирования, анти-паттерны и позитивные практики.

1. **Шаблоны**:
   - Singleton, Factory, Strategy, Observer или неформальный шаблон.
2. **Анти-паттерны**:
   - God Class, Long Method, Duplicated Code.
3. **Позитивные практики**:
   - Читаемость, Обработка ошибок, Модульность.
4. **Формат ответа**:
```
Patterns:
- Название: [Название шаблона]
  Описание: [Описание]
Anti-patterns:
- Название: [Название анти-паттерна]
  Описание: [Описание]
Positive Practices:
- Название: [Название практики]
  Описание: [Описание]
```

**Код**: 
{code}
""",
    "overall_quality": """
Вы — старший разработчик для {language}. Оцените качество пользовательских изменений по шкале 0-10 для метрик: Code Quality, Maintainability, Security, Gpt Quality. Учитывайте ошибки и контекст.

1. **Формат ответа**:
```
Metrics:
- Code Quality: [Число]/10
- Maintainability: [Число]/10
- Security: [Число]/10
- Gpt Quality: [Число]/10
```

**Код**: 
{code}
**Метрики**:
- Количество ошибок: {num_issues}
- Серьезность: {severity_summary}
""",
}

# Примеры для каждого языка
LANGUAGE_EXAMPLES = {
    "python": {
        "doc_ignore": "missing-module-docstring",
        "style_ignore": "invalid-name",
    },
    "java": {
        "doc_ignore": "missing-javadoc",
        "style_ignore": "naming-convention",
    },
    "php": {
        "doc_ignore": "phpdoc",
        "style_ignore": "coding-standard",
    },
}


class CodeAnalysisCrew:
    def __init__(self, diff_input: str, path: str, file_name: str):
        """Инициализация анализатора кода на основе GitHub diff.

        Args:
            diff_input (str): Строка с изменениями в формате GitHub diff.
        """
        self.path = path
        self.file_name = file_name
        self.diff_input = diff_input
        self.file_diffs = []  # Список FileDiff из ParserService
        self.language = None
        self.temp_files = []  # Для очистки временных файлов
        self.report_data = {
            "key_issues": [],
            "patterns": [],
            "anti_patterns": [],
            "positive_practices": [],
            "recommendations": [],
            "metrics": {
                "code_quality": 5,
                "maintainability": 5,
                "security": 5,
                "gpt_quality": 5,
            },
            "user_contribution": {
                "files_changed": 0,
                "lines_added": 0,
                "lines_removed": 0,
                "contribution_score": 0,
            },
            "score": 0,
        }
        self.tool_issues = []

        self._parse_diff()
        self._detect_language()
        self._validate_environment()

    def _parse_diff(self):
        """Парсинг GitHub diff с использованием ParserService."""
        logger.info("Парсинг diff...")
        parser = ParserService()
        self.file_diffs = parser.parse(self.diff_input)

        # Подсчет статистики вклада
        self.report_data["user_contribution"]["files_changed"] = len(self.file_diffs)
        for diff in self.file_diffs:
            new_lines = diff.new.splitlines()
            self.report_data["user_contribution"]["lines_added"] += len(new_lines)
            self.report_data["user_contribution"]["lines_removed"] += diff.old_count
        logger.info(f"Извлечено изменений: {len(self.file_diffs)} файлов")

    def _detect_language(self):
        """Определение языка по расширениям файлов в diff."""
        extensions = {Path(diff.filename).suffix.lower() for diff in self.file_diffs}
        if len(extensions) > 1:
            raise ValueError("Diff содержит файлы с разными языками")
        ext = extensions.pop() if extensions else ".py"
        if ext == ".py":
            self.language = "python"
        elif ext == ".java":
            self.language = "java"
        elif ext == ".php":
            self.language = "php"
        else:
            raise ValueError(f"Неподдерживаемое расширение: {ext}")
        logger.info(f"Определен язык: {self.language}")

    def _validate_environment(self):
        """Проверка наличия инструментов для Python."""
        if self.language != "python":
            return
        required = {tool["cmd"][0] for tool in LANGUAGE_TOOLS["python"].values()}
        missing = []
        for cmd in required:
            try:
                subprocess.run(
                    [cmd, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                missing.append(cmd)
        if missing:
            raise EnvironmentError(f"Отсутствуют инструменты: {', '.join(missing)}")

    def _create_temp_file(self, code: str, suffix: str) -> str:
        """Создание временного файла для анализа."""
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, mode="w", encoding="utf-8"
        )
        temp_file.write(code)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def _extract_code_fragment(self, code: str, lineno: int, context: int = 3) -> str:
        """Извлечение фрагмента кода."""
        lines = code.splitlines()
        start = max(0, lineno - context)
        end = min(len(lines), lineno + context + 1)
        return "\n".join(lines[start:end])

    def _run_gpt_analysis(self, code: str, filename: str):
        """Анализ кода через GPT для Java и PHP."""
        logger.info(f"Запуск GPT-анализа для {filename}...")
        try:
            prompt = GPT_CONFIG["code_analysis"].format(
                language=self.language,
                code=code,
                doc_ignore=LANGUAGE_EXAMPLES[self.language]["doc_ignore"],
                style_ignore=LANGUAGE_EXAMPLES[self.language]["style_ignore"],
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=15,
            )
            gpt_result = response.choices[0].message.content.strip()
            issues = []
            current_issue = {}
            for line in gpt_result.splitlines():
                line = line.strip()
                if line.startswith("- Тип:"):
                    current_issue = {"type": line.split(":")[1].strip()}
                elif line.startswith("  Сообщение:"):
                    current_issue["message"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Место:"):
                    current_issue["location"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Код:"):
                    current_issue["code"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Рекомендация:"):
                    current_issue["recommendation"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Серьезность:"):
                    current_issue["severity"] = line.split(":", 1)[1].strip()
                    current_issue["location"] = (
                        f"{filename}:{current_issue['location'].split(':')[1]}"
                    )
                    if not any(
                        x in current_issue["message"].lower()
                        for x in ["javadoc", "phpdoc", "name"]
                    ):
                        issues.append(current_issue)
                    current_issue = {}
            self.tool_issues.extend(issues[:5])
            logger.info("GPT-анализ завершен")
        except Exception as e:
            logger.error(f"Ошибка GPT-анализа: {e}")

    def _run_python_linter(self, temp_file: str, filename: str):
        """Pylint для Python."""
        logger.info(f"Запуск Pylint для {filename}...")
        tool = LANGUAGE_TOOLS["python"]["linter"]
        cmd = [
            arg.format(file=temp_file, dir=os.path.dirname(temp_file))
            for arg in tool["cmd"]
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            ).stdout
            data = json.loads(result)
            for msg in data:
                if msg["symbol"] in tool["ignore"]:
                    continue
                line_num = msg.get("line", 0)
                code_fragment = self._extract_code_fragment(
                    Path(temp_file).read_text(), line_num
                )
                issue = {
                    "type": "lint",
                    "code": code_fragment,
                    "message": f"Pylint: {msg['message']} ({msg['symbol']})",
                    "location": f"{filename}:{line_num}",
                    "recommendation": f"Исправить {msg['symbol']}",
                    "severity": "critical"
                    if msg["type"] == "error"
                    else "non-critical",
                }
                self.tool_issues.append(issue)
            logger.info("Pylint завершен")
        except Exception as e:
            logger.error(f"Ошибка Pylint: {e}")

    def _run_python_security(self, temp_file: str, filename: str):
        """Bandit для Python."""
        logger.info(f"Запуск Bandit для {filename}...")
        tool = LANGUAGE_TOOLS["python"]["security"]
        cmd = [
            arg.format(file=temp_file, dir=os.path.dirname(temp_file))
            for arg in tool["cmd"]
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            ).stdout
            data = json.loads(result)
            for issue in data.get("results", []):
                if issue["issue_severity"] in ["HIGH", "MEDIUM"]:
                    line_num = issue.get("line_number", 0)
                    code_fragment = self._extract_code_fragment(
                        Path(temp_file).read_text(), line_num
                    )
                    issue_data = {
                        "type": "security",
                        "code": code_fragment,
                        "message": f"Bandit: {issue.get('issue_text', '')}",
                        "location": f"{filename}:{line_num}",
                        "recommendation": f"Исправить уязвимость {issue.get('test_id', '')}",
                        "severity": "critical"
                        if issue["issue_severity"] == "HIGH"
                        else "non-critical",
                    }
                    self.tool_issues.append(issue_data)
            logger.info("Bandit завершен")
        except Exception as e:
            logger.error(f"Ошибка Bandit: {e}")

    def _run_python_type_checker(self, temp_file: str, filename: str):
        """MyPy для Python."""
        logger.info(f"Запуск MyPy для {filename}...")
        tool = LANGUAGE_TOOLS["python"]["type_checker"]
        cmd = [
            arg.format(file=temp_file, dir=os.path.dirname(temp_file))
            for arg in tool["cmd"]
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            ).stdout
            for line in result.splitlines():
                if ":" in line and "error:" in line:
                    parts = line.split(":", maxsplit=3)
                    if len(parts) < 4:
                        logger.debug(
                            f"Пропущена строка MyPy с неверным форматом: {line}"
                        )
                        continue
                    file_path, line_num, _, msg = parts
                    if not line_num.isdigit():
                        logger.debug(
                            f"Неверный номер строки в MyPy: {line_num}, строка: {line}"
                        )
                        continue
                    if any(pattern in msg for pattern in tool["ignore"]):
                        continue
                    line_num_int = int(line_num)
                    code_fragment = self._extract_code_fragment(
                        Path(temp_file).read_text(), line_num_int
                    )
                    issue = {
                        "type": "type_error",
                        "code": code_fragment,
                        "message": f"MyPy: {msg.strip()}",
                        "location": f"{filename}:{line_num}",
                        "recommendation": f"Исправить ошибку типов",
                        "severity": "non-critical"
                        if "missing" in msg.lower()
                        else "critical",
                    }
                    self.tool_issues.append(issue)
            logger.info("MyPy завершен")
        except Exception as e:
            logger.error(f"Ошибка MyPy: {e}")

    def _prioritize_issues_with_gpt(self, code: str) -> List[Dict]:
        """Ранжирование ошибок через GPT."""
        try:
            issues_str = "\n".join(
                [
                    f"{i + 1}. {issue['type'].capitalize()}: {issue['message']} в {issue['location']}"
                    for i, issue in enumerate(self.tool_issues)
                ]
            )
            prompt = GPT_CONFIG["prioritize_issues"].format(
                language=self.language,
                code=code,
                issues=issues_str,
                doc_ignore=LANGUAGE_EXAMPLES[self.language]["doc_ignore"],
                style_ignore=LANGUAGE_EXAMPLES[self.language]["style_ignore"],
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=15,
            )
            gpt_result = response.choices[0].message.content.strip()
            prioritized_issues = []
            current_issue = {}
            for line in gpt_result.splitlines():
                line = line.strip()
                if line.startswith("- Тип:"):
                    current_issue = {"type": line.split(":")[1].strip()}
                elif line.startswith("  Сообщение:"):
                    current_issue["message"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Место:"):
                    current_issue["location"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Код:"):
                    current_issue["code"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Проблема:"):
                    current_issue["problem"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Рекомендация:"):
                    current_issue["recommendation"] = line.split(":", 1)[1].strip()
                elif line.startswith("  Обоснование:"):
                    current_issue["justification"] = line.split(":", 1)[1].strip()
                    prioritized_issues.append(current_issue)
                    current_issue = {}
            return [
                {
                    "source": issue["type"].capitalize(),
                    "message": f"{issue['message']}\nПроблема: {issue['problem']}\nРекомендация: {issue['recommendation']}\nОбоснование: {issue['justification']}\nКод: {issue['code']}",
                }
                for issue in prioritized_issues[:3]
            ]
        except Exception as e:
            logger.error(f"Ошибка приоритизации GPT: {e}")
            return []

    def _get_gpt_quality_score(
        self, code: str, num_issues: int, severity_summary: str
    ) -> Dict:
        """Оценка метрик качества через GPT."""
        try:
            prompt = GPT_CONFIG["overall_quality"].format(
                language=self.language,
                code=code,
                num_issues=num_issues,
                severity_summary=severity_summary,
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=10,
            )
            gpt_result = response.choices[0].message.content.strip()
            metrics = {}
            for line in gpt_result.splitlines():
                line = line.strip()
                if line.startswith("- Code Quality:"):
                    metrics["code_quality"] = int(
                        line.split(":")[1].split("/")[0].strip()
                    )
                elif line.startswith("- Maintainability:"):
                    metrics["maintainability"] = int(
                        line.split(":")[1].split("/")[0].strip()
                    )
                elif line.startswith("- Security:"):
                    metrics["security"] = int(line.split(":")[1].split("/")[0].strip())
                elif line.startswith("- Gpt Quality:"):
                    metrics["gpt_quality"] = int(
                        line.split(":")[1].split("/")[0].strip()
                    )
            return metrics
        except Exception as e:
            logger.error(f"Ошибка GPT-оценки: {e}")
            return {
                "code_quality": 5,
                "maintainability": 5,
                "security": 5,
                "gpt_quality": 5,
            }

    def _pattern_analysis(self, code: str):
        """Анализ шаблонов через GPT."""
        logger.info("Запуск анализа паттернов...")
        try:
            prompt = GPT_CONFIG["analyze_patterns"].format(
                language=self.language,
                code=code,
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                timeout=10,
            )
            analysis = response.choices[0].message.content.strip()
            self._parse_analysis(analysis)
            logger.info("Анализ паттернов завершен")
        except Exception as e:
            logger.error(f"Ошибка анализа паттернов: {e}")

    def _parse_analysis(self, text: str):
        """Парсинг анализа паттернов."""
        section = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Patterns:"):
                section = "patterns"
            elif line.startswith("Anti-patterns:"):
                section = "anti_patterns"
            elif line.startswith("Positive Practices:"):
                section = "positive_practices"
            elif line.startswith("- Название:") and section:
                try:
                    name = line.split(":", 1)[1].strip()
                    desc_line = next(
                        l
                        for l in text.splitlines()[text.splitlines().index(line) + 1 :]
                        if l.strip().startswith("Описание:")
                    )
                    desc = desc_line.split(":", 1)[1].strip()
                    self.report_data[section].append(
                        {"name": name, "description": desc}
                    )
                except (ValueError, StopIteration):
                    continue
        if not self.report_data["patterns"]:
            self.report_data["patterns"].append(
                {
                    "name": "Неформальный шаблон",
                    "description": "Инкапсуляция через функции или классы",
                }
            )

    def _add_recommendation(self, text: str):
        """Добавление рекомендации."""
        if text and text not in self.report_data["recommendations"]:
            self.report_data["recommendations"].append(text)

    def _calculate_score(self):
        """Расчет итогового скора."""
        weights = {
            "code_quality": 0.3,
            "maintainability": 0.3,
            "security": 0.2,
            "gpt_quality": 0.2,
        }
        score = sum(self.report_data["metrics"][k] * w for k, w in weights.items())
        if not self.report_data["anti_patterns"]:
            score += 0.5
        if self.report_data["positive_practices"]:
            score += 0.5
        self.report_data["score"] = min(10, round(score, 1))
        self.report_data["user_contribution"]["contribution_score"] = self.report_data[
            "score"
        ]

    def _generate_report(self):
        """Генерация отчета."""
        logger.info("Генерация отчета...")
        self._calculate_score()
        lines = []
        lines.append(f"User Contribution Analysis Report ({datetime.now().date()})")
        lines.append(f"\nContribution Summary:")
        lines.append(
            f"Files Changed: {self.report_data['user_contribution']['files_changed']}"
        )
        lines.append(
            f"Lines Added: {self.report_data['user_contribution']['lines_added']}"
        )
        lines.append(
            f"Lines Removed: {self.report_data['user_contribution']['lines_removed']}"
        )

        lines.append("\nKey Issues in User Changes:")
        for i, issue in enumerate(self.report_data["key_issues"]):
            lines.append(f"{i + 1}. [{issue['source']}] {issue['message']}")

        if not self.report_data["key_issues"]:
            lines.append("None: Проблемы не обнаружены")

        lines.append("\nDetected Patterns in User Changes:")
        for i, p in enumerate(self.report_data["patterns"]):
            lines.append(f"{i + 1}. {p['name']}: {p['description']}")

        lines.append("\nDetected Anti-patterns in User Changes:")
        if not self.report_data["anti_patterns"]:
            lines.append("None: Анти-паттерны не обнаружены")
        else:
            for i, ap in enumerate(self.report_data["anti_patterns"]):
                lines.append(f"{i + 1}. {ap['name']}: {ap['description']}")

        lines.append("\nPositive Practices in User Changes:")
        for i, pp in enumerate(self.report_data["positive_practices"]):
            lines.append(f"{i + 1}. {pp['name']}: {pp['description']}")
        if not self.report_data["positive_practices"]:
            lines.append(
                "1. Читаемость: Использование понятных имен и стиля кодирования"
            )

        lines.append("\nMetrics for User Contribution:")
        for k, v in self.report_data["metrics"].items():
            lines.append(f"{k.replace('_', ' ').title()}: {v}/10")

        lines.append(f"\nOverall Contribution Score: {self.report_data['score']}/10")

        lines.append("\nRecommendations for User Changes:")
        for i, rec in enumerate(self.report_data["recommendations"]):
            lines.append(f"{i + 1}. {rec}")
        if not self.report_data["recommendations"]:
            lines.append("None: Рекомендации отсутствуют")

        report_text = "\n".join(lines)
        print(report_text)
        try:
            path = self.path / self.file_name
            with open(path, "w", encoding="utf-8") as f:
                f.write(report_text)
            logger.info(f"Отчет сохранен в {path}")
            return f"Отчет сгенерирован: {path}"
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            return f"Ошибка генерации отчета: {e}"

    def run_all_tools(self):
        """Запуск всех инструментов для пользовательских изменений."""
        logger.info(f"Запуск анализа для {self.language}...")
        for diff in self.file_diffs:
            code = diff.new
            if not code.strip():
                continue

            if self.language == "python":
                # Создаем временный файл для анализа
                temp_file = self._create_temp_file(code, suffix=".py")
                tools = [
                    lambda: self._run_python_linter(temp_file, diff.filename),
                    lambda: self._run_python_security(temp_file, diff.filename),
                    lambda: self._run_python_type_checker(temp_file, diff.filename),
                ]
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [executor.submit(tool) for tool in tools]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Ошибка инструмента: {e}")
            else:
                # Для Java и PHP используем GPT
                self._run_gpt_analysis(code, diff.filename)

    def analyze(self):
        """Основной метод анализа пользовательского вклада."""
        logger.info("Начало анализа...")
        self.run_all_tools()

        # Собираем весь пользовательский код для анализа шаблонов и метрик
        user_code = "\n".join(
            f"# {diff.filename}\n{diff.new}"
            for diff in self.file_diffs
            if diff.new.strip()
        )

        if not user_code.strip():
            raise ValueError("Нет пользовательских изменений для анализа")

        self._pattern_analysis(user_code)
        self.report_data["key_issues"] = self._prioritize_issues_with_gpt(user_code)
        self.report_data["recommendations"] = [
            issue["message"].split("\nРекомендация: ")[1].split("\n")[0]
            for issue in self.report_data["key_issues"]
            if "Рекомендация: " in issue["message"]
        ]
        num_issues = len(self.report_data["key_issues"])
        severity_summary = f"{num_issues} key issues in user changes"
        self.report_data["metrics"].update(
            self._get_gpt_quality_score(user_code, num_issues, severity_summary)
        )
        self._generate_report()

        # Очистка временных файлов
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"Удален временный файл: {temp_file}")
            except Exception as e:
                logger.error(f"Ошибка удаления временного файла: {e}")
