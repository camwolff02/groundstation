"""
This script demonstrates how to write a Foxglove WebSocket server that transmits Protobuf-encoded
data. The included Protobuf schemas are generated from https://github.com/foxglove/schemas.
"""

import asyncio
import sys
import time
import argparse
from base64 import b64encode
from traceback import print_exception
from typing import Set, Type
from foxglove_websocket import run_cancellable
from foxglove_websocket.server import FoxgloveServer, FoxgloveServerListener
from foxglove_websocket.types import ChannelId
from mcap_protobuf.writer import Writer
import math  # TODO remove
import cv2

# import custom protobuf schema
from tom_packet_pb2 import TomPacket, TwoStageState  
from CompressedImage_pb2 import CompressedImage
# import protobuf schemas
try:
    import google.protobuf.message
    from google.protobuf.descriptor_pb2 import FileDescriptorSet
    from google.protobuf.descriptor import FileDescriptor
except ImportError as err:
    print_exception(*sys.exc_info())
    print(
        "Unable to import protobuf schemas; did you forget to run `pip install 'foxglove-websocket[examples]'`?",
    )
    sys.exit(1)

# add arguments for command line interface
parser = argparse.ArgumentParser(
    prog="protobuf_server",
    description="A ground station for TOM flight boards",
    epilog="text at the bottom of help",
)

parser.add_argument("-a", "--address", default="0.0.0.0", help="server address")
parser.add_argument("-p", "--port", default=8765, type=int, help="server port")
parser.add_argument("-n", "--server-name", default="ground control", help="server name")
parser.add_argument(
    "-l",
    "--enable_logging",
    action="store_true",
    help="enable logging on groundstation",
)
parser.add_argument(
    "-c",
    "--enable_camera",
    action="store_true",
    help="enable and disable logging on ground",
)
args = parser.parse_args()


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


async def main():
    class Listener(FoxgloveServerListener):
        async def on_subscribe(self, server: FoxgloveServer, channel_id: ChannelId):
            print("First client subscribed to", channel_id)

        async def on_unsubscribe(self, server: FoxgloveServer, channel_id: ChannelId):
            print("Last client unsubscribed from", channel_id)

    async with FoxgloveServer(args.address, args.port, args.server_name) as server:
        server.set_listener(Listener())

        telemetry_channel_id = await server.add_channel(
            {
                "topic": "telemetry",
                "encoding": "protobuf",
                "schemaName": TomPacket.DESCRIPTOR.full_name,
                "schema": b64encode(
                    build_file_descriptor_set(TomPacket).SerializeToString()
                ).decode("ascii"),
                "schemaEncoding": "protobuf",
            }
        )

        camera_channel_id = await server.add_channel(
            {
                "topic": "camera/image_compressed",
                "encoding": "protobuf",
                "schemaName": CompressedImage.DESCRIPTOR.full_name,
                "schema": b64encode(
                    build_file_descriptor_set(CompressedImage).SerializeToString()
                ).decode("ascii"),
                "schemaEncoding": "protobuf",
            }
        )

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera")
            sys.exit(1)


        # TODO figure out how to make logging optional
        # if args.enable_logging:
        #     mcap_writer = Writer(open("log.mcap", "wb"))
        # else:
        #     mcap_writer = None
        with open("log.mcap", "wb") as f, Writer(f) as mcap_writer:
            state = TwoStageState.MAXQ
            i = 0
            while True:
                i += 1
                await asyncio.sleep(0.05)
                now = time.time_ns()

                # TELEMETRY PUBLISHER
                # Send a custom message
                tom_packet = TomPacket()
                tom_packet.latitude = 10
                tom_packet.longitude = 20
                tom_packet.altitude = math.sin(i / 100)

                if i % 20 == 0:
                    state += 1
                    if state > 4:
                        state = 0
                tom_packet.state = state

                await server.send_message(
                    telemetry_channel_id, now, tom_packet.SerializeToString()
                )

                if not mcap_writer is None:
                    mcap_writer.write_message(
                        topic="telemetry",
                        message=tom_packet,
                        log_time=now,
                        publish_time=now,
                    )

                # CAMERA PUBLISHER
                ret, frame = cap.read()

                if not ret:
                    print("Error: Can't receive frame")
                    break

                im_packet = CompressedImage()
                im_packet.timestamp.FromNanoseconds(now)
                im_packet.data = cv2.imencode(".jpeg", frame)[1].tobytes()
                im_packet.format = "jpeg"
                await server.send_message(
                    camera_channel_id, now, im_packet.SerializeToString()
                )

                try:
                    if not mcap_writer is None:
                        mcap_writer.write_message(
                            topic="camera/image_compressed",
                            message=im_packet,
                            log_time=now,
                            publish_time=now,
                        )
                except OSError as e:
                    pass


if __name__ == "__main__":
    run_cancellable(main())
