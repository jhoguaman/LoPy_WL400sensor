from network import WLAN
import socket
from machine import ADC
import pycom
import time
import sys
pycom.heartbeat(False)

host=''
port=80

#Parámetros: calibración del sensor wl400
Vmin=763        #~205mV
V1=856          #~230mV
h1=14           #altura[cm] correspondiente a V1

#method:cálculo de la pendiente
def pendiente(Vmin,Vx,hx):
    m=(Vx-Vmin)/(hx)
    #aquí:código para almacenar en la flash m y Vmin
    return m

#
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
    print('into wifi')
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
        print('into while')
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


m=pendiente(Vmin,V1,h1)
print('pendiente: ',m)


wifi()
#Vx=adc()
#waterLevel(Vmin,m,Vx)
