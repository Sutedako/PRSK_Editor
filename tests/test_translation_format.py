import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt5.QtWidgets import QApplication, QTableWidget
from Editor import Editor
from TranslationFormat import parse_v2, is_v2


class TranslationFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.source = [
            dict(speaker='', text='原文', translation_key=('dialog', 2), scenario_id='story'),
            dict(speaker='', text=''),
            dict(speaker='场景', text='横幅', translation_key=('banner', 5)),
            dict(speaker='左上场景', text='地点', translation_key=('marker', 8)),
        ]
        self.content = ('# 注释\r\n@version:2\r\n@scenario:story\r\n'
                        '@marker:008\r\n 地点 \r\n@banner:005\r\n\r\n'
                        '@dialog:2[]\r\n 时间12:30：正文 \r\n# 忽略\r\n'
                        '\r\n\\@正文\r\n\\#正文\r\n\\\\路径\\N\r\n')

    def test_reordering_empty_body_and_escaping(self):
        rows = parse_v2(self.content, 'story', self.source)
        self.assertEqual([row['text'] for row in rows],
                         ['时间12:30：正文', '', '@正文', '#正文', '\\路径\\N', '', '', '地点'])
        self.assertEqual(rows[0]['speaker'], '')
        self.assertTrue(rows[4]['end'])
        self.assertEqual(rows[-1]['idx'], 4)

    def test_invalid_documents(self):
        cases = [
            self.content.replace('@version:2', '@version:3'),
            self.content.replace('@scenario:story', '@scenario:other'),
            self.content.replace('@scenario:story', ''),
            self.content.replace('@marker:008', '@banner:008'),
            self.content.replace('@dialog:2[]', '@dialog:2'),
            self.content.replace('@dialog:2[]', '@dialog:0[]'),
            self.content + '@dialog:002[x]\n重复',
            self.content + '@end\n',
            self.content.replace('@marker:008\r\n 地点 \r\n', ''),
            self.content.replace('@scenario:story', '@scenario:story\n无归属正文'),
            self.content.replace('@scenario:story', '@scenario:story\n@scenario:story'),
        ]
        for content in cases:
            with self.subTest(content=content):
                self.assertTrue(is_v2(content))
                with self.assertRaises(ValueError):
                    parse_v2(content, 'story', self.source)
        with self.assertRaises(ValueError):
            parse_v2(self.content, None, self.source)

    def test_editor_import_is_atomic_and_retains_explicit_empty_rows(self):
        table = QTableWidget(0, 4)
        editor = Editor(table)
        editor.createFile(self.source)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / 'translation.txt'
            path.write_text(self.content, encoding='utf-8-sig', newline='')
            editor.loadFile(0, path)
            self.assertEqual(len(editor.dsttalks), 8)
            self.assertEqual(editor.dsttalks[6]['text'], '')
            before = copy.deepcopy(editor.dsttalks)
            path.write_text(self.content + '@unknown\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                editor.loadFile(0, path)
            self.assertEqual(editor.dsttalks, before)
            editor.resetTalk(1, before)
            self.assertEqual(editor.dsttalks, before)

    def test_legacy_import(self):
        table = QTableWidget(0, 4)
        editor = Editor(table)
        editor.createFile([dict(speaker='初音ミク', text='原文')])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / 'legacy.txt'
            path.write_text('初音未来：译文。', encoding='utf-8')
            editor.loadFile(0, path)
            self.assertEqual(editor.dsttalks[0]['text'], '译文。')


if __name__ == '__main__':
    unittest.main()
