# encoding: utf-8
"""A dummy test - just to have at least one test always passing."""


def test_dummy():
	try:
		from docstring_to_text import VERSION
	except ImportError:
		assert False, "Can't import the package"
	print(f"Version: {VERSION}")
	assert True
