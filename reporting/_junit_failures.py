"""Internal helpers: failed-test detail extracted from parsed JUnit XML.

Shared by ``ci_run_summary.py`` and ``system_tests_run_summary.py`` so both
summaries report failed tests identically. Everything here is pure: callers
parse the XML (through their own XXE-hardened ``parse_xml_root``), hand the
root element in, and own all file and stdout I/O.

Why this exists: failed-test detail used to come from a third-party action
that created a separate Check Run per suite through the Checks API. That API
call (``PATCH /check-runs/{id}`` right after creation) intermittently returned
404 and left the run stuck ``in_progress``. The repo summaries already parse
the same JUnit XML, so they now render the failure detail themselves and emit
workflow-command annotations that the runner turns into annotations without
any Checks API call or ``checks: write`` permission.
"""

MAX_MESSAGE_CHARS = 200
MAX_ROWS_PER_SUITE = 50
MAX_ANNOTATIONS_PER_SUITE = 10


def extract_failures(root):
    """Return ``(classname, name, message)`` for each failed/errored testcase.

    When a testcase carries multiple failure/error records (e.g. a failed test
    whose teardown also errored), each record is emitted separately so the count
    matches the JUnit suite header, tagged with ``(failure)`` or ``(error)``.
    The message is the ``message`` attribute, else the first non-empty line of
    the element text, truncated to ``MAX_MESSAGE_CHARS``.
    """
    failures = []
    for testcase in root.findall(".//testcase"):
        elements = [el for el in testcase if el.tag in ("failure", "error")]
        if not elements:
            continue
        has_multiple = len(elements) > 1
        base_name = testcase.get("name", "unknown")
        classname = testcase.get("classname", "")
        for element in elements:
            raw = (element.get("message") or element.text or "").strip()
            message = raw.split("\n")[0].strip()[:MAX_MESSAGE_CHARS]
            name = f"{base_name} ({element.tag})" if has_multiple else base_name
            failures.append(
                (
                    classname,
                    name,
                    message or "no message",
                )
            )
    return failures


def _test_label(classname, name):
    return f"{classname}.{name}" if classname else name


def format_failure_section(label, failures, escape, fail_count=None):
    """Open collapsible markdown section listing failed tests for one suite.

    ``escape`` is the caller's markdown-table cell escaper (``md_cell``); every
    cell goes through it because test names and messages are untrusted text.
    ``fail_count`` is the failure total reported by the JUnit suite header; when
    it exceeds the parsed failures the difference is shown as unavailable.
    Returns ``[]`` when there is nothing to report so successful runs render
    byte-identical output.
    """
    total = max(fail_count or 0, len(failures))
    if total <= 0:
        return []
    lines = [
        "",
        f"<details open><summary>❌ <b>{label}</b> — {total} Failed</summary>",
        "",
        "| Test | Message |",
        "|:-----|:--------|",
    ]
    for classname, name, message in failures[:MAX_ROWS_PER_SUITE]:
        lines.append(f"| {escape(_test_label(classname, name))} | {escape(message)} |")
    hidden_by_cap = max(len(failures) - MAX_ROWS_PER_SUITE, 0)
    unavailable = max(total - len(failures), 0)
    if hidden_by_cap:
        lines.append(f"| …and {hidden_by_cap} more | |")
    if unavailable:
        lines.append(f"| …and {unavailable} more (details unavailable in JUnit XML) | |")
    lines += ["", "</details>"]
    return lines


def _escape_command_data(value):
    """Escape a workflow-command message per the GitHub Actions format."""
    return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_command_property(value):
    """Escape a workflow-command property (e.g. ``title``) value."""
    return _escape_command_data(value).replace(":", "%3A").replace(",", "%2C")


def annotation_lines(label, failures):
    """Return ``::error`` workflow commands for the first failures of a suite.

    Capped at ``MAX_ANNOTATIONS_PER_SUITE`` so one broken suite cannot flood the
    run page. The caller prints these to stdout; the runner creates the
    annotations itself.
    """
    title = _escape_command_property(label)
    return [
        f"::error title={title}::"
        + _escape_command_data(f"{_test_label(classname, name)}: {message}")
        for classname, name, message in failures[:MAX_ANNOTATIONS_PER_SUITE]
    ]
