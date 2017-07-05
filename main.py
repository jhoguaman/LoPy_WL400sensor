from network import WLAN
from machine import ADC, RTC, Timer
import socket
import pycom
import time
import sys




pycom.heartbeat(False)
host=''
port=80

pathConfigFile='/flash/configFile/wl400_0'
pathLogs='/flash/Logs/wl'
pathCurrentFile='/flash/Logs/currentFile'

#clockSynchronization: Sincronización del rtc con el dateTime recibido por el gps
def clockSynchronization(dateTime):
    rtc.init(dateTime)
    print(rtc.now())


#configFile: lee los valores de configuracion de la memoria flash,
#existen dos archivos de configuracion: wl400_00 y wl400_01, el 1ero se crea
#por defecto con parámetros pre-establecidos, y el 2do se crea al momento de
#calibrar el dispositivo por medio del wifi.
def configFile():
    try:
        files=os.listdir('configFile')
        lenFile=len(files)
        print('leer :', files[lenFile-1])
        if files[lenFile-1]=='wl400_0'+str(lenFile):
            print('configFile a leer:', files[lenFile-1])
            config=readFile(pathConfigFile,lenFile)

    except Exception as e:#MyError:
        print("configFile doesn't exist")
        #Parámetros: calibración del sensor wl400 (valores obtenidos en basea mediciones, pueden ser modificados)
        Vmin=763        #~205mV
        V1=856          #~230mV
        h1=14           #altura[cm] correspondiente a V1
        config=generateConfig(Vmin,V1,h1)
        #creación del directorio configFile que contendrá los archivos wl400_0x
        os.mkdir('/flash/configFile')
        writeFile(pathConfigFile,'w',1,config)
        time.sleep(0.1)
    return config

def readFile(path,numFile):
    f = open(path+str(numFile), 'r')
    config=f.readall()
    f.close()
    return config


def writeFile(path,mode,numFile,config):
    f = open(str(path)+str(numFile), mode)
    f.write(config)
    f.close()

#generateConfig:calcula la pendiente y devuelve config:Vmin_m
def generateConfig(Vmin,Vx,hx):
    m=(Vx-Vmin)/(hx)
    config=str(Vmin)+'_'+str(m)
    return config

#calibrationType: Llamado desde el method:wifi, redirecciona a los métodos:
#h0Calibration, h1Calibration o finishCalibration. Según sea el parámetro a calibrar
def calibrationType(argCalibration):
    print('argCalibration: ', argCalibration[0])
    switcher = {
        97: h0Calibration,
        98: h1Calibration,
        99: finishCalibration,
    }
    func = switcher.get(argCalibration[0])       # Get the function from switcher dictionary
    return func(argCalibration)                  # Execute the function

def h0Calibration(none):
    Vmin=adc()
    writeFile(pathConfigFile,'w',2,str(Vmin))
    msg='altura inicial calibrada en LoPy'
    return True, msg

def h1Calibration(hx):
    Vx=adc()
    Vmin=readFile(pathConfigFile,2)
    if Vmin.find('_')!=-1:
        Vmin=Vmin[:Vmin.find('_')]
    config=generateConfig(int(Vmin),int(Vx),int(hx[1:]))
    writeFile(pathConfigFile,'w',2,config)
    msg='hx calibrado en LoPy'
    return True,msg

def finishCalibration(none):
    msg='Finish wifi LoPy'
    pycom.rgbled(False)
    return False,msg

def wifi():
    print('wifi init')
    pycom.rgbled(0x008B8B) # blue
    wlan = WLAN(mode=WLAN.AP, ssid='wipy-wlan', auth=(WLAN.WPA2,'ucuenca1234'), channel=7, antenna=WLAN.INT_ANT)
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        serversocket.bind(socket.getaddrinfo(host,port)[0][-1])     #ipServer 192.168.4.1
    except Exception as e:
        print('bind failed, error code: ',str(e[0]))
        sys.exit()

    serversocket.listen(1)
    print('socket is now listening over port: ', port)

    wifiSocket=True

    while (wifiSocket):
        print('socket init')
        sc, addr = serversocket.accept()
        print('sc: ',sc,' addr: ',addr)

        recibido = sc.recv(16)
        print('valor recibido :', recibido)
        #print('tipo :', type(recibido))
        #dato=recibido.decode("utf-8")
        #print('dato decode',dato)
        print('dato[0]: ',recibido[0])

        wifiSocket, msg=calibrationType(recibido)
        sc.send(msg)

    print('closing wifi and socket')
    sc.close()
    serversocket.close()
    wlan.deinit()

def adc():
    adc = ADC()
    adc.init(bits=12)
    #adc_c = adc.channel(pin='P13',attn=ADC.ATTN_11DB)  #ADC pin input range is 0-3.3V with 11DB.
    adc_c = adc.channel(pin='P13')                      #ADC pin input range is 0-1.1V.
    #for cycles in range(1): # stop after 10 cycles
        #pycom.rgbled(0x007f00) # green
    Vx= adc_c.value()
        #pycom.rgbled(0x7f7f00) # yellow
    print("ADC value:", Vx)
    time.sleep(0.5)
    adc.deinit()
    return Vx

#waterLevel:Calcula la profundidad del agua, Vx:nuevo valor del sensor,
#config: contiene los valores de Vmin y m correspondiente a los parametros de la
#ecuación lineal
def waterLevel(config,Vx):
    Vmin=config[:config.find('_')]
    m=config[config.find('_')+1:]
    hx=(Vx-int(Vmin))/float(m)
    print('altura Vx: ',hx)
    return hx

class Clock():

    def __init__(self):
        self.seconds = 0
        self.__alarm = Timer.Alarm(self._seconds_handler, 10, periodic=True)
        self.__alarm2 = Timer.Alarm(self._seconds_handler2, 60, periodic=True)

    def _seconds_handler(self, alarm):
        print("alarma 10seg ")
        timeStamp=rtc.now()
        print(timeStamp[:6])
        Vx=adc()
        waterLevel(config,Vx)


#        if self.seconds == 2:
#        alarm.cancel() # stop counting after 10 seconds


    def _seconds_handler2(self, alarm):
        print("alarma 60seg")
        timeStamp=rtc.now()
        print(timeStamp[:6])


rtc = RTC()
dateTime=(2014, 5, 1, 4, 13, 0, 0, 0)
clockSynchronization(dateTime)

print('init program')
config=configFile()
print('config parameters: ',config)

clock = Clock()
#wifi()

#Vx=adc()
#waterLevel(config,Vx)
