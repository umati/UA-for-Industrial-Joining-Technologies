# This file makes src/python/ a regular Python package.
#
# Without it, Python treats src/python/ as a namespace package and continues
# scanning sys.path entries. If tests/python/ (the test directory) also
# appears on sys.path, it gets merged into the same namespace package — and
# depending on sys.path ordering (which differs between Windows and Linux CI),
# the test directory can shadow the real source package, producing:
#   ModuleNotFoundError: No module named 'python'
#
# A regular package (with __init__.py) always beats namespace package
# portions, regardless of sys.path ordering.
