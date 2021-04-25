sudo docker run -d -p 1883:1883 -p 9001:9001 --name mqtt-server eclipse-mosquitto
# sudo docker start mqtt-server

sudo docker run -d -p 8086:8086 -v influxdb:/var/lib/influxdb --name influxdb influxdb:1.8
# create database in container
sudo docker exec -it influxdb influx -execute 'create database sensors'
sudo docker exec -it influxdb influx -execute "create user telegraf with password 'telegraf'"
sudo docker exec -it influxdb influx -execute 'grant all on sensors to telegraf'
# sudo docker start influxdb

sudo docker run -d -v "$PWD"/docker/telegraf.conf:/etc/telegraf/telegraf.conf:ro --name telegraf-mosquitto-influx telegraf
# sudo docker start telegraf-mosquitto-influx

sudo docker run -d --name=grafana -p 3000:3000 grafana/grafana
# sudo docker start grafana
