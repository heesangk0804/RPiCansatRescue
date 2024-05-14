import socket
import select
import json
import threading
import time
import sys

###
import sys
import time
import difflib
import smbus2                 #import SMBus module of I2C
import serial
import datetime
import pynmea2
import bme280
###

#some MPU6050 Registers and their Address
PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47

#HOST = '127.0.0.1'
BASEHOST = '192.168.1.2'  #'192.168.0.1'
BASEPORT = 2500
BASEADDR = (BASEHOST, BASEPORT)
HOST = '192.168.1.1'
PORT = 10000
BUFSIZE = 1024
ADDR = (HOST, PORT)

sensor_msg_obj = {          #also same with meshinfo_msg packet
    "msg": {
        "sender": "CanSat01",
        "receiver": None,
        "time": None
    },
    "sensor": {
        "gps": { "lat": 36.0, "lon": 127.3, "alt":  0.0 },
        "imu": { "acc": None, "gyr": None },
        "bme": { "temp": None, "pres": None, "humi": None }
    }
}

'''
clithr_event_elm = {"client"    : newclientSocket,
                    "sensor_event"  : threading.Event(),
                    "help_event"    : threading.Event()
                    }
'''

def initIMU(devaddr):
    bus.write_byte_data(devaddr, SMPLRT_DIV, 7)     #Write to sample rate reg
    bus.write_byte_data(devaddr, PWR_MGMT_1, 1)     #Write to power management register
    bus.write_byte_data(devaddr, CONFIG, 0)         #Write to Configuration register
    bus.write_byte_data(devaddr, GYRO_CONFIG, 24)   #Write to Gyro configuration register
    bus.write_byte_data(devaddr, INT_ENABLE, 1)     #Write to interrupt enable register

def read_IMU_data(devaddr, addr):
    #Accelero and Gyro value are 16-bit
    high = bus.read_byte_data(devaddr, addr)
    low = bus.read_byte_data(devaddr, addr+1)
    
    #concatenate higher and lower value
    value = ((high << 8) | low)
        
    #to get signed value from mpu6050
    if(value > 32768):
        value = value - 65536
    return value

def parseIMU(devaddr):
    #Read Accelerometer raw value
    acc_x = read_IMU_data(devaddr, ACCEL_XOUT_H)
    acc_y = read_IMU_data(devaddr, ACCEL_YOUT_H)
    acc_z = read_IMU_data(devaddr, ACCEL_ZOUT_H)
    
    #Read Gyroscope raw value
    gyro_x = read_IMU_data(devaddr, GYRO_XOUT_H)
    gyro_y = read_IMU_data(devaddr, GYRO_YOUT_H)
    gyro_z = read_IMU_data(devaddr, GYRO_ZOUT_H)
    
    #Full scale range +/- 250 degree/C as per sensitivity scale factor
    Ax = acc_x/16384.0
    Ay = acc_y/16384.0
    Az = acc_z/16384.0
    Acc_data = [Ax, Ay, Az]

    Gx = gyro_x/131.0
    Gy = gyro_y/131.0
    Gz = gyro_z/131.0
    Gyr_data = [Gx, Gy, Gz]
    
    #gyro_info = "Gx = {0:.2f} deg/s\tGy = {1:.2f} deg/s\t\tGz = {2:.2f} deg/s\r\nAx = {3:.2f} g\t\tAy = {4:.2f} g\t\tAz = {5:.2f} g\r\n".format(Gx, Gy, Gz, Ax, Ay, Az)
    return (Acc_data, Gyr_data)

def parseGPS(device):
    gps_msg = None
    for i in range(8):
        data = device.readline().decode()
        if data.find('GGA') > 0:
            gps_msg = pynmea2.parse(data)
            #print("Timestamp: %s -- Lat: %s %s -- Lon: %s %s -- Altitude: %s %s\n" 
            #        % (gps_msg.timestamp, gps_msg.lat, gps_msg.lat_dir, gps_msg.lon, gps_msg.lon_dir, gps_msg.altitude, gps_msg.altitude_units))
    if gps_msg:
        return (gps_msg.lat, gps_msg.lon, gps_msg.altitude)
    else:
        return (None, None, None)

def parseBME(bus, address, calibration_params):
    # the sample method will take a single reading and return a
    # compensated_reading object
    data = bme280.sample(bus, address, calibration_params)

    # the compensated_reading class has the following attributes
    #print(data.id)
    #print(data.timestamp)
    #print("Temperature: %.2f -- Pressure: %.2f -- Humidity: %.2f\n" % (data.temperature, data.pressure, data.humidity))
    return (data.temperature, data.pressure, data.humidity)

def meshinfo_thread():
    count = 0
    try:
        baseclientSocket.connect(BASEADDR)
        lat = 36.0
        lon = 129.3
        alt = 0.0
        print("connected base address :" + str(baseclientSocket.getpeername()))
        
        while True:
            obj = sensor_msg_obj
            #lat, lon, alt = parseGPS(uart)
            acc, gyr = parseIMU(MPU_Address)
            temp, pres, humi = parseBME(bus, BME_Address, bme_calibration_params)
            #print("sensor data calibration done\n")
            
            obj["msg"]["receiver"] = baseclientSocket.getpeername()
            obj["msg"]["time"] = now.strftime('%Y-%m-%d %H:%M:%S')
            #print("peer address, time measurement done")
            
            obj["sensor"]["gps"] = { "lat": lat, "lon": lon, "alt": alt }
            obj["sensor"]["imu"] = { "acc": acc, "gyr": gyr } # add "mag": [0.0, 0.0, 0.0]
            obj["sensor"]["bme"] = { "temp": temp, "pres": pres, "humi": humi }
            #print("sensor data pasted well to obj dictionary")
            
            data = json.dumps(obj)
            l = len(data)
            #print('data:' + str(data) + 'length:' + str(l) + '\n')
            print('meshinfo data length: ' + str(l))
            # send 2byte_len + payload to mobile
            baseclientSocket.send(l.to_bytes(2, byteorder='big') + data.encode())
            print('Sensor data sent to Base Station %s successfully\n' % str(baseclientSocket.getpeername()))
            count += 1
            time.sleep(3)
            lat = lat + 0.001
            lon = lon - 0.001
            #print("Done")
        #print("Loop done")
                    
    except Exception as e:
        print('Exception at meshinfo_thread; %s:%s'%BASEADDR)
        return




def sensor_thread(clientSocket_sensor):
    count = 0
    obj = sensor_msg_obj
    #print("sensor thread start")
    try:
        while True:
            for clithr_event in clithr_event_list:
                if clithr_event["client"] == clientSocket_sensor:
                    event_sensor = clithr_event["sensor_event"]
            if event_sensor.is_set():
                break
            #if gpio_ConnErr == 1:
            #    break
            #sensor_datetime = datetime.datetime.now()
            lat, lon, alt = parseGPS(uart)
            acc, gyr = parseIMU(MPU_Address)
            temp, pres, humi = parseBME(bus, BME_Address, bme_calibration_params)
       
            obj["msg"]["receiver"] = clientSocket_sensor.getpeername()
            obj["msg"]["time"] = now.strftime('%Y-%m-%d %H:%M:%S')
        
            #obj["sensor"]["gps"] = { "lat": lat, "lon": lon, "alt": alt }
            obj["sensor"]["imu"] = { "acc": acc, "gyr": gyr } # add "mag": [0.0, 0.0, 0.0]
            obj["sensor"]["bme"] = { "temp": temp, "pres": pres, "humi": humi }
        
            data = json.dumps(obj)
            l = len(data)
            #print('data:' + str(data) + 'length:' + str(l) + '\n')
            print('sensor data length:' + str(l))
            # send 2byte_len + payload to mobile
            clientSocket_sensor.send(l.to_bytes(2, byteorder='big') + data.encode())
            print('Sensor data sent to %s successfully\n' % str(clientSocket_sensor.getpeername()))
            count += 1
            time.sleep(1)
    
    except Exception as e:
        print('Exception at source_thread; %s:%s'%clientSocket_sensor.getpeername())
        return
    return


def help_thread(data_help, clientSocket_help):
    count = 0
    try:
        #baseclientSocket.connect(BASEADDR)
        while True:
           
            print("help message from mobile: ", str(data_help))
            for clithr_event in clithr_event_list:
                if clithr_event["client"] == clientSocket_help:
                    event_help = clithr_event["help_event"]
            if event_help.is_set():
                break
             
            jsonobj_help = json.loads(data_help[2:])
            print("message from mobile: ", str(jsonobj_help))
            if jsonobj_help["msg"]["gps"] == "":
                print("NO gps data from mobile: sending CanSat's GPS")
                
                lat, lon, alt = parseGPS(uart)
                jsonobj_help["mgs"]["gps"] = { "lat": lat, "lon": lon}
                data_help = json.dumps(jsonobj_help)

            baseclientSocket.send(data_help)
            print("SOS from %s sent to base" %str(clientSocket_help.getpeername()))
            data_resp = baseclientSocket.recv(BUFSIZE)
            l = int.from_bytes(data_resp[:2], 'big')
            print("from base: " + str(data_resp[2:]) + ' len=' + str(l))

            if data_resp[2] == 123:
                jsonobj_resp = json.loads(data_resp[2:])
                msg_resp = jsonobj_resp["msg"]
                if msg_resp.get("dispatch") and msg_resp["dispatch"] == "true":
                    
                    obj = {"msg" : {"sender": "", "receiver": "", "dispatch": "", "duration": ""}}
                    obj["msg"]["sender"] = msg_resp["sender"]
                    obj["msg"]["receiver"] = msg_resp["receiver"]
                    obj["msg"]["dispatch"] = msg_resp["dispatch"]
                    obj["msg"]["duration"] = msg_resp["duration"]
                    data_rewr = json.dumps(obj)
                    l_rewr = len(data_rewr) 

                    clientSocket_help.send(l_rewr.to_bytes(2, byteorder='big') + data_rewr.encode())
                    #clientSocket_help.send(data_resp)
                    print('Dispatch message of length %d=%dsent to %s successfully'%l %l_rewr  % str(clientSocket_help.getpeername()))
                    count += 1
                    time.sleep(1)
                    break
                #print("Done")
            #print("Loop done")
                    
    except Exception as e:
        print('Exception at help_thread; refugee %s:%s / base %s:%s ' %clientSocket_help.getpeername() %BASEADDR)
        return


#Serial Connection Initialization
#gpio_ConnErr = 0
try:
    bus = smbus2.SMBus(1)     # or bus = smbus.SMBus(0) for older version boards
    MPU_Address = 0x68      # MPU9250 device address
    BME_Address = 0x76      # BME280 device address

    initIMU(MPU_Address)
    uart = serial.Serial(                \
        port='/dev/ttyS0',                \
        baudrate = 9600,                \
        parity=serial.PARITY_NONE,        \
        stopbits=serial.STOPBITS_ONE,    \
        bytesize=serial.EIGHTBITS,        \
        timeout=1                        \
    )
    bme_calibration_params = bme280.load_calibration_params(bus, BME_Address)
    print('uart, i2c connection all clear')

    counter=0
except:
    gpio_ConnErr = 1
    print("GPIO connecting error!\n")
    #pi.bb_serial_read_close(RX)
    #pi.stop()

baseclientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
baseclientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serverSocket.bind(ADDR)
serverSocket.listen(100)
client_list = [serverSocket]  #list of client sockets to be saved

thread_meshinfo = threading.Thread(target=meshinfo_thread, args=())
thread_meshinfo.start()

#Test: use gethost, remotenetwork 
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
#base_name = 'raspberrypi2'
#base_ip = socket.gethostbyname(base_name)
print('Host Name: ' + str(host_name) + '   Host IP: ' + str(host_ip))
print('Base Station: ' + str(baseclientSocket))

clithr_event_list = []
threading.Event()

# __name__ special variable storing a name of a module: when imported,'name of module' allocated / when executed directly by code, '__main__' allocated
#if __name__ == '__main__':

# Loop of receiving socket from clients and opening threads to send back
loopcount = 0
while True:
    now = datetime.datetime.now()
    #now.strftime('%Y-%m-%d %H:%M:%S')   
    #clientSocket, addr_info = serverSocket.accept()
    #thread_meshinfo = threading.Thread(target=meshinfo_thread, args=())
    #thread_meshinfo.start()
    
    
    #assign a socket object in imput_list where I/O occurred
    input_ready, _, _ = select.select(client_list, [], [])


    for cur_clientSocket in input_ready:
        #print("New Message from client " + str(input_ready))
        #print("WHILE LOOP - cur_clientSocket = " + str(cur_clientSocket))
        # add new client sockets connecting to server
        if cur_clientSocket == serverSocket:        #for hosts newly connecting to server
            newclientSocket, addr_info = serverSocket.accept()
            print('connected to ' + str(newclientSocket))
            print('peer host address:' + str(newclientSocket.getpeername()))
            client_list.append(newclientSocket)
            print('number of clients in list: %d' % len(client_list))
            print(*client_list, sep = "\n\n")
            clithr_event_elm = {"client"    : newclientSocket,
                                "sensor_event"  : threading.Event(),
                                "help_event"    : threading.Event()
                                }
            clithr_event_list.append(clithr_event_elm)
            print(*clithr_event_list, sep = "\n\n")
            loopcount = loopcount + 1
            print("adding client done: loop count =", loopcount)
        # receive packet(=2byte_len + msg payload) from mobile.
    
    for cur_clientSocket in client_list:             
        if cur_clientSocket == serverSocket:
            continue
        cur_data = cur_clientSocket.recv(BUFSIZE)
        length = int.from_bytes(cur_data[:2], 'big')
        #print(str(cur_clientSocket))
        print("from mobile: " + str(cur_data[2:]) + ' len='+str(length))
        #print('recv return datatype: ' + str(type(cur_data)))
        #print all threads currently being executed
        print("======================Threads Activated====================")
        for threadi in threading.enumerate():
            print(threadi.name)
        print("===========================================================")
        
        # Chcck packet message syntax
        if cur_data[2] == 123: # b'{':
            jsonobj = json.loads(cur_data[2:])
            msg = jsonobj["msg"]
            print("data=" + str(msg) + "length=%d" % len(str(msg)))
            
            # 'Sensor' Button Pressed
            if msg.get("sensor"):                  
                #event_sensor = threading.Event()
                if msg["sensor"] == "true":
                    for clithr_event in clithr_event_list:
                        if clithr_event["client"] == cur_clientSocket:
                            clithr_event["sensor_event"].clear()
                    thread_sensor = threading.Thread(target=sensor_thread, args=(cur_clientSocket,))
                    #thread_sensor.daemon = True #daemon thread bkgnd executing; terminates when program terminates
                    thread_sensor.start()
                elif msg["sensor"] == "false":
                    for clithr_event in clithr_event_list:
                        if clithr_event["client"] == cur_clientSocket:
                            clithr_event["sensor_event"].set()
                    thread_sensor.join()
                    
            # 'Help' Button Pressed
            elif msg.get("help") and msg["help"] == "true":
                #send the received msg to base station
                thread_help = threading.Thread(target=help_thread, args=(cur_data,cur_clientSocket))
                thread_help.start()
            #print("cur_data['msg']['gps']=%s" % (str(jsonobj['msg']['gps'])))
            
        else:
            cur_data = input(' -> ')
            l = len(cur_data)
            # send 2byte_len + payload to mobile
            cur_clientSocket.send(l.to_bytes(2, byteorder='big') + cur_data.encode())
        
        loopcount = loopcount + 1
        print("adding client done: loop count =", loopcount)
        # receive packet(=2byte_len + msg payload) from mobile.

baseclientSocket.close()
clientSocket.close()
serverSocket.close()
