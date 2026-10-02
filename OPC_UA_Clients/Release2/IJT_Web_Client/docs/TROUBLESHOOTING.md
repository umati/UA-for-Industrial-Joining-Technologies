# IJT Web Client Troubleshooting

- Check that Python 3.14+ and Node.js 24.15+ are installed and available on `PATH`.
- If automatic tooling preparation fails, check write permissions and package-index,
  proxy, or offline-cache access; uv does not need manual installation.
- Run setup and test commands from the Web Client directory. A lock mismatch
  requires reviewing `pyproject.toml` and regenerating `uv.lock` with `uv lock`;
  do not bypass it by installing floating dependencies.
- Confirm the IJT server is reachable at the configured endpoint.
- For pip deployment or source reuse, follow the
  [integration guide](../../../../docs/PYTHON_CLIENT_INTEGRATION.md).
  Contributor architecture is documented separately in `docs/SKILLS.md`.
