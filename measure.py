import acconeer.exptool as et
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QGraphicsScene
import sys
from PyQt5 import uic
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QPixmap, QImage
import numpy as np
import cv2
import qimage2ndarray
from queue import Queue

class abms(QMainWindow):
    def __init__(self):
        super(abms, self).__init__()
        uic.loadUi("./UI/acconeer.ui", self)
        self.show()
        self.sWidget.setCurrentIndex(0)
        self.aRCS.triggered.connect(self.RCS)
        self.pRCS.clicked.connect(self.RCS)
        self.aDistance.triggered.connect(self.distanceWave)
        self.pDistance.clicked.connect(self.distanceWave)
        self.aFrequency.triggered.connect(self.frequencyWave)
        self.pFrequency.clicked.connect(self.frequencyWave)

        self.acconeer_distance = np.zeros(900)
        self.cnt = 0
        self.dataQueue = Queue()
        self.maxQueue = Queue()

        self.init()

        timer = QTimer(self)
        timer.timeout.connect(self.acconeer)
        timer.start()

        distanceTimer = QTimer(self)
        distanceTimer.timeout.connect(self.distance) 
        distanceTimer.start()

    def frequencyWave(self):
        self.sWidget.setCurrentIndex(3)

    def distanceWave(self):
        self.sWidget.setCurrentIndex(2)

    def RCS(self):
        self.sWidget.setCurrentIndex(1)

    def init(self):
        args = et.utils.ExampleArgumentParser().parse_args()
        et.utils.config_logging(args)

        if args.socket_addr:
            self.client = et.SocketClient(args.socket_addr)
        elif args.spi:
            self.client = et.SPIClient()
        else:
            port = args.serial_port or et.utils.autodetect_serial_port()
            self.client = et.UARTClient(port)

        config = et.configs.EnvelopeServiceConfig()
        config.sensor = args.sensors
        # config.range_interval = [0.2, 0.4] # length = 414
        # config.range_interval = [0.2, 0.3] # length = 207
        # config.range_interval = [0.2, 0.5] # length = 620
        config.range_interval = [0.2, 0.5]  # length = 620
        config.update_rate = 30

        session_info = self.client.setup_session(config)
        print("Session info:\n", session_info, "\n")

        self.client.start_session()

        interrupt_handler = et.utils.ExampleInterruptHandler()
        print("Press Ctrl-C to end session\n")

    def acconeer(self):
        canvas = np.zeros((1000, 650, 3), np.uint8)
        info, self.data = self.client.get_next()
        self.dataQueue.put(self.data)

        canvas = cv2.line(canvas, (3, 3), (3, 980), (255, 0, 0), 2)
        canvas = cv2.line(canvas, (3, 970), (650, 970), (255, 0, 0), 2)

        for i in range(0, 619):
            canvas = cv2.line(canvas, (i+6, 1000 - int(self.data[i])), ((i+1)+6, 1000 - int(self.data[i+1])), (255, 255, 255), 2)
        
        h, w, c = canvas.shape
        qImg = QImage(canvas.data, w, h, w*c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qImg)

        self.image.setPixmap(pixmap)
        self.image.setScaledContents(1)
        self.image.show()


    def distance(self):

        self.distance_canvas = np.zeros((1000, 1000, 3), np.uint8)
        self.distance_data = self.dataQueue.get()
        self.acconeer_distance[self.cnt] = np.argmax(self.distance_data) 
        self.cnt = self.cnt + 1

        if self.cnt == 900:
            self.cnt = 0

        self.distance_canvas = cv2.line(self.distance_canvas, (3, 3), (3, 980), (255, 0, 0), 2)
        self.distance_canvas = cv2.line(self.distance_canvas, (3, 980), (930, 980), (255, 0, 0), 2)

        for i in range(0, 899):
            y1 = 1400 - int(self.acconeer_distance[i])
            y2 = 1400 - int(self.acconeer_distance[i+1])
            y1 = int(y1 * 0.7)
            y2 = int(y2 * 0.7)
            self.distance_canvas = cv2.line(self.distance_canvas, (i+6, y1), ((i+1)+6, y2), (255, 255, 255), 1)
        
        h, w, c = self.distance_canvas.shape
        qImg = QImage(self.distance_canvas.data, w, h, w*c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qImg)

        self.qdistance.setPixmap(pixmap)
        self.qdistance.setScaledContents(1)
        self.qdistance.show()
         		
        self.frequency_canvas = np.zeros((1000, 980, 3), np.uint8)
        self.frequency_data = self.acconeer_distance
        Ts = 0.03
        Fs = 1/Ts 
        n = len(self.frequency_data) 					
        k = np.arange(n)
        T = n/Fs
        freq = k/T

        self.Y = abs(np.fft.fft(self.frequency_data))
        x_fft = np.fft.fftfreq(900, 1/30)

        #breath = np.argmax(self.Y)
        print("#########################################################################")
        self.Y[0] = 0
        for i in range(450, 900, 1):
            self.Y[i] = 0
        breath = np.argmax(self.Y)
        print("Index : {}, Breath : {}, Frequency : {}Hz".format(breath, x_fft[breath] * 60, x_fft[breath]))

        frequency_canvas = cv2.line(self.frequency_canvas, (3, 3), (3, 980), (255, 0, 0), 2)
        frequency_canvas = cv2.line(self.frequency_canvas, (3, 980), (930, 980), (255, 0, 0), 2)


        for i in range(0, 899, 1):
            y1 = 2000 - int(self.Y[i])
            y2 = 2400 - int(self.Y[i+1])
            y1 = int(y1 * 0.4)
            y2 = int(y2 * 0.4)
            self.frequency_canvas = cv2.line(self.frequency_canvas, (i+6, y1), ((i+1)+6, y2), (255, 255, 255), 1)
        
        h, w, c = self.frequency_canvas.shape
        qImg = QImage(self.frequency_canvas.data, w, h, w*c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qImg)

        self.qfrequency.setPixmap(pixmap)
        self.qfrequency.setScaledContents(1)
        self.qfrequency.show()


        #print(info, "\n", data, "\n")
        #print("Disconnecting...")
        #client.disconnect()

app = QApplication(sys.argv)
win = abms()
app.exec_()
