# IJT Web Client Testing

From the Web Client directory, with Python 3.14+ and Node.js 24.15+,
run the project test suite with:

```bash
python run_all_tests.py
```

The runner prepares uv automatically if needed; first use requires package-index
access or a supplied package cache.

For Python static checks and unit tests without a server:

```bash
python run_all_tests.py --phase1-python
```

The runner installs dependencies from `uv.lock` into `.venv_test`; local
`--ci-mode` uses `.venv_ci`. Private Envelope checks run automatically when its
checkout is available and are ignored when absent.
