# Native python imports
from datetime import datetime
import logging
import os

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


def run_telemetry_loop(
    lora: RFM9x,
    server: WebSocketServer,
    image_channel: CompressedImageChannel | None = None,
    cap: cv2.VideoCapture | None = None,
    rocket_ids: list[str] = [],
) -> None:
    # Create a dictionary to store channels for each rocket
    rocket_channels = {
        rocket_id: {
            "telemetry": Channel(
                topic=f"/telemetry/{rocket_id}",
                message_encoding="protobuf",
                schema=Schema(
                    name=TomPacket.DESCRIPTOR.full_name,
                    encoding="protobuf",
                    data=build_file_descriptor_set(TomPacket).SerializeToString(),
                ),
            ),
            "location": Channel(
                topic=f"/location/{rocket_id}",
                message_encoding="protobuf",
                schema=Schema(
                    name=LocationFix.DESCRIPTOR.full_name,
                    encoding="protobuf",
                    data=build_file_descriptor_set(LocationFix).SerializeToString(),
                ),
            ),
            "signal": Channel(
                topic=f"/signal/{rocket_id}",
                message_encoding="protobuf",
                schema=Schema(
                    name=Signal.DESCRIPTOR.full_name,
                    encoding="protobuf",
                    data=build_file_descriptor_set(Signal).SerializeToString(),
                ),
            ),
        }
        for rocket_id in rocket_ids
    }

    try:
        while True:
            # Get data from LoRa
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

                    # Publish location data to the rocket's location channel
                    if tom_packet.HasField("location"):
                        channels["location"].log(tom_packet.location.SerializeToString())

                    # Publish telemetry data to the rocket's telemetry channel
                    channels["telemetry"].log(bytes(packet))

                    # Publish signal data to the rocket's signal channel
                    signal_data = Signal(rssi=lora.last_rssi, snr=lora.last_snr)
                    channels["signal"].log(signal_data.SerializeToString())
                except google.protobuf.message.DecodeError:
                    print(
                        "[ERROR] Could not decode packet! Did flight computer shut off?"
                    )

            # Get data from Camera
            if cap is not None and image_channel is not None:
                ret, frame = cap.read()
                if ret:
                    im_packet = CompressedImage(
                        data=cv2.imencode(".jpeg", frame)[1].tobytes(), format="jpeg"
                    )
                    image_channel.log(im_packet)

    except KeyboardInterrupt:
        print()
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
