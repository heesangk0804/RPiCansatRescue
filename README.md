# RaspPiSetup for Developing CanSat Constellation Rescue System

## 1. Basic Tools
: Update and install basic tools, libraries

> sudo apt upgrade
> 
> sudo apt install vim
>
> sudo apt install python3

## 2. Swap Memory Setting
: Spare extra memory for RAM by swapping some from SD Card

* Check current memory/swap size
> free -h
* Check SD Card(disk) size
> df -h
* Modify swap size by accessing dphs-swapfile
> sudo vi /etc/dphys-swapfile
>> ...
>>
>> CONF_SWAPFILE=/home/pi &nbsp;&nbsp;&nbsp; #location of swap file
>> 
>> CONF_SWAPSIZE=2048 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; #size of swap
>>
>> ...
* Restart the dphs-swapfile
> service dphys-swapfile restart

## 3. Linux Kernel Header
: Install linux kernel header to add modules to kernel, perform system call, etc

* Install kernel header if not
> sudo apt install linux-headers
* Check if kernel header successfully installed, with proper version
> /usr/src $ ls
> 
> /usr/src $ uname -r

## 4. Setup for Wifi Connection, LAN Card Drivers
* Fixed IP Settings for convenience in ssh remote access
> netstat -nr
> 
> sudo vi /etc/dhcpcd.conf
>> ...
>>
>> interface wlan0
>>
>> static ip_address=192.168.**252.XX**/24 &nbsp;&nbsp;&nbsp; #fixed local IP address for Pi
>>  
>> static routers=192.168.**252.1** &nbsp;&nbsp;&nbsp; #IP address of gateway server
>> 
>> ...

* Install drivers for unsupported Wi-Fi LAN Cards (ex: RealTek LANs)
> git clone https://github.com/morrownr/88x2bu-20210702 &nbsp;&nbsp;&nbsp; #88x2bu LAN driver
>
> git clone https://github.com/morrownr/8821cu-20210916 &nbsp;&nbsp;&nbsp; #8821cu LAN driver
>
> cd ~/**(driver directory)**
>
> sudo ./install-driver.sh

## 5. Setup for Serial Communications
: install libraries to control serial connected peripherals from python code
* Install smbus for i2c control
> sudo pip3 install smbus2
* Install driver for bme280 sensor
> sudo pip3 install RPi.bme280
* Install pynmea library for parsing GPS data
> sudo pip3 install pynmea2

## 6. Setup for Camera Streaming
: install libraries for camera control and streaming
* install libcamera for camera control (unnecessary; already included in default packages
> sudo apt install libcamera-apps
* install vlc for rtsp streaming the video
> sudo apt install vlc

## 6. Setup for Ad-Hoc Mesh Network
: adjusting WLAN interface settings, adding **'batman-adv'** driver module, running execution files to set up an ad-hoc mesh network

reference: https://github.com/binnes/WiFiMeshRaspberryPi/blob/master/part1/README.md

* i. WLAN Interface Settings

i-(1). Change the wlan0 interface mode into Ad-Hoc
> sudo vi /etc/network/interfaces.d/wlan0
>> auto wlan0
>> 
>> iface wlan0 inet manual
>> 
>> &nbsp;&nbsp;&nbsp; wireless-channel 1	&nbsp;&nbsp;&nbsp;	#channel num among 2.4G band
>>
>> &nbsp;&nbsp;&nbsp; wireless-essid cansat-mesh &nbsp;&nbsp;&nbsp; #name for network
>>
>> &nbsp;&nbsp;&nbsp; wireless-mode ad-hoc &nbsp;&nbsp;&nbsp; #set as ad-hoc

i-(2). Block the wlan0 interface from Dymanic IP Allocation (DHCP) from network 
> echo 'denyinterfaces wlan0' | sudo tee --append /etc/dhcpcd.conf

< Additional Settings for Gateway >

i-(3). Make gateway server to dynamically allocate IP to its clients
> sudo apt install -y dnsmasq
> sudo vi /etc/dnsmasq.conf
>> interface=bat0
>>
>> dhcp-range=192.168.199.2,192.168.199.99,255.255.255.0,12h

* ii 'batman-adv' Driver Presettings

ii-(1). Set 'batman-adv' kernel driver module to be loaded every time the system boots
> echo 'batman-adv' | sudo tee --append /etc/modules
>
> lsmod &nbsp;&nbsp;&nbsp; #check if batman module properly added

ii-(2). Install batctl utility to control batman-adv
>sudo apt install -y batctl

* iii. Create & Run shell script exe program to run mesh network

iii-(1). Write shell script file to run mesh network (node client version)
> vi ~/start-batman-adv.sh
>> #!/bin/bash
>>
>> #batman-adv interface to use
>>
>> sudo batctl if add wlan0
>>
>> sudo ifconfig bat0 mtu 1468
>>
>> #Tell batman-adv this is a gateway client
>> 
>> sudo batctl gw_mode client
>>
>> #Activates batman-adv interfaces
>>
>> sudo ifconfig wlan0 up
>>
>> sudo ifconfig bat0 up
>>
>> sudo ifconfig bat0 192.168.199.**X**/24 #Fixed IP

iii-(1). Write shell script file to run mesh network (gateway version)
> vi ~/start-batman-adv.sh
>> #!/bin/bash
>>
>> #batman-adv interface to use
>>
>> sudo batctl if add wlan0
>>
>> sudo ifconfig bat0 mtu 1468
>>
>> #Tell batman-adv this is an internet gateway
>>
>> sudo batctl gw_mode server
>>
>> #Enable port forwarding
>>
>> sudo sysctl -w net.ipv4.ip_forward=1
>>
>> sudo iptables -t nat -A POSTROUTING -o wlan1 -j MASQUERADE
>>
>> sudo iptables -A FORWARD -i wlan1 -o bat0 -m conntrack –ctstate RELATED,ESTABLISHED -j ACCEPT
>>
>> sudo iptables -A FORWARD -i bat0 -o wlan1 -j ACCEPT
>>
>> #Activates batman-adv interfaces
>>
>> sudo ifconfig wlan0 up
>>
>> sudo ifconfig bat0 up
>>
>> sudo ifconfig bat0 192.168.199.1/24


iii-(2). Make the file executable, then let it run every time the system boots
> chmod +x ~/start-batman-adv.sh
>
> sudo vi /etc/rc.local
>> ...
>>
>> /home/pi/start-batman-adv.sh &
>>
>> ...
>
> sudo reboot -h now


* +Commands to check network connenction
> ifconfig  &nbsp;&nbsp;&nbsp; #configure ip address, packets of each interfaces
>
> netstat  &nbsp;&nbsp;&nbsp; #configure every network connenction(Internet+Internal domain)
>
> iwconfig  &nbsp;&nbsp;&nbsp; #configure wireless interface settings, information
>
> ping  &nbsp;&nbsp;&nbsp; #check if external IP accessable through network
>
> sudo batctl n &nbsp;&nbsp;&nbsp; #check external IP devices(nodes) in mesh network
> 
> sudo batctl if &nbsp;&nbsp;&nbsp; #check mesh network active
