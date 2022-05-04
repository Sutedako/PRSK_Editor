from __future__ import unicode_literals

import sys
import traceback

import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtGui import QIcon

from Editor import Editor
from Loader import Loader
import logging
import os.path as osp
import platform

loggingPath = ""


class mainForm(qw.QMainWindow, Ui_SekaiText):

    def __init__(self, root):
        super().__init__()

        self.resultPath = osp.join(root, u"审核结果.txt")
        self.answerPath = osp.join(root, u"答题纸.txt")

        self.iconpath = "image/icon"
        if getattr(sys, 'frozen', False):
            self.iconpath = osp.join(sys._MEIPASS, self.iconpath)
        if platform.system() == "Darwin":
            titleIcon = osp.join(self.iconpath, "32.icns")
        else:
            titleIcon = osp.join(self.iconpath, "32.ico")
        if osp.exists(titleIcon):
            self.setWindowIcon(QIcon(titleIcon))
            logging.info("Icon Loaded")

        self.editormode = -1

        self.setupUi(self)
        self.dstText = Editor(self.tableWidgetDst)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemClicked.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

    def load(self):
        try:
            if self.editormode == 0:
                jsonname = "translate.json"
            elif self.editormode == 1:
                jsonname = "proofread.json"
            jsonpath = "data"
            if getattr(sys, 'frozen', False):
                jsonpath = osp.join(sys._MEIPASS, jsonpath)
            jsonpath = osp.join(jsonpath, jsonname)
            self.srcText = Loader(jsonpath, self.tableWidgetSrc)
            logging.info("Json Loaded")

            if not (osp.exists(self.resultPath) or osp.exists(self.answerPath)):
                self.dstText.createFile(self.srcText.talks)
            self.dstText.fillTable()
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"loadJson错误\n请将“log.txt发给弃子”")

    def editText(self, item):
        try:
            self.tableWidgetDst.blockSignals(True)
            editRow = self.dstText.comment(item.row() + 1)
            editItem = self.tableWidgetDst.item(editRow, item.column())
            self.tableWidgetDst.editItem(editItem)
            item.setText(item.text().split("\n")[0].rstrip().lstrip())
            self.tableWidgetDst.blockSignals(False)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"editText错误\n请将“log.txt发给弃子”")

    def saveFile(self):
        content = ""
        content += "Q1:" + self.nameText.text() + "\n"
        content += "Q2:" + str(self.editormode) + "\n"
        content += "Q3:" + self.recommendText.text() + "\n"
        content += "Q4:" + self.degreeText.toPlainText().replace('\n', '\\N') + "\n"
        content += "Q5:" + self.understandText.toPlainText().replace('\n', '\\N') + "\n"
        content += self.dstText.saveFile()

        with open(self.resultPath, 'w', encoding='UTF-8') as f:
            f.write(content)
            f.close()


    def changeText(self, item):
        try:
            self.dstText.changeText(item, self.editormode)
            self.saveFile()
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"changeText错误\n请将“log.txt发给弃子”")

    def trackSrc(self, currentRow, currentColumn, previousRow, previousColumn):
        try:
            if currentColumn >= 3:
                return
            srcrow = self.tableWidgetSrc.rowCount()
            if currentRow < len(self.dstText.talks):
                srcrow = min(srcrow, self.dstText.talks[currentRow]['idx'])
                srcItem = self.tableWidgetSrc.item(srcrow - 1, 1)
                self.tableWidgetSrc.setCurrentItem(srcItem)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"trackSrc错误\n请将“log.txt发给弃子”")

    def translateMode(self):
        self.editormode = 0

    def proofreadMode(self):
        self.editormode = 1

    def checkExistingFile(self):
        textPath = ""
        if osp.exists(self.resultPath):
            textPath = self.resultPath
        elif osp.exists(self.answerPath):
            textPath = self.answerPath

        if textPath:
            profile = self.dstText.loadFile(textPath)

            if len(profile) == 5:
                self.nameText.setText(profile[0].rstrip())
                self.editormode = int(profile[1].rstrip())
                self.recommendText.setText(profile[2].rstrip())
                self.degreeText.setText(
                    profile[3].rstrip().replace('\\N', '\n'))
                self.understandText.setText(
                    profile[4].rstrip().replace('\\N', '\n'))

            if self.editormode > -1:
                return True

        return False


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)

    root, _ = osp.split(osp.abspath(sys.argv[0]))
    if not getattr(sys, 'frozen', False):
        root = osp.join(root, "../")

    if platform.system() == "Darwin":
        root = osp.join(root, '../../../')

    loggingPath = osp.join(root, "log.txt")

    logging.basicConfig(level=logging.INFO,
                        filename=loggingPath,
                        filemode='w')
    try:
        mainform = mainForm(root)

        if not mainform.checkExistingFile():
            modeSelectWinodw = qw.QMessageBox()
            modeSelectWinodw.setWindowTitle("Sekai Test")
            modeSelectWinodw.setText("请阅读题干与格式规范\n建议对照视频进行翻译")
            if platform.system() == "Darwin":
                proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
                translateButton = modeSelectWinodw.addButton(u"翻译", 2)
            else:
                translateButton = modeSelectWinodw.addButton(u"翻译", 2)
                proofreadButton = modeSelectWinodw.addButton(u"校对", 2)

            translateButton.clicked.connect(mainform.translateMode)
            proofreadButton.clicked.connect(mainform.proofreadMode)

            modeSelectWinodw.exec_()

        mainform.load()
        mainform.show()
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)
