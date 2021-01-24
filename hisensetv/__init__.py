from types import TracebackType
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union
import functools
import json
import logging
import paho.mqtt.client as mqtt
import posixpath
import queue
import ssl
import time
import uuid


class HisenseTvError(Exception):
    """ Base exception for all exceptions raise by this API. """

    pass


class HisenseTvNotConnectedError(HisenseTvError):
    """ Raised when an API function is called without a connection. """

    pass


class HisenseTvAuthorizationError(HisenseTvError):
    """ Raised upon authorization failures. """

    pass


class HisenseTvTimeoutError(HisenseTvError):
    """ Raised upon a failure to receive a response in the timeout period. """

    pass


def _check_connected(func: Callable):
    """ Raises :py:class:`HisenseTvNotConnectedError` if not connected. """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.connected:
            raise HisenseTvNotConnectedError(
                f"you must be connected to call {func.__name__}"
            )
        return func(self, *args, **kwargs)

    return wrapper


class HisenseTv:
    """
    Hisense TV.
    Args:
        hostname: TV hostname or IP.
        port: Port of the MQTT broker on the TV, typically 36669.
        username: Username for the MQTT broker on the TV,
                  typically "hisenseservice".
        password: Password for the MQTT broker on the TV,
                  typically "multimqttservice".
        timeout: Duration to wait for a response from the TV for API calls.
        enable_client_logger: Enable MQTT client logging for debug.
        ssl_context:
            SSL context to utilize for the connection,
            ``None`` to skip SSL usage (required for some models).
    """

    #: Services in the MQTT API.
    _VALID_SERVICES = {"platform_service", "remote_service", "ui_service"}

    def __init__(
        self,
        hostname: str,
        *,
        port: int = 36669,
        username: str = "hisenseservice",
        password: str = "multimqttservice",
        timeout: Union[int, float] = 10.0,
        enable_client_logger: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.enable_client_logger = enable_client_logger
        self.client_id = f"{self.__class__.__name__}/{uuid.uuid4()!s}"
        self.connected = False
        self.ssl_context = ssl_context

        self._mac = "XX:XX:XX:XX:XX:XY"
        self._device_topic = f"{self._mac.upper()}$normal"
        self._queue = queue.Queue()

    def __enter__(self):
        self._mqtt_client = mqtt.Client(self.client_id)
        self._mqtt_client.username_pw_set(
            username=self.username, password=self.password
        )
        if self.ssl_context is not None:
            self._mqtt_client.tls_set_context(context=self.ssl_context)

        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        if self.enable_client_logger:
            self._mqtt_client.enable_logger()

        self._mqtt_client.connect(self.hostname, self.port)

        self._mqtt_client.loop_start()

        start_time = time.monotonic()
        while not self.connected:
            time.sleep(0.01)
            if time.monotonic() - start_time > self.timeout:
                raise HisenseTvTimeoutError(f"failed to connect in {self.timeout:.3f}s")

        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        self.connected = False
        if isinstance(exception_value, Exception):
            self._mqtt_client.disconnect()
            self._mqtt_client.loop_stop()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Optional[Any],
        flags: Dict[str, int],
        rc: int,
    ):
        """ Callback upon MQTT broker connection. """
        base_topic = posixpath.join("/", "remoteapp", "mobile")
        # broadcast_topic = posixpath.join(base_topic, "broadcast", "#")
        our_topic = posixpath.join(base_topic, self._device_topic, "#")

        self.logger.debug(f"subcribing to {our_topic}")
        self._mqtt_client.subscribe(our_topic)
        self.connected = True

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Optional[Any],
        msg: mqtt.MQTTMessage,
    ):
        """ Callback upon MQTT broker message on a subcribed topic. """
        if msg.payload:
            try:
                payload = msg.payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                self.logger.error(f"Payload is invalid UTF-8: {msg.payload!r}")
                raise

            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                self.logger.error(f"Payload is invalid JSON: {payload!r}")
                raise

            self.logger.debug(
                f"Recieved message on topic {msg.topic} with payload: {payload}"
            )
        else:
            payload = msg.payload

        self._queue.put_nowait(payload)

    def _wait_for_response(self) -> Optional[dict]:
        """ Waits for the first response from the TV. """
        try:
            return self._queue.get(block=True, timeout=self.timeout)
        except queue.Empty as e:
            raise HisenseTvTimeoutError(
                f"failed to recieve a response in {self.timeout:.3f}s"
            ) from e

    def _call_service(
        self,
        *,
        service: str,
        action: str,
        payload: Optional[Union[str, dict]] = None,
    ):
        """
        Calls a service on the TV API.
        Args:
            service: "platform_service", remote_service", or "ui_service".
            action: The action to send to the service.
            payload: Payload to send.
        """
        if service not in self._VALID_SERVICES:
            raise ValueError(
                f"service of {service!r} is invalid, service must be one of "
                f"{self._VALID_SERVICES!r}"
            )

        if isinstance(payload, dict):
            payload = json.dumps(payload)

        full_topic = posixpath.join(
            "/",
            "remoteapp",
            "tv",
            service,
            self._device_topic,
            "actions",
            action,
        )

        msg = self._mqtt_client.publish(topic=full_topic, payload=payload)
        msg.wait_for_publish()

    def send_key(self, keyname: str):
        """
        Sends a keypress to the TV, as if it had been pressed on the IR remote.
        Args:
            keyname: Name of the key press to send.
        """
        self._call_service(service="remote_service", action="sendkey", payload=keyname)

    def _launch_app(self, app: str):
        """
        Sends a launch command to the TV, as if it had been pressed on the
        "remoteNOW" app.

        Args:
            app: Name of the app to launch
        """
        if app == "amazon":
            launch = {"name": "Amazon", "urlType": 37, "storeType": 0, "url": "amazon"}

        elif app == "netflix":
            launch = {
                "name": "Netflix",
                "urlType": 37,
                "storeType": 0,
                "url": "netflix",
            }

        elif app == "youtube":
            launch = {
                "name": "YouTube",
                "urlType": 37,
                "storeType": 0,
                "url": "youtube",
            }

        else:
            raise ValueError(f"{app} is not a known app.")

        self._call_service(service="ui_service", action="launchapp", payload=launch)

    def _change_source(self, id: str):
        """
        Sets the source of the TV.
            id: id of the Source
        """
        payload = {"sourceid": id}
        self._call_service(service="ui_service", action="changesource", payload=payload)

    @_check_connected
    def send_key_power(self):
        """ Sends a keypress of the powerkey to the TV. """
        self.send_key("KEY_POWER")

    @_check_connected
    def send_key_up(self):
        """ Sends a keypress of the up key to the TV. """
        self.send_key("KEY_UP")

    @_check_connected
    def send_key_down(self):
        """ Sends a keypress of the down key to the TV. """
        self.send_key("KEY_DOWN")

    @_check_connected
    def send_key_left(self):
        """ Sends a keypress of the left key to the TV. """
        self.send_key("KEY_LEFT")

    @_check_connected
    def send_key_right(self):
        """ Sends a keypress of the right key to the TV. """
        self.send_key("KEY_RIGHT")

    @_check_connected
    def send_key_menu(self):
        """ Sends a keypress of the menu key to the TV. """
        self.send_key("KEY_MENU")

    @_check_connected
    def send_key_back(self):
        """ Sends a keypress of the back key to the TV. """
        self.send_key("KEY_RETURNS")

    @_check_connected
    def send_key_exit(self):
        """ Sends a keypress of the exit key to the TV. """
        self.send_key("KEY_EXIT")

    @_check_connected
    def send_key_ok(self):
        """ Sends a keypress of the OK key to the TV. """
        self.send_key("KEY_OK")

    @_check_connected
    def send_key_volume_up(self):
        """ Sends a keypress of the volume up key to the TV. """
        self.send_key("KEY_VOLUMEUP")

    @_check_connected
    def send_key_volume_down(self):
        """ Sends a keypress of the volume down key to the TV. """
        self.send_key("KEY_VOLUMEDOWN")

    @_check_connected
    def send_key_fast_channel_up(self):
        """ Sends a keypress of the channel up key to the TV. """
        self.send_key("KEY_CHANNELUP")

    @_check_connected
    def send_key_fast_channel_down(self):
        """ Sends a keypress of the channel down key to the TV. """
        self.send_key("KEY_CHANNELDOWN")

    @_check_connected
    def send_key_fast_forward(self):
        """ Sends a keypress of the fast forward key to the TV. """
        self.send_key("KEY_FORWARDS")

    @_check_connected
    def send_key_rewind(self):
        """ Sends a keypress of the rewind key to the TV. """
        self.send_key("KEY_BACK")

    @_check_connected
    def send_key_stop(self):
        """ Sends a keypress of the stop key to the TV. """
        self.send_key("KEY_STOP")

    @_check_connected
    def send_key_play(self):
        """ Sends a keypress of the play key to the TV. """
        self.send_key("KEY_PLAY")

    @_check_connected
    def send_key_pause(self):
        """ Sends a keypress of the pause key to the TV. """
        self.send_key("KEY_PAUSE")

    @_check_connected
    def send_key_mute(self):
        """ Sends a keypress of the mute key to the TV. """
        self.send_key("KEY_MUTE")

    @_check_connected
    def send_key_home(self):
        """ Sends a keypress of the home key to the TV. """
        self.send_key("KEY_HOME")

    @_check_connected
    def send_key_subtitle(self):
        """ Sends a keypress of the subtitle key to the TV. """
        self.send_key("KEY_SUBTITLE")

    @_check_connected
    def send_key_netflix(self):
        """ Sends a keypress of the Netflix key to the TV. """
        self._launch_app("netflix")

    @_check_connected
    def send_key_youtube(self):
        """ Sends a keypress of the YouTube key to the TV. """
        self._launch_app("youtube")

    @_check_connected
    def send_key_amazon(self):
        """ Sends a keypress of the Amazon key to the TV. """
        self._launch_app("amazon")

    @_check_connected
    def send_key_0(self):
        """ Sends a keypress of the 0 key to the TV. """
        self.send_key("KEY_0")

    @_check_connected
    def send_key_1(self):
        """ Sends a keypress of the 1 key to the TV. """
        self.send_key("KEY_1")

    @_check_connected
    def send_key_2(self):
        """ Sends a keypress of the 2 key to the TV. """
        self.send_key("KEY_2")

    @_check_connected
    def send_key_3(self):
        """ Sends a keypress of the 3 key to the TV. """
        self.send_key("KEY_3")

    @_check_connected
    def send_key_4(self):
        """ Sends a keypress of the 4 key to the TV. """
        self.send_key("KEY_4")

    @_check_connected
    def send_key_5(self):
        """ Sends a keypress of the 5 key to the TV. """
        self.send_key("KEY_5")

    @_check_connected
    def send_key_6(self):
        """ Sends a keypress of the 6 key to the TV. """
        self.send_key("KEY_6")

    @_check_connected
    def send_key_7(self):
        """ Sends a keypress of the 7 key to the TV. """
        self.send_key("KEY_7")

    @_check_connected
    def send_key_8(self):
        """ Sends a keypress of the 8 key to the TV. """
        self.send_key("KEY_8")

    @_check_connected
    def send_key_9(self):
        """ Sends a keypress of the 9 key to the TV. """
        self.send_key("KEY_9")

    @_check_connected
    def send_key_source_0(self):
        """ Sets TV to Input 0 """
        self._change_source("0")

    @_check_connected
    def send_key_source_1(self):
        """ Sets TV to Input 1 """
        self._change_source("1")

    @_check_connected
    def send_key_source_2(self):
        """ Sets TV to Input 2 """
        self._change_source("2")

    @_check_connected
    def send_key_source_3(self):
        """ Sets TV to Input 3 """
        self._change_source("3")

    @_check_connected
    def send_key_source_4(self):
        """ Sets TV to Input 4 """
        self._change_source("4")

    @_check_connected
    def send_key_source_5(self):
        """ Sets TV to Input 5 """
        self._change_source("5")

    @_check_connected
    def send_key_source_6(self):
        """ Sets TV to Input 6 """
        self._change_source("6")

    @_check_connected
    def send_key_source_7(self):
        """ Sets TV to Input 7 """
        self._change_source("7")

    @_check_connected
    def get_sources(self) -> List[Dict[str, str]]:
        """
        Gets the video sources from the TV.
        Returns:
            List of source dictionaries.
            Example::
                [
                    {
                        "displayname": "TV",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "1",
                        "sourceid": "1",
                        "sourcename": "TV",
                    },
                    {
                        "displayname": "HDMI 1",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "0",
                        "sourceid": "2",
                        "sourcename": "HDMI 1",
                    },
                    {
                        "displayname": "HDMI 2",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "0",
                        "sourceid": "3",
                        "sourcename": "HDMI 2",
                    },
                    {
                        "displayname": "HDMI 3",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "0",
                        "sourceid": "4",
                        "sourcename": "HDMI 3",
                    },
                    {
                        "displayname": "PC",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "1",
                        "sourceid": "5",
                        "sourcename": "HDMI 4",
                    },
                    {
                        "displayname": "Composite",
                        "hotel_mode": "0",
                        "is_lock": "false",
                        "is_signal": "0",
                        "sourceid": "6",
                        "sourcename": "Composite",
                    },
                ]
        """
        self._call_service(service="ui_service", action="sourcelist")
        return self._wait_for_response()

    @_check_connected
    def set_source(self, sourceid: Union[int, str], sourcename: str):
        """
        Sets the video source on the TV.
        Args:
            sourceid: Numeric source identier.
            sourcename: Human readable source name.
        """
        sourceid = str(int(sourceid))
        self._call_service(
            service="ui_service",
            action="changesource",
            payload={"sourceid": sourceid, "sourcename": sourcename},
        )

    @_check_connected
    def get_volume(self) -> dict:
        """
        Gets the volume level on the TV.
        Returns:
            Dictionary with keys for volume_type and volume_value.
            Example::
                {"volume_type": 0, "volume_value": 0}
        """
        self._call_service(service="platform_service", action="getvolume")
        return self._wait_for_response()

    @_check_connected
    def set_volume(self, volume: int):
        """
        Sets the volume level on the TV.
        Args:
            volume: Volume level from 0-100.
        Raises:
            ValueError: Volume level is out of range.
        """
        volume = int(volume)
        if volume < 0 or volume > 100:
            raise ValueError(
                f"volume of {volume!r} is invalid, volume must be between 0 and 100"
            )
        self._call_service(
            service="platform_service",
            action="changevolume",
            payload=str(volume),
        )

    @_check_connected
    def start_authorization(self):
        """ Starts the authorization flow. """
        self._call_service(service="ui_service", action="gettvstate")
        self._wait_for_response()

    @_check_connected
    def send_authorization_code(self, code: Union[int, str]):
        """
        Sends the authorization code to the TV.
        Args:
            code: 4-digit code as displayed on the TV.
        Raises:
            HisenseTvAuthorizationError: Failed to authenticate with the TV.
        """
        self._call_service(
            service="ui_service",
            action="authenticationcode",
            payload={"authNum": str(code)},
        )
        payload = self._wait_for_response()
        result = int(payload["result"])
        if result != 1:
            raise HisenseTvAuthorizationError(
                f"authorization failed with code {result}"
            )
