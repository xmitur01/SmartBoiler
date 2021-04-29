# SmartBoiler
DIY smart water tank heating system, build on smart plug Tp-Link HS110, NodeMCU ESP8266 and server components. Optimalize water tank heating shedule based on historic usage patterns. Prediction basic component is Exponential moving average.

# Instalation and setup
Requirements and modules needed to keep for proper system run.

## Server
At first you need to install Docker and Python on your server, which are used by Smart boiler system, by running these commands: 
```
sudo apt install docker
sudo apt install python
sudo apt install pip
```
After this docker containers need to be pulled, started and set up, what is done by runing script **`create_and_run_docker_containers.sh`** inside directore,
where it is located after downoloading and extracting this project.

When containers are set up and working, then you should run **`dependencies.sh`** script, which intall all nencecary Python libraries.
After this things are done, environment is prepared to host Smart boiler system.

Next thing which need to be done is to copy, modifie (based on your pc setup) and start **`.service`** files, located inside **docker, HS110 and ControllAlgorithm** directories inside **`/etc/systemd/system`** directory. So it can work as system service. Before plug and MCU has to be running.

## ESP8266 setup

ESP module needs to be cleared and flashed with MicroPython software at first. After fleshing, we can 
approach to uploading code on MCU located in ESP8266 folder. After upload marked lines in files need to be changed. Then **`installPackages.py`** can be run. Successful instalation means that device is ready to run.

## Smart plug

Tp-Link HS110 smart plug has to be connected to your Wi-Fi network by following guid.
