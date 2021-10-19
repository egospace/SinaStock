from threading import Thread
from PySide2.QtCore import QObject, Signal
from PySide2.QtWidgets import QApplication, QTextBrowser, QMessageBox, QTableWidgetItem, QGraphicsScene
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QFileDialog
import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

matplotlib.use("Qt5Agg")


class MyFigureCanvas(FigureCanvas):
    """
    通过继承FigureCanvas类，使得该类既是一个PyQt5的Qwidget，又是一个matplotlib的FigureCanvas，这是连接pyqt5与matplotlib的关键
    """

    def __init__(self, parent=None, width=8, height=3, dpi=100):
        # 创建一个Figure
        fig = plt.Figure(figsize=(width, height), dpi=dpi, tight_layout=True)  # tight_layout: 用于去除画图时两边的空白

        FigureCanvas.__init__(self, fig)  # 初始化父类
        self.setParent(parent)

        self.axes = fig.add_subplot(111)  # 添加子图
        self.axes.spines['top'].set_visible(False)  # 去掉绘图时上面的横线
        self.axes.spines['right'].set_visible(False)  # 去掉绘图时右面的横线


# 自定义信号源对象类型
class MySignals(QObject):
    text_print = Signal(QTextBrowser)

    add_Table = Signal(QApplication)


# 实例化
global_ms = MySignals()


class SinaStatsGUI:
    file_path = "./"
    code = "sz000001"
    date1 = "2021-04-27"
    date2 = date1
    ls = []

    def __init__(self):
        self.graphic_scene = QGraphicsScene()  # 创建一个QGraphicsScene
        self.ui = QUiLoader().load('UI/sinaSpider.ui')
        self.ui.pushButton.clicked.connect(self.get_data)
        self.ui.selectPath.clicked.connect(self.get_path)
        self.ui.save.clicked.connect(self.save_file)
        self.ui.genTable.clicked.connect(self.gen_table)
        self.ui.genGo.clicked.connect(self.gen_go)
        self.ui.genGraph.clicked.connect(self.gen_graph)

    def get_data(self):
        self.code = self.ui.code.text()
        self.date1 = self.ui.date1.date().toString('yyyy-MM-dd')
        self.date2 = self.ui.date2.date().toString('yyyy-MM-dd')
        if self.date2 >= self.date1:
            thread = Thread(target=self.spider)
            thread.start()
        else:
            QMessageBox().setText("Date Error!!!").exec_()

    def progress(self, data):
        self.ui.progress.append(data)
        self.ui.progress.ensureCursorVisible()

    def get_path(self):
        self.file_path = QFileDialog.getExistingDirectory(self.ui, '选择存储路径')
        self.ui.savepath.setText(self.file_path)

    def save_file(self):
        if len(self.ls) != 0:
            tp = pd.DataFrame(self.ls, columns=['成交时间', '成交价', '价格变动', '成交量(手)', '成交额(元)', '性质'])
            if os.path.exists(self.file_path + '/' + self.code + '-' + self.date1 + '-' + self.date2 + '.csv'):
                os.remove(self.file_path + '/' + self.code + '-' + self.date1 + '-' + self.date2 + '.csv')
            tp.to_csv(self.file_path + '/' + self.code + '-' + self.date1 + '-' + self.date2 + '.csv',
                      encoding='utf_8_sig')
        else:
            QMessageBox().setText("请先爬取数据!!!").exec_()

    def gen_graph(self):
        tp = pd.DataFrame(self.ls, columns=['成交时间', '成交价', '价格变动', '成交量(手)', '成交额(元)', '性质'])
        x = tp.iloc[:, 0]
        y = tp.iloc[:, 1]
        gv_visual = MyFigureCanvas()
        gv_visual.axes.cla()
        gv_visual.axes.plot(x, y)
        gv_visual.axes.set_title('Graph')
        self.graphic_scene.addWidget(gv_visual)
        self.ui.graphicsView.setScene(self.graphic_scene)
        self.ui.graphicsView.show()

    def gen_go(self):
        tp = pd.DataFrame(self.ls, columns=['成交时间', '成交价', '价格变动', '成交量(手)', '成交额(元)', '性质'])
        self.ui.tableStats.setColumnCount(1)
        self.ui.tableStats.setRowCount(3)
        self.ui.tableStats.setItem(0, 0, QTableWidgetItem(str(tp.iloc[:, 1].max())))
        self.ui.tableStats.setItem(0, 1, QTableWidgetItem(str(tp.iloc[:, 1].mean())))
        self.ui.tableStats.setItem(0, 2, QTableWidgetItem(str(tp.iloc[:, 1].min())))

    def gen_table(self):
        self.ui.table.setColumnCount(6)
        self.ui.table.setRowCount(len(self.ls))
        line = 0
        for k in self.ls:
            for j in range(len(k)):
                self.ui.table.setItem(line, j, QTableWidgetItem(str(k[j])))
            line += 1

    def spider(self):
        if len(self.code) == 0:
            self.code = 'sz000001'
        if self.date2 >= self.date1:
            index = pd.date_range(self.date1, self.date2)
            for i in index:
                page = 1
                tm = i.strftime("%Y-%m-%d")
                while True:
                    detail = time.strftime("%Y-%m-%d %H:%M:%S") + "<-:->" + self.code + ":" + tm + ":" + str(page)
                    global_ms.text_print.emit(self.progress(detail))
                    time.sleep(1)
                    post_url = r'http://market.finance.sina.com.cn/transHis.php?symbol=' + self.code + '&date=' + tm + '&page=' + str(
                        page) + '&qq-pf-to=pcqq.c2c'
                    # 进行UA伪装
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                      'like Gecko) '
                                      'Chrome/94.0.4606.81 Safari/537.36 '
                    }
                    # 请求发送
                    response = requests.get(url=post_url, headers=headers)
                    response.encoding = response.apparent_encoding
                    tmp = response.text
                    soup = BeautifulSoup(tmp, 'lxml').findAll('tr')
                    if len(soup) <= 1:
                        break
                    for j in range(1, len(soup)):
                        tp = [soup[j].findAll('th')[0].text, eval(soup[j].findAll('td')[0].text),
                              soup[j].findAll('td')[1].text,
                              soup[j].findAll('td')[2].text, soup[j].findAll('td')[3].text,
                              soup[j].findAll('th')[1].text]
                        self.ls.append(tp)
                    page += 1
        global_ms.text_print.emit(self.progress("Finish!!!"))


if __name__ == "__main__":
    app = QApplication([])
    SinaStats = SinaStatsGUI()
    SinaStats.ui.show()
    app.exec_()
