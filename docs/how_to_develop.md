# Contributing to Lark

There are many ways you can help the project:

* Help solve issues
* Improve the documentation
* Write new grammars for Lark's library
* Write a blog post introducing Lark to your audience
* Port Lark to another language
* Help with code development

If you're interested in taking one of these on, contact us on [Gitter](https://gitter.im/lark-parser/Lobby) or [Github Discussion](https://github.com/lark-parser/lark/discussions), and we will provide more details and assist you in the process.

## Code Style

Lark does not follow a predefined code style.
We accept any code style that makes sense, as long as it's Pythonic and easy to read.

## Unit Tests

Lark comes with an extensive set of tests. Many of the tests will run several times, once for each parser configuration.

To run the tests, just go to the lark project root, and run the command:
```bash
python -m tests
```

or

```bash
pypy -m tests
```

For a list of supported interpreters, you can consult the `tox.ini` file.

You can also run a single unittest using its class and method name, for example:
```bash
##   test_package test_class_name.test_function_name
python -m tests TestLalrBasic.test_keep_all_tokens
```

### tox

To run all Unit Tests with tox,
install tox and Python 2.7 up to the latest python interpreter supported (consult the file tox.ini).
Then,
run the command `tox` on the root of this project (where the main setup.py file is on).

And, for example,
if you would like to only run the Unit Tests for Python version 2.7,
you can run the command `tox -e py27`

### pytest

You can also run the tests using pytest:

```bash
pytest tests
```

### Using setup.py

Another way to run the tests is using setup.py:

```bash
python setup.py test
```

## Building the Documentation

To build the documentation:

```sh
cd docs/
pip install -r requirements.txt
make html
```

To review the result, open the built HTML files under `_build/html/` in your browser.
