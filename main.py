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
from LoRaRF import SX127x

# Local imports for custom protobuf schema and CLI
from cli import parser
# from TomPacket_pb2 import TomPacket
from tom_packet_pb2 import TomPacket  # using old protobuf for cert launch
from utils import build_file_descriptor_set, CustomListener


def run_telemetry_loop(
        lora: SX127x,
        server: WebSocketServer,
        telemetry_channel: Channel,
        image_channel: CompressedImageChannel,
        cap: cv2.VideoCapture | None = None,
) -> None:
    try:
        # tom_packet_size = len(TomPacket().SerializeToString())

        while True:
            # Get data from LoRa
            lora.request()
            print("waiting")

            if lora.wait(timeout=10.0):
                # while lora.available() > tom_packet_size:
                #     telemetry_channel.log(lora.read(tom_packet_size))

                print("collecting")
                bytestr = b""

                while lora.available() > 0:
                    bytestr += bytes(lora.read())

                if len(bytestr) > 0:
                    print(bytestr)
                    telemetry_channel.log(bytestr)
                else:
                    print("failed!")

            # Get data from Camera
            if cap is not None:
                ret, frame = cap.read()
                if ret:
                    im_packet = CompressedImage(
                        data=cv2.imencode(".jpeg", frame)[1].tobytes(),
                        format="jpeg"
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

    if args.enable_logging:
        # Create logs directory if it doesn't exist
        os.makedirs(args.log_dir, exist_ok=True)

        # Create filename with current datetime
        timestamp = datetime.now().strftime("%Y:%m:%d-%H:%M:%S")
        path = os.path.join(
            args.log_dir, f"{args.rocket_name}-{timestamp}.mcap"
        )

        with foxglove.open_mcap(path):
            run_telemetry_loop(
                lora,
                server,
                telemetry_channel,
                image_channel,
                cap
            )
    else:
        run_telemetry_loop(
            lora,
            server,
            telemetry_channel,
            image_channel,
            cap
        )


if __name__ == '__main__':
    main()
