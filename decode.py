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
            "gnss.latitude",
            "gnss.longitude",
            "gnss.satellites",
            "imu0.acc_x",
            "imu0.acc_y",
            "imu0.acc_z",
            "imu0.gyr_x",
            "imu0.gyr_y",
            "imu0.gyr_z",
            "imu1.acc_x",
            "imu1.acc_y",
            "imu1.acc_z",
            "imu1.gyr_x",
            "imu1.gyr_y",
            "imu1.gyr_z",
            "imu2.acc_x",
            "imu2.acc_y",
            "imu2.acc_z",
            "imu2.gyr_x",
            "imu2.gyr_y",
            "imu2.gyr_z",
            "alt0.altitude",
            "alt1.altitude",
            "alt2.altitude",
            "magn.x",
            "magn.y",
            "magn.z",
        ])
        for line in file.readlines():
            packet = NavPacket()
            packet.ParseFromString(b64decode(line))

            nav_channel.log(packet.SerializeToString())
            writer.writerow([
                packet.gnss.latitude,
                packet.gnss.longitude,
                packet.gnss.satellites,
                packet.imu0.acc_x,
                packet.imu0.acc_y,
                packet.imu0.acc_z,
                packet.imu0.gyr_x,
                packet.imu0.gyr_y,
                packet.imu0.gyr_z,
                packet.imu1.acc_x,
                packet.imu1.acc_y,
                packet.imu1.acc_z,
                packet.imu1.gyr_x,
                packet.imu1.gyr_y,
                packet.imu1.gyr_z,
                packet.imu2.acc_x,
                packet.imu2.acc_y,
                packet.imu2.acc_z,
                packet.imu2.gyr_x,
                packet.imu2.gyr_y,
                packet.imu2.gyr_z,
                packet.alt0.altitude,
                packet.alt1.altitude,
                packet.alt2.altitude,
                packet.magn.x,
                packet.magn.y,
                packet.magn.z,
            ])


if __name__ == '__main__':
    main()
