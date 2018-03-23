# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Bo Maryniuk <bo@suse.de>`
'''
from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
from tests.support.unit import TestCase, skipIf
from tests.support.mock import (
    NO_MOCK,
    NO_MOCK_REASON,
    MagicMock,
    patch)

import salt.exceptions
from salt.utils import thin
from salt.utils import json
import salt.utils.stringutils
from salt.utils.stringutils import to_bytes as bts

try:
    import pytest
except ImportError:
    pytest = None


@skipIf(NO_MOCK, NO_MOCK_REASON)
@skipIf(pytest is None, 'PyTest is missing')
class SSHThinTestCase(TestCase):
    '''
    TestCase for SaltSSH-related parts.
    '''

    def _popen(self, return_value=None, side_effect=None, returncode=0):
        '''
        Fake subprocess.Popen
        :return:
        '''

        proc = MagicMock()
        proc.communicate = MagicMock(return_value=return_value, side_effect=side_effect)
        proc.returncode = returncode
        popen = MagicMock(return_value=proc)

        return popen

    def _version_info(self, major=None, minor=None):
        '''
        Fake version info.

        :param major:
        :param minor:
        :return:
        '''
        class VersionInfo(tuple):
            pass

        vi = VersionInfo([major, minor])
        vi.major = major or sys.version_info.major
        vi.minor = minor or sys.version_info.minor

        return vi

    def _tarfile(self, getinfo=False):
        '''
        Fake tarfile handler.

        :return:
        '''
        spec = ['add', 'close']
        if getinfo:
            spec.append('getinfo')

        tf = MagicMock()
        tf.open = MagicMock(return_value=MagicMock(spec=spec))

        return tf


    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=False))
    def test_get_ext_tops_cfg_missing_dependencies(self):
        '''
        Test thin.get_ext_tops contains all required dependencies.

        :return:
        '''
        cfg = {'namespace': {'py-version': [0, 0], 'path': '/foo', 'dependencies': []}}

        with pytest.raises(Exception) as err:
            thin.get_ext_tops(cfg)
        assert 'Missing dependencies' in str(err)
        assert thin.log.error.called
        assert 'Missing dependencies' in thin.log.error.call_args[0][0]
        assert 'jinja2, yaml, tornado, msgpack' in thin.log.error.call_args[0][0]

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=False))
    def test_get_ext_tops_cfg_missing_interpreter(self):
        '''
        Test thin.get_ext_tops contains interpreter configuration.

        :return:
        '''
        cfg = {'namespace': {'path': '/foo',
                             'dependencies': []}}
        with pytest.raises(salt.exceptions.SaltSystemExit) as err:
            thin.get_ext_tops(cfg)
        assert 'missing specific locked Python version' in str(err)

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=False))
    def test_get_ext_tops_cfg_wrong_interpreter(self):
        '''
        Test thin.get_ext_tops contains correct interpreter configuration.

        :return:
        '''
        cfg = {'namespace': {'path': '/foo',
                             'py-version': 2,
                             'dependencies': []}}

        with pytest.raises(salt.exceptions.SaltSystemExit) as err:
            thin.get_ext_tops(cfg)
        assert 'specific locked Python version should be a list of major/minor version' in str(err)

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=False))
    def test_get_ext_tops_cfg_interpreter(self):
        '''
        Test thin.get_ext_tops interpreter configuration.

        :return:
        '''
        cfg = {'namespace': {'path': '/foo',
                             'py-version': [2, 6],
                             'dependencies': {'jinja2': '',
                                              'yaml': '',
                                              'tornado': '',
                                              'msgpack': ''}}}

        with pytest.raises(salt.exceptions.SaltSystemExit):
            thin.get_ext_tops(cfg)
        assert len(thin.log.warning.mock_calls) == 4
        assert sorted([x[1][1] for x in thin.log.warning.mock_calls]) == ['jinja2', 'msgpack', 'tornado', 'yaml']
        assert 'Module test has missing configuration' == thin.log.warning.mock_calls[0][1][0] % 'test'

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=False))
    def test_get_ext_tops_dependency_config_check(self):
        '''
        Test thin.get_ext_tops dependencies are importable

        :return:
        '''
        cfg = {'namespace': {'path': '/foo',
                             'py-version': [2, 6],
                             'dependencies': {'jinja2': '/jinja/foo.py',
                                              'yaml': '/yaml/',
                                              'tornado': '/tornado/wrong.rb',
                                              'msgpack': 'msgpack.sh'}}}

        with pytest.raises(salt.exceptions.SaltSystemExit) as err:
            thin.get_ext_tops(cfg)
        assert 'Missing dependencies for the alternative version in the external configuration' in str(err)

        messages = {}
        for cl in thin.log.warning.mock_calls:
            messages[cl[1][1]] = cl[1][0] % (cl[1][1], cl[1][2])
        for mod in ['tornado', 'yaml', 'msgpack']:
            assert 'not a Python importable module' in messages[mod]
        assert 'configured with not a file or does not exist' in messages['jinja2']

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.path.isfile', MagicMock(return_value=True))
    def test_get_ext_tops_config_pass(self):
        '''
        Test thin.get_ext_tops configuration

        :return:
        '''
        cfg = {'namespace': {'path': '/foo',
                             'py-version': [2, 6],
                             'dependencies': {'jinja2': '/jinja/foo.py',
                                              'yaml': '/yaml/',
                                              'tornado': '/tornado/tornado.py',
                                              'msgpack': 'msgpack.py'}}}
        assert cfg == thin.get_ext_tops(cfg)

    @patch('salt.utils.thin.sys.argv', [None, '{"foo": "bar"}'])
    @patch('salt.utils.thin.get_tops', lambda **kw: kw)
    def test_gte(self):
        '''
        Test thin.gte external call for processing the info about tops per interpreter.

        :return:
        '''
        assert json.loads(thin.gte()).get('foo') == 'bar'

    def test_add_dep_path(self):
        '''
        Test thin._add_dependency function to setup dependency paths
        :return:
        '''
        container = []
        for pth in ['/foo/bar.py', '/something/else/__init__.py']:
            thin._add_dependency(container, type(str('obj'), (), {'__file__': pth})())
        assert '__init__' not in container[1]
        assert container == ['/foo/bar.py', '/something/else']

    def test_thin_path(self):
        '''
        Test thin.thin_path returns the expected path.

        :return:
        '''
        assert thin.thin_path('/path/to') == '/path/to/thin/thin.tgz'

    def test_get_salt_call_script(self):
        '''
        Test get salt-call script rendered.

        :return:
        '''
        out = thin._get_salt_call('foo', 'bar', py26=[2, 6], py27=[2, 7], py34=[3, 4])
        for line in salt.utils.stringutils.to_str(out).split(os.linesep):
            if line.startswith('namespaces = {'):
                data = json.loads(line.replace('namespaces = ', '').strip())
                assert data.get('py26') == [2, 6]
                assert data.get('py27') == [2, 7]
                assert data.get('py34') == [3, 4]
            if line.startswith('syspaths = '):
                data = json.loads(line.replace('syspaths = ', ''))
                assert data == ['foo', 'bar']

    def test_get_ext_namespaces_empty(self):
        '''
        Test thin._get_ext_namespaces function returns an empty dictionary on nothing
        :return:
        '''
        for obj in [None, {}, []]:
            assert thin._get_ext_namespaces(obj) == {}

    def test_get_ext_namespaces(self):
        '''
        Test thin._get_ext_namespaces function returns namespaces properly out of the config.
        :return:
        '''
        cfg = {'ns': {'py-version': [2, 7]}}
        assert thin._get_ext_namespaces(cfg).get('ns') == (2, 7,)
        assert isinstance(thin._get_ext_namespaces(cfg).get('ns'), tuple)

    def test_get_ext_namespaces_failure(self):
        '''
        Test thin._get_ext_namespaces function raises an exception
        if python major/minor version is not configured.
        :return:
        '''
        with pytest.raises(salt.exceptions.SaltSystemExit):
            thin._get_ext_namespaces({'ns': {}})

    @patch('salt.utils.thin.salt', type(str('salt'), (), {'__file__': '/site-packages/salt'}))
    @patch('salt.utils.thin.jinja2', type(str('jinja2'), (), {'__file__': '/site-packages/jinja2'}))
    @patch('salt.utils.thin.yaml', type(str('yaml'), (), {'__file__': '/site-packages/yaml'}))
    @patch('salt.utils.thin.tornado', type(str('tornado'), (), {'__file__': '/site-packages/tornado'}))
    @patch('salt.utils.thin.msgpack', type(str('msgpack'), (), {'__file__': '/site-packages/msgpack'}))
    @patch('salt.utils.thin.certifi', type(str('certifi'), (), {'__file__': '/site-packages/certifi'}))
    @patch('salt.utils.thin.singledispatch', type(str('singledispatch'), (), {'__file__': '/site-packages/sdp'}))
    @patch('salt.utils.thin.singledispatch_helpers', type(str('singledispatch_helpers'), (), {'__file__': '/site-packages/sdp_hlp'}))
    @patch('salt.utils.thin.ssl_match_hostname', type(str('ssl_match_hostname'), (), {'__file__': '/site-packages/ssl_mh'}))
    @patch('salt.utils.thin.markupsafe', type(str('markupsafe'), (), {'__file__': '/site-packages/markupsafe'}))
    @patch('salt.utils.thin.backports_abc', type(str('backports_abc'), (), {'__file__': '/site-packages/backports_abc'}))
    @patch('salt.utils.thin.log', MagicMock())
    def test_get_tops(self):
        '''
        Test thin.get_tops to get top directories, based on the interpreter.
        :return:
        '''
        base_tops = ['/site-packages/salt', '/site-packages/jinja2', '/site-packages/yaml',
                     '/site-packages/tornado', '/site-packages/msgpack', '/site-packages/certifi',
                     '/site-packages/sdp', '/site-packages/sdp_hlp', '/site-packages/ssl_mh',
                     '/site-packages/markupsafe', '/site-packages/backports_abc']

        tops = thin.get_tops()
        assert len(tops) == len(base_tops)
        assert sorted(tops) == sorted(base_tops)

    @patch('salt.utils.thin.salt', type(str('salt'), (), {'__file__': '/site-packages/salt'}))
    @patch('salt.utils.thin.jinja2', type(str('jinja2'), (), {'__file__': '/site-packages/jinja2'}))
    @patch('salt.utils.thin.yaml', type(str('yaml'), (), {'__file__': '/site-packages/yaml'}))
    @patch('salt.utils.thin.tornado', type(str('tornado'), (), {'__file__': '/site-packages/tornado'}))
    @patch('salt.utils.thin.msgpack', type(str('msgpack'), (), {'__file__': '/site-packages/msgpack'}))
    @patch('salt.utils.thin.certifi', type(str('certifi'), (), {'__file__': '/site-packages/certifi'}))
    @patch('salt.utils.thin.singledispatch', type(str('singledispatch'), (), {'__file__': '/site-packages/sdp'}))
    @patch('salt.utils.thin.singledispatch_helpers', type(str('singledispatch_helpers'), (), {'__file__': '/site-packages/sdp_hlp'}))
    @patch('salt.utils.thin.ssl_match_hostname', type(str('ssl_match_hostname'), (), {'__file__': '/site-packages/ssl_mh'}))
    @patch('salt.utils.thin.markupsafe', type(str('markupsafe'), (), {'__file__': '/site-packages/markupsafe'}))
    @patch('salt.utils.thin.backports_abc', type(str('backports_abc'), (), {'__file__': '/site-packages/backports_abc'}))
    @patch('salt.utils.thin.log', MagicMock())
    def test_get_tops_extra_mods(self):
        '''
        Test thin.get_tops to get extra-modules alongside the top directories, based on the interpreter.
        :return:
        '''
        base_tops = ['/site-packages/salt', '/site-packages/jinja2', '/site-packages/yaml',
                     '/site-packages/tornado', '/site-packages/msgpack', '/site-packages/certifi',
                     '/site-packages/sdp', '/site-packages/sdp_hlp', '/site-packages/ssl_mh',
                     '/site-packages/markupsafe', '/site-packages/backports_abc', '/custom/foo', '/custom/bar.py']
        builtins = sys.version_info.major == 3 and 'builtins' or '__builtin__'
        with patch('{}.__import__'.format(builtins),
                   MagicMock(side_effect=[type(str('foo'), (), {'__file__': '/custom/foo/__init__.py'}),
                                          type(str('bar'), (), {'__file__': '/custom/bar'})])):
            tops = thin.get_tops(extra_mods='foo,bar')
        assert len(tops) == len(base_tops)
        assert sorted(tops) == sorted(base_tops)

    @patch('salt.utils.thin.salt', type(str('salt'), (), {'__file__': '/site-packages/salt'}))
    @patch('salt.utils.thin.jinja2', type(str('jinja2'), (), {'__file__': '/site-packages/jinja2'}))
    @patch('salt.utils.thin.yaml', type(str('yaml'), (), {'__file__': '/site-packages/yaml'}))
    @patch('salt.utils.thin.tornado', type(str('tornado'), (), {'__file__': '/site-packages/tornado'}))
    @patch('salt.utils.thin.msgpack', type(str('msgpack'), (), {'__file__': '/site-packages/msgpack'}))
    @patch('salt.utils.thin.certifi', type(str('certifi'), (), {'__file__': '/site-packages/certifi'}))
    @patch('salt.utils.thin.singledispatch', type(str('singledispatch'), (), {'__file__': '/site-packages/sdp'}))
    @patch('salt.utils.thin.singledispatch_helpers', type(str('singledispatch_helpers'), (), {'__file__': '/site-packages/sdp_hlp'}))
    @patch('salt.utils.thin.ssl_match_hostname', type(str('ssl_match_hostname'), (), {'__file__': '/site-packages/ssl_mh'}))
    @patch('salt.utils.thin.markupsafe', type(str('markupsafe'), (), {'__file__': '/site-packages/markupsafe'}))
    @patch('salt.utils.thin.backports_abc', type(str('backports_abc'), (), {'__file__': '/site-packages/backports_abc'}))
    @patch('salt.utils.thin.log', MagicMock())
    def test_get_tops_so_mods(self):
        '''
        Test thin.get_tops to get extra-modules alongside the top directories, based on the interpreter.
        :return:
        '''
        base_tops = ['/site-packages/salt', '/site-packages/jinja2', '/site-packages/yaml',
                     '/site-packages/tornado', '/site-packages/msgpack', '/site-packages/certifi',
                     '/site-packages/sdp', '/site-packages/sdp_hlp', '/site-packages/ssl_mh',
                     '/site-packages/markupsafe', '/site-packages/backports_abc', '/custom/foo.so', '/custom/bar.so']
        builtins = sys.version_info.major == 3 and 'builtins' or '__builtin__'
        with patch('{}.__import__'.format(builtins),
                   MagicMock(side_effect=[type(str('salt'), (), {'__file__': '/custom/foo.so'}),
                                          type(str('salt'), (), {'__file__': '/custom/bar.so'})])):
            tops = thin.get_tops(so_mods='foo,bar')
        assert len(tops) == len(base_tops)
        assert sorted(tops) == sorted(base_tops)

    @patch('salt.utils.thin.gen_thin', MagicMock(return_value='/path/to/thin/thin.tgz'))
    @patch('salt.utils.hashutils.get_hash', MagicMock(return_value=12345))
    def test_thin_sum(self):
        '''
        Test thin.thin_sum function.

        :return:
        '''
        assert thin.thin_sum('/cachedir', form='sha256') == 12345
        thin.salt.utils.hashutils.get_hash.assert_called()
        assert thin.salt.utils.hashutils.get_hash.call_count == 1

        path, form = thin.salt.utils.hashutils.get_hash.call_args[0]
        assert path == '/path/to/thin/thin.tgz'
        assert form == 'sha256'

    @patch('salt.utils.thin.gen_min', MagicMock(return_value='/path/to/thin/min.tgz'))
    @patch('salt.utils.hashutils.get_hash', MagicMock(return_value=12345))
    def test_min_sum(self):
        '''
        Test thin.thin_sum function.

        :return:
        '''
        assert thin.min_sum('/cachedir', form='sha256') == 12345
        thin.salt.utils.hashutils.get_hash.assert_called()
        assert thin.salt.utils.hashutils.get_hash.call_count == 1

        path, form = thin.salt.utils.hashutils.get_hash.call_args[0]
        assert path == '/path/to/thin/min.tgz'
        assert form == 'sha256'

    @patch('salt.utils.thin.sys.version_info', (2, 5))
    @patch('salt.exceptions.SaltSystemExit', Exception)
    def test_gen_thin_fails_ancient_python_version(self):
        '''
        Test thin.gen_thin function raises an exception
        if Python major/minor version is lower than 2.6

        :return:
        '''
        with pytest.raises(salt.exceptions.SaltSystemExit) as err:
            thin.sys.exc_clear = lambda: None
            thin.gen_thin('')
        assert 'The minimum required python version to run salt-ssh is "2.6"' in str(err)

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.makedirs', MagicMock())
    @patch('salt.utils.files.fopen', MagicMock())
    @patch('salt.utils.thin._get_salt_call', MagicMock())
    @patch('salt.utils.thin._get_ext_namespaces', MagicMock())
    @patch('salt.utils.thin.get_tops', MagicMock(return_value=['/foo3', '/bar3']))
    @patch('salt.utils.thin.os.path.isfile', MagicMock())
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.remove', MagicMock())
    @patch('salt.utils.thin.os.path.exists', MagicMock())
    @patch('salt.utils.path.os_walk', MagicMock())
    @patch('salt.utils.thin.subprocess.Popen',
           _popen(None, side_effect=[(bts('2.7'), bts('')), (bts('["/foo27", "/bar27"]'), bts(''))]))
    @patch('salt.utils.thin.tarfile', MagicMock())
    @patch('salt.utils.thin.zipfile', MagicMock())
    @patch('salt.utils.thin.os.getcwd', MagicMock())
    @patch('salt.utils.thin.os.chdir', MagicMock())
    @patch('salt.utils.thin.tempfile', MagicMock())
    @patch('salt.utils.thin.shutil', MagicMock())
    @patch('salt.utils.thin._six.PY3', True)
    @patch('salt.utils.thin._six.PY2', False)
    @patch('salt.utils.thin.sys.version_info', _version_info(None, 3, 6))
    def test_gen_thin_compression_fallback_py3(self):
        '''
        Test thin.gen_thin function if fallbacks to the gzip compression, once setup wrong.
        NOTE: Py2 version of this test is not required, as code shares the same spot across the versions.

        :return:
        '''
        thin.gen_thin('', compress='arj')
        thin.log.warning.assert_called()
        pt, msg = thin.log.warning.mock_calls[0][1]
        assert pt % msg == 'Unknown compression type: "arj". Falling back to "gzip" compression.'
        thin.zipfile.ZipFile.assert_not_called()
        thin.tarfile.open.assert_called()

    @patch('salt.exceptions.SaltSystemExit', Exception)
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.makedirs', MagicMock())
    @patch('salt.utils.files.fopen', MagicMock())
    @patch('salt.utils.thin._get_salt_call', MagicMock())
    @patch('salt.utils.thin._get_ext_namespaces', MagicMock())
    @patch('salt.utils.thin.get_tops', MagicMock(return_value=['/foo3', '/bar3']))
    @patch('salt.utils.thin.os.path.isfile', MagicMock())
    @patch('salt.utils.thin.log', MagicMock())
    @patch('salt.utils.thin.os.remove', MagicMock())
    @patch('salt.utils.thin.os.path.exists', MagicMock())
    @patch('salt.utils.path.os_walk', MagicMock())
    @patch('salt.utils.thin.subprocess.Popen',
           _popen(None, side_effect=[(bts('2.7'), bts('')), (bts('["/foo27", "/bar27"]'), bts(''))]))
    @patch('salt.utils.thin.tarfile', MagicMock())
    @patch('salt.utils.thin.zipfile', MagicMock())
    @patch('salt.utils.thin.os.getcwd', MagicMock())
    @patch('salt.utils.thin.os.chdir', MagicMock())
    @patch('salt.utils.thin.tempfile', MagicMock())
    @patch('salt.utils.thin.shutil', MagicMock())
    @patch('salt.utils.thin._six.PY3', True)
    @patch('salt.utils.thin._six.PY2', False)
    @patch('salt.utils.thin.sys.version_info', _version_info(None, 3, 6))
    def test_gen_thin_control_files_written_py3(self):
        '''
        Test thin.gen_thin function if control files are written (version, salt-call etc).
        NOTE: Py2 version of this test is not required, as code shares the same spot across the versions.

        :return:
        '''
        thin.gen_thin('')
        thin.tarfile.open().close.assert_called()
        arc_name, arc_mode = thin.tarfile.method_calls[0][1]
        assert arc_name == 'thin/thin.tgz'
        assert arc_mode == 'w:gz'
        for idx, fname in enumerate(['salt-call', 'version', '.thin-gen-py-version']):
            assert thin.tarfile.open().method_calls[idx + 4][1][0] == fname
