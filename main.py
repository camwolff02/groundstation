# Native python imports
from datetime import datetime
import logging
import os
from queue import Queue, Empty
import threading
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Event

# External library imports for lora and foxglove foxglove, logging, etc.
import cv2
import foxglove
from foxglove import Channel, Schema
from foxglove.channels import CompressedImageChannel
from foxglove.websocket import (
    Capability,
    WebSocketServer,
)
from foxglove.schemas import (
    CompressedImage,
)
import google.protobuf.message
import board
import busio
import digitalio
from adafruit_rfm9x import RFM9x

# Local imports for custom protobuf schema and CLI
from cli import parser
from TomPacket_pb2 import TomPacket
from LocationFix_pb2 import LocationFix
from Signal_pb2 import Signal

from utils import build_file_descriptor_set, CustomListener

@dataclass
class ChannelData:
    queue: Queue
    stop_event: Event
    thread: Optional[threading.Thread] = None

def channel_publisher(queue: Queue, channel: Channel, stop_event: Event, name: str) -> None:
    while not stop_event.is_set():
        try:
            data = queue.get(timeout=1.0)
            channel.log(data)
        except Empty:
            continue

def lora_reader(lora: RFM9x, rocket_channels: Dict, stop_event: Event) -> None:
    while not stop_event.is_set():
        packet = lora.receive(with_header=True)
        if packet is not None:
            print(bytes(packet))
            try:
                tom_packet = TomPacket()
                tom_packet.ParseFromString(packet)

                if tom_packet.rocket_id not in rocket_channels:
                    continue

                if abs(tom_packet.location.altitude) > 1_000_000:
                    continue

                # Get the channels for the specific rocket
                channels = rocket_channels[tom_packet.rocket_id]

                # Queue location data
                if tom_packet.HasField("location"):
                    channels["location"]["data"].queue.put(
                        tom_packet.location.SerializeToString()
                    )

                # Queue telemetry data
                channels["telemetry"]["data"].queue.put(bytes(packet))

                # Queue signal data
                signal_data = Signal(rssi=lora.last_rssi, snr=lora.last_snr)
                channels["signal"]["data"].queue.put(
                    signal_data.SerializeToString()
                )
            except google.protobuf.message.DecodeError:
                print("[ERROR] Could not decode packet! Did flight computer shut off?")

def camera_reader(cap: cv2.VideoCapture, image_queue: Queue, stop_event: Event) -> None:
    while not stop_event.is_set():
        ret, frame = cap.read()
        if ret:
            im_packet = CompressedImage(
                data=cv2.imencode(".jpeg", frame)[1].tobytes(),
                format="jpeg"
            )
            image_queue.put(im_packet)

def run_telemetry_loop(
    lora: RFM9x,
    server: WebSocketServer,
    image_channel: CompressedImageChannel | None = None,
    cap: cv2.VideoCapture | None = None,
    rocket_ids: list[str] = [],
) -> None:
    # Create a dictionary to store channels and their queues for each rocket
    rocket_channels: Dict[str, Dict[str, dict]] = {}
    
    for rocket_id in rocket_ids:
        rocket_channels[rocket_id] = {
            "telemetry": {
                "channel": Channel(
                    topic=f"/telemetry/{rocket_id}",
                    message_encoding="protobuf",
                    schema=Schema(
                        name=TomPacket.DESCRIPTOR.full_name,
                        encoding="protobuf",
                        data=build_file_descriptor_set(TomPacket).SerializeToString(),
                    ),
                ),
                "data": ChannelData(Queue(), Event())
            },
            "location": {
                "channel": Channel(
                    topic=f"/location/{rocket_id}",
                    message_encoding="protobuf",
                    schema=Schema(
                        name=LocationFix.DESCRIPTOR.full_name,
                        encoding="protobuf",
                        data=build_file_descriptor_set(LocationFix).SerializeToString(),
                    ),
                ),
                "data": ChannelData(Queue(), Event())
            },
            "signal": {
                "channel": Channel(
                    topic=f"/signal/{rocket_id}",
                    message_encoding="protobuf",
                    schema=Schema(
                        name=Signal.DESCRIPTOR.full_name,
                        encoding="protobuf",
                        data=build_file_descriptor_set(Signal).SerializeToString(),
                    ),
                ),
                "data": ChannelData(Queue(), Event())
            },
        }

    # Start publisher threads for each channel
    for rocket_id, channels in rocket_channels.items():
        for channel_name, channel_info in channels.items():
            thread = threading.Thread(
                target=channel_publisher,
                args=(
                    channel_info["data"].queue,
                    channel_info["channel"],
                    channel_info["data"].stop_event,
                    f"{rocket_id}-{channel_name}"
                ),
                name=f"{rocket_id}-{channel_name}-publisher"
            )
            channel_info["data"].thread = thread
            thread.start()

    # Create and start LoRa reader thread
    lora_stop_event = Event()
    lora_thread = threading.Thread(
        target=lora_reader,
        args=(lora, rocket_channels, lora_stop_event),
        name="lora-reader"
    )
    lora_thread.start()

    # Create image publisher thread if camera is enabled
    image_queue = None
    image_stop_event = None
    camera_stop_event = None
    if cap is not None and image_channel is not None:
        image_queue = Queue()
        image_stop_event = Event()
        camera_stop_event = Event()
        
        # Start image publisher thread
        image_thread = threading.Thread(
            target=channel_publisher,
            args=(image_queue, image_channel, image_stop_event, "image"),
            name="image-publisher"
        )
        image_thread.start()
        
        # Start camera reader thread
        camera_thread = threading.Thread(
            target=camera_reader,
            args=(cap, image_queue, camera_stop_event),
            name="camera-reader"
        )
        camera_thread.start()

    try:
        # Main thread just waits for interrupt
        while True:
            threading.Event().wait(1)
            
    except KeyboardInterrupt:
        print("\nShutting down threads...")
        # Stop all publisher threads
        for rocket_id, channels in rocket_channels.items():
            for channel_info in channels.values():
                channel_info["data"].stop_event.set()
                if channel_info["data"].thread:
                    channel_info["data"].thread.join()

        # Stop LoRa thread
        lora_stop_event.set()
        lora_thread.join()

        # Stop camera and image threads if they exist
        if camera_stop_event:
            camera_stop_event.set()
            camera_thread.join()
        if image_stop_event:
            image_stop_event.set()
            image_thread.join()

        server.stop()


def main() -> None:
    args = parser.parse_args()

    # INITIALIZE FOXGLOVE SERVER
    foxglove.set_log_level(logging.DEBUG)

    listener = CustomListener()

    server = foxglove.start_server(
        name=args.server_name,
        host=args.address,
        port=args.port,
        server_listener=listener,
        capabilities=[Capability.ClientPublish],
        supported_encodings=["json", "protobuf"],
    )

    telemetry_channel = Channel(
        topic="/telemetry",
        message_encoding="protobuf",
        schema=Schema(
            name=TomPacket.DESCRIPTOR.full_name,
            encoding="protobuf",
            data=build_file_descriptor_set(TomPacket).SerializeToString(),
        ),
    )

    location_channel = Channel(
        topic="/location",
        message_encoding="protobuf",
        schema=Schema(
            name=LocationFix.DESCRIPTOR.full_name,
            encoding="protobuf",
            data=build_file_descriptor_set(LocationFix).SerializeToString(),
        ),
    )

    signal_channel = Channel(
        topic="/signal",
        message_encoding="protobuf",
        schema=Schema(
            name=Signal.DESCRIPTOR.full_name,
            encoding="protobuf",
            data=build_file_descriptor_set(Signal).SerializeToString(),
        ),
    )

    if args.enable_camera:
        image_channel = CompressedImageChannel(topic="/camera/image_compressed")
    else:
        image_channel = None

    # INITIALIZE IO RESOURCES
    # LoRa Wiring settings
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Setup Chip Select and Reset pins
    cs = digitalio.DigitalInOut(getattr(board, f"CE{args.spi_cs}"))
    reset = digitalio.DigitalInOut(getattr(board, f"D{args.pins_reset}"))

    # Initialize RFM9x
    lora = RFM9x(spi, cs, reset, args.frequency / 1_000_000)

    # Apply modulation settings
    lora.signal_bandwidth = args.modulation_bw
    lora.spreading_factor = args.modulation_sf
    lora.coding_rate = args.modulation_cr
    lora.preamble_length = args.preamble_len
    lora.sync_word = args.sync_word

    print("[INFO] LoRa initialized")

    # Video capture initialization
    if args.enable_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Could not open camera")
            cap = None
            image_channel = None
        else:
            print("[INFO] Initialized Video Camera")
    else:
        cap = None

    rocket_ids = args.rocket_name.split(',')

    if args.enable_logging:
        # Create logs directory if it doesn't exist
        os.makedirs(args.log_dir, exist_ok=True)

        # Create filename with current datetime
        timestamp = datetime.now().strftime("%Y:%m:%d-%H:%M:%S")
        path = os.path.join(args.log_dir, f"{args.rocket_name}-{timestamp}.mcap")

        with foxglove.open_mcap(path):
            run_telemetry_loop(
                lora, server, image_channel, cap, rocket_ids
            )
    else:
        run_telemetry_loop(
            lora, server, image_channel, cap, rocket_ids
        )


if __name__ == "__main__":
    main()
