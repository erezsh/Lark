from __future__ import annotations

import logging
import os

from lark import Lark, UnexpectedInput, logger
from lark.indenter import PythonIndenter
from pathlib import Path
logger.setLevel(logging.DEBUG)
python_parser3 = Lark.open_from_package('lark', 'python.lark', ['grammars'],
                                        parser='lalr', postlex=PythonIndenter(), start=['file_input', 'single_input', 'eval_input'], debug=True)
# python_parser3.parse('def f(it, *varargs, **kwargs):\n    return list(it)\n\n\n', start="single_input")

for file in (Path(__file__).parent / "Cpython-tests").glob("*.py"):
    try:
        tree = python_parser3.parse(file.read_text(encoding="utf-8"), start="file_input")
    except UnexpectedInput as e:
        print(f'File "{file}", line {e.line}')
        print(f"{e.__class__.__qualname__}: {str(e)}")
