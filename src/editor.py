from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtCore import Qt

Color = {
    'RED': QBrush(QColor(255, 192, 192)),
    'YELLOW': QBrush(QColor(255, 255, 128)),
    'GREEN': QBrush(QColor(128, 255, 128)),
    'BLUE': QBrush(QColor(0, 128, 255)),
    'WHITE': QBrush(QColor(255, 255, 255))
}


class Editor():

    srctalks = []
    talks = []

    translatepath = ""
    proofreadpath = ""
    checkpath = ""
    isProofReading = False
    showDifference = False

    def __init__(self, table=None, srctalks=None):
        self.table = table
        if(srctalks):
            self.loadJson(0, srctalks)

    def createFile(self, srctalks):
        self.srctalks = srctalks
        self.talks = []

        for idx, srctalk in enumerate(self.srctalks):
            subsrctalks = srctalk['text'].split("\n")
            self.talks.append({
                'idx': idx + 1,
                'speaker': srctalk['speaker'],
                'text': '',
                'start': True,
                'end': False,
                'comment': False,
                'warning': False
            })
            if len(subsrctalks) > 1:
                for subsrctalk in subsrctalks[1:]:
                    self.talks.append({
                        'idx': idx + 1,
                        'speaker': srctalk['speaker'],
                        'text': '',
                        'start': False,
                        'end': False,
                        'comment': False,
                        'warning': False
                    })
            self.talks[-1]['end'] = True

    def loadFile(self, filepath):
        srcfile = open(filepath, 'r', encoding='UTF-8')
        lines = srcfile.readlines()

        profile = []
        while lines[0][0] == 'Q' or not lines[0]:
            content = "" if len(lines[0].split(':')) <= 1 else lines[0].split(':')[-1]
            profile.append(content)
            lines.pop(0)

        self.talks = []
        for idx, line in enumerate(lines):
            line = line.replace(":", "：")
            if "：" in line:
                speaker = line.split("：")[0]
                fulltext = line[len(speaker) + 1:]
            else:
                speaker = u"场景" if len(line.strip()) else ""
                fulltext = line.replace(u"场景", "")

            texts = fulltext.split("\\N")
            for iidx, text in enumerate(texts):
                comment = text.split("\\C")[-1] if "\\C" in text else ""
                if comment:
                    text = text.split("\\C")[0]
                talk = {
                    'idx': idx + 1,
                    'speaker': speaker,
                    'text': text.rstrip(),
                    'start': iidx == 0,
                    'end': False,
                    'comment': False,
                    'warning': False,
                }
                self.talks.append(talk)
                if comment:
                    talk_c = {
                        'idx': idx + 1,
                        'speaker': speaker,
                        'text': comment.rstrip(),
                        'start': False,
                        'end': True,
                        'comment': True,
                        'warning': False,
                    }
                    self.talks.append(talk_c)
            if not self.talks[-1]['comment']:
                self.talks[-1]['end'] = True
            else:
                self.talks[-2]['end'] = True
        return profile

    def saveFile(self):
        outTalk = ''
        for talk in self.talks:
            if talk['comment']:
                outTalk = outTalk.rstrip()
                outTalk += '\\C'
            if not talk['speaker']:
                outTalk += '\n'
            elif talk['speaker'] == u'场景':
                outTalk += talk['text'] if talk['text'] else u'场景'
                outTalk += '\n'
            else:
                if talk['start']:
                    outTalk += talk['speaker'] + "："
                outTalk += talk['text'].split("\n")[0]
                if not talk['end']:
                    outTalk += '\\N'
                else:
                    outTalk += '\n'
        outTalk = outTalk.rstrip()
        return outTalk

    def comment(self, row):
        if not self.talks[row - 1]['speaker']:
            return -1
        if self.talks[row - 1]['comment']:
            return row - 1
        if row + 1 < len(self.talks) and self.talks[row]['comment']:
            return row
        self.table.blockSignals(True)
        self.table.insertRow(row)
        self.talks.insert(row, {
            'idx': self.talks[row - 1]['idx'],
            'speaker': self.talks[row - 1]['speaker'],
            'text': '',
            'start': False,
            'end': True,
            'comment': True,
            'warning': False
        })
        self.fillTableLine(row, self.talks[row])
        self.table.blockSignals(False)
        return row

    def fillTableLine(self, row, talk):
        self.table.blockSignals(True)
        if talk['start']:
            self.table.setItem(row, 0, QTableWidgetItem(str(talk['idx'])))
            self.table.setItem(row, 1, QTableWidgetItem(talk['speaker']))
        else:
            self.table.setItem(row, 0, QTableWidgetItem(" "))
            self.table.setItem(row, 1, QTableWidgetItem(" "))
        self.table.setItem(row, 2, QTableWidgetItem(talk['text']))

        if not talk['end']:
            self.table.removeCellWidget(row, 3)
            self.table.setItem(row, 3, QTableWidgetItem("\\N"))

        height = len(talk['text'].split('\n')) - 1
        self.table.setRowHeight(row, 40 + 20 * height)

        for column in range(self.table.columnCount()):
            if self.table.item(row, column) and column != 2:
                self.table.item(row, column).setFlags(Qt.NoItemFlags)

        if talk['comment']:
            self.table.item(row, 2).setBackground(Color['YELLOW'])
        elif talk['warning']:
            self.table.item(row, 2).setBackground(Color['RED'])
        else:
            self.table.item(row, 2).setBackground(Color['WHITE'])

        self.table.blockSignals(False)

    def fillTable(self):
        self.table.setRowCount(0)
        for talk in self.talks:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.fillTableLine(row, talk)

    def changeText(self, item, editormode):
        row = item.row()
        column = item.column()
        speaker = self.talks[row]['speaker']
        text = item.text()
        check = True
        if not self.talks[row]['comment']:
            text, check = self.checkText(speaker, text)
        if len(text.split("\n")) > 1:
            check = False

        if not self.talks[row]['speaker']:
            self.table.item(row, column).setText("")
            return

        self.talks[row]['text'] = text
        self.talks[row]['warning'] = not check
        self.fillTableLine(row, self.talks[row])

        if row < self.table.rowCount():
            nextItem = self.table.item(row + 1, column)
            self.table.setCurrentItem(nextItem)
            self.table.editItem(nextItem)

    def checkText(self, speaker, text):
        check = True
        if (speaker not in ["", u"场景"]) and (not text):
            text += "\n【空行，若不需要改行请点右侧“-”删去本行】"
            return text, check
        text = text.split("\n")[0].rstrip().lstrip()
        if not text:
            return text, check

        if speaker in [u'场景', '']:
            return text, check

        text = text.replace('…', '...')
        text = text.replace('(', '（')
        text = text.replace(')', '）')
        text = text.replace(',', '，')
        text = text.replace('?', '？')
        text = text.replace('!', '！')
        text = text.replace('欸', '诶')

        normalend = ['、', '，', '。', '？', '！', '~', '♪', '☆', '.', '—']
        unusualend = ['）', '」', '』', '”']
        if text[-1] in normalend:
            if '.，' in text or '.。' in text:
                text += "\n【「……。」和「……，」只保留省略号】"
                check = False
        elif text[-1] in unusualend:
            if len(text) > 1 and text[-2] not in normalend:
                text += "\n【句尾缺少逗号句号】"
                check = False
        else:
            text += "\n【句尾缺少逗号句号】"
            check = False

        if "—" in text:
            if len(text.split("—")) != len(text.split("——")) * 2 - 1:
                text += "\n【破折号用双破折——，或者视情况删掉】"
                check = False

        if len(text.split("\n")[0].replace('...', '…')) >= 30:
            text += "\n【单行过长，请删减或换行】"
            check = False

        return text, check
