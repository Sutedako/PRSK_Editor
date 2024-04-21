from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QPushButton, QCheckBox, QHBoxLayout, QMenu
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtCore import Qt, QSize
import copy

from Dictionary import characterDict

Color = {
    'RED': QBrush(QColor(255, 192, 192, 192)),
    'YELLOW': QBrush(QColor(255, 255, 128, 192)),
    'GREEN': QBrush(QColor(128, 255, 128, 192)),
    'BLUE': QBrush(QColor(0, 128, 255, 192)),
    'WHITE': QBrush(QColor(255, 255, 255, 0))
}


class Editor():
    def __init__(self, table=None, srctalks=None, fontSize=18, realignHook = None):
        self.talks = []

        self.srctalks = []
        self.refertalks = []
        self.dsttalks = []

        self.translatepath = ""
        self.proofreadpath = ""
        self.checkpath = ""
        self.isProofReading = False
        self.showDifference = False
        self.realignHook = None

        self.table = table
        if(self.table):
            self.table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self.dstMenu)
            self.setFontSize(fontSize)
        if(srctalks):
            self.loadJson(0, srctalks)
        
        self.updateHiddenRowMap()
        self.realignHook = realignHook

    def setFontSize(self, fontSize):
        self.fontSize = fontSize
        if(not self.table):
            return
        font = self.table.font()
        font.setPixelSize(self.fontSize)
        self.table.setFont(font)
        self.table.horizontalHeader().resizeSection(0, self.fontSize * 3)
        self.table.horizontalHeader().resizeSection(1, self.fontSize * 7)

        for row in range(self.table.rowCount()):
            text = self.table.item(row, 1).text()
            height = len(text.split('\n'))
            self.table.setRowHeight(row, 20 + (15 + self.fontSize) * height)

    def loadJson(self, editormode, srctalks, jp=False):
        self.srctalks = srctalks
        self.talks = []
        self.refertalks = self.checkLines(self.refertalks)
        self.dsttalks = self.checkLines(self.dsttalks)

        if editormode == 0:
            for idx, talk in enumerate(self.dsttalks):
                newtalk = copy.deepcopy(talk)
                newtalk['dstidx'] = idx
                newtalk['referid'] = idx
                self.talks.append(newtalk)
        elif editormode == 1 or editormode == 2:
            self.talks = self.compareText(self.dsttalks, editormode)

        self.table.setRowCount(0)
        for talk in self.talks:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.fillTableLine(row, talk)
        
        self.updateHiddenRowMap()

    # create new text from json
    def createFile(self, srctalks, jp=False):
        self.loadJson(0, srctalks)
        self.talks = []
        self.refertalks = []
        self.dsttalks = []

        for idx, srctalk in enumerate(self.srctalks):
            subsrctalks = srctalk['text'].split("\n")
            for iidx, subsrctalk in enumerate(subsrctalks):
                tempText = ''
                for char in subsrctalk:
                    if char in ['♪', '☆', '/', '『', '』']:
                        tempText += char
                self.dsttalks.append({
                    'idx': idx + 1,
                    'speaker': srctalk['speaker'],
                    'text': tempText if not jp else subsrctalk,
                    'start': iidx == 0,
                    'end': False,
                    'checked': True,
                    'save': True
                })
            self.dsttalks[-1]['end'] = True

        for idx, talk in enumerate(self.dsttalks):
            speakers = talk['speaker'].replace(u"の声", "").split(u"・")
            for speaker in speakers:
                for character in characterDict:
                    if speaker == character["name_j"]:
                        self.dsttalks[idx]['speaker'] = self.dsttalks[idx]['speaker'].replace(speaker, character["name_c"])
                        break
            self.dsttalks[idx]['speaker'] = self.dsttalks[idx]['speaker'].replace(u"の声", u"的声音")
            self.dsttalks[idx]['speaker'] = self.dsttalks[idx]['speaker'].replace(u"ネネロボ", u"宁宁号")

        for idx, talk in enumerate(self.dsttalks):
            newtalk = copy.deepcopy(talk)
            newtalk['dstidx'] = idx
            self.talks.append(newtalk)

        self.table.setRowCount(0)
        for talk in self.talks:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.fillTableLine(row, talk)
        
        self.updateHiddenRowMap()

    def loadFile(self, editormode, filepath):
        srcfile = open(filepath, 'r', encoding='UTF-8')
        lines = srcfile.readlines()

        loadtalks = []
        preblank = False
        for idx, line in enumerate(lines):
            line = line.replace(":", "：")
            if "：" in line:
                speaker = line.split("：")[0]
                fulltext = line[len(speaker) + 1:]
            elif "/" in line:
                speaker = u"选项"
                fulltext = line
            else:
                speaker = u"场景" if len(line.strip()) else ""
                fulltext = line

            # skip continuous balnk line
            if speaker == "":
                if preblank:
                    continue
                preblank = True
            else:
                preblank = False

            texts = fulltext.split("\\N")
            for iidx, text in enumerate(texts):
                text, check = self.checkText(speaker, text)
                talk = {
                    'idx': idx + 1,
                    'speaker': speaker,
                    'text': text,
                    'start': iidx == 0,
                    'end': False,
                    'checked': check,
                    'save': True
                }
                loadtalks.append(talk)
            loadtalks[-1]['end'] = True

        if preblank:
            loadtalks.pop()

        self.resetTalk(editormode, loadtalks)

    def saveFile(self, filepath, saveN):
        outTalk = ''
        for talk in self.dsttalks:
            if talk['speaker'] in [u'场景', u'左上场景', u'选项', '']:
                if talk['speaker'] in [u'场景', u'左上场景'] and talk['text'] == '':
                    talk['text'] = u'场景'
                elif talk['speaker'] == u'选项' and '/' not in talk['text']:
                    talk['text'] = talk['text'] + '/'
                outTalk += talk['text'] + '\n'
            else:
                if talk['start']:
                    outTalk += talk['speaker'] + "："
                outTalk += talk['text'].split("\n")[0]
                if not talk['end']:
                    if saveN:
                        outTalk += '\\N'
                else:
                    outTalk += '\n'
        outTalk = outTalk.rstrip()
        with open(filepath, 'w', encoding='UTF-8') as f:
            f.write(outTalk)
            f.close()

    def fillTableLine(self, row, talk):
        self.table.blockSignals(True)
        if talk['start']:
            self.table.setItem(row, 0, QTableWidgetItem(str(talk['idx'])))
            self.table.setItem(row, 1, QTableWidgetItem(talk['speaker']))
        else:
            self.table.setItem(row, 0, QTableWidgetItem(" "))
            self.table.setItem(row, 1, QTableWidgetItem(" "))
        self.table.setItem(row, 2, QTableWidgetItem(talk['text']))

        if talk['end']:
            if self.table.item(row, 3):
                self.table.item(row, 3).setText("")
            else:
                self.table.setItem(row, 3, QTableWidgetItem(" "))

            if 'proofread' not in talk or talk['proofread']:
                lineCtrl = QWidget()
                layout = QHBoxLayout(lineCtrl)

                if talk['speaker'] not in ["", u"场景", u"左上场景", u"选项"]:
                    buttonAdd = QPushButton("+", lineCtrl)
                    buttonAdd.setFixedSize(30, 30)
                    layout.addWidget(buttonAdd)
                    buttonAdd.clicked.connect(self.addLine)

                if not talk['start']:
                    buttonRemove = QPushButton("-", lineCtrl)
                    buttonRemove.setFixedSize(30, 30)
                    layout.addWidget(buttonRemove)
                    buttonRemove.clicked.connect(self.removeLine)

                self.table.setCellWidget(row, 3, lineCtrl)
            else:
                self.table.removeCellWidget(row, 3)
        else:
            self.table.removeCellWidget(row, 3)
            self.table.setItem(row, 3, QTableWidgetItem("\\N"))

        height = len(talk['text'].split('\n'))
        self.table.setRowHeight(row, 20 + (15 + self.fontSize) * height)

        for column in range(self.table.columnCount()):
            if self.table.item(row, column) and (talk['speaker'] == "" or not(column == 2 or (column == 1 and talk['start']))):
                self.table.item(row, column).setFlags(Qt.NoItemFlags)

        if 'proofread' in talk:
            if self.showDifference and talk['proofread']:
                color = Color['GREEN']
            elif not talk['proofread']:
                color = Color['YELLOW']
            else:
                color = Color['WHITE']
            for column in range(self.table.columnCount()):
                if self.table.item(row, column):
                    self.table.item(row, column).setBackground(color)

                if 'checkmode' in talk:
                    if self.table.item(row, 3):
                        self.table.item(row, 3).setText("")
                    checkbox = QCheckBox()
                    # checkbox.setFixedSize(30, 30)
                    checkbox.clicked.connect(self.checkProofread)
                    self.table.setCellWidget(row, 3, checkbox)

        elif not talk['checked'] and talk['save']:
            self.table.item(row, 2).setBackground(Color['RED'])

        else:
            self.table.item(row, 2).setBackground(Color['WHITE'])

        if not self.showDifference and not talk['save']:
            self.table.setRowHidden(row, True)
        self.table.blockSignals(False)

    def changeSpeaker(self, item, editormode):
        row = item.row()
        column = item.column()
        srcSpeaker = self.srctalks[self.talks[row]['idx'] - 1]['speaker']
        newSpeaker = item.text()

        if (srcSpeaker in ["", u"场景", u"左上场景", u"选项"]) or not newSpeaker:
            return

        for idx, talk in enumerate(self.talks):
            if self.srctalks[talk['idx'] - 1]['speaker'] == srcSpeaker:
                self.talks[idx]['speaker'] = newSpeaker
                self.dsttalks[self.talks[idx]['dstidx']]['speaker'] = newSpeaker

                if(self.talks[idx]['start']):
                    self.table.blockSignals(True)
                    self.table.item(idx, column).setText(newSpeaker)
                    self.table.blockSignals(False)

        return

    def showSpeakers(self):
        if not self.talks:
            return

        self.speakerTable = QTableWidget()
        self.speakerTable.verticalHeader().hide()

        speakers = {}
        for talk in self.talks:
            if self.srctalks:
                srcSpeaker = self.srctalks[talk['idx'] - 1]['speaker']
            else:
                srcSpeaker = talk['speaker']

            if srcSpeaker not in ["", u"场景", u"左上场景", u"选项"] and srcSpeaker not in speakers:
                speakers[srcSpeaker] = talk['speaker']

        self.speakerTable.setColumnCount(2)
        self.speakerTable.setRowCount(0)
        self.speakerTable.horizontalHeader().resizeSection(0, 200)
        if self.srctalks:
            self.speakerTable.setHorizontalHeaderItem(0, QTableWidgetItem(u"日文原文"))
        else:
            self.speakerTable.setHorizontalHeaderItem(0, QTableWidgetItem(u"原翻译"))
        self.speakerTable.horizontalHeader().resizeSection(1, 200)
        self.speakerTable.setHorizontalHeaderItem(1, QTableWidgetItem(u"翻译"))

        for speaker in speakers:
            row = self.speakerTable.rowCount()
            self.speakerTable.setRowCount(row + 1)
            self.speakerTable.setItem(row, 0, QTableWidgetItem(speaker))
            self.speakerTable.setItem(row, 1, QTableWidgetItem(speakers[speaker]))
            self.speakerTable.setRowHeight(row, 20 + (15 + self.fontSize))
            self.speakerTable.item(row, 0).setFlags(Qt.NoItemFlags)

        self.speakerTable.setFixedSize(QSize(415, min(800, 45 + 40 * len(speakers))))
        self.speakerTable.itemChanged.connect(self.changeSpeakerTable)

        self.speakerTable.setWindowTitle(u"检查说话人")
        self.speakerTable.show()

    def changeSpeakerTable(self, item):
        row = item.row()
        srcSpeaker = self.speakerTable.item(row, 0).text()
        newSpeaker = item.text()

        for idx, talk in enumerate(self.talks):
            if self.srctalks:
                speaker = self.srctalks[talk['idx'] - 1]['speaker']
            else:
                speaker = talk['speaker']

            if speaker == srcSpeaker:
                self.talks[idx]['speaker'] = newSpeaker
                self.dsttalks[self.talks[idx]['dstidx']]['speaker'] = newSpeaker

                if(self.talks[idx]['start']):
                    self.table.blockSignals(True)
                    self.table.item(idx, 1).setText(newSpeaker)
                    self.table.blockSignals(False)
        return

    def changeText(self, item, editormode):
        row = item.row()
        column = item.column()
        speaker = self.talks[row]['speaker']
        text, check = self.checkText(speaker, item.text())
        if len(text.split("\n")) > 1:
            check = False

        if not speaker:
            self.table.item(row, column).setText("")
            return

        # translate
        if editormode == 0:
            self.talks[row]['text'] = text
            self.talks[row]['checked'] = check
            self.dsttalks[self.talks[row]['dstidx']]['text'] = text
            self.dsttalks[self.talks[row]['dstidx']]['checked'] = check
            self.fillTableLine(row, self.talks[row])
        # proofread
        elif editormode == 1 or editormode == 2:
            if 'proofread' not in self.talks[row]:
                newtalk = copy.deepcopy(self.talks[row])
                newtalk['text'] = text
                newtalk['checked'] = True
                newtalk['save'] = True
                newtalk['proofread'] = True

                dstidx = self.talks[row]['dstidx']
                self.dsttalks[dstidx]['text'] = text
                self.dsttalks[dstidx]['checked'] = check
                newtalk['dstidx'] = dstidx
                self.talks.insert(row + 1, newtalk)

                self.table.blockSignals(True)
                self.table.insertRow(row + 1)
                self.table.blockSignals(False)

                self.fillTableLine(row + 1, newtalk)

                self.talks[row]['checked'] = False
                self.talks[row]['save'] = False
                self.talks[row]['proofread'] = False
                self.fillTableLine(row, self.talks[row])

                row += 1

            elif self.talks[row]['proofread']:

                self.talks[row]['text'] = text
                self.dsttalks[self.talks[row]['dstidx']]['text'] = text
                self.talks[row]['checked'] = True
                self.fillTableLine(row, self.talks[row])

            else:
                self.fillTableLine(row, self.talks[row])

        if row < self.table.rowCount() - 1:
            nextItem = self.table.item(row + 1, column)
            self.table.setCurrentItem(nextItem)
            self.table.editItem(nextItem)

    def checkText(self, speaker, text):
        check = True
        if (speaker not in ["", u"场景", u"左上场景", u"选项"]) and (not text):
            text += "\n【空行，若不需要改行请点右侧“-”删去本行】"
            return text, check
        text = text.split("\n")[0].rstrip().lstrip()
        if not text:
            return text, check

        if speaker in [u'场景', u"左上场景", '']:
            return text, check
        
        if speaker == u"选项":
            if '/' not in text:
                text =  text + '/'
            if text[-1] == '/':
                text += "\n【选项必须用/分隔】"
                check = False
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

    def checkLines(self, loadtalks):
        srcCount = 0
        for srctalk in self.srctalks:
            if srctalk['speaker'] in [u"场景", u"左上场景", u"选项"]:
                srcCount += 1
            elif srctalk['speaker'] != "":
                break
        Count = 0
        for talk in loadtalks:
            if talk['speaker'] in [u"场景", u"左上场景", u"选项"]:
                Count += 1
            elif talk['speaker'] != "":
                break
        if Count > srcCount:
            for i in range(Count - srcCount):
                del loadtalks[0]
        while loadtalks and loadtalks[0]['text'] == '':
            del loadtalks[0]

        newtalks = []
        idx = 0
        dstend = False
        for srcidx, srctalk in enumerate(self.srctalks):
            if idx >= len(loadtalks):
                dstend = True
            
            if not dstend and srctalk['speaker'] == u'左上场景' and loadtalks[idx]['speaker'] == u'场景':
                loadtalks[idx]['speaker'] = u'左上场景'

            if srctalk['speaker'] in [u'场景', u'左上场景', u'选项', '']:
                if dstend or srctalk['speaker'] != loadtalks[idx]['speaker']:
                    newtalk = {
                        'idx': srcidx + 1,
                        'speaker': srctalk['speaker'],
                        'text': srctalk['text'],
                        'start': True,
                        'end': True,
                        'checked': True,
                        'save': True
                    }
                    newtalks.append(newtalk)
                    continue

            subsrctalks = srctalk['text'].split("\n")
            dstidx = loadtalks[idx]['idx'] if not dstend else -1
            for iidx, subsrctalk in enumerate(subsrctalks):
                if idx >= len(loadtalks):
                    dstend = True
                if not dstend and loadtalks[idx]['idx'] == dstidx:
                    loadtalks[idx]['text'], check = self.checkText(srctalk['speaker'], loadtalks[idx]['text'])
                    talk = {
                        'idx': srcidx + 1,
                        'speaker': loadtalks[idx]['speaker'],
                        'text': loadtalks[idx]['text'],
                        'start': iidx == 0,
                        'end': False,
                        'checked': check,
                        'save': True
                    }
                    idx += 1

                elif dstend:
                    talk = {
                        'idx': srcidx + 1,
                        'speaker': srctalk['speaker'],
                        'text': " ",
                        'start': iidx == 0,
                        'end': False,
                        'checked': False,
                        'save': True
                    }

                # when \N is lost
                else:
                    newtalks[-1]['text'] = newtalks[-1]['text'] + "\n【分行不一致】"
                    newtalks[-1]['end'] = True
                    newtalks[-1]['checked'] = False
                    continue

                newtalks.append(talk)

            # when \N is too much
            while idx < len(loadtalks) and loadtalks[idx]['idx'] == dstidx:
                loadtalks[idx]['text'], check = self.checkText(srctalk['speaker'], loadtalks[idx]['text'])
                talk = {
                    'idx': srcidx + 1,
                    'speaker': loadtalks[idx]['speaker'],
                    'text': loadtalks[idx]['text'] + "\n【分行不一致】",
                    'start': False,
                    'end': True,
                    'checked': False,
                    'save': True
                }
                idx += 1
                newtalks.append(talk)

            newtalks[-1]['end'] = True

        if idx < len(loadtalks):
            idxdiff = newtalks[-1]['idx'] - loadtalks[idx]['idx'] + 1
            for talk in loadtalks[idx:]:
                newtalk = talk
                newtalk['idx'] = talk['idx'] + idxdiff
                newtalk['text'] = talk['text'] + "\n【多余行】"
                newtalk['checked'] = False
                newtalks.append(newtalk)
        return newtalks

    def compareText(self, checktalks, editormode):
        newtalks = []
        cidx = 0
        for idx, talk in enumerate(self.refertalks):

            while cidx < len(checktalks) and talk['idx'] > checktalks[cidx]['idx']:
                checktalks[cidx]['proofread'] = True
                newtalks.append(checktalks[cidx])
                newtalks[-1]['dstidx'] = cidx
                cidx += 1

            if cidx >= len(checktalks):
                newtalk = copy.deepcopy(talk)
                newtalk['checked'] = False
                newtalk['save'] = False
                newtalk['proofread'] = False
                if editormode == 2:
                    newtalk['checkmode'] = True
                newtalks.append(newtalk)
                newtalks[-1]['referid'] = idx
                continue

            if talk['idx'] == checktalks[cidx]['idx']:
                newtalk = copy.deepcopy(talk)
                if talk['text'] == checktalks[cidx]['text']:
                    newtalks.append(newtalk)
                    newtalks[-1]['dstidx'] = cidx
                    newtalks[-1]['referid'] = idx
                    cidx += 1
                else:
                    newtalk['checked'] = False
                    newtalk['save'] = False
                    newtalk['proofread'] = False
                    if editormode == 2:
                        newtalk['checkmode'] = True
                    newtalks.append(newtalk)
                    newtalks[-1]['referid'] = idx

                    checktalks[cidx]['proofread'] = True
                    newtalks.append(checktalks[cidx])
                    newtalks[-1]['dstidx'] = cidx
                    cidx += 1

            elif talk['idx'] < checktalks[cidx]['idx']:
                newtalk = copy.deepcopy(talk)
                newtalk['checked'] = False
                newtalk['save'] = False
                newtalk['proofread'] = False
                if editormode == 2:
                    newtalk['checkmode'] = True
                newtalks.append(newtalk)
                newtalks[-1]['referid'] = idx

        return newtalks

    def showDiff(self, state):
        self.showDifference = state
        for idx, talk in enumerate(self.talks):
            if 'proofread' in talk:
                if talk['proofread']:
                    if state:
                        color = Color['GREEN']
                    else:
                        color = Color['WHITE']
                    for column in range(self.table.columnCount()):
                        if self.table.item(idx, column):
                            self.table.blockSignals(True)
                            self.table.item(idx, column).setBackground(color)
                            self.table.blockSignals(False)

                    if not talk['checked']:
                        if talk['save']:
                            self.table.blockSignals(True)
                            self.table.item(idx, 2).setBackground(Color['RED'])
                            self.table.blockSignals(False)

                if not talk['proofread']:
                    if state:
                        self.table.setRowHidden(idx, False)
                    else:
                        self.table.setRowHidden(idx, True)

    def addLine(self):
        button = self.table.sender()
        if button:
            tablecell = button.parent()
            row = self.table.indexAt(tablecell.pos()).row()

            newtalk = copy.deepcopy(self.talks[row])
            newtalk['text'] = " "
            newtalk['end'] = True
            newtalk['checked'] = True
            newtalk['save'] = True
            newtalk['start'] = False
            if self.isProofReading:
                newtalk['proofread'] = True

            dstidx = self.talks[row]['dstidx']
            self.dsttalks.insert(dstidx + 1, newtalk)
            self.talks.insert(row + 1, newtalk)
            for talk in self.talks[row + 1:]:
                if 'dstidx' in talk:
                    talk['dstidx'] += 1

            self.table.blockSignals(True)
            self.table.insertRow(row + 1)
            self.table.blockSignals(False)

            self.fillTableLine(row + 1, newtalk)

            if not self.isProofReading or (
                'proofread' in self.talks[row] and self.talks[row]['proofread']):
                self.talks[row]['end'] = False
                self.talks[row]['checked'] = True
                self.talks[row]['save'] = True
                self.dsttalks[dstidx]['end'] = False
                self.dsttalks[dstidx]['checked'] = True
                self.dsttalks[dstidx]['save'] = True
            else:
                self.talks[row]['proofread'] = False
                self.talks[row]['checked'] = False
                self.talks[row]['save'] = False

                temptalk = copy.deepcopy(self.talks[row])
                temptalk['end'] = False
                temptalk['proofread'] = True
                temptalk['checked'] = True
                temptalk['save'] = True
                self.dsttalks[dstidx]['end'] = False
                self.dsttalks[dstidx]['checked'] = True
                self.dsttalks[dstidx]['save'] = True
                self.talks.insert(row + 1, temptalk)

                self.table.blockSignals(True)
                self.table.insertRow(row + 1)
                self.table.blockSignals(False)

                self.fillTableLine(row + 1, temptalk)

            self.fillTableLine(row, self.talks[row])

            nextItem = self.table.item(row + 1, 2)
            self.table.setCurrentItem(nextItem)
            self.table.editItem(nextItem)

            self.updateHiddenRowMap()

    def removeLine(self):
        button = self.table.sender()
        if button:
            tablecell = button.parent()
            row = self.table.indexAt(tablecell.pos()).row()
            dstidx = self.talks[row]['dstidx']

            if row > 0:
                self.talks[row - 1]['end'] = True
                self.dsttalks[dstidx - 1]['end'] = True
                self.fillTableLine(row - 1, self.talks[row - 1])

            self.talks.pop(row)
            self.dsttalks.pop(dstidx)
            for talk in self.talks[row:]:
                if 'dstidx' in talk:
                    talk['dstidx'] -= 1

            self.table.blockSignals(True)
            self.table.removeRow(row)
            self.table.blockSignals(False)

            preItem = self.table.item(row - 1, 2)
            self.table.setCurrentItem(preItem)
            self.table.editItem(preItem)
            
            self.updateHiddenRowMap()

    def dstMenu(self, pos):
        row = -1
        for i in self.table.selectionModel().selection().indexes():
            row = i.row()

        if 0 <= row < self.table.rowCount():
            menu = QMenu()
            repalceBracketsAction1 = menu.addAction(u"替换为「」")
            repalceBracketsAction2 = menu.addAction(u"替换为『』")
            repalceBracketsAction3 = menu.addAction(u"替换为（）")
            repalceBracketsAction4 = menu.addAction(u"替换为“”")
            repalceBracketsAction5 = menu.addAction(u"替换为‘’")
            action = menu.exec_(self.table.mapToGlobal(pos))

            if action == repalceBracketsAction1:
                self.repalceBrackets(row, '「」')
            elif action == repalceBracketsAction2:
                self.repalceBrackets(row, '『』')
            elif action == repalceBracketsAction3:
                self.repalceBrackets(row, '（）')
            elif action == repalceBracketsAction4:
                self.repalceBrackets(row, '“”')
            elif action == repalceBracketsAction5:
                self.repalceBrackets(row, '‘’')
            else:
                return

    def resetTalk(self, editormode, loadtalks):
        self.talks = []
        if self.srctalks:
            loadtalks = self.checkLines(loadtalks)

        if editormode == 0:
            self.refertalks = copy.deepcopy(loadtalks)
            self.dsttalks = copy.deepcopy(loadtalks)
            for idx, talk in enumerate(self.dsttalks):
                newtalk = copy.deepcopy(talk)
                newtalk['dstidx'] = idx
                newtalk['referid'] = idx
                self.talks.append(newtalk)
        elif editormode == 1 or editormode == 2:
            self.dsttalks = copy.deepcopy(loadtalks)
            self.talks = self.compareText(loadtalks, editormode)

        self.table.setRowCount(0)
        for talk in self.talks:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.fillTableLine(row, talk)
        
        self.updateHiddenRowMap()

    def repalceBrackets(self, row, brackets):
        text = self.table.item(row, 2).text()
        newText = ""
        for idx, char in enumerate(text):
            if char in ['「', '『', '（', '“', '‘', '【']:
                newText += brackets[0]
            elif char in ['」', '』', '）', '”', '’', '】']:
                newText += brackets[1]
            else:
                newText += char
        self.table.item(row, 2).setText(newText)

    def checkProofread(self):
        box = self.table.sender()
        if box:
            row = self.table.indexAt(box.pos()).row()
        self.talks[row]['checked'] = box.isChecked()
        if self.talks[row]['checked']:
            color = Color['BLUE']
        else:
            color = Color['YELLOW']
        self.table.blockSignals(True)
        for column in range(self.table.columnCount()):
            if self.table.item(row, column):
                self.table.item(row, column).setBackground(color)
        self.table.blockSignals(False)

    def updateHiddenRowMap(self):
        
        current = 0
        self.compressRowMap = []
        self.decompressRowMap = []

        for idx, talk in enumerate(self.talks):
            self.compressRowMap.append(current)
            if 'proofread' in talk:
                if not talk['proofread']:
                    continue
            self.decompressRowMap.append(idx)
            current += 1

        # print(self.compressRowMap)
        # print(self.decompressRowMap)

        # Call main ui to re-align both editors
        if self.realignHook is not None:
            self.realignHook()
