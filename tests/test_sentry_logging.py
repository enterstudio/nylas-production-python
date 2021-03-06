import json
import sys
import traceback

from nylas.logging import (get_logger, safe_format_exception,
                           MAX_EXCEPTION_LENGTH)
from nylas.logging.sentry import log_uncaught_errors, get_sentry_client


class ReallyVerboseError(Exception):
    def __str__(self):
        return 10**6 * 'A'


def test_root_filelogger(logfile):
    logger = get_logger()
    logger.info('INFO')
    logger.warning('WARNING')
    logger.error('ERROR')
    # NOTE: This slurps the whole logfile. Hope it's not big.
    log_contents = logfile.read()

    loglines = [json.loads(l) for l in log_contents.strip().split('\n')]
    assert [l['event'] for l in loglines] == ['INFO', 'WARNING', 'ERROR']

    for l in loglines:
        assert l['module'].startswith(__name__)
        assert 'greenlet_id' in l


# Helper functions for test_log_uncaught_errors


def error_throwing_function():
    raise ValueError


def test_log_uncaught_errors(logfile):
    try:
        error_throwing_function()
    except:
        log_uncaught_errors()

    last_log_entry = json.loads(logfile.readlines()[-1])

    assert 'error' in last_log_entry
    assert 'error_message' in last_log_entry
    assert 'error_tb' in last_log_entry
    error_tb = last_log_entry['error_tb']

    assert 'ValueError' == last_log_entry['error']
    assert 'GreenletExit' not in last_log_entry['error_tb']
    # Check that the traceback is logged. The traceback stored in
    # sys.exc_info() contains an extra entry for the test_log_uncaught_errors
    # frame, so just look for the rest of the traceback.
    tb = sys.exc_info()[2]
    for call in traceback.format_tb(tb)[1:]:
        assert call in error_tb


def test_safe_format_exception():
    try:
        raise ReallyVerboseError()
    except ReallyVerboseError:
        # Check that the stdlib exception formatting would be large
        assert (len('\t'.join(traceback.format_exception(*sys.exc_info()))) >
                2 * MAX_EXCEPTION_LENGTH)
        exc = safe_format_exception(*sys.exc_info())
        # And check that the resulting string is reasonably-sized.
        assert len(exc) < 2 * MAX_EXCEPTION_LENGTH
