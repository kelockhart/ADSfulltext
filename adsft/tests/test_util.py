import unittest
import os
import re

from adsft import utils
from adsft.tests import test_base
import math

class TestFileStreamInput(test_base.TestUnit):
    """
    Class that tests the FileStreamInput class and its methods.
    """

    def test_file_stream_input_extract_file(self):
        """
        Tests the extract method. It checks that the number of rows extracted
        by the class is actually the number of rows inside the file by
        explicitly opening the file and reading the number of lines.

        :return: no return
        """

        FileInputStream = utils.FileInputStream(self.test_file)
        FileInputStream.extract()

        with open(self.test_file, 'r') as f:
            nor = len(f.readlines())

        self.assertEqual(
            len(FileInputStream.bibcode),
            nor,
            'Did not extract the correct number of records from the input file'
        )

    def test_file_stream_input_extract_list(self):
        """
        Tests the extract method. It checks that it parses the content of the
        file correctly by checking each of the attributes set in the class.

        :return: no return
        """

        FileInputStream = utils.FileInputStream(self.test_file_stub)
        ext = FileInputStream.extract()

        self.assertIn('2015MNRAS.446.4239E', FileInputStream.bibcode)
        self.assertIn(
            os.path.join(self.app.conf['PROJ_HOME'], 'test.pdf'),
            FileInputStream.full_text_path
        )
        self.assertIn('MNRAS', FileInputStream.provider)

    
    def test_trim(self):
        """
        Tests that the trim normalizes the text.
        """
        # non-breakable space
        a = 'a\xc2\xa0b'.decode('utf8')
        b = 'a' + b'\xc2\xa0' + 'b' #utf-8 bytecode
        c = u'a' + u'\xa0' + u'b' # unicode
        d = u'a' + chr(160).decode('latin1') + u'b'
        for x in (a, b, c, d):
            r = utils.TextCleaner(x).run(translate=False, decode=True, normalise=True, trim=True)
            self.assertEqual(r, u'a b')

if __name__ == '__main__':
    unittest.main()