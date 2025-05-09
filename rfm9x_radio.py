import gzip
from gpiozero import Button
import board
import busio
import digitalio
import adafruit_rfm9x
import time


def main():
	# Declare parameters
	node_id = 255        
	dest_id = 255
	tx_pwr = 13
	spi_sck = "SCK"
	spi_mosi = "MOSI"
	spi_miso = "MISO"
	spi_cs = "D5"
	spi_reset = "D25"
	interrupt_pin = "5"

	# Initialize SPI and LoRa using parameters for GPIO pins
	spi = busio.SPI(getattr(board, spi_sck), MOSI=getattr(board, spi_mosi), MISO=getattr(board, spi_miso))
	cs = digitalio.DigitalInOut(getattr(board, spi_cs))
	reset = digitalio.DigitalInOut(getattr(board, spi_reset))
	rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, 915.0)
	rfm9x.tx_power = tx_pwr
	rfm9x.node = node_id
	rfm9x.destination = dest_id

	print(f"Initialized radio (SPI:[CK:{spi_sck} MO:{spi_mosi} MI:{spi_miso}] CS:{spi_cs} RST:{spi_reset} PWR:{tx_pwr} NODE:{node_id} DST:{dest_id}")

	# Create subscription and publisher for each topic with appropriate message type
	# TODO call in loop
	while True:
		lora_rx_callback(rfm9x)
		time.sleep(0.05)

def lora_rx_callback(rfm9x):
	if rfm9x.rx_done:
		packet = rfm9x.receive()
		if packet is not None:
			# Decompress the payload
			decompressed_payload = gzip.decompress(packet)

			# Split the payload into topic name and serialized message
			delimiter = b'|'
			topic_name, serialized_msg = decompressed_payload.split(delimiter, 1)

			# Decode the topic name
			topic_name = topic_name.decode()

			# Find the appropriate message type and publisher for the topic
			if topic_name in pubs:
				msg_class = topic_type_map[topic_name]
				deserialized_msg = deserialize_message(serialized_msg, msg_class)
				publisher = pubs[topic_name]

				if deserialized_msg:
					get_logger().debug(f"Received [{topic_name}]: {deserialized_msg}")
					publisher.publish(deserialized_msg)


if __name__ == '__main__':
    main()
