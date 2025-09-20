# docstring-to-text

A simple pip package converting docstrings into clean text (proper paragraphs and indents).

For example, here's a class docstring:
```python
class MyClass:
  """
  Here's a class.
  
  
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
  * And you might need various bullet
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
Here's a class.

It has sphinx-like paragraphs, which can span multiple lines. Any modern IDE would display them as a single line, that wraps the given width.
You can't just remove all the new lines in the entire string, because you want to preserve paragraphs themselves.
Also, when it comes to lists:
- You probably want to separate items with new lines.
- However, you don't want to preserve lines inside each item.
* And you might need various bullet characters.
• Including unicode ones.
And don't forget that the list still needs to be separated from the following text.
```
