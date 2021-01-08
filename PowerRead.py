#!/usr/bin/python3

#Querry power meter and publish MQTT message
#ServerPi/TotalPower
#(month,day,hr,minute,sec,total_power,daily_energy)
#Version2 implements watchdog timer if connection to MyEyeDro takes too long without an exception
#Sends a message for power and Energy received from MyEyeDro energy onitor on MQTT
#Removed WDT

import json
import urllib3
import time
from timeloop import Timeloop
from datetime import timedelta
import paho.mqtt.client as mqtt
import atexit


tl = Timeloop()

i = 0
day = 0
energy = 0.0
powerMax = 0

broker_address="192.168.50.201"
#broker_address="iot.eclipse.org" #to use external broker
client = mqtt.Client("ServerPi")
client.connect(broker_address)
client.loop_start() #handles reconnecting.  Runs in separate thread to let main thread run
#client.loop_forever() #Stops main thread for mqtt loop
#client.reinitialise()
    

#Get power from JSON query of MyEyeDro power monitor
def getPowerData():
    try:
        
        url = "http://192.168.50.20:8080/getdata"
        #timeout = Timeout(connect=10,read=10)
        http=urllib3.PoolManager()
        data = http.request('GET',url)
        obj = json.loads(data.data.decode("utf-8"))
        powera = obj['data'][0][3]
        powerb = obj['data'][1][3]
        
        #print("Power A ",powera, "\n Power B ", powerb)
        power = powera + powerb
        return power
    except:
        data.close()
        traceback.print_exc()
        print("Data Connection Closed")
        return 0

def msgTotalPower():
    power = getPowerData()
    if power <= 0:
        time.sleep(2)
        power = getPowerData()
    if power <=0:
        time.sleep(2)
        power = getPowerData()
    messageTP = ('"'+","+str(power)+","+'"')
    client.publish("ServerPi/TotalPower",messageTP)
    #global sampleTime
    #print(sampleTime,power)
    return power

def msgEnergy(powerMax): #Energy used for the last 60 seconds
    global energy
    #print(round(energy,1), " Wh")
    messageEnergy = ('"'+","+str(round(energy,1))+","+str(powerMax)+","+'"')
    client.publish("ServerPi/Energy",messageEnergy)
    energy = 0
        
def getCurrentTime():
    #timeNow = time.localtime()
    #year = time.localtime().tm_year
    #month = time.localtime().tm_mon
    day = time.localtime().tm_mday
    hour = time.localtime().tm_hour
    minute = time.localtime().tm_min
    second = time.localtime().tm_sec
    return day,hour,minute,second

def Average(l):
    avg = sum(l)/len(l)
    return avg

sampleTime = 5 #can be any factor of 60(1,2,3,4,5,6,10,12,15,20,30)
day,hour,minute,second = getCurrentTime()
secondPast = second #Seconds from last timer execution
minutePast = minute
missingTime = 1 #Increment to 1,2,3,etc. if missing a time block

try:
    while True:
        day,hour,minute,second = getCurrentTime()
        tmrTotalPower = second%sampleTime
        
        if tmrTotalPower == 0:
            missingTime = ((minute-minutePast)*60+(second-secondPast))/sampleTime
            power = msgTotalPower()
            if power is None:
                print("None Found")
                time.sleep(3)
                power = msgTotalPower()
                print("Power ",power)
            secondPast = second
            if powerMax < power:
                powerMax = power
            if missingTime <= 0:
                print("missingTime less than zero, corrected")
                missingTime = 1
            energy += power*missingTime * sampleTime / 3600 #convert to Wh
            if minute == (minutePast+1):
                msgEnergy(powerMax)
                powerMax = 0
            minutePast = minute
            if missingTime>1:
                print("Missing Time ",missingTime,day,hour,minute,second)
        
        missimgTime =1
        
        time.sleep(1)
except:
    client.loop_stop()
    print("MQTT loop closed")
    
