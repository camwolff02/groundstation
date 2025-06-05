import polars as pl
import argparse
import numpy as np

from NavPacket_pb2 import NavPacket

parser = argparse.ArgumentParser(description="Process OpenRocket CSV data with optional noise.")
parser.add_argument(
    "-f",
    "--csv-file",
    type=str,
    default="forte_openrocket.csv",
    help="Path to the OpenRocket CSV file. Default is 'forte_openrocket.csv'."
)
parser.add_argument(
    "-n",
    "--add-noise",
    action="store_true",
    help="Add random noise to the data to simulate real sensor readings."
)
parser.add_argument(
    "-s",
    "--noise-std",
    type=float,
    default=0.05,
    help="Standard deviation of the noise to be added. Default is 0.05."
)


def main() -> None:
    # Set up argument parser
    args = parser.parse_args()

    # Read the CSV file into a Polars DataFrame
    df = pl.read_csv(
        args.csv_file,
        has_header=False,
        new_columns=["time", "altitude", "velocity", "acceleration"],
    )

    # Add noise if the argument is provided
    if args.add_noise:
        df = df.with_columns([
            (df["altitude"] + np.random.normal(0, args.noise_std, len(df))).alias("altitude"),
            (df["velocity"] + np.random.normal(0, args.noise_std, len(df))).alias("velocity"),
            (df["acceleration"] + np.random.normal(0, args.noise_std, len(df))).alias("acceleration"),
        ])

    # Display the first few rows
    print("OpenRocket DataFrame:")
    print(df.head())

    # Create NavPacket for each row in the DataFrame
    nav_packets: list[NavPacket] = [create_nav_packet(packet) for packet in df.iter_rows()]

    # Example: Print the first NavPacket
    print(nav_packets[0])


def create_nav_packet(row: tuple[float, float, float, float]) -> NavPacket:
    """
    Create a NavPacket from a single row of the DataFrame.
    """
    all_seconds, altitude, _, acceleration = row
    seconds: int = int(all_seconds)
    nanoseconds: int = int((all_seconds - seconds) * 1e9)

    packet = NavPacket()
    packet.timestamp.seconds = seconds
    packet.timestamp.nanos = nanoseconds
    packet.gnss.timestamp.seconds = seconds
    packet.gnss.timestamp.nanos = nanoseconds
    packet.gnss.altitude = altitude
    packet.imu.acc_x = acceleration 
    packet.alt.altitude = altitude
    return packet


if __name__ == "__main__":
    main()
