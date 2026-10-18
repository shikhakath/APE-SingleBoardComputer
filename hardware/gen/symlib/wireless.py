"""Symbols for sheet 13 (wireless): LOTES M.2 Key-E socket and the Wurth SMT
standoff that holds the 2230 card.
"""
from schgen import Pin, Symbol, box

# LOTES APCI0085-P002A, drawing AP-APCI0085-P rev 1 (LCSC C841649),
# https://datasheet.lcsc.com/datasheet/pdf/dd04174b85f5751d9f98e98486e9a8c9.pdf?productCode=C841649
# sheet 1/4 (PIN 1/2/22/23/32/33/74/75 callouts) and sheet 3/4 "Recommended PCB
# layout": standard M.2 numbering, odd 1-23 + 33-75 on one row, even 2-22 + 32-74
# on the other (24-31 = key E), 0.5 A per contact. The two SMT hold-down tabs are
# not numbered on the drawing: mapped here as pins 76 and 77 (solder to GND).
# The two locating pegs are non-plated holes (no pin).
# Signal names: PCI Express M.2 Specification Rev 5.0 v1.0, Table 3-12 "SDIO Based
# Add-in Card Pinouts (Key E)" (shipped in TI SWAC007, M2-CC3351 design files).
# Names are from the CARD's point of view: pin 22 UART_TXD is the card's output
# (goes to the SoC RXD), pin 32 UART_RXD is the card's input; TI SWAU133 Table 2-2
# and the SK-AM62B-P1 wiring agree.
_ODD = [
    (1, "GND", "pwr"), (3, "USB_D+", "pas"), (5, "USB_D-", "pas"), (7, "GND", "pwr"),
    (9, "SDIO_CLK", "pas"), (11, "SDIO_CMD", "pas"), (13, "SDIO_DATA0", "pas"),
    (15, "SDIO_DATA1", "pas"), (17, "SDIO_DATA2", "pas"), (19, "SDIO_DATA3", "pas"),
    (21, "SDIO_WAKE#", "pas"), (23, "SDIO_RESET#/TX_BLANK", "pas"),
    (33, "GND", "pwr"), (35, "PERp0", "pas"), (37, "PERn0", "pas"), (39, "GND", "pwr"),
    (41, "PETp0", "pas"), (43, "PETn0", "pas"), (45, "GND", "pwr"),
    (47, "REFCLKp0", "pas"), (49, "REFCLKn0", "pas"), (51, "GND", "pwr"),
    (53, "CLKREQ0#", "pas"), (55, "PEWAKE0#", "pas"), (57, "GND", "pwr"),
    (59, "RSVD/PERp1", "pas"), (61, "RSVD/PERn1", "pas"), (63, "GND", "pwr"),
    (65, "RSVD/PETp1", "pas"), (67, "RSVD/PETn1", "pas"), (69, "GND", "pwr"),
    (71, "RSVD/REFCLKp1", "pas"), (73, "RSVD/REFCLKn1", "pas"), (75, "GND", "pwr"),
]
_EVEN = [
    (2, "3.3V", "pwr"), (4, "3.3V", "pwr"), (6, "LED_1#", "pas"),
    (8, "PCM_CLK/I2S_SCK", "pas"), (10, "PCM_SYNC/I2S_WS", "pas"),
    (12, "PCM_OUT/I2S_SD_OUT", "pas"), (14, "PCM_IN/I2S_SD_IN", "pas"),
    (16, "LED_2#", "pas"), (18, "VIO_CFG", "pas"), (20, "UART_WAKE#", "pas"),
    (22, "UART_TXD", "pas"), (32, "UART_RXD", "pas"), (34, "UART_RTS", "pas"),
    (36, "UART_CTS", "pas"), (38, "VENDOR_DEF", "pas"), (40, "VENDOR_DEF", "pas"),
    (42, "VENDOR_DEF", "pas"), (44, "COEX3", "pas"), (46, "COEX_TXD", "pas"),
    (48, "COEX_RXD", "pas"), (50, "SUSCLK", "pas"), (52, "PERST0#", "pas"),
    (54, "W_DISABLE2#", "pas"), (56, "W_DISABLE1#", "pas"), (58, "I2C_DATA", "pas"),
    (60, "I2C_CLK", "pas"), (62, "ALERT#", "pas"), (64, "VIO_1V8", "pwr"),
    (66, "PERST1#/UIM_SWP", "pas"), (68, "CLKREQ1#/UIM_PWR_SNK", "pas"),
    (70, "PEWAKE1#/UIM_PWR_SRC", "pas"), (72, "3.3V", "pwr"), (74, "3.3V", "pwr"),
]
M2_KEY_E = box("APCI0085-P002A", "M.2 Key-E socket, 67 contacts 0.5 mm, H3.2, 2 SMT tabs (LOTES APCI0085-P002A)",
               [(n, nm, k, "L") for n, nm, k in _ODD]
               + [(76, "TAB", "pwr", "L"), (77, "TAB", "pwr", "L")]
               + [(n, nm, k, "R") for n, nm, k in _EVEN],
               prefix="J", footprint="M2_KEYE_APCI0085")
if len(M2_KEY_E.pins) != 69:
    raise ValueError("M.2 Key-E symbol must have 67 contacts + 2 tabs")

# Wurth WA-SMSI 9774015243R, M2 internal thread, L = 1.5 mm, drawing rev 001.003
# (JLC C22431324): one annular SMT solder pad (5.2/5.3 mm OD) around a 3.1 mm
# non-plated hole. Single pin, tie to GND.
STANDOFF_M2 = Symbol("STANDOFF_SMT_M2", "SMT steel standoff, M2 thread (1 pad, to GND)",
                     [Pin("1", "PAD", "pas", "L", 1, 60, -40, 0, 2)],
                     graphics=["ellipse|1|1|0|0|0|40|40", "ellipse|1|1|0|0|0|15|15"],
                     designator_prefix="H", footprint="WE_9774015243R",
                     show_names=False, show_numbers=False)

SYMBOLS = [M2_KEY_E, STANDOFF_M2]
