import unittest
import os
import sys
import json
import io
import re
from collections import namedtuple
from truffleHogger import truffleHogger


try:
    from mock import patch 
    from mock import MagicMock
except:
    from unittest.mock import patch
    from unittest.mock import MagicMock


class MockArg:
    def __init__(self, git_url, entropy_threshold_base64=4.5, entropy_threshold_hex=3, length_threshold=20):
        self.git_url = git_url
        self.entropy_threshold_base64 = entropy_threshold_base64
        self.entropy_threshold_hex = entropy_threshold_hex
        self.length_threshold = length_threshold


class TestStringMethods(unittest.TestCase):
    def test_regex(self):
        import re
        regexes = truffleHogger.load_regexes()
        # every one of these should match and if any did not, fail the test
        test_strings = [
            'sk_test_4eC39HqLyjWDarjtT1zdp7dc',
            'rk_test_4eC39HqLyjWDarjtT1zdp7dc',
            'ghp_000000000000000000000000000000000000',
            'ghp_ki4gI9AaxP1Tc53PEMmbv4d2NDzzez3fMWop'
            'gho_000000000000000000000000000000000000',
            'gho_ki4gI9AaxP1Tc53PEMmbv4d2NDzzez3fMWop'
            'ghu_000000000000000000000000000000000000',
            'ghu_ki4gI9AaxP1Tc53PEMmbv4d2NDzzez3fMWop'
            'ghs_000000000000000000000000000000000000',
            'ghs_ki4gI9AaxP1Tc53PEMmbv4d2NDzzez3fMWop'
            'ghr_000000000000000000000000000000000000',
            'ghr_ki4gI9AaxP1Tc53PEMmbv4d2NDzzez3fMWop'
        ]
        for test_string in test_strings:
            matches = 0
            for key in regexes:
                found_strings = re.findall(regexes[key], test_string)
                if len(found_strings) > 0:
                    # print(f"regex: {regexes[key]}, found:{found_strings}")
                    matches += 1
            if matches == 0:
                self.fail(f"Expected to find a regex match but could not for {test_string}")

    def test_shannon(self):
        random_stringB64 = "ZWVTjPQSdhwRgl204Hc51YCsritMIzn8B=/p9UyeX7xu6KkAGqfm3FJ+oObLDNEva"
        random_stringHex = "b3A0a1FDfe86dcCE945B72" 
        self.assertGreater(truffleHogger.shannon_entropy(random_stringB64, truffleHogger.BASE64_CHARS), 4.5)
        self.assertGreater(truffleHogger.shannon_entropy(random_stringHex, truffleHogger.HEX_CHARS), 3)

    def test_cloning(self):
        project_path = truffleHogger.clone_git_repo("https://github.com/dxa4481/truffleHog.git")
        license_file = os.path.join(project_path, "LICENSE")
        self.assertTrue(os.path.isfile(license_file))

    def test_unicode_expection(self):
        try:  # TODO: create the unicode test repo programmatically
            mock_arg = MockArg('https://github.com/dxa4481/tst.git')
            truffleHogger.find_strings(mock_arg, mock_arg.git_url)
        except UnicodeEncodeError:
            self.fail("Unicode print error")

    def test_return_correct_commit_hash(self):
        # Start at commit 202564cf776b402800a4aab8bb14fa4624888475, which 
        # is immediately followed by a secret inserting commit:
        # https://github.com/dxa4481/truffleHog/commit/d15627104d07846ac2914a976e8e347a663bbd9b
        since_commit = '202564cf776b402800a4aab8bb14fa4624888475'
        commit_w_secret = 'd15627104d07846ac2914a976e8e347a663bbd9b'
        cross_valdiating_commit_w_secret_comment = 'Oh no a secret file'

        json_result = ''
        if sys.version_info >= (3,):
            tmp_stdout = io.StringIO()
        else:
            tmp_stdout = io.BytesIO()
        bak_stdout = sys.stdout

        # slowly start to modify the signatures to use a param object, hence we must mock it
        mock_arg = MockArg("https://github.com/dxa4481/truffleHog.git")

        # Redirect STDOUT, run scan and re-establish STDOUT
        sys.stdout = tmp_stdout
        try:
            truffleHogger.find_strings(
                mock_arg,
                mock_arg.git_url,
                since_commit=since_commit,
                printJson=True,
                surpress_output=False,
                output_json_stream=True)
        finally:
            sys.stdout = bak_stdout

        json_result_list = tmp_stdout.getvalue().split('\n')
        results = [json.loads(r) for r in json_result_list if bool(r.strip())]
        filtered_results = list(filter(lambda r: r['commitHash'] == commit_w_secret and r['branch'] == 'origin/master', results))
        self.assertEqual(1, len(filtered_results))
        self.assertEqual(commit_w_secret, filtered_results[0]['commitHash'])
        # Additionally, we cross-validate the commit comment matches the expected comment
        self.assertEqual(cross_valdiating_commit_w_secret_comment, filtered_results[0]['commit'].strip())

    @patch('truffleHogger.truffleHogger.clone_git_repo')
    @patch('truffleHogger.truffleHogger.Repo')
    @patch('shutil.rmtree')
    def test_branch(self, rmtree_mock, repo_const_mock, clone_git_repo):
        repo = MagicMock()
        repo_const_mock.return_value = repo

        mock_arg = MockArg("test_repo")
        truffleHogger.find_strings(mock_arg, mock_arg.git_url, branch="testbranch")
        repo.remotes.origin.fetch.assert_called_once_with("testbranch")

    def test_path_included(self):
        Blob = namedtuple('Blob', ('a_path', 'b_path'))
        blobs = {
            'file-root-dir': Blob('file', 'file'),
            'file-sub-dir': Blob('sub-dir/file', 'sub-dir/file'),
            'new-file-root-dir': Blob(None, 'new-file'),
            'new-file-sub-dir': Blob(None, 'sub-dir/new-file'),
            'deleted-file-root-dir': Blob('deleted-file', None),
            'deleted-file-sub-dir': Blob('sub-dir/deleted-file', None),
            'renamed-file-root-dir': Blob('file', 'renamed-file'),
            'renamed-file-sub-dir': Blob('sub-dir/file', 'sub-dir/renamed-file'),
            'moved-file-root-dir-to-sub-dir': Blob('moved-file', 'sub-dir/moved-file'),
            'moved-file-sub-dir-to-root-dir': Blob('sub-dir/moved-file', 'moved-file'),
            'moved-file-sub-dir-to-sub-dir': Blob('sub-dir/moved-file', 'moved/moved-file'),
        }
        src_paths = set(blob.a_path for blob in blobs.values() if blob.a_path is not None)
        dest_paths = set(blob.b_path for blob in blobs.values() if blob.b_path is not None)
        all_paths = src_paths.union(dest_paths)
        all_paths_patterns = [re.compile(re.escape(p)) for p in all_paths]
        overlap_patterns = [re.compile(r'sub-dir/.*'), re.compile(r'moved/'), re.compile(r'[^/]*file$')]
        sub_dirs_patterns = [re.compile(r'.+/.+')]
        deleted_paths_patterns = [re.compile(r'(.*/)?deleted-file$')]
        for name, blob in blobs.items():
            self.assertTrue(truffleHogger.path_included(blob),
                            '{} should be included by default'.format(blob))
            self.assertTrue(truffleHogger.path_included(blob, include_patterns=all_paths_patterns),
                            '{} should be included with include_patterns: {}'.format(blob, all_paths_patterns))
            self.assertFalse(truffleHogger.path_included(blob, exclude_patterns=all_paths_patterns),
                             '{} should be excluded with exclude_patterns: {}'.format(blob, all_paths_patterns))
            self.assertFalse(truffleHogger.path_included(blob,
                                                         include_patterns=all_paths_patterns,
                                                         exclude_patterns=all_paths_patterns),
                             '{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}'.format(
                                 blob, all_paths_patterns, all_paths_patterns))
            self.assertFalse(truffleHogger.path_included(blob,
                                                         include_patterns=overlap_patterns,
                                                         exclude_patterns=all_paths_patterns),
                             '{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}'.format(
                                 blob, overlap_patterns, all_paths_patterns))
            self.assertFalse(truffleHogger.path_included(blob,
                                                         include_patterns=all_paths_patterns,
                                                         exclude_patterns=overlap_patterns),
                             '{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}'.format(
                                 blob, all_paths_patterns, overlap_patterns))
            path = blob.b_path if blob.b_path else blob.a_path
            if '/' in path:
                self.assertTrue(truffleHogger.path_included(blob, include_patterns=sub_dirs_patterns),
                                '{}: inclusion should include sub directory paths: {}'.format(blob, sub_dirs_patterns))
                self.assertFalse(truffleHogger.path_included(blob, exclude_patterns=sub_dirs_patterns),
                                 '{}: exclusion should exclude sub directory paths: {}'.format(blob, sub_dirs_patterns))
            else:
                self.assertFalse(truffleHogger.path_included(blob, include_patterns=sub_dirs_patterns),
                                 '{}: inclusion should exclude root directory paths: {}'.format(blob, sub_dirs_patterns))
                self.assertTrue(truffleHogger.path_included(blob, exclude_patterns=sub_dirs_patterns),
                                '{}: exclusion should include root directory paths: {}'.format(blob, sub_dirs_patterns))
            if name.startswith('deleted-file-'):
                self.assertTrue(truffleHogger.path_included(blob, include_patterns=deleted_paths_patterns),
                                '{}: inclusion should match deleted paths: {}'.format(blob, deleted_paths_patterns))
                self.assertFalse(truffleHogger.path_included(blob, exclude_patterns=deleted_paths_patterns),
                                 '{}: exclusion should match deleted paths: {}'.format(blob, deleted_paths_patterns))



    @patch('truffleHogger.truffleHogger.clone_git_repo')
    @patch('truffleHogger.truffleHogger.Repo')
    @patch('shutil.rmtree')
    def test_repo_path(self, rmtree_mock, repo_const_mock, clone_git_repo):
        mock_arg = MockArg("test_repo")
        truffleHogger.find_strings(mock_arg, mock_arg.git_url, repo_path="test/path/")
        rmtree_mock.assert_not_called()
        clone_git_repo.assert_not_called()

if __name__ == '__main__':
    unittest.main()
