import argparse
from base64 import b64decode
import csv
import foxglove
from NavPacket_pb2 import NavPacket
import os
from utils import build_file_descriptor_set


parser = argparse.ArgumentParser()
parser.add_argument('filename')
args = parser.parse_args()


def main() -> None:
    prefix = args.filename.split(".")[0]
    csvfilename = prefix + ".csv"
    mcapfilename = prefix + ".mcap"
    nav_channel = foxglove.Channel(
        topic="/navigation",
        message_encoding="protobuf",
        schema=foxglove.Schema(
            name=NavPacket.DESCRIPTOR.full_name,
            encoding="protobuf",
            data=build_file_descriptor_set(NavPacket).SerializeToString(),
        )
    )
    mode = "w" if os.path.exists(csvfilename) else "x"

    with (
        open(args.filename) as file,
        open(csvfilename, mode) as csvfile,
        foxglove.open_mcap(mcapfilename, allow_overwrite=True)
    ):
        writer = csv.writer(csvfile)
        writer.writerow([
            "timestamp.seconds",
            "timestamp.nanos",
            "gnss.latitude",
            "gnss.longitude",
            "imu.acc_x",
            "imu.acc_y",
            "imu.acc_z",
            "imu.gyr_x",
            "imu.gyr_y",
            "imu.gyr_z",
            "alt.altitude",
            "magn.x",
            "magn.y",
            "magn.z",
        ])
        for line in file.readlines():
            if len(line.strip()) == 0 or line.startswith("#"):
                continue

            packet = NavPacket()
            try:
                packet.ParseFromString(b64decode(line))
            except Exception as e:
                continue

            nav_channel.log(packet.SerializeToString(), log_time=int(packet.timestamp.seconds * 1e9 + packet.timestamp.nanos))
            writer.writerow([
                packet.timestamp.seconds,
                packet.timestamp.nanos,
                packet.gnss.latitude,
                packet.gnss.longitude,
                packet.imu.acc_x,
                packet.imu.acc_y,
                packet.imu.acc_z,
                packet.imu.gyr_x,
                packet.imu.gyr_y,
                packet.imu.gyr_z,
                packet.alt.altitude,
                packet.magn.x,
                packet.magn.y,
                packet.magn.z,
            ])


if __name__ == '__main__':
    main()
