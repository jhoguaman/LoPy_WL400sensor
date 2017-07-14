from network import WLAN
from machine import ADC, RTC, Timer
import struct
import socket
import pycom
import time
import sys

pycom.heartbeat(False)

#host-port:comunicación vía socket con la app
host=''
port=80

#pathConfigFile:archivo de configuracion, contiene el Vmin y la pendiente
#pathLogs:directorio donde se almacenan archivos diarios con info de avg,min,max de cada 5min
#pathCurrentFile:archivo que almacena el hx cada 5min
pathConfigFile='/flash/configFile/wl400_0'
pathLogs='/flash/logsDir/wl'
pathCurrentFile='/flash/logsDir/currentFile'

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
        files=os.listdir('/flash/configFile')
        lenFile=len(files)
        print('lenFile :', lenFile)
        print('leer :', files[lenFile-1])
        if files[lenFile-1]=='wl400_0'+str(lenFile):
            print('configFile a leer:', pathConfigFile+str(lenFile))
            config=readFile(pathConfigFile,'r',str(lenFile))
    except Exception as e:#MyError:
        print("configFile doesn't exist")
        #Parámetros: calibración del sensor wl400 (valores obtenidos en basea mediciones, pueden ser modificados)
        #Vmin=763        #~205mV
        Vmin=0        #solo para hacer pruebas y no de valores negativos ya que el sensor no esta conectado
        V1=856          #~230mV
        h1=140           #altura[mm] correspondiente a V1
        config=generateConfig(Vmin,V1,h1)
        #creación del directorio configFile que contendrá los archivos wl400_0x
        os.mkdir('/flash/configFile')
        writeFile(pathConfigFile,'w',1,config)
        time.sleep(0.1)
    return config

#logsDir: Verifica que esté creado el dir para el almacenamiento de logs, si no existe lo crea
def logsDir():
    try:
        print('reading logsDir')
        files=os.listdir('logsDir')
        #os.remove(pathCurrentFile)
    except Exception as e:
        print("logsDir doesn't exist")
        os.mkdir('/flash/logsDir')
        time.sleep(0.1)

#readFile: Lee un archivo, path:ubicación del archivo, mode: tipo de lectura 'r' o 'rb'
#typeFile:En caso de haber mas de un archivo con nombres similares, se especifica la variacion que tiene al final
def readFile(path,mode,typeFile):
    f = open(path+str(typeFile), mode)
    config=f.readall()
    f.close()
    return config

#readFile: Lee un archivo, path:ubicación del archivo, mode: tipo de lectura 'w' o 'wb'
#typeFile:En caso de haber mas de un archivo con nombres similares, se especifica la variacion que tiene al final
#file:archivo a guardar
def writeFile(path,mode,typeFile,files):
    f = open(str(path)+str(typeFile), mode)
    f.write(files)
    f.close()

#generateConfig:calcula la pendiente y devuelve config:Vmin_m
#Vmin:voltaje mínimo Vx:voltaje tomado en la calibración hx:altura de calibración
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
#h0Calibration:almacena el valor de Vmin
def h0Calibration(none):
    Vmin=adc()
    writeFile(pathConfigFile,'w',2,str(Vmin))
    msg='altura inicial calibrada en LoPy'
    return True, msg
#h1Calibration:almacena el valor Vx junto al Vmin (Vmin_Vx)
def h1Calibration(hx):
    Vx=adc()
    Vmin=readFile(pathConfigFile,'r',2)
    if Vmin.find('_')!=-1:
        Vmin=Vmin[:Vmin.find('_')]
    config=generateConfig(int(Vmin),int(Vx),int(hx[1:]))
    writeFile(pathConfigFile,'w',2,config)
    msg='hx calibrado en LoPy'
    return True,msg
#finishCalibration: finaliza la calibración, desactiva el wifi
def finishCalibration(none):
    msg='Finish wifi LoPy'
    pycom.rgbled(False)
    return False,msg
#wifi:Activa el wifi ssid:wipy-wlan, clave: ucuenca1234. Levante un socket con ipServer:"host" y puerto:"port" (definidos al inicio)
#luego del proceso de calibración se desactiva el wifi.
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


    #for cycles in range(1): # stop after 10 cycles
        #pycom.rgbled(0x007f00) # green

    time.sleep(0.5)
    Vx= adc_c.value()
    time.sleep(0.1)

    print("ADC value:", Vx)
#    adc.deinit()
    return Vx

#waterLevel:Calcula la profundidad del agua, Vx:nuevo valor del sensor,
#config: contiene los valores de Vmin y m correspondiente a los parametros de la
#ecuación lineal, retorna hxInt es el valor int incluido el un decimal
def waterLevel(config,Vx):
    Vmin=config[:config.find('_')]
    m=config[config.find('_')+1:]
    hx=(Vx-int(Vmin))/float(m)
    hxInt=int(hx)                 #1decimal a recuperar
    print('altura Vx: ',hxInt)
    hxBin=struct.pack('H',hxInt)
    return hxBin

def _transmissionAlarm(alarm):
#    print("alarma 20seg ")
    global timeStamp
    timeStamp=rtc.now()
#    print(timeStamp[:7])
    global transmissionMain
    transmissionMain=True

#_measurementAlarm: alarma de mediciones (cada 10 Seg)
def _measurementAlarm(alarm):
#    print("alarma 5seg")
    global timeStamp_measurement
    timeStamp_measurement=rtc.now()
#    print(timeStamp_measurement[:7])
    global measurementMain
    measurementMain=True

def activeAlarmM():
    measurementAlarm = Timer.Alarm(_measurementAlarm, 2, periodic=True)
    return measurementAlarm

def activeAlarmT():
    transmissionAlarm = Timer.Alarm(_transmissionAlarm, 60.0, periodic=True)
    return transmissionAlarm

def loraTransmission(value):
    pass

#statisticValue: recibe la lista currentFileInt que contiene los valores tomados cada 10seg
#y calcula los valores promedio, mínimo y máximo. Estos valores se empaquetan como binarios
#siendo su tamaño 2, 1 y 1 bytes respectivamente.
def statisticValue(currentFileInt):
    avgVal=int(sum(currentFileInt)/len(currentFileInt))
    maxDel=max(currentFileInt)-avgVal
    minDel=avgVal-min(currentFileInt)
    value=struct.pack('HBB',avgVal,minDel,maxDel)
    return value


rtc = RTC()
dateTime=(2014, 5, 1, 4, 59, 40, 0, 0)
clockSynchronization(dateTime)
print('hora actual: ',rtc.now())

print('init program')
config=configFile()
print('config parameters: ',config)
logsDir()

adc = ADC(id=0)
adc.init(bits=12)
#adc_c = adc.channel(pin='P13',attn=ADC.ATTN_11DB)  #ADC pin input range is 0-3.3V with 11DB.
#ADC.ATTN_0DB ADC.ATTN_2_5DB ADC.ATTN_6DB ADC.ATTN_11DB
global adc_c
adc_c = adc.channel(pin='P15',attn=ADC.ATTN_11DB)                      #ADC pin input range is 0-1.1V.


calibAlarm=True
while calibAlarm:
    timeStamp1=rtc.now()
    if (timeStamp1[5]/10)-int(timeStamp1[5]/10)==0:
        calibAlarm=False
#ACTIVAR LA ALARMA**********************************
measurementAlarm = activeAlarmM()
###transmissionAlarm =activeAlarmT()
#***************************************************

transmissionMain=False
measurementMain=False

sendTime=1      #tiempo para hacer la transmision en minutos
storeTime=3     #almacenamiento de datos cada hora (la poscicion 3 representa la hora) representa la hora
#os.remove('logsDir/currentFile')
#tm=os.stat('logsDir/currentFile')[6]   #tamaño de un archivoos
typeWrite="wb"

wifiPrueba=False

while True:
#for cycles in range(0): # stop after 10 cycles
    if wifiPrueba:
        #measurementAlarm.cancel()
        wifi()
        wifiPrueba=False

    if measurementMain:
        print('mediciones del nivel de agua')
        #Vx=adc()
        time.sleep(0.1)
        Vx= adc_c.value()
        #time.sleep(0.1)
        if Vx!=0:
            print("ADC value:", Vx)
        ####hxBin=waterLevel(config,Vx)
            hxBin=struct.pack('H',Vx)
            writeFile(pathCurrentFile,typeWrite,'',hxBin)
        #time.sleep(1.5)
        #print(timeStamp_measurement)

        if (timeStamp_measurement[4]/sendTime)-int(timeStamp_measurement[4]/sendTime)==0 and timeStamp_measurement[5]==0:
            transmissionMain=True

        typeWrite="ab"
        measurementMain=False


    if transmissionMain:
        print('transmision de datos LoRa')
        #leer datos int para corroborar el almacenamiento*********
        #*********************************************************
        currentFileBin=readFile(pathCurrentFile,'rb','')
        tmFile=os.stat('logsDir/currentFile')[6]
        print('num de datos alamacenados:', tmFile/2)
        fmt='H'*(int(tmFile/2))
        currentFileInt=struct.unpack(fmt,currentFileBin)
        print(currentFileInt)
        #*********************************************************
        value=statisticValue(currentFileInt)            #value variable binaria: contiene 2bytes 1byte 1byte--> avg,min,max respectivamente
        valueint=struct.unpack('HBB',value)
        loraTransmission(value)
        print('valores estadisticos: ',valueint)
        #timeStampEpoch=timeStamp[4]*60+timeStamp[5]
        #print(timeStamp)
        #if (timeStamp_measurement[4]/storeTime)-int(timeStamp_measurement[4]/storeTime)==0 and timeStamp_measurement[5]==0:
        fecha=str(timeStamp_measurement[0])+str(timeStamp_measurement[1])+str(timeStamp_measurement[3])+'.log'
        print(fecha)
        writeFile(pathLogs,"ab",fecha,value)
        typeWrite="wb"          #luego de la trasmision y el almacenamiento de value que representa el resultado del currentFile. se sobreescribe el currentFile
        transmissionMain=False





    #transmissionAlarm.cancel()
