# encoding: utf-8
"""A sanity-check import test - just to have at least one test, which (supposedly) always passes."""


def test_import_package():
	try:
		import docstring_to_text
	except ImportError:
		assert False, "Can't import the package"
	assert True


def test_import_version():
	try:
		from docstring_to_text import VERSION
	except ImportError:
		assert False, "Can't import the package version"
	assert isinstance(VERSION, str)

def test_broken():
	assert False, "Intentionally broken test"
