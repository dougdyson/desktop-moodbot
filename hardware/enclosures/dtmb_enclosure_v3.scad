include <BOSL2/std.scad>

// === DTMB Enclosure v3 ===
// Built from official CoreInk diagram
// Portrait: 40w x 56h x 16d, standing upright, screen facing -Y
//
// CUTOUTS NEEDED:
//   Front:  display window, Button G5 access
//   Bottom: USB-C, Grove connector
//   Right:  3-direction switch, power button
//   Top:    EXT.HAT (optional), RST button (optional)

// --- CoreInk hardware dims ---
hw_w = 40;
hw_h = 56;
hw_d = 16;

// --- Display (front face, upper portion) ---
hw_disp_w = 27.6;
hw_disp_h = 27.6;
hw_disp_z = 38;     // center from bottom of CoreInk

// --- Button G5 (front face, below display) ---
hw_g5_w = 6;
hw_g5_h = 4;
hw_g5_z = 18;

// --- USB-C (bottom, offset left) ---
hw_usbc_w = 9;
hw_usbc_d = 3.5;
hw_usbc_x = -5;

// --- Grove (bottom, offset right) ---
hw_grove_w = 8;
hw_grove_d = 5;
hw_grove_x = 8;

// --- 3-Dir Switch (right side, upper) ---
hw_sw_h = 8;
hw_sw_d = 4;
hw_sw_z = 40;

// --- Power button (right side, lower) ---
hw_pwr_h = 5;
hw_pwr_d = 3;
hw_pwr_z = 25;

// --- Shell parameters ---
wall = 2.0;
tol = 0.3;
corner_r = 5;
edge_r = 3;       // rounding on ALL edges (iPod-style, no 90° anywhere)

// --- Derived enclosure dims ---
enc_w = hw_w + 2*(wall + tol);
enc_h = hw_h + 2*(wall + tol);
enc_d = hw_d + 2*(wall + tol);

// Z offset: bottom of CoreInk sits at wall+tol above enclosure bottom
ci_z0 = wall + tol;

// --- Display cutout (slightly oversized) ---
disp_cut_w = hw_disp_w + 1.0;
disp_cut_h = hw_disp_h + 1.0;
disp_cut_z = ci_z0 + hw_disp_z;    // center from enclosure bottom

// --- Bezel ---
bezel_extra = 1.5;
bezel_depth = 0.5;

// --- Feet: two simple flat pads ---
foot_w = enc_w * 0.28;
foot_d = enc_d * 0.85;
foot_h = 5;
foot_r = 2;
foot_gap = enc_w * 0.12;

// =====================
// SHELL
// =====================
module shell() {
    difference() {
        // Outer body — rounded on ALL edges, no 90° surfaces
        cuboid([enc_w, enc_d, enc_h],
               rounding=edge_r, edges="ALL",
               anchor=BOTTOM);

        // Inner cavity (open from back, +Y)
        translate([0, wall/2, wall])
            cuboid([enc_w - 2*wall, enc_d - wall, enc_h - wall],
                   rounding=max(corner_r - wall, 1), edges="Z",
                   anchor=BOTTOM);

        // === FRONT FACE (-Y) ===

        // Display window
        translate([0, -enc_d/2, disp_cut_z])
            cuboid([disp_cut_w, wall*2, disp_cut_h], anchor=CENTER);

        // Display bezel recess
        translate([0, -enc_d/2 + wall/2, disp_cut_z])
            cuboid([disp_cut_w + 2*bezel_extra, bezel_depth,
                    disp_cut_h + 2*bezel_extra],
                   rounding=2, edges="Y", anchor=CENTER);

        // Button G5 — no cutout, covered by enclosure (clean front face)

        // === BOTTOM (-Z) ===

        // USB-C
        translate([hw_usbc_x, 0, 0])
            cuboid([hw_usbc_w + 2, hw_usbc_d + 2, wall*2],
                   rounding=1, edges="Z", anchor=CENTER);

        // Grove connector
        translate([hw_grove_x, 0, 0])
            cuboid([hw_grove_w + 2, hw_grove_d + 2, wall*2],
                   rounding=1, edges="Z", anchor=CENTER);

        // === RIGHT SIDE (+X) ===

        // 3-Direction switch
        translate([enc_w/2, 0, ci_z0 + hw_sw_z])
            cuboid([wall*2, hw_sw_d + 2, hw_sw_h + 2],
                   rounding=1, edges="X", anchor=CENTER);

        // Power button
        translate([enc_w/2, 0, ci_z0 + hw_pwr_z])
            cuboid([wall*2, hw_pwr_d + 2, hw_pwr_h + 2],
                   rounding=1, edges="X", anchor=CENTER);

        // === TOP (+Z) — small RST access hole ===
        translate([6, 0, enc_h])
            cuboid([4, 4, wall*2], anchor=CENTER);
    }
}

// =====================
// BACK PLATE
// =====================
module back_plate() {
    bp_w = enc_w - 2*wall - 0.4;
    bp_h = enc_h - 2*wall - 0.4;

    difference() {
        cuboid([bp_w, wall * 0.8, bp_h],
               rounding=max(corner_r - wall, 1), edges="Y",
               anchor=BOTTOM);
        // Vent slots
        for (i = [-1, 0, 1])
            translate([i * 10, 0, bp_h * 0.35])
                cuboid([6, wall + 0.02, 2.5],
                       rounding=0.8, edges="Y", anchor=CENTER);
    }
}

// =====================
// FOOT
// =====================
module foot() {
    // Simple flat-bottom rounded pad
    cuboid([foot_w, foot_d, foot_h],
           rounding=foot_r,
           edges=BOTTOM+LEFT+RIGHT+FRONT+BACK,
           anchor=BOTTOM, $fn=20);
}

// =====================
// ASSEMBLY
// =====================

color("WhiteSmoke") {
    translate([0, 0, foot_h])
        shell();

    // Two feet
    for (sign = [-1, 1])
        translate([sign * (foot_gap/2 + foot_w/2), 0, 0])
            foot();
}

// Back plate (offset for viewing)
color("GhostWhite")
    translate([enc_w + 15, 0, 0])
        back_plate();

// Ghost CoreInk
%translate([0, 0, foot_h + ci_z0 + hw_h/2])
    cube([hw_w, hw_d, hw_h], center=true);

// =====================
// MOOD FACE on display
// =====================
// Sits just proud of the front face, on the display area
// Scale: display is 27.6mm, face lives within that

module mood_face() {
    screen_z = foot_h + disp_cut_z;
    screen_y = -enc_d/2 + 0.5;

    translate([0, screen_y, screen_z])
    rotate([90, 0, 0]) {
        // E-ink screen background (e-paper white)
        color("White")
            linear_extrude(0.5)
                square([disp_cut_w, disp_cut_h], center=true);

        // Eyes
        color("Black") {
            translate([-5, 3, 0.5])
                linear_extrude(0.3)
                    circle(r=1.8, $fn=20);
            translate([5, 3, 0.5])
                linear_extrude(0.3)
                    circle(r=1.8, $fn=20);
        }

        // Smile
        color("Black")
            translate([0, -4, 0.5])
                linear_extrude(0.3)
                    difference() {
                        circle(r=7, $fn=40);
                        circle(r=5.8, $fn=40);
                        translate([0, 3.5, 0])
                            square([16, 12], center=true);
                    }
    }
}

// mood_face();  // uncomment to show face on display
