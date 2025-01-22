from __future__ import annotations
from __future__ import annotations

import logging
import os
import doctest

from lark import Lark, UnexpectedInput, logger
from lark.indenter import PythonIndenter
from pathlib import Path
logger.setLevel(logging.DEBUG)
python_parser3 = Lark.open_from_package('lark', 'python.lark', ['grammars'],
                                        parser='lalr', postlex=PythonIndenter(), start=['file_input', 'single_input', 'eval_input'], debug=True)

no_print = {
    "fp": lambda *args, **kwargs: None,
    "fn": lambda *args, **kwargs: None,

    "tp": lambda *args, **kwargs: None,
    "tn": lambda *args, **kwargs: None
}


print_all = {
    "fp": print,
    "fn": print,

    "tp": print,
    "tn": print
}

for file in (Path(__file__).parent / "Cpython-tests").glob("*.py"):
    text = file.read_text(encoding="utf-8")
    if "import doctest" in text:
        doc_parser = doctest.DocTestParser()
        docstring = next(t.value for t in python_parser3.lex(text) if "STRING" in t.type)
        examples = doc_parser.get_examples(eval(docstring), str(file))
        data = {"fp": 0, "tp": 0, "fn": 0, "tn": 0}
        if "test_pep646_syntax" in file.name:
            functions = print_all
        else:
            functions = no_print
        for example in examples:
            try:
                tree = python_parser3.parse(example.source + "\n", start="single_input")
                err = None
            except UnexpectedInput as e:
                tree = None
                err = e
            if example.exc_msg is not None:
                if err is None:
                    functions["fp"](f"Unexpected success with example:\n{example.source.rstrip()}")
                    functions["fp"]("Excepted error message:", example.exc_msg.rstrip())
                    functions["fp"]()
                    data["fp"] += 1
                else:
                    functions["tn"]("Correctly errored on:\n", example.source.rstrip())
                    data["tn"] += 1
            else:
                if err is not None:
                    functions["fn"](f"Unexpected failure with example:\n{example.source.rstrip()}")
                    functions["fn"](f"Got error message: {err.__class__.__qualname__}: {str(err)}")
                    functions["fn"](repr(example.source))
                    functions["fn"]()
                    data["fn"] += 1
                else:
                    functions["tp"]("Correctly parsed:\n", example.source.rstrip())
                    data["tp"] += 1
        print(file, data)
