// M5Stack CoreInk - Reference Model
// From official diagram: 56x40x16mm @ 32g
// Portrait orientation (standing upright, screen facing -Y)
//
// FRONT (-Y face): e-ink display (upper), Button G5 (below screen)
// BOTTOM (-Z):     USB-C (left of center), HY2.0-4P Grove (right of center)
// TOP (+Z):        EXT.HAT header, LED G10, System RST button
// RIGHT (+X):      3-Direction Switch, Power ON button
// BACK (+Y):       MI-BUS 2x8Pin header, built-in magnet

// --- Body ---
body_w = 40;    // X
body_h = 56;    // Z (tall axis)
body_d = 16;    // Y (thickness)

// --- E-ink display (front face, upper portion) ---
// 200x200 @ 1.54", active area 27.6 x 27.6mm
display_w = 27.6;
display_h = 27.6;
display_z = 38;   // center of display from bottom (upper portion)

// --- Button G5 (front face, below display) ---
btn_g5_w = 6;
btn_g5_h = 4;
btn_g5_z = 18;    // center from bottom

// --- USB-C (bottom edge, slightly left of center) ---
usbc_w = 9;
usbc_d = 3.5;
usbc_x = -5;      // offset left of center

// --- HY2.0-4P Grove (bottom edge, right of center) ---
grove_w = 8;
grove_d = 5;
grove_x = 8;      // offset right of center

// --- 3-Direction Switch (right side, upper) ---
switch_h = 8;
switch_d = 4;
switch_z = 40;    // center from bottom

// --- Power ON button (right side, lower) ---
pwr_h = 5;
pwr_d = 3;
pwr_z = 25;       // center from bottom

// --- EXT.HAT header (top edge) ---
hat_w = 20;
hat_d = 5;

// --- System RST (top edge, small) ---
rst_w = 3;
rst_d = 2;
rst_x = 12;       // offset from center

// --- Corner screw holes ---
screw_r = 2;
screw_inset = 3;

module coreink() {
    color("WhiteSmoke") {
        difference() {
            // Main body
            cube([body_w, body_d, body_h], center=true);

            // Corner screw holes (through Z)
            for (x = [-1, 1], z = [-1, 1])
                translate([x*(body_w/2 - screw_inset), 0,
                           z*(body_h/2 - screw_inset)])
                    rotate([90, 0, 0])
                        cylinder(r=screw_r, h=body_d+1, center=true, $fn=16);
        }
    }

    // E-ink display
    color("LightGray")
        translate([0, -body_d/2 + 0.5, display_z - body_h/2])
            cube([display_w, 1.1, display_h], center=true);

    // Button G5
    color("DarkGray")
        translate([0, -body_d/2 - 0.5, btn_g5_z - body_h/2])
            cube([btn_g5_w, 2, btn_g5_h], center=true);

    // USB-C
    color("Silver")
        translate([usbc_x, 0, -body_h/2 - 0.5])
            cube([usbc_w, usbc_d, 2], center=true);

    // HY2.0-4P Grove
    color("Yellow")
        translate([grove_x, 0, -body_h/2 - 0.5])
            cube([grove_w, grove_d, 2], center=true);

    // 3-Direction Switch (right side)
    color("DarkGray")
        translate([body_w/2 + 1, 0, switch_z - body_h/2])
            cube([3, switch_d, switch_h], center=true);

    // Power ON button (right side)
    color("Orange")
        translate([body_w/2 + 1, 0, pwr_z - body_h/2])
            cube([3, pwr_d, pwr_h], center=true);

    // EXT.HAT header (top)
    color("Gray")
        translate([0, 0, body_h/2 + 0.5])
            cube([hat_w, hat_d, 2], center=true);

    // RST button (top)
    color("Red")
        translate([rst_x, 0, body_h/2 + 0.5])
            cube([rst_w, rst_d, 1.5], center=true);
}

coreink();
