from __future__ import unicode_literals

import sys
import traceback

import PyQt5.QtCore as qc
import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtGui import QKeySequence, QIcon, QBrush, QColor

from Editor import Editor
from Loader import Loader
from chr import chrs

import json
import logging
import os.path as osp
import platform

loggingPath = ""

class mainForm(qw.QMainWindow, Ui_SekaiText):

    def __init__(self, root):
        super().__init__()

        self.resultPath = osp.join(root, "result.txt")
        self.answerPath = osp.join(root, "answer.txt")

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

        self.setupUi(self)

        self.profile = {
            "name": "",
            "questions": []
        }
        self.dstText = Editor(self.tableWidgetDst)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

    def load(self, jsonname):
        try:
            jsonpath = "data"
            if getattr(sys, 'frozen', False):
                jsonpath = osp.join(sys._MEIPASS, jsonpath)
            jsonpath = osp.join(jsonpath, jsonname)
            self.srcText = Loader(jsonpath, self.tableWidgetSrc)
            logging.info("Json Loaded")

            if osp.exists(self.resultPath):
                self.dstText.loadFile(self.resultPath)
                logging.info("Result Loaded")
            elif osp.exists(self.answerPath):
                self.dstText.loadFile(self.answerPath)
                logging.info("Answer Loaded")
            else:
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
            self.tableWidgetDst.editItem(item)
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
        writeTalk = self.dstText.saveFile()

        with open(self.answerPath, 'w', encoding='UTF-8') as f:
            f.write(writeTalk)
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
        self.load("translate.json")

    def proofreadMode(self):
        self.editormode = 1
        self.load("proofread.json")


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
        modeSelectWinodw = qw.QMessageBox()
        modeSelectWinodw.setWindowTitle("Sekai Test")
        modeSelectWinodw.setText("请阅读题干与格式规范\n建议对照视频进行翻译")
        if platform.system() == "Darwin":
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
        else:
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)

        mainform = mainForm(root)
        translateButton.clicked.connect(mainform.translateMode)
        proofreadButton.clicked.connect(mainform.proofreadMode)

        modeSelectWinodw.exec_()
        mainform.show()
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)