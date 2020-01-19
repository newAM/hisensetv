# Python API for Hisense Televsions

Work-in-progress based off of [mqtt-hisensetv](https://github.com/Krazy998/mqtt-hisensetv).

## Demo
```
./hisensetv.py --help                 
usage: hisensetv.py [-h] [--authorize] [--get {sources,volume}] [--key {back,down,exit,left,menu,power,right,up}] [-v] hostname

Hisense TV control.

positional arguments:
  hostname              Hostname or IP for the TV.

optional arguments:
  -h, --help            show this help message and exit
  --authorize           Authorize this API to access the TV.
  --get {sources,volume}
                        Gets a value from the TV.
  --key {back,down,exit,left,menu,power,right,up}
                        Sends a keypress to the TV.
  -v, --verbose         Logging verbosity.
```

### One Time Setup
```
./hisensetv.py 10.0.0.128 --authorize   
Please enter the 4-digit code: 7815
```

### Keypresses
```
./hisensetv.py 10.0.0.28 --key up    
INFO:__main__:sending keypress: up
```

### Gets
```
./hisensetv.py 10.0.0.28 --get volume 
INFO:__main__:volume: {
    "volume_type": 0,
    "volume_value": 0
}
```

## Known Issues

### Features
* Power on functionality (this can be done via WOL) (should this even be part of this API?).

### Concurrency
* Multiple instances of this class with conflict with one-another.
* Not thread-safe.
* This API really *should* be asyncio in 2020, but asyncio is not yet part of the paho mqtt library (see [445](https://github.com/eclipse/paho.mqtt.python/issues/455)).

### Reliability
* I might abandon this project if I loose interest.
* Tested only with a single TV.
* The concurrency issues contribute to reliability issues in general.
* Unit tests do not exist yet.

### Security
* The self-signed certificates from the TV are completely bypassed.
