from LoRaRF import SX127x
from cli import parser


def run_telemetry_loop(lora: SX127x) -> None:
    try:
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
            else:
                print("failed!")

    except KeyboardInterrupt:
        print()


def main() -> None:
    args = parser.parse_args()

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
    run_telemetry_loop(lora)


if __name__ == '__main__':
    main()
