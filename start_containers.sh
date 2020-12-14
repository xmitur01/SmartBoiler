sudo docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto

sudo docker run -d -p 8086:8086 -v influxdb:/var/lib/influxdb --name influxdb influxdb
# sudo docker start influxdb

# create database in container
# sudo docker exec -it influxdb influx
#     create database sensors
#     create user telegraf with password 'telegraf'
#     grant all on sensors to telegraf

sudo docker run -v "$PWD"/docker/telegraf.conf:/etc/telegraf/telegraf.conf:ro telegraf

# sudo docker start grafana
sudo docker run -d --name=grafana -p 3000:3000 grafana/grafana