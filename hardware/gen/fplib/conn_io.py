"""I/O connectors: USB-C, HDMI-A, microSD, 3.5 mm jack, CSI FPC, eMMC-module B2B plugs.

All coordinates are in mm, +y up (top view), in the frame of the manufacturer's
land-pattern drawing (datum named per footprint); footprints.py shifts them to
the body centre on emission. Mating faces point to -y where the part has one.
"""
from footprints import Footprint, npth, row, smd, tht


def vslot(name, x, y, w, h, hole, length):
    """Plated oval slot running along y: copper w x h, hole ``hole`` wide x ``length`` long."""
    return tht(name, x, y, w, h, hole=hole, slot=length, slot_rot=90.0)


# --------------------------------------------------------------------- USB-C
# Korean Hroparts TYPE-C-31-M-12 (LCSC C165948), USB 2.0 16-contact receptacle.
# Drawing "TYPE-C-31-M-12" rev A, sheet 1 of 1, 2020-12-08:
#   https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948
# "RECOMMEND P.C.B LAYOUT (COMPONENT SIDE)" = top view, mating face toward the
# PCB edge (-y); pad labels left to right as drawn: A1/B12 A4/B9 B8 A5 B7 A6 A7
# B6 A8 B5 B4/A9 B1/A12 (slash dropped to match the symbol).
# Datum: x = centre line, y = 0 on the line through the pad inner (front) edges,
# which is also the rear-slot centre line (the "4.18" dimension starts there).
#   * pads: 4-0.60 wide (shared pads, centres 4.80 and 6.40 apart -> x = +-2.40,
#     +-3.20) and 8-0.30 at 0.50 pitch (3.50 / 2.50 / 1.50 between B8-B5, A5-A8,
#     B7-B6). Length: "1.64" pad outer edge -> locating-hole centre line minus
#     "0.50" pad inner edge -> hole centre line = 1.14; centre y = 0.57.
#   * locating holes: 2x d0.60 NPTH, centres 5.78 apart, 0.50 below y = 0.
#   * shell slots, x = +-8.65/2 = +-4.325: rear (next to the pads) hole 0.60 x
#     1.70, copper 0.90 x 2.00, at y = 0; front hole 0.60 x 1.40, copper 0.90 x
#     1.70, at y = -4.18. The side view confirms rear legs 1.10 / front legs 0.80
#     wide, 4.17 apart. Annular ring 0.15 as drawn.
#   * body 8.94 x 7.35 (top view). Front face: the bottom view gives 6.28 from the
#     front face to the posts -> y = -0.50 - 6.28 = -6.78 (side view: front face to
#     front leg 2.60 = 6.78 - 4.18, consistent); rear = -6.78 + 7.35 = +0.57. The
#     PCB edge is drawn 5.79 below the hole centres (y = -6.29), so the shell
#     overhangs the board edge by 0.49.
USB_C = Footprint(
    "USB-C_HRO_TYPE-C-31-M-12",
    "HRO TYPE-C-31-M-12 USB 2.0 Type-C receptacle, SMD + 4 plated shell slots",
    [smd("A1B12", -3.20, 0.57, 0.60, 1.14), smd("A4B9", -2.40, 0.57, 0.60, 1.14)]
    + row(["B8", "A5", "B7", "A6", "A7", "B6", "A8", "B5"], -1.75, 0.57, 0.50, 0, 0.30, 1.14)
    + [smd("B4A9", 2.40, 0.57, 0.60, 1.14), smd("B1A12", 3.20, 0.57, 0.60, 1.14),
       vslot("S1", -4.325, -4.18, 0.90, 1.70, 0.60, 1.40),
       vslot("S2", 4.325, -4.18, 0.90, 1.70, 0.60, 1.40),
       vslot("S3", -4.325, 0.0, 0.90, 2.00, 0.60, 1.70),
       vslot("S4", 4.325, 0.0, 0.90, 2.00, 0.60, 1.70),
       npth(-2.89, -0.50, 0.60), npth(2.89, -0.50, 0.60)],
    body=(-4.47, -6.78, 4.47, 0.57), marker_pad="A1B12",
    assumed="The shell slots are unnumbered on the drawing: S1/S2 = front (board-edge, 0.6 x 1.4) "
            "slots left/right, S3/S4 = rear (0.6 x 1.7) slots left/right.")

# ---------------------------------------------------------------------- HDMI
# XFCN HDMI-A-19F-S-D, HDMI type-A receptacle "HDMI A 19P/F SMT+DIP", rev A1,
# 2025-11-19 (via LCSC C5151728): https://www.lcsc.com/datasheet/C5151728.pdf
# "PCB LAYOUT" (vector drawing; positions checked against the PDF geometry).
# Datum: x = centre line, y = 0 on the rear-slot centre line.
#   * 19 pads 0.30 x 2.60, 0.50 pitch, 9.00 first to last, centred between the
#     slots; outer edge 2.06 above y = 0 -> centre y = 2.06 - 1.30 = 0.76.
#   * slots "2-14.50" apart (x = +-7.25), copper "4-1.50" wide, hole "4-0.90":
#     rear (y = 0) hole 2.70 / copper 3.30 long ("2-2.70", "2-3.30"); front 5.96
#     below, hole 1.70 / copper 2.30 ("2-1.70", "2-2.30").
#   * body: 14.50 wide (front view), 11.80 deep (top view). Side view: front face
#     4.50 ahead of the front leg -> y = -5.96 - 4.50 = -10.46; rear = -10.46 + 11.80
#     = +1.34. The PCB edge is drawn 9.50 below y = 0 (shell overhangs it by 0.96).
# The drawing does not number the contacts. Pin 1 is put at +x (right, seen from
# the top with the opening down), as on the TI SK-AM62B J5 (Amphenol 10029449,
# same standard type-A tail order): in reference/1_PROC142B/4_Gerber/
# IPC-D-356_NETLIST/PROC142B_IPC.ipc the J5 pads run 1 -> 19 along +Y with the
# front legs at -X; rotated so the opening faces -y, pin 1 lands at +x. The KiCad
# library footprint HDMI_A_Amphenol_10029449-x01xLF_Horizontal agrees (pad 1 at
# x +4.75, pad 19 at -4.25, "PCB Edge" on the opening side). Shell legs follow the
# SK numbering: 20 rear / pin-1 side, 21 rear / pin-19 side, 22 front / pin-1
# side, 23 front / pin-19 side.
HDMI_A = Footprint(
    "HDMI_A_XFCN_19F_S_D",
    "XFCN HDMI-A-19F-S-D HDMI type-A receptacle, 19 SMD contacts 0.5 mm + 4 plated shell slots",
    row(range(1, 20), 4.50, 0.76, -0.50, 0, 0.30, 2.60)
    + [vslot(20, 7.25, 0.0, 1.50, 3.30, 0.90, 2.70), vslot(21, -7.25, 0.0, 1.50, 3.30, 0.90, 2.70),
       vslot(22, 7.25, -5.96, 1.50, 2.30, 0.90, 1.70), vslot(23, -7.25, -5.96, 1.50, 2.30, 0.90, 1.70)],
    body=(-7.25, -10.46, 7.25, 1.34),
    assumed="Contacts are unnumbered on the drawing: 1..19 in HDMI type-A order with pin 1 at +x "
            "(opening down), as on the SK-AM62B J5 and KiCad Amphenol 10029449 footprints; legs 20/21 "
            "rear right/left, 22/23 front right/left.")

# ------------------------------------------------------------------- microSD
# Korean Hroparts TF-01A push-push microSD socket (LCSC C91145), drawing "TF-01A"
# rev A, 2014-09-29, sheet 1 of 1:
#   https://datasheet.lcsc.com/datasheet/pdf/7650eac21a54674b08ad4ba21e17fceb.pdf?productCode=C91145
# "PCB Layout (Pattern Side)", drawn rotated 90 deg on the sheet. Read in the same
# orientation as the shell top view on the sheet (that view also has the Cd tail at
# the left end of the tail row), i.e. a top view, card slot toward -y. Positions
# were taken from the vector geometry (9.682 pt/mm) and agree with the dimensions.
# Datum: x = 0 on pad 1, y = 0 on the contact-pad centre line.
#   * 9 pads 0.70 x 1.30 ("9-0.70", "9-1.30") at 1.10 pitch, labelled
#     Cd 8 7 6 5 4 3 2 1 from left to right: pad n at x = -(n-1)*1.10, Cd at -8.80.
#   * shell tabs 1.20 wide: rear pair 1.40 long, centre 1.50 below the pad outer
#     edge (y = 0.65 - 1.50 = -0.85), left one 1.10 left of Cd (x = -9.90), right
#     one 13.58 right of Cd (x = 4.78); front pair 2.00 long, 11.20 below the pad
#     outer edge / 9.70 below the rear tabs (y = -10.55), left x = -9.90, right
#     15.52 right of the left tab (x = 5.62).
#   * 2x d1.00 NPTH, 2.81 and 10.81 right of the left tabs (x = -7.09, 0.91).
#     Their y is not dimensioned in the layout; the bottom view gives 10.49 from
#     the shell rear edge to the posts -> y = -0.35 - 10.49 = -10.84 (matches the
#     vector drawing).
#   * body = shell outline in the layout, 14.80 x 14.50 (top view): x -9.59..5.20,
#     y -14.85 (front, right side; the left side stops at 13.79) .. -0.35 (rear).
# Cross-check: the LCSC EasyEDA footprint for C91145 has the same pad order but
# puts every tab and post 0.10 mm further left of the contacts (Cd to rear-left tab
# 1.20). The drawing's "1.10" runs to the tab centre, so the drawing values stay.
TF_01A = Footprint(
    "MICROSD_HRO_TF-01A",
    "HRO TF-01A push-push microSD socket with card detect, SMD",
    row(range(1, 9), 0.0, 0.0, -1.10, 0, 0.70, 1.30)
    + [smd(9, -8.80, 0.0, 0.70, 1.30),
       smd(10, -9.90, -0.85, 1.20, 1.40), smd(11, 4.78, -0.85, 1.20, 1.40),
       smd(12, -9.90, -10.55, 1.20, 2.00), smd(13, 5.62, -10.55, 1.20, 2.00),
       npth(-7.09, -10.84, 1.00), npth(0.91, -10.84, 1.00)],
    body=(-9.59, -14.85, 5.20, -0.35),
    assumed="'Cd' is pad 9; the unnumbered shell tabs are 10 rear-left and 11 rear-right (1.40 mm), "
            "12 front-left and 13 front-right (2.00 mm).")

# ---------------------------------------------------------------- audio jack
# Korean Hroparts PJ-320DB (variant -A = 4 contacts + dummy), 3.5 mm SMD jack,
# drawing "PJ-320DB" rev A, sheet 1 of 1 (via LCSC C707225):
#   https://www.lcsc.com/datasheet/C707225.pdf
# "P.C.B Layout TOP view": plug entry on the left; pads numbered on the drawing,
# matching the symbol (1 sleeve, 2 tip, 3 ring 1, 4 ring 2, 5 dummy per the
# drawing's schematic table). Drawing frame: x along the barrel from the body
# front face, y = 0 on the barrel axis.
#   * pads 1.20 ("1.20 (Typ)") x 2.50: rows 4.00 apart inside / 9.00 outside ->
#     length (9.00 - 4.00)/2 = 2.50, row centres +-3.25.
#     Upper row: 4 at x 3.20, 3 at 6.20, 2 at 10.20; lower row: 5 at 2.40, 1 at 11.20.
#   * 2x d1.20 NPTH (posts d1.00) on the axis at x 1.60 and 1.60 + 7.00 = 8.60.
#   * body 12.10 long x 6.10 wide; the d5.00 mouth sticks out 2.00 ahead of x = 0.
# Rotated +90 deg here, (x, y) -> (-y, x), so the plug enters from -y: the upper
# row (2, 3, 4) goes to x = -3.25, the lower row (1, 5) to x = +3.25. The body
# outline excludes the mouth; the courtyard covers it (5.00 x 2.00 at y < 0).
JACK_PJ320DB = Footprint(
    "JACK_HRO_PJ-320DB",
    "HRO PJ-320DB 3.5 mm 4-pole SMD audio jack, 5 pads + 2 locating posts",
    [smd(4, -3.25, 3.20, 2.50, 1.20), smd(3, -3.25, 6.20, 2.50, 1.20), smd(2, -3.25, 10.20, 2.50, 1.20),
     smd(5, 3.25, 2.40, 2.50, 1.20), smd(1, 3.25, 11.20, 2.50, 1.20),
     npth(0.0, 1.60, 1.20), npth(0.0, 8.60, 1.20)],
    body=(-3.05, 0.0, 3.05, 12.10),
    # pads reach x +-4.50; pin-1 dot at x = 4.50 + 0.35 (+0.20 radius); mouth to y = -2.00
    courtyard=(-4.75, -2.25, 5.30, 12.35))

# ------------------------------------------------------------------- CSI FPC
# TE Connectivity 1-1734248-5, 15-position 1.0 mm FPC, ZIF, vertical, SMT.
# Customer drawing C-1734248 rev E1 (06JAN14), "1.0 MM FPC, ZIF VERTICAL, SMT
# TYPE", sheet 1 of 2, "RECOMMENDED PCB LAYOUT" (via LCSC C2922285):
#   https://www.lcsc.com/datasheet/C2922285.pdf
# The layout is drawn for a generic position count (9 shown); 15 positions:
# table row 1-1734248-5: DIM A 14.0 = (15-1) x 1.00, DIM B 20.6 body, actuator
# 0.90 longer each end ("0.90 2 PLC").
# Datum: x = 0 at the middle circuit (8), y = 0 on the "CONNECTOR LOCATION" line
# (outline top edge). CIRCUIT NO.1 is at the right: circuit n at x = 7.0 - (n-1).
#   * each circuit has two tails (one per row), pads 0.60 wide ("0.60 TYP"):
#     row 1 from y +0.95 to -0.90 (1.85 long, centre 0.025); row 2 from -2.90 to
#     -2.90 - 1.65 = -4.55 (centre -3.725). Same as SK J19 (nA 0.61 x 1.85, nB
#     0.61 x 1.65, 3.75 apart). Both pads of circuit n are pad "n": the side view
#     shows each contact with a tail on both sides (1.25 / 1.45 TYP). The LCSC
#     EasyEDA footprint for C2922285 has the rows 3.37 apart; the drawing gives 3.75.
#   * body = "CONNECTOR LOCATION" outline: 4.20 beyond the outer circuits
#     (7.0 + 4.2 = 11.2 = 22.4 / 2, the actuator length 20.6 + 2 x 0.90), 4.50 deep
#     (3.40 at the ends, the narrow centre part 4.50; scaled from the vector drawing).
# The drawing shows no hold-down or solder tabs (none on SK J19 either), so this
# footprint has no unnamed tab pads.
FPC15 = Footprint(
    "FPC_TE_1-1734248-5",
    "TE 1-1734248-5 15-pos 1.0 mm FPC connector, ZIF vertical, SMT, two tails per circuit",
    row(range(1, 16), 7.0, 0.025, -1.0, 0, 0.60, 1.85) + row(range(1, 16), 7.0, -3.725, -1.0, 0, 0.60, 1.65),
    body=(-11.2, -4.50, 11.2, 0.0),
    assumed="Both tails of circuit n are pad n; circuits 1..15 run right to left as drawn (CIRCUIT NO.1 at the right).")

# ------------------------------------------------------------- eMMC B2B plugs
# LS Mtron GB042 series 0.4 mm PCB-to-PCB connector, plug "GB042-xxP-H10-E3000".
# Source: LS Mtron connector catalogue, "GB042 series Plug & Embossed Tape
# Assembly" (catalogue p.14) with "PCB LAYOUT(REFERENCE)"; the copy used is
#   https://www.zagroselec.ir/stfiles/getappdocument/1/true/27eb9e85-7e18-4b0a-9a05-f75f93a6cbc2.pdf
# (PDF page 8; the same pages are mirrored at
#  https://www.datasheetcafe.com/wp-content/uploads/2021/01/GB042-10P-H10-E3000.pdf).
#   * two rows of pads 0.23 x 0.70, 0.4 pitch, rows 1.8 apart inside -> row
#     centres +-(0.9 + 0.35) = +-1.25. Pin span A = 6.4 (34P) / 5.6 (30P) =
#     (n/2 - 1) x 0.4; body B = 8.3 / 7.5 long, 2.2 wide (2.7 over the tails).
#   * the catalogue lists only insulator and contacts for GB042 (the GB044 page
#     lists hold-downs), and both drawings show plastic end blocks with no tails:
#     there are NO hold-down pads. The symbol pins 35-38 (34P) / 31-34 (30P)
#     were removed from the symbols.
# Contact numbering is not in the catalogue. It is taken from a working
# third-party design with this plug, the OSH Park "eMMC ODROID connector flex
# extender" (dls, 2021, https://oshpark.com/shared_projects/WPv807Oy, gerbers
# downloaded from the project page): its GB042-34P-H10 land pattern is exactly the
# catalogue one, with no other pads. Tracing its copper, the two 2-pad power nets
# (VCCQ 20/21, VCC 22/23) sit side by side in one row and the GND/signal
# alternation of the Radxa RAD-DOC-0126 pinout fits 31 of 34 positions only with
# rows 1..17 and 18..34 and pin 34 opposite pin 1 (counter-clockwise seen from the
# top, like an IC); odd/even rows do not fit. Its pin-1 silk dot agrees, and so do
# the ROCK64 (J7101) and ROCK 3A (J5) symbols (1..17 down one side, 34..18 down the
# other). Here: 1..17 bottom row left to right, 18..34 top row right to left.
# The 30-pin plug (all contacts GND) is numbered the same way by analogy.
# Confirmed by the Radxa eMMC module's own board export (PADS job
# EMMC_V1.1_20190402.pcb, 2D DXF): its GB042-34 and GB042-30 socket decals run
# 1..k along one row and back along the other (last pin opposite 1), clockwise seen
# from the socket face, and have no hold-down pads. The plug meets the socket face
# to face, so seen from the host top it is the mirror image: counter-clockwise, as
# here. On the module the 30-pin socket centre is 13.0 mm from the 34-pin one, on
# the 34-pin socket's 1..17 row side, centres in line, both turned the same way.


def _gb042_plug(n, body_len):
    k = n // 2
    a = (k - 1) * 0.4
    pads = (row(range(1, k + 1), -a / 2, -1.25, 0.4, 0, 0.23, 0.70)
            + row(range(k + 1, n + 1), a / 2, 1.25, -0.4, 0, 0.23, 0.70))
    return Footprint(
        f"B2B_LSM_GB042-{n}P-H10",
        f"LS Mtron GB042-{n}P-H10 0.4 mm board-to-board plug, {n} contacts, 1.0 mm stack, no hold-downs",
        pads, body=(body_len, 2.2),
        assumed=f"Contact numbering (1..{k} one row, {k + 1}..{n} back along the other, {n} opposite 1) is not in "
                "the LS Mtron catalogue; it is derived from a third-party working design and the ROCK64/ROCK 3A "
                "symbols, and there are no hold-down pads: check both on a sample before layout.")


GB042_34P = _gb042_plug(34, 8.3)
GB042_30P = _gb042_plug(30, 7.5)

FOOTPRINTS = [USB_C, HDMI_A, TF_01A, JACK_PJ320DB, FPC15, GB042_34P, GB042_30P]
