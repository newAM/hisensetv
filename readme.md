# Python API for Hisense Televsions

Work-in-progress based off of [mqtt-hisensetv](https://github.com/Krazy998/mqtt-hisensetv).

## Known Issues

### Features
* Initial one-time authentication.
* Missing power on functionality (this can be done via WOL) (should this even be part of this API?).

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
