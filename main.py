from network import WLAN
import socket
from machine import ADC
import pycom
import time
import sys

pycom.heartbeat(False)
host=''
port=80

#configFile: lee los valores de configuracion de la memoria flash,
#existen dos archivos de configuracion: wl400_00 y wl400_01, el 1ero se crea
#por defecto con parámetros pre-establecidos, y el 2do se crea al momento de
#calibrar el dispositivo por medio del wifi.
def configFile():
    try:
        files=os.listdir('configFile')
        lenFile=len(files)

        if files[lenFile-1]=='wl400_0'+str(lenFile-1):
            print('configFile a leer:', files[lenFile-1])
            f = open('/flash/configFile/wl400_0'+str(lenFile-1), 'r')
            config=f.readall()
            f.close()
    except Exception as e:#MyError:
        print("configFile doesn't exist")
        #Parámetros: calibración del sensor wl400 (valores obtenidos en basea mediciones, pueden ser modificados)
        Vmin=763        #~205mV
        V1=856          #~230mV
        h1=14           #altura[cm] correspondiente a V1
        m=pendiente(Vmin,V1,h1)
        config=str(Vmin)+'_'+str(m)
        #creación del directorio configFile que contendrá los archivos wl400_0x
        os.mkdir('/flash/configFile')
        writeFile(1,config)
        time.sleep(0.1)
    return config

def writeFile(numFile,config):
        f = open('/flash/configFile/wl400_0'+str(numFile-1), 'w')
        f.write(config)
        f.close()

#method:cálculo de la pendiente
def pendiente(Vmin,Vx,hx):
    m=(Vx-Vmin)/(hx)
    #aquí:código para almacenar en la flash m y Vmin
    return m

#calibrationType: Llamado desde el method:wifi, redirecciona a los métodos:
#calibrationType, h0Calibration, o h1Calibration. Según sea el parámetro a calibrar
def calibrationType(argCalibration):
    print('argCalibration', argCalibration)
    switcher = {
        97: h0Calibration,
        98: h1Calibration,
        99: finishCalibration,
    }
    func = switcher.get(argCalibration)       # Get the function from switcher dictionary
    return func()                       # Execute the function

def h0Calibration():
    
    writeFile(2,config)
    msg='altura inicial calibrada en LoPy'
    pycom.rgbled(False)
    return True,msg

def h1Calibration():
    msg='hx calibrado en LoPy'
    pycom.rgbled(False)
    return True,msg

def finishCalibration():
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

        wifiSocket, msg=calibrationType(recibido[0])
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
    for cycles in range(10): # stop after 10 cycles
        #pycom.rgbled(0x007f00) # green
        Vx= adc_c.value()
        #pycom.rgbled(0x7f7f00) # yellow
        print("ADC value:", Vx)
        time.sleep(1)
    adc.deinit()
    return Vx

def waterLevel(Vmin,m,Vx):
    hx=(Vx-Vmin)/m
    print('altura Vmin: ',hx)
    return hx



print('init program')
config=configFile()
print('config parameters: ',config)


#wifi()
#Vx=adc()
#waterLevel(Vmin,m,Vx)
