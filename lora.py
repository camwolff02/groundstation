# Native python imports
import argparse
import os
import sys
import time

# External library imports for gpio, lora, foxglove, logging, etc.
from base64 import b64encode
import cv2
from foxglove_websocket import run_cancellable
from foxglove_websocket.server import FoxgloveServer, FoxgloveServerListener
from foxglove_websocket.types import ChannelId
from mcap_protobuf.writer import Writer
from traceback import print_exception
from typing import Set, Type

from LoRaRF import SX127x


# add arguments for command line interface
parser = argparse.ArgumentParser(
    prog="protobuf_server",
    description="A ground station for TOM flight s",
    epilog="text at the bottom of help",
)

# Arguments for radio
parser.add_argument("--node_id", default=255)
parser.add_argument("--dest_id", default=255)
parser.add_argument("--tx_pwr", default=13)
parser.add_argument("--spi_sck", default="SCK")
parser.add_argument("--spi_mosi", default="MOSI")
parser.add_argument("--spi_miso", default="MISO")
parser.add_argument("--spi_cs", default="CE1")
parser.add_argument("--spi_reset", default="D27")
parser.add_argument("--frequency", default=915)
parser.add_argument("--preamble_length", default=12)
parser.add_argument("--bandwidth", default=250_000)
parser.add_argument("--spreading_factor", default=10)

args = parser.parse_args()


def main() -> None:
    # Initialize SPI and LoRa radio using parameters for GPIO pins
    lora = SX127x()
    lora.setSpi(0, 1, 1_000_000)
    lora.setPins(
        reset=27,
        irq=17
    )
    lora.begin()

    # Setting packet stuff
    lora.setModem(SX127x.LORA_MODEM)
    lora.setFrequency(915_000_000)
    lora.setLoRaModulation(
        sf=10,
        bw=250_000,
        cr=8,
    )
    lora.setPreambleLength(8)
    lora.setSyncWord(0x34)
    lora.setRxGain(True, lora.RX_GAIN_BOOSTED)

    # spi = busio.SPI(
    #     getattr(board, args.spi_sck),
    #     MOSI=getattr(board, args.spi_mosi),
    #     MISO=getattr(board, args.spi_miso),
    # )
    # cs = digitalio.DigitalInOut(getattr(board, args.spi_cs))
    # reset = digitalio.DigitalInOut(getattr(board, args.spi_reset))
    # rfm9x = RFM9x(spi, cs, reset, args.frequency)
    # rfm9x.tx_power = args.tx_pwr
    # rfm9x.node = args.node_id
    # rfm9x.destination = args.dest_id
    # rfm9x.preamble_length = args.preamble_length
    # rfm9x.signal_bandwidth = args.bandwidth
    # rfm9x.spreading_factor = args.spreading_factor

    print('lora initialized')

    try:
        while True:
            lora.request()
            lora.wait()

            bytes = []
            while lora.available() > 0:
                byte = lora.read()
                bytes.append(byte)

            if len(bytes) > 0:
                print("".join([f"{byte:02x}" for byte in bytes]))
            else:
                print(":( ")

    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
