# Code style in project

## Tabs

Yes, I ([@Lex-DRL](https://github.com/Lex-DRL)) know that 4-spaces-as-tabs is the official PEP guideline. Yes, I still use tabs as indents across my entire codebase regardless. No, I won't reconsider.

The justification is long and leads to another tabs-vs-spaces holy war, so please just accept it as a given: this repo uses **only** tabs for indents.

## Hanging indents

I'm strictly against those. So, when a long line needs splitting, instead of this:

```python
# PEP8-preferred style
def some_function_with_self_explaining_name(aaa: Iterable[str], bbb: int = 0,
                                            ccc: bool = False) -> None:
    ...
```

... I stick to this:

```python
# Black's output style
def some_function_with_self_explaining_name(
	aaa: Iterable[str], bbb: int = 0,  # Related arguments might be at the same line
	ccc: bool = False,
) -> None:
	...
```

- It's tab-size agnostic.
- It doesn't offset all the important code to the right.
- It leaves more space for comments at line end.

## Wrapping size

We all have widescreen monitors, don't we? So, hard limit is `120` characters... with rare exceptions for a few extra chars in same-line comment / type hint.

In long multiline comments, soft limit is `60-80` chars to make it more readable.

## Otherwise...

This repo tries to follow PEP guidelines.
