"""
Downloads the three test files from the Cpython repo for their parser.
These are then analyzed, preprocessed and then run by other scripts in this folder
"""
import urllib.request
import os

files = {
    "Lib/test/test_grammar.py": ["test_with_statement"],  # List of function names to comment out
    "Lib/test/test_syntax.py": [],
    "Lib/test/test_exceptions.py": [],
    "Lib/test/test_patma.py": [],
    "Lib/test/test_pep646_syntax.py": [],
}

url_template = "https://raw.githubusercontent.com/python/cpython/main/{}"
file_template = f"{os.path.dirname(__file__)}/CPython-tests/{{}}"

for filename in files:
    file = file_template.format(filename.rpartition("/")[2])
    print(file)
    urllib.request.urlretrieve(
        url_template.format(filename),
        file
    )
    if files[filename]:
        with open(file, "r+", encoding="utf-8") as f:
            out = []
            commenting_out = None
            f.seek(0)
            for line in f.readlines():
                if any(name in line for name in files[filename]):
                    commenting_out = line[:line.index("def")] + ' '
                    out.append(f"# {line}")
                    continue
                if commenting_out is not None and (
                        line.startswith(commenting_out) or
                        line.strip() == '' or
                        line.strip().startswith('#')):
                    out.append(f"# {line}")
                else:
                    commenting_out = None
                    out.append(line)
            f.seek(0)
            f.writelines(out)
