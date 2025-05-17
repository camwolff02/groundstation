import argparse

# add arguments for command line interface
parser = argparse.ArgumentParser(
    prog="protobuf_server",
    description="A ground station for TOM flight s",
    epilog="text at the bottom of help",
)

# Arguments for server instance
parser.add_argument(
    "-a", "--address",
    default="0.0.0.0",
    help="Server host address, default to all external hosts"
)
parser.add_argument("-p", "--port", default=8765, type=int, help="server port")
parser.add_argument(
    "-n",
    "--server-name",
    default="ground control",
    help="server name"
)
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
parser.add_argument("--spi_cs", default=0)
parser.add_argument("--spi_speed", default=1_000_000)
parser.add_argument("--pins_reset", default=27)
parser.add_argument("--pins_irq", default=17)
parser.add_argument("--frequency", default=915_000_000)
parser.add_argument("--modulation_sf", default=10)
parser.add_argument("--modulation_bw", default=500_000, help="Bandwidth")
parser.add_argument("--modulation_cr", default=8)
parser.add_argument("--preamble_len", default=12)
parser.add_argument("--sync_word", default=0x34)
