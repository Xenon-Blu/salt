# -*- coding: utf-8 -*-

# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import os
import textwrap

# Import Salt Testing libs
from tests.support.case import ModuleCase
from tests.support.unit import skipIf
from tests.support.helpers import destructiveTest
from tests.support.runtests import RUNTIME_VARS

# Import Salt libs
import salt.utils.files
import salt.utils.platform

REPO_DIR = os.path.join(RUNTIME_VARS.FILES, 'file', 'base', 'win', 'repo-ng')
CURL = os.path.join(REPO_DIR, 'curl.sls')


@skipIf(not salt.utils.platform.is_windows(), 'windows test only')
class WinPKGTest(ModuleCase):
    '''
    Tests for salt.modules.win_pkg. There are already
    some pkg execution module tests in the the test
    integration.modules.test_pkg but this will be for
    specific windows software respository tests while
    using the win_pkg module.
    '''
    @destructiveTest
    def test_adding_removing_pkg_sls(self):
        '''
        Test add and removing a new pkg sls
        in the windows software repository
        '''
        def _check_pkg(pkgs, exists=True, check_refresh=None):
            refresh = self.run_function('pkg.refresh_db')
            if check_refresh:
                count = 2
                while count != 0:
                    try:
                        self.assertEqual(0, refresh['failed'],
                             msg='failed returned {0}. Expected return: 0'.format(refresh['failed']))
                        self.assertEqual(check_refresh, refresh['total'],
                             msg='total returned {0}. Expected return {1}'.format(check_refresh, refresh['total']))
                        self.assertEqual(check_refresh, refresh['success'],
                             msg='success returned {0}. Expected return {1}'.format(check_refresh, refresh['success']))
                        count = 0
                    except AssertionError as err:
                        if count == 1:
                            raise AssertionError(err)
                        count = count -1
                        refresh = self.run_function('pkg.refresh_db')
            repo_data = self.run_function('pkg.get_repo_data', timeout=300)
            repo_cache = os.path.join(RUNTIME_VARS.TMP, 'rootdir', 'cache', 'files', 'base', 'win', 'repo-ng')
            for pkg in pkgs:
                if exists:
                    assert pkg in str(repo_data), str(repo_data)
                else:
                    assert pkg not in str(repo_data), str(repo_data)

                for root, dirs, files in os.walk(repo_cache):
                    if exists:
                        assert pkg + '.sls' in files
                    else:
                        assert pkg + '.sls' not in files

        pkgs = ['putty', '7zip']
        # check putty and 7zip are in cache and repo query
        _check_pkg(pkgs)

        # now add new sls
        with salt.utils.files.fopen(CURL, 'w') as fp_:
            fp_.write(textwrap.dedent('''
                curl:
                  '7.46.0':
                    full_name: 'cURL'
                    {% if grains['cpuarch'] == 'AMD64' %}
                    installer: 'salt://win/repo-ng/curl/curl-7.46.0-win64.msi'
                    uninstaller: 'salt://win/repo-ng/curl/curl-7.46.0-win64.msi'
                    {% else %}
                    installer: 'salt://win/repo-ng/curl/curl-7.46.0-win32.msi'
                    uninstaller: 'salt://win/repo-ng/curl/curl-7.46.0-win32.msi'
                    {% endif %}
                    install_flags: '/qn /norestart'
                    uninstall_flags: '/qn /norestart'
                    msiexec: True
                    locale: en_US
                    reboot: False
                '''))
        # now check if curl is also in cache and repo query
        pkgs.append('curl')
        for pkg in pkgs:
            self.assertIn(pkg + '.sls', os.listdir(REPO_DIR))
        _check_pkg(pkgs, check_refresh=3)

        # remove curl sls and check its not in cache and repo query
        os.remove(CURL)
        _check_pkg(['curl'], exists=False)

    def tearDown(self):
        if os.path.isfile(CURL):
            os.remove(CURL)
