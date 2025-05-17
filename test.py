import argparse
from datetime import datetime
import logging
import os
import sys
import time
from typing import Set, Type
from traceback import print_exception
import cv2

# External library imports for lora and foxglove foxglove, logging, etc.
import foxglove
from foxglove import Channel, Schema
from foxglove.channels import CompressedImageChannel
from foxglove.websocket import (
    Capability,
    ChannelView,
    Client,
    ClientChannel,
    ServerListener,
    WebSocketServer,
)
from foxglove.schemas import CompressedImage
from LoRaRF import SX127x

# Local imports for custom protobuf schema
from tom_packet_pb2 import TomPacket

try:
    import google.protobuf.message
    from google.protobuf.descriptor_pb2 import FileDescriptorSet
    from google.protobuf.descriptor import FileDescriptor
except ImportError:
    print_exception(*sys.exc_info())
    print(
        "Unable to import protobuf schemas; did you forget to run `pip install 'foxglove-websocket[examples]'`?",
    )
    sys.exit(1)


# add arguments for command line interface
parser = argparse.ArgumentParser(
    prog="protobuf_server",
    description="A ground station for TOM flight s",
    epilog="text at the bottom of help",
)

# Arguments for server instance
parser.add_argument("-a", "--address", default="0.0.0.0", help="Server host address, default to all external hosts")
parser.add_argument("-p", "--port", default=8765, type=int, help="server port")
parser.add_argument("-n", "--server-name", default="ground control", help="server name")
parser.add_argument("-r", "--rocket-name", default="TOM", help="rocket name")
parser.add_argument(
    "-l",
    "--enable_logging",
    action="store_true",
    help="enable logging on groundstation",
)
parser.add_argument("-d", "--log_dir", default="logs")
parser.add_argument(
    "-c",
    "--enable_camera",
    action="store_true",
    help="enable and disable logging on ground",
)

# Arguments for radio
parser.add_argument("--spi_bus", default=0)
parser.add_argument("--spi_cs", default=1)
parser.add_argument("--spi_speed", default=1_000_000)
parser.add_argument("--pins_reset", default=27)
parser.add_argument("--pins_irq", default=17)
parser.add_argument("--frequency", default=915_000_000)
parser.add_argument("--modulation_sf", default=10)
parser.add_argument("--modulation_bw", default=250_000)
parser.add_argument("--modulation_cr", default=8)
parser.add_argument("--preamble_len", default=8)
parser.add_argument("--sync_word", default=0x34)

args = parser.parse_args()


def main() -> None:
    # INITIALIZE FOXGLOVE SERVER
    foxglove.set_log_level(logging.DEBUG)

    listener = ExampleListener()

    server = foxglove.start_server(
        name=args.server_name,
        host=args.address,
        port=args.port,
        server_listener=listener,
        capabilities=[Capability.ClientPublish],
        supported_encodings=["json", "protobuf"]
    )

    telemetry_channel = Channel(
        topic="/telemetry",
        message_encoding="protobuf",
        schema=Schema(
            name=TomPacket.DESCRIPTOR.full_name,
            encoding="protobuf",
            data=build_file_descriptor_set(TomPacket).SerializeToString(),
        )
    )

    image_channel = CompressedImageChannel(topic="/camera/image_compressed")

    # INITIALIZE IO RESOURCES
    # LoRa Wiring settings
    lora = SX127x()
    lora.setSpi(args.spi_bus, args.spi_cs, args.spi_speed)
    lora.setPins(reset=args.pins_reset, irq=args.pins_irq)
    lora.begin()

    # LoRa packet settings
    lora.setModem(SX127x.LORA_MODEM)
    lora.setFrequency(args.frequency)
    lora.setLoRaModulation(
        sf=args.modulation_sf,
        bw=args.modulation_bw,
        cr=args.modulation_cr,
    )
    lora.setPreambleLength(args.preamble_len)
    lora.setSyncWord(args.sync_word)
    lora.setRxGain(True, lora.RX_GAIN_BOOSTED)

    print('[INFO] LoRa initialized')

    # Video capture initialization
    if args.enable_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Could not open camera")
            cap = None
        else:
            print("[INFO] Initialized Video Camera")
    else:
        cap = None

    run_telemetry_loop(lora, server, telemetry_channel, image_channel, cap)


def run_telemetry_loop(
        lora: SX127x,
        server: WebSocketServer,
        telemetry_channel: Channel,
        image_channel: CompressedImageChannel,
        cap: cv2.VideoCapture | None = None):
    try:
        while True:
            # Get data from LoRa
            lora.request()
            lora.wait()

            byte_str = b""
            while lora.available() > 0:
                byte = lora.read()
                byte_str += bytes(byte)

            if len(byte_str) > 0:
                # print("".join([f"{byte:02x}" for byte in bytes]))
                telemetry_channel.log(byte_str)
            else:
                print("[ERROR] Packet received with no bytes")

            # Get data from Camera
            if cap is not None:
                ret, frame = cap.read()
                print(frame.shape)
                if ret:
                    im_packet = CompressedImage(
                        data=cv2.imencode(".jpeg", frame)[1].tobytes(),
                        format="jpeg"
                    )
                    image_channel.log(im_packet)

    except KeyboardInterrupt:
        print()
        server.stop()


def build_file_descriptor_set(
    message_class: Type[google.protobuf.message.Message],
) -> FileDescriptorSet:
    """
    Build a FileDescriptorSet representing the message class and its dependencies.
    """
    file_descriptor_set = FileDescriptorSet()
    seen_dependencies: Set[str] = set()

    def append_file_descriptor(file_descriptor: FileDescriptor):
        for dep in file_descriptor.dependencies:
            if dep.name not in seen_dependencies:
                seen_dependencies.add(dep.name)
                append_file_descriptor(dep)
        file_descriptor.CopyToProto(file_descriptor_set.file.add())  # type: ignore

    append_file_descriptor(message_class.DESCRIPTOR.file)
    return file_descriptor_set


class ExampleListener(ServerListener):
    def __init__(self) -> None:
        # Map client id -> set of subscribed topics
        self.subscribers: dict[int, set[str]] = {}

    def has_subscribers(self) -> bool:
        return len(self.subscribers) > 0

    def on_subscribe(
        self,
        client: Client,
        channel: ChannelView,
    ) -> None:
        """
        Called by the server when a client subscribes to a channel.
        We'll use this and on_unsubscribe to simply track if we have any 
        subscribers at all.
        """
        logging.info(f"Client {client} subscribed to channel {channel.topic}")
        self.subscribers.setdefault(client.id, set()).add(channel.topic)

    def on_unsubscribe(
        self,
        client: Client,
        channel: ChannelView,
    ) -> None:
        """
        Called by the server when a client unsubscribes from a channel.
        """
        logging.info(
            f"Client {client} unsubscribed from channel {channel.topic}"
        )
        self.subscribers[client.id].remove(channel.topic)
        if not self.subscribers[client.id]:
            del self.subscribers[client.id]

    def on_client_advertise(
        self,
        client: Client,
        channel: ClientChannel,
    ) -> None:
        """
        Called when a client advertises a new channel.
        """
        logging.info(f"Client {client.id} advertised channel: {channel.id}")
        logging.info(f"  Topic: {channel.topic}")
        logging.info(f"  Encoding: {channel.encoding}")
        logging.info(f"  Schema name: {channel.schema_name}")
        logging.info(f"  Schema encoding: {channel.schema_encoding}")
        logging.info(f"  Schema: {channel.schema!r}")

    def on_message_data(
        self,
        client: Client,
        client_channel_id: int,
        data: bytes,
    ) -> None:
        """
        This handler demonstrates receiving messages from the client.
        You can send messages from Foxglove app in the publish panel:
        https://docs.foxglove.dev/docs/visualization/panels/publish
        """
        logging.info(
            f"Message from client {client.id} on channel {client_channel_id}"
        )
        logging.info(f"Data: {data!r}")

    def on_client_unadvertise(
        self,
        client: Client,
        client_channel_id: int,
    ) -> None:
        """
        Called when a client unadvertises a new channel.
        """
        logging.info(
            f"Client {client.id} unadvertised channel: {client_channel_id}"
        )


if __name__ == '__main__':
    main()
