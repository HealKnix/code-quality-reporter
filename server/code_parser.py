import re
from typing import List, NamedTuple


class FileDiff(NamedTuple):
    """
    Описывает структуру разбора одного файла:
    - filename: имя файла
    - original: исходный код до изменений
    - old_start: начальная строка в оригинальном файле
    - old_count: количество строк в оригинальном фрагменте оригинального файла
    - new_start: начальная строка в новом файле
    - new_count: количество строк в новом фрагменте
    - new: новый код после изменений
    """

    filename: str
    original: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    new: str


class ParserService:
    """Сервис для парсинга строки с диффом по файлам"""

    # Компилируем шаблон один раз
    _PATTERN = re.compile(
        r"###\s*(?P<filename>.+?)\n"  # заголовок с именем файла
        r"(?P<original>.*?)(?:# user code in .+?\n)"  # исходный код до изменений
        r"@@\s*-(?P<old_start>\d+),(?P<old_count>\d+)"  # информация об оригинале
        r"\s+\+(?P<new_start>\d+),(?P<new_count>\d+)"  # информация о новом коде
        r"\s*@@\n"  # конец хедера
        r"(?P<new>.*?)(?=(?:\n###)|\Z)",  # новый код до следующего файла
        re.DOTALL,
    )

    def parse(self, text: str) -> List[FileDiff]:
        """
        Разбирает входной текст и возвращает список FileDiff для каждого обнаруженного файла.
        :param text: входная строка с описанием изменений в нескольких файлах
        :return: список объектов FileDiff
        """
        diffs: List[FileDiff] = []
        for match in self._PATTERN.finditer(text):
            diffs.append(
                FileDiff(
                    filename=match.group("filename").strip(),
                    original=match.group("original").strip(),
                    old_start=int(match.group("old_start")),
                    old_count=int(match.group("old_count")),
                    new_start=int(match.group("new_start")),
                    new_count=int(match.group("new_count")),
                    new=match.group("new").strip(),
                )
            )
        return diffs


# Пример использования
if __name__ == "__main__":
    sample = """
### file1.py
def func1():
	return

# user code in file1.py
@@ -92,6 +92,21 @@\n
def func1():
	print("Hello1")
	return

### file2.py
def func2():
	return

# user code in file2.py
@@ -248,21 +262,12 @@\n
def func2():
	print("Hello2")
	return

### file3.py
def func3():
	return

# user code in file3.py
@@ -275,6 +280,13 @@\n
def func4():
	print("Hello4")
	return
    """
    service = ParserService()
    result = service.parse(sample)
    for diff in result:
        print(diff)
