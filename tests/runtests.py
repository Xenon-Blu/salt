#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Discover all instances of unittest.TestCase in this directory.
'''
# Import python libs
import sys
import os
import logging
import optparse
import resource

# Import salt libs
try:
    import console
    width, height = console.getTerminalSize()
    PNUM = width
except:
    PNUM = 70
import saltunittest
from integration import TestDaemon

try:
    import xmlrunner
except ImportError:
    pass

TEST_DIR = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

REQUIRED_OPEN_FILES = 2048

TEST_RESULTS = []


def print_header(header, sep='~', top=True, bottom=True, inline=False,
                 centered=False):
    if top and not inline:
        print(sep * PNUM)

    if centered and not inline:
        fmt = u'{0:^{width}}'
    elif inline and not centered:
        fmt = u'{0:{sep}<{width}}'
    elif inline and centered:
        fmt = u'{0:{sep}^{width}}'
    else:
        fmt = u'{0}'
    print(fmt.format(header, sep=sep, width=PNUM))

    if bottom and not inline:
        print(sep * PNUM)


def run_suite(opts, path, display_name, suffix='[!_]*.py'):
    '''
    Execute a unit test suite
    '''
    loader = saltunittest.TestLoader()
    if opts.name:
        tests = loader.loadTestsFromName(display_name)
    else:
        tests = loader.discover(path, suffix, TEST_DIR)

    header = '{0} Tests'.format(display_name)
    print_header('Starting {0}'.format(header))

    if opts.xmlout:
        runner = xmlrunner.XMLTestRunner(output='test-reports').run(tests)
    else:
        runner = saltunittest.TextTestRunner(
            verbosity=opts.verbosity
        ).run(tests)
        TEST_RESULTS.append((header, runner))
    return runner.wasSuccessful()


def run_integration_suite(opts, suite_folder, display_name):
    '''
    Run an integration test suite
    '''
    path = os.path.join(TEST_DIR, 'integration', suite_folder)
    return run_suite(opts, path, display_name)


def run_integration_tests(opts):
    '''
    Execute the integration tests suite
    '''
    smax_open_files, hmax_open_files = resource.getrlimit(resource.RLIMIT_NOFILE)
    if smax_open_files < REQUIRED_OPEN_FILES:
        print('~' * PNUM)
        print('Max open files setting is too low({0}) for running the tests'.format(smax_open_files))
        print('Trying to raise the limit to {0}'.format(REQUIRED_OPEN_FILES))
        if hmax_open_files < 4096:
            hmax_open_files = 4096  # Decent default?
        try:
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (REQUIRED_OPEN_FILES, hmax_open_files)
            )
        except Exception, err:
            print('ERROR: Failed to raise the max open files setting -> {0}'.format(err))
            print('Please issue the following command on your console:')
            print('  ulimit -n {0}'.format(REQUIRED_OPEN_FILES))
            sys.exit(1)
        finally:
            print('~' * PNUM)

    print_header('Setting up Salt daemons to execute tests')
    status = []
    if not any([opts.client, opts.module, opts.runner,
                opts.shell, opts.state, opts.name]):
        return status
    with TestDaemon(clean=opts.clean):
        if opts.name:
            for name in opts.name:
                results = run_suite(opts, '', name)
                status.append(results)
        if opts.runner:
            status.append(run_integration_suite(opts, 'runners', 'Runner'))
        if opts.module:
            status.append(run_integration_suite(opts, 'modules', 'Module'))
        if opts.state:
            status.append(run_integration_suite(opts, 'states', 'State'))
        if opts.client:
            status.append(run_integration_suite(opts, 'client', 'Client'))
        if opts.shell:
            status.append(run_integration_suite(opts, 'shell', 'Shell'))
    return status


def run_unit_tests(opts):
    '''
    Execute the unit tests
    '''
    if not opts.unit:
        return [True]
    status = []
    results = run_suite(
        opts, os.path.join(TEST_DIR, 'unit'), 'Unit', '*_test.py')
    status.append(results)
    return status


def parse_opts():
    '''
    Parse command line options for running specific tests
    '''
    parser = optparse.OptionParser()
    parser.add_option('-m',
            '--module',
            '--module-tests',
            dest='module',
            default=False,
            action='store_true',
            help='Run tests for modules')
    parser.add_option('-S',
            '--state',
            '--state-tests',
            dest='state',
            default=False,
            action='store_true',
            help='Run tests for states')
    parser.add_option('-c',
            '--client',
            '--client-tests',
            dest='client',
            default=False,
            action='store_true',
            help='Run tests for client')
    parser.add_option('-s',
            '--shell',
            dest='shell',
            default=False,
            action='store_true',
            help='Run shell tests')
    parser.add_option('-r',
            '--runner',
            dest='runner',
            default=False,
            action='store_true',
            help='Run runner tests')
    parser.add_option('-u',
            '--unit',
            '--unit-tests',
            dest='unit',
            default=False,
            action='store_true',
            help='Run unit tests')
    parser.add_option('-v',
            '--verbose',
            dest='verbosity',
            default=1,
            action='count',
            help='Verbose test runner output')
    parser.add_option('-x',
            '--xml',
            dest='xmlout',
            default=False,
            action='store_true',
            help='XML test runner output')
    parser.add_option('-n',
            '--name',
            dest='name',
            action='append',
            default=[],
            help='Specific test name to run')
    parser.add_option('--clean',
            dest='clean',
            default=True,
            action='store_true',
            help=('Clean up test environment before and after '
                  'integration testing (default behaviour)'))
    parser.add_option('--no-clean',
            dest='clean',
            action='store_false',
            help=('Don\'t clean up test environment before and after '
                  'integration testing (speed up test process)'))
    parser.add_option('--no-report',
            default=False,
            action='store_true',
            help='Do NOT show the overall tests result'
    )

    options, _ = parser.parse_args()

    # Setup minimal logging to stop errors and use if greater verbosity is used
    if options.verbosity > 2:
        # -vv
        level = logging.INFO
        if options.verbosity > 3:
            # -vvv
            level = logging.DEBUG
        logging.basicConfig(
            stream=sys.stderr, level=level,
            format="[%(levelname)-8s][%(name)-10s:%(lineno)-4d] %(message)s"
        )
    else:
        logging.basicConfig(stream=open(os.devnull, 'w'), level=0)

    if not any((options.module, options.client,
                options.shell, options.unit,
                options.state, options.runner,
                options.name)):
        options.module = True
        options.client = True
        options.shell = True
        options.unit = True
        options.runner = True
        options.state = True
    return options


if __name__ == '__main__':
    opts = parse_opts()
    overall_status = []
    status = run_integration_tests(opts)
    overall_status.extend(status)
    status = run_unit_tests(opts)
    overall_status.extend(status)
    false_count = overall_status.count(False)

    show_report = False
    for (name, results) in TEST_RESULTS:
        if results.failures or results.errors or results.skipped:
            show_report = True
            break

    if opts.no_report or not show_report:
        if false_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)


    print('')
    print_header(u'  Overall Tests Resume  ', sep=u'=', centered=True, inline=True)


    for (name, results) in TEST_RESULTS:
        if not results.failures and not results.errors and not results.skipped:
            continue

        print_header(u'\u22c6\u22c6\u22c6 {0}  '.format(name), sep=u'\u22c6', inline=True)
        if results.skipped:
            print_header(u' --------  Skipped Tests  ', sep='-', inline=True)
            maxlen = len(max([tc.id() for (tc, reason) in results.skipped], key=len))
            fmt = u'   \u2192 {0: <{maxlen}}  \u2192  {1}'
            for tc, reason in results.skipped:
                print(fmt.format(tc.id(), reason, maxlen=maxlen))
            print_header(u' ', sep='-', inline=True)

        if results.errors:
            print_header(u' --------  Tests with Errors  ', sep='-', inline=True)
            for tc, reason in results.errors:
                print_header(u'   \u2192 {0}  '.format(tc.id()), sep=u'.', inline=True)
                for line in reason.rstrip().splitlines():
                    print('       {0}'.format(line.rstrip()))
                print_header(u'   ', sep=u'.', inline=True)
            print_header(u' ', sep='-', inline=True)

        if results.failures:
            print_header(u' --------  Failed Tests  ', sep='-', inline=True)
            for tc, reason in results.failures:
                print_header(u'   \u2192 {0}  '.format(tc.id()), sep=u'.', inline=True)
                for line in reason.rstrip().splitlines():
                    print('       {0}'.format(line.rstrip()))
                print_header(u'   ', sep=u'.', inline=True)
            print_header(u' ', sep='-', inline=True)

        print_header(u'', sep=u'\u22c6', inline=True)

    print_header('  Overall Tests Resume  ', sep='=', centered=True, inline=True)

    if false_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)
