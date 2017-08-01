from network import WLAN
from machine import I2C, RTC, Timer, Pin
import ustruct
import socket
import pycom
import time
import sys

pycom.heartbeat(False)

i2c = I2C(0)                         # create on bus 0
i2c = I2C(0, I2C.MASTER)             # create and init as a master
i2c.init(I2C.MASTER, baudrate=9600) # init as a master


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
            if os.stat(pathConfigFile+str(lenFile))[6]==8:
                print('configFile a leer:', pathConfigFile+str(lenFile))
                config=readFile(pathConfigFile,'r',str(lenFile))
            else:
                print('error en config:',pathConfigFile+str(lenFile))
                print('leyendo:',pathConfigFile+str(lenFile-1))
                config=readFile(pathConfigFile,'r',str(lenFile-1))

    except Exception as e:#MyError:
        print("configFile doesn't exist")
        #Parámetros: calibración del sensor wl400 (valores obtenidos en basea mediciones, pueden ser modificados)
        vMin=2754        #~mV
        hMin=70
        v1=2900          #~mV
        h1=140           #altura[mm] correspondiente a V1
        ##config=generateConfig(vMin,v1,h1)
        config=ustruct.pack('HHHH',vMin,hMin,v1,h1)     #estructura el archivo de configuracion 2bytes para cada valor
        #creación del directorio configFile que contendrá los archivos wl400_0x
        os.mkdir('/flash/configFile')
        writeFile(pathConfigFile,'wb',1,config)
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

#readFile: Lee un archivo, path:ubicación del archivo, mode: tipo de escritura 'w' o 'wb'
#typeFile:En caso de haber mas de un archivo con nombres similares, se especifica la variacion que tiene al final
#file:archivo a guardar
def writeFile(path,mode,typeFile,files):
    f = open(str(path)+str(typeFile), mode)
    f.write(files)
    f.close()
    #print('saved fiel:', ustruct.unpack('HHHH',files))

#generateConfig:calcula la pendiente y devuelve la estructura config:Vmin_hMin_m
#Vmin:voltaje mínimo Vx:voltaje tomado en la calibración hx:altura de calibración
def slope(config):
    config=ustruct.unpack('HHHH',config)
    m=(config[2]-config[0])/(config[3]-config[1])
    equationParameters=(config[0],config[1],m)
    return equationParameters

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
    vMin=ads1115Read()
    p1=ustruct.pack('HH',vMin,0)
    writeFile(pathConfigFile,'wb',2,p1)
    msg='altura inicial calibrada en LoPy'
    return True, msg
#h1Calibration:almacena el valor Vx junto al Vmin (Vmin_Vx)
def h1Calibration(hx):
    v1=ads1115Read()
    p1=readFile(pathConfigFile,'rb',2) #tupla binaria con p1
    p1=ustruct.unpack('HH',p1)
    config=ustruct.pack('HHHH',p1[0],p1[1],v1,int(hx[1:]))
    writeFile(pathConfigFile,'wb',2,config)
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
    wlan = WLAN(mode=WLAN.AP, ssid='waterLevel', auth=(WLAN.WPA2,'ucuenca1234'), channel=7, antenna=WLAN.INT_ANT)
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
def waterLevel(equationParameters,vX):
    hX=((vX-equationParameters[0])/equationParameters[2])+equationParameters[1]
    print('altura Vx: ',hX)
    hX=ustruct.pack('H',round(abs(hX))) ####quitar abs y hacer un if para valores negativos
    return hX

def _transmissionAlarm(alarm):
#    print("alarma 20seg ")
    global timeStamp
    timeStamp=rtc.now()
#    print(timeStamp[:7])
    global transmissionMain
    transmissionMain=True

#_measurementAlarm: alarma de mediciones (cada 10 Seg)
def _measurementAlarm(alarm):
    print("measurement alarm")
    global updateAlarm, measurementAlarm
    if updateAlarm:
        measurementAlarm.cancel()
        measurementAlarm = activeAlarmM(measurementTime*60)
        updateAlarm=False
    global timeStamp_measurement
    timeStamp_measurement=rtc.now()
    print(timeStamp_measurement[:7])
    global measurementMain
    measurementMain=True

def activeAlarmM(segM):
    print('alarma activada cada',segM)
    measurementAlarm = Timer.Alarm(_measurementAlarm, segM, periodic=True)
    return measurementAlarm

def activeAlarmT():
    transmissionAlarm = Timer.Alarm(_transmissionAlarm, 60.0, periodic=True)
    return transmissionAlarm

def loraTransmission(value):
    print('loRaTransmission',value)

#statisticValue: recibe la lista currentFileInt que contiene los valores tomados cada 10seg
#y calcula los valores promedio, mínimo y máximo. Estos valores se empaquetan como binarios
#siendo su tamaño 2, 1 y 1 bytes respectivamente.
def statisticValue(currentFileInt):
    avgVal=int(sum(currentFileInt)/len(currentFileInt))
    maxDel=max(currentFileInt)-avgVal
    minDel=avgVal-min(currentFileInt)
    value=ustruct.pack('HBB',avgVal,minDel,maxDel)
    return value

def ads1115Write():
    data = ustruct.pack('>BH', 0x01,0xC4,0x83)
    i2c.writeto(0x48, data)
    time.sleep(0.5)

def ads1115Read():
    data = i2c.readfrom_mem(0x48, 0x00, 2 )
    time.sleep(0.1)
    vX=ustruct.unpack('>h', data)[0]
    print(vX)
    return vX

def pin_handler(arg):
    print('ingreso pin han')
    print("got an interrupt in pin %s" % (arg.id()))
    global wifiMain
    wifiMain=True


rtc = RTC()
dateTime=(2014, 5, 1, 4, 58, 50, 0, 0)
clockSynchronization(dateTime)
print('hora actual: ',rtc.now())

print('init program')
config=configFile()
print('config parameters: ',ustruct.unpack('HHHH',config))
equationParameters=slope(config)
print('equationParameters',equationParameters)
logsDir()
ads1115Write()

def segAlarm():
    timeStampM=rtc.now()
    minM = measurementTime-(timeStampM[4] % measurementTime)
    segM=minM*60-timeStampM[5]
    return segM

global measurementTime, updateAlarm     #measurementTime: tiempo en minutos para la medida, updateAlarm: habilita la condición en measurementAlarm para reestablecer cada measurementTime.
measurementTime=1
updateAlarm =True

segM=segAlarm()

####ACTIVAR LA ALARMA**********************************
measurementAlarm = activeAlarmM(segM)
###transmissionAlarm =activeAlarmT()
#***************************************************

transmissionMain=False
measurementMain=False

sendTime=3      #tiempo para hacer la transmision en minutos
storeTime=3     #almacenamiento de datos cada hora (la poscicion 3 representa la hora- 2 el día)
#os.remove('logsDir/currentFile')
#tm=os.stat('logsDir/currentFile')[6]   #tamaño de un archivoos
typeWrite="wb"

wifiMain=False

p_in = Pin('P8', mode=Pin.IN, pull=Pin.PULL_UP)
p_in.callback(Pin.IRQ_FALLING , pin_handler)

while True:
#for cycles in range(0): # stop after 10 cycles
    if wifiMain:
        measurementAlarm.cancel()
        print('ingresa a la calibracion mediante WIFI, 5 segundos para desactivar')
        #time.sleep(5)
        wifi()
        updateAlarm =True
        segM=segAlarm()
        measurementAlarm = activeAlarmM(segM)

        print('init program: new configFile after wifi configuration')
        config=configFile()
        print('config parameters: ',ustruct.unpack('HHHH',config))
        equationParameters=slope(config)
        print('equationParameters',equationParameters)

        wifiMain=False

    if measurementMain:
        measurementMain=False
        print('mediciones del nivel de agua')
        #Vx=adc()
        time.sleep(0.1)
        #Vx= adc_c.value()
        #time.sleep(0.1)
        vX=ads1115Read()
        hX=waterLevel(equationParameters,vX)
        print(ustruct.unpack('H', hX)[0])
        #print(vX,round(hX),'[mm]',round(hX/10),'[cm]')
        ####hxBin=waterLevel(config,Vx)
        #hxBin=ustruct.pack('H',Vx)
        #writeFile(pathCurrentFile,typeWrite,'',hxBin)
        #time.sleep(1.5)
        #print(timeStamp_measurement)
        timeStampEpoch=3600*(timeStamp_measurement[3])+60*(timeStamp_measurement[4])+(timeStamp_measurement[5])
        print(timeStampEpoch)

        record=ustruct.pack('HH', timeStampEpoch,ustruct.unpack('H', hX)[0])
        print('record',ustruct.unpack('HH', record))
        dayDate=str(timeStamp_measurement[0])+str(timeStamp_measurement[1])+str(timeStamp_measurement[3])+'.log'    #cambiar 3 a 2 para el almacenamiento de archivos diario
        #print(dayDate)
        writeFile(pathLogs,"ab",dayDate,record)             #almacenamiento en el archivo diario
        writeFile(pathCurrentFile,typeWrite,'',record)      #almacenamiento en el archivo temporal

        #leer datos int para corroborar el almacenamiento*********
        #*********************************************************
        currentFileBin=readFile(pathLogs,'rb',dayDate)
        tmFile=os.stat(pathLogs+dayDate)[6]
        print('num de datos alamacenados:', tmFile/4)
        fmt='H'*(int(tmFile/2))
        currentFileInt=ustruct.unpack(fmt,currentFileBin)
        print(currentFileInt)
        #*********************************************************
        #leer datos int para corroborar el almacenamiento*********
        #*********************************************************
        temporalFile=readFile(pathCurrentFile,'rb','')
        tmFile=os.stat(pathCurrentFile)[6]
        print('num de datos alamacenados:', tmFile/4)
        fmt='H'*(int(tmFile/2))
        currentFileInt=ustruct.unpack(fmt,temporalFile)
        print(currentFileInt)
        #*********************************************************


        if (timeStamp_measurement[4]/sendTime)-int(timeStamp_measurement[4]/sendTime)==0 and timeStamp_measurement[5]==0:
            transmissionMain=True

        typeWrite="ab"




    if transmissionMain:
        print('transmision de datos LoRa')
        #leer datos int para corroborar el almacenamiento*********
        #*********************************************************
        #currentFileBin=readFile(pathCurrentFile,'rb','')
        #tmFile=os.stat('logsDir/currentFile')[6]
        #print('num de datos alamacenados:', tmFile/2)
        #fmt='H'*(int(tmFile/2))
        #currentFileInt=ustruct.unpack(fmt,currentFileBin)
        #print(currentFileInt)
        #*********************************************************
        #value=statisticValue(currentFileInt)            #value variable binaria: contiene 2bytes 1byte 1byte--> avg,min,max respectivamente
        #valueint=ustruct.unpack('HBB',value)
        loraTransmission(hX)
        #print('valores estadisticos: ',valueint)
        #print(timeStamp)
        #if (timeStamp_measurement[4]/storeTime)-int(timeStamp_measurement[4]/storeTime)==0 and timeStamp_measurement[5]==0:
        #fecha=str(timeStamp_measurement[0])+str(timeStamp_measurement[1])+str(timeStamp_measurement[3])+'.log'
        #print(fecha)
        #writeFile(pathLogs,"ab",fecha,value)
        typeWrite="wb"          #luego de la trasmision y el almacenamiento de value que representa el resultado del currentFile. se sobreescribe el currentFile
        transmissionMain=False





    #transmissionAlarm.cancel()
