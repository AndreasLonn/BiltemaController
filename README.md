# BiltemaController
Controll remote controlled outlets through
[MQTT](https://en.wikipedia.org/wiki/MQTT) by connecting the remote
to the GPIO pins of a
[Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/),
preferably with the help of
[optocouplers](https://en.wikipedia.org/wiki/Opto-isolator).

## Installation

First, install python 3.x and the required libraries.
```bash
$ pip install paho-mqtt
```

Put the `biltemacontroller.service` file in `/lib/systemd/system/` and edit the
paths in `ExecStart` to start the script and use the correct configuration file.
Then enable and start the service using:
```bash
$ sudo systemctl enable biltemacontroller.service
$ sudo systemctl start biltemacontroller.service
```
You can then check that the script is running using:
```bash
$ sudo systemctl status biltemacontroller.service
```
If the it says `Active: active (running)`, that means that it's running

## Configuration

### Broker configuration

If the MQTT broker doesn't require username and password, leave them blank:
```ini
brokerUsername=
brokerPassword=
```

### Pin and MQTT configuration

The `pins` configuration entry is a python dictionary where the key is the name
of the outlet (this value is added to the `topicStatePrefix` to create the MQTT
topic for that outlet). The value of the dictionary element is a touple of the
pin that turns the outlet off, and the pin that turns it on. For example:
`'1':(4,14)` means that the outlet is called `1`, that pin `4` turns the outlet
off and that pin `14` turns it on.

The `triggerDelay` refers to the delay between the HIGH and LOW and again after the
LOW for the GPIO pin. This is entered in seconds. Increase this if the remote control
doesn't have time to send signals.

#### State

When the outlet has been turned on or off, a MQTT message will be sent letting
(if they are listening) anyone know that the the outlet has been turned on or
off. This message will use the same topic as the original message, but will add
the `topicStateSuffix` att the end.

To not use this feature, leave `topicStateSuffix` blank.

#### Availability

When the script is executed it will let anyone listening know that it is online
by sending a message with the topic specified in `topicAvailability` with the
content specified in `payloadAvailable`. When the script is stopped it will send
a message with the topic specified in `topicAvailability` and the content
specified in `payloadUnavailable`. If the script is killed the MQTT broker will
send the disconnect message on its behalf using MQTT:s
[LWT](https://www.hivemq.com/blog/mqtt-essentials-part-9-last-will-and-testament/)
feature.

To not use this feature, leave `topicAvailability` blank.

## Control using [Home Assistant](https://www.home-assistant.io/)

Here is an example entry in `configuration.yaml` using
[MQTT Switch](https://www.home-assistant.io/integrations/switch.mqtt/) integration:

```yaml
mqtt:
  switch:
    - name: "My light"
      unique_id: biltema.switch.1
      retain: true
      command_topic: "biltemactrl/switch/1"
      state_topic: "biltemactrl/switch/1/state"
      availability_topic: "biltemactrl/availability"
      device:
          name: "Biltema Switch Channel 1"
          manufacturer: "Biltema"
          model: "35-392"
          identifiers: "35-392.c1"
```

## Control using the [command line](https://mosquitto.org/man/mosquitto_pub-1.html)

The tools are available [here](https://mosquitto.org/download/)

```bash
$ mosquitto_pub -h "192.168.0.123" -u "Nice Username" -P "correct horse battery staple" -t "biltemactrl/switch/4" -m "ON"
$ mosquitto_pub -h "192.168.0.123" -u "Nice Username" -P "correct horse battery staple" -t "biltemactrl/switch/4" -m "OFF"
```

## License and Credits

Some of the code has been borrowed and heavily modified from LucaKaufmann:s
[rpi-touchscreen-mqtt](https://github.com/LucaKaufmann/rpi-touchscreen-mqtt)

Feel free to use this script as you like, but giving me credit would be nice.
Also, I don't own any rights to the Biltema name. Don't include that name in any
projects where they could object without first asking them for permission
