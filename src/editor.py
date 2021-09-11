from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QPushButton, QCheckBox, QHBoxLayout, QMenu
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtCore import Qt, QItemSelectionModel
import os.path as osp
import copy

Color = {
    'RED': QBrush(QColor(255, 192, 192)),
    'YELLOW': QBrush(QColor(255, 255, 128)),
    'GREEN': QBrush(QColor(128, 255, 128)),
    'WHITE': QBrush(QColor(255, 255, 255))
}

class Editor():

    talks = []

    srctalks = []
    refertalks = []
    dsttalks = []

    translatepath = ""
    proofreadpath = ""
    checkpath = ""
    isProofReading = False

    def __init__(self, table=None, srctalks=None):
        self.table = table
        if(self.table):
            self.table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self.dstMenu)
        if(srctalks):
            self.loadJson(srctalks)

    def loadJson(self, srctalks):
        self.srctalks = srctalks

    # create new text for json
    def createFile(self, srctalks):
        self.loadJson(srctalks)
        self.talks = []
        self.refertalks = []
        self.dsttalks = []

        for idx, srctalk in enumerate(self.srctalks):
            subsrctalks = srctalk['text'].split("\n")
            self.dsttalks.append({
                'idx': idx + 1,
                'speaker': srctalk['speaker'],
                'text': '',
                'start': True,
                'end': False,
                'checked': True,
                'save': True
            })
            if len(subsrctalks) > 1:
                for subsrctalk in subsrctalks[1:]:
                    self.dsttalks.append({
                        'idx': idx + 1,
                        'speaker': srctalk['speaker'],
                        'text': '',
                        'start': False,
                        'end': False,
                        'checked': True,
                        'save': True
                    })
            self.dsttalks[-1]['end'] = True

        for idx, talk in enumerate(self.dsttalks):
            newtalk = copy.deepcopy(talk)
            newtalk['dstidx'] = idx
            self.talks.append(newtalk)

        self.table.setRowCount(0)
        for talk in self.talks:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self.fillTableLine(row, talk)

    def loadFile(self, editormode, filepath):

        self.talks = []
        self.refertalks = []
        self.dsttalks = []

        dirpath = osp.dirname(filepath)
        filename = osp.basename(filepath)
        srcfile = open(filepath, 'r', encoding='UTF-8')
        lines = srcfile.readlines()

        loadtalks = []
        preblank = False
        for idx, line in enumerate(lines):
            line = line.replace(":", "：")
            if "：" in line:
                speaker = line.split("：")[0]
                fulltext = line[len(speaker) + 1:]
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

    def saveFile(self, filepath):
        outTalk = ''
        for talk in self.dsttalks:
            if talk['speaker'] in [u'场景', '']:
                outTalk += talk['text'] + '\n'
            else:
                if talk['start']:
                    outTalk += talk['speaker'] + "："
                outTalk += talk['text'].split("\n")[0]
                if not talk['end']:
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

                if talk['speaker'] not in ["", u"场景"]:
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

        height = len(talk['text'].split('\n')) - 1
        self.table.setRowHeight(row, 40 + 20 * height)

        for column in range(self.table.columnCount()):
            if self.table.item(row, column) and column != 2:
                self.table.item(row, column).setFlags(Qt.NoItemFlags)

        if 'proofread' in talk:
            if talk['proofread']:
                color = Color['GREEN']
            else:
                color = Color['YELLOW']
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

        self.table.blockSignals(False)

    def changeText(self, item, editormode):
        
        row = item.row()
        column = item.column()
        speaker = self.talks[row]['speaker']
        text, check = self.checkText(speaker, item.text())
        if len(text.split("\n")) > 1:
            check = False

        if not self.talks[row]['speaker']:
            self.table.item(row, column).setText("")
            return

        # translate
        if editormode == 0:
            self.talks[row]['text'] = text
            self.talks[row]['checked'] = check
            self.dsttalks[self.talks[row]['dstidx']]['text'] = text
            self.dsttalks[self.talks[row]['dstidx']]['checked'] = check
            self.fillTableLine(row, self.talks[row])
            nextItem = self.table.item(row + 1, column)
            self.table.setCurrentItem(nextItem)
            self.table.editItem(nextItem)
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

                nextItem = self.table.item(row + 2, column)
                self.table.setCurrentItem(nextItem)
                self.table.editItem(nextItem)

            elif self.talks[row]['proofread']:

                self.talks[row]['text'] = text
                self.dsttalks[self.talks[row]['dstidx']]['text'] = text
                self.talks[row]['checked'] = True
                self.fillTableLine(row, self.talks[row])
                nextItem = self.table.item(row + 1, column)
                self.table.setCurrentItem(nextItem)
                self.table.editItem(nextItem)

            else:
                self.fillTableLine(row, self.talks[row])
                nextItem = self.table.item(row + 1, column)
                self.table.setCurrentItem(nextItem)
                self.table.editItem(nextItem)

    def checkText(self, speaker, text):
        text = text.split("\n")[0].rstrip().lstrip()
        check = True
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

        normalend = ['，', '。', '？', '！', '~', '♪', '☆', '.', '—']
        unusualend = ['）', '」', '』', '”']
        if text[-1] in normalend:
            if text[-1] in [',', '。']:
                if len(text) > 1 and text[-2] == '.':
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

        if len(text.split("\n")[0]) >= 30:
            text += "\n【单行过长，请删减或换行】"
            check = False

        return text, check

    def checkLines(self, loadtalks):
        srcCount = 0
        for srctalk in self.srctalks:
            if srctalk['speaker'] == u"场景":
                srcCount += 1
            elif srctalk['speaker'] != "":
                break
        Count = 0
        for talk in loadtalks:
            if talk['speaker'] == u"场景":
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

            if srctalk['speaker'] in ['', u'场景']:
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
                        'speaker': srctalk['speaker'],
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
                    'speaker': srctalk['speaker'],
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
            if not self.isProofReading or (
                'proofread' in newtalk and newtalk['proofread']):
                newtalk['start'] = False
            else:
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

            self.fillTableLine(row, self.talks[row])

            nextItem = self.table.item(row + 1, 2)
            self.table.setCurrentItem(nextItem)
            self.table.editItem(nextItem)

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

    def dstMenu(self, pos):
        row = -1
        for i in self.table.selectionModel().selection().indexes():
            row = i.row()
        
        if 0 <= row < self.table.rowCount() and self.talks[row]['speaker'] not in ["", u"场景"]:
            menu = QMenu()
            if self.talks[row]['start']:
                addTalkUpAction = menu.addAction(u"在上方插入一行")
            if self.talks[row]['end']:
                addTalkDownAction = menu.addAction(u"在下方插入一行")
            if self.talks[row]['start'] and self.talks[row]['end']:
                removeTalkAction = menu.addAction(u"删除该行")
            action = menu.exec_(self.table.mapToGlobal(pos))

            if self.talks[row]['start'] and action == addTalkUpAction:
                self.addTalk(row)
            elif self.talks[row]['end'] and action == addTalkDownAction:
                self.addTalk(row + 1)
            elif self.talks[row]['start'] and self.talks[row]['end'] and action == removeTalkAction:
                self.removeTalk(row)
            else:
                return

    def addTalk(self, row):
        self.table.blockSignals(True)

        if self.talks[row]['speaker'] not in ["", u"场景"]:
            talk = copy.deepcopy(self.talks[row])
        else:
            talk = copy.deepcopy(self.talks[row - 1])
        talk['text'] = " "
        self.talks.insert(row, talk)

        editdst = 'proofread' not in self.talks[row] or self.talks[row]['proofread']
        if editdst:
            dsttalk = copy.deepcopy(self.dsttalks[talk['dstidx']])
            dsttalk['text'] = " "
            self.dsttalks.insert(talk['dstidx'], dsttalk)

        editrefer = self.isProofReading and (
            'proofread' not in self.talks[row] or not self.talks[row]['proofread'])
        if editrefer:
            refertalk = copy.deepcopy(self.refertalks[talk['referid']])
            refertalk['text'] = " "
            self.refertalks.insert(talk['referid'], refertalk)

        stoprow = -1
        if row + 1 < len(self.talks):
            for idx, talk in enumerate(self.talks[row + 1:]):
                if talk['speaker'] in ["", u"场景"]:
                    stoprow = row + idx
                    break

                talk['idx'] += 1
                if 'dstidx' in talk:
                    talk['dstidx'] += 1
                if 'referid' in talk:
                    talk['referid'] += 1

                if editdst and 'dstidx' in talk:
                    self.dsttalks[talk['dstidx']]['idx'] += 1
                if editrefer and 'referid' in talk:
                    self.refertalks[talk['referid']]['idx'] += 1

        if stoprow != -1:
            if editdst:
                self.dsttalks.pop(self.talks[stoprow]['dstidx'])
            if editrefer:
                self.refertalks.pop(self.talks[stoprow]['srcidx'])
            self.talks.pop(stoprow)
        elif self.talks[stoprow]['text'] == "":
            self.talks.pop()
            if editdst :
                self.dsttalks.pop()
            if editrefer:
                self.refertalks.pop()

        if editdst:
            self.dsttalks = self.checkLines(self.dsttalks)
        if editrefer:
            self.refertalks = self.checkLines(self.refertalks)

        if not self.isProofReading:
            self.talks = []
            for idx, talk in enumerate(self.dsttalks):
                newtalk = copy.deepcopy(talk)
                newtalk['dstidx'] = idx
                self.talks.append(newtalk)
        else:
            self.talks = self.compareText(self.dsttalks, 1)

        for idx, talk in enumerate(self.talks[row:]):
            if row + idx >= self.table.rowCount():
                self.table.setRowCount(row + idx + 1)
            self.fillTableLine(row + idx, talk)
        self.table.setRowCount(len(self.talks))

        nextItem = self.table.item(row, 2)
        self.table.setCurrentItem(nextItem)
        self.table.editItem(nextItem)

        self.table.blockSignals(False)

    def removeTalk(self, row):
        self.table.blockSignals(True)
        
        talk = self.talks[row]

        editdst = 'proofread' not in self.talks[row] or self.talks[row]['proofread']
        if editdst:
            self.dsttalks.pop(talk['dstidx'])

        editrefer = self.isProofReading and (
            'proofread' not in self.talks[row] or not self.talks[row]['proofread'])
        if editrefer:
            self.refertalks.pop(talk['referid'])

        self.talks.pop(row)

        if row < len(self.talks):
            for idx, talk in enumerate(self.talks[row:]):
                if talk['speaker'] in ["", u"场景"]:
                    break

                talk['idx'] -= 1
                if 'dstidx' in talk:
                    talk['dstidx'] -= 1
                if 'referid' in talk:
                    talk['referid'] -= 1

                if editdst and 'dstidx' in talk:
                    self.dsttalks[talk['dstidx']]['idx'] -= 1
                if editrefer and 'referid' in talk:
                    self.refertalks[talk['referid']]['idx'] -= 1

                blankCount = 0

        if editdst:
            self.dsttalks = self.checkLines(self.dsttalks)
        if editrefer:
            self.refertalks = self.checkLines(self.refertalks)

        if not self.isProofReading:
            self.talks = []
            for idx, talk in enumerate(self.dsttalks):
                newtalk = copy.deepcopy(talk)
                newtalk['dstidx'] = idx
                self.talks.append(newtalk)
        else:
            self.talks = self.compareText(self.dsttalks, 1)

        for idx, talk in enumerate(self.talks[row:]):
            self.fillTableLine(row + idx, talk)
        self.table.setRowCount(len(self.talks))

        nextItem = self.table.item(row, 2)
        self.table.setCurrentItem(nextItem)
        self.table.editItem(nextItem)

        self.table.blockSignals(False)

    def checkProofread(self):
        box = self.table.sender()
        if box:
            row = self.table.indexAt(box.pos()).row()
        self.talks.pop(row)
        self.table.removeRow(row)