<div align="center">
  
# docstring-to-text

[![PyPI][pypi-shield]][pypi-url]
[![GitHub Release][github-release-shield]][github-release-url]
[![Test status][github-tests-shield]][github-tests-url]

[pypi-shield]: https://img.shields.io/pypi/v/docstring-to-text?logo=pypi
[pypi-url]: https://pypi.org/p/docstring-to-text
[github-tests-shield]: https://github.com/Lex-DRL/Py-docstring-to-text/actions/workflows/test.yml/badge.svg?branch=main
[github-tests-url]: https://github.com/Lex-DRL/Py-docstring-to-text/actions/workflows/test.yml?query=branch%3Amain
[github-release-shield]: https://img.shields.io/github/v/release/Lex-DRL/Py-docstring-to-text?logo=github
[github-release-url]: https://github.com/Lex-DRL/Py-docstring-to-text/releases/latest

**A simple pip package converting docstrings into clean text.**<br />(proper paragraphs and indents)
</div>

For example, here's a class docstring:
```python
class MyClass:
  """
  This is a class docstring.
  
  
  It has sphinx-like paragraphs, which can
  span multiple lines. Any modern IDE would
  display them as a single line, that wraps
  the given width.
  
  You can't just remove all the new lines
  in the entire string, because you want
  to preserve paragraphs themselves.
  
  Also, when it comes to lists:
    - You probably want to separate items
    with new lines.
    - However, you don't want to preserve
    lines inside each item.
  
  And...
  * ... you might need various bullet
  characters.
  • Including unicode ones.
  
  And don't forget that the list still needs
  to be separated from the following text.
  """
  ...
```

With this package, you could do:
```python
from docstring_to_text import *

clean_text = format_docstring(cleandoc(MyClass.__doc__))
clean_text = format_object_docstring(MyClass)
```

Then, the resulting string would be:
```text
This is a class docstring.

It has sphinx-like paragraphs, which can span multiple lines. Any modern IDE would display them as a single line, that wraps the given width.
You can't just remove all the new lines in the entire string, because you want to preserve paragraphs themselves.
Also, when it comes to lists:
- You probably want to separate items with new lines.
- However, you don't want to preserve lines inside each item.
And...
* ... you might need various bullet characters.
• Including unicode ones.
And don't forget that the list still needs to be separated from the following text.
```

## Contributing

> [!NOTE]
> The package uses _slightly_ PEP-non-compliant [code style](CODESTYLE.md).
