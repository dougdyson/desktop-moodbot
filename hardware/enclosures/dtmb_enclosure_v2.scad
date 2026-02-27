include <BOSL2/std.scad>

// === DTMB Enclosure v2 ===
// Built directly around CoreInk reference dimensions
// Portrait: 40w x 56h x 16d (standing upright, screen facing you)

// --- CoreInk hardware (from reference) ---
hw_w = 40;     // width (X)
hw_h = 56;     // height (Z)
hw_d = 16;     // depth (Y)
hw_display_w = 27.6;
hw_display_h = 27.6;
hw_display_z = 36;    // display center from bottom of CoreInk
hw_usbc_w = 9;
hw_usbc_h = 3.5;
hw_dial_w = 10;
hw_dial_d = 4;
hw_side_btn_h = 6;
hw_side_btn_z = 28;   // from bottom of CoreInk

// --- Enclosure shell ---
wall = 2.0;
tol = 0.3;
corner_r = 6;

// --- Derived ---
enc_w = hw_w + 2*(wall + tol);
enc_h = hw_h + 2*(wall + tol);
enc_d = hw_d + 2*(wall + tol);

// --- Display cutout (slightly oversized for clearance) ---
disp_cut_w = hw_display_w + 1;
disp_cut_h = hw_display_h + 1;
disp_cut_z = wall + tol + hw_display_z;  // from bottom of enclosure

// --- Bezel ---
bezel_w = 1.5;
bezel_depth = 0.5;

// --- Feet ---
// Two stubby feet, like the concept image
// Each about 1/3 body width, flat bottom, rounded front
foot_w = enc_w * 0.3;
foot_d = enc_d * 0.7;
foot_h = 5;
foot_r = 2.5;
foot_gap = enc_w * 0.15;

// --- Branding ---
brand_text = "DTMB";
brand_size = 4.5;
brand_depth = 0.4;

// =====================
// FOOT
// =====================
module foot() {
    intersection() {
        // Rounded box, flat on bottom
        translate([0, 0, foot_h/2])
            cuboid([foot_w, foot_d, foot_h],
                   rounding=foot_r, edges=BOTTOM+LEFT+RIGHT+FRONT+BACK,
                   anchor=CENTER, $fn=24);
        // Trim to flat bottom
        translate([0, 0, foot_h])
            cube([foot_w + 1, foot_d + 1, foot_h*2], center=true);
    }
}

// =====================
// BODY SHELL
// =====================
module body_shell() {
    difference() {
        // Outer
        cuboid([enc_w, enc_d, enc_h],
               rounding=corner_r, edges="Z",
               anchor=BOTTOM);

        // Inner cavity (open from back, +Y)
        translate([0, wall, wall])
            cuboid([enc_w - 2*wall, enc_d, enc_h - wall],
                   rounding=max(corner_r - wall, 1), edges="Z",
                   anchor=BOTTOM);

        // Display window (front face = -Y)
        translate([0, -enc_d/2, disp_cut_z])
            cuboid([disp_cut_w, wall + 0.02, disp_cut_h],
                   anchor=CENTER);

        // Bezel recess
        translate([0, -enc_d/2 + wall/2, disp_cut_z])
            cuboid([disp_cut_w + 2*bezel_w, bezel_depth, disp_cut_h + 2*bezel_w],
                   rounding=1.5, edges="Y",
                   anchor=CENTER);

        // USB-C (bottom of front face)
        translate([0, -enc_d/2, wall + tol + hw_usbc_h/2])
            cuboid([hw_usbc_w + 2, wall*3, hw_usbc_h + 1],
                   rounding=1, edges="Y",
                   anchor=CENTER);

        // Top dial (top edge)
        translate([0, -enc_d/4, enc_h - wall/2])
            cuboid([hw_dial_w + 2, hw_dial_d + 2, wall + 0.02],
                   anchor=CENTER);

        // Side button (right, +X)
        translate([enc_w/2, -enc_d/4, wall + tol + hw_side_btn_z])
            cuboid([wall*3, hw_dial_d + 1, hw_side_btn_h + 1],
                   rounding=1, edges="X",
                   anchor=CENTER);

        // Back branding
        translate([0, enc_d/2 - 0.01, enc_h * 0.3])
            rotate([90, 0, 0])
                linear_extrude(brand_depth)
                    text(brand_text, size=brand_size, halign="center",
                         valign="center", font="Helvetica Neue:style=Light");
    }
}

// =====================
// BACK PLATE
// =====================
module back_plate() {
    bp_w = enc_w - 2*wall - 0.4;
    bp_h = enc_h - 2*wall - 0.4;
    difference() {
        cuboid([bp_w, wall, bp_h],
               rounding=max(corner_r - wall, 1), edges="Y",
               anchor=BOTTOM);
        for (i = [-1, 0, 1])
            translate([i * 10, 0, bp_h * 0.3])
                cuboid([6, wall + 0.02, 3],
                       rounding=1, edges="Y", anchor=CENTER);
    }
}

// =====================
// ASSEMBLY
// =====================

color("WhiteSmoke") {
    // Body on top of feet
    translate([0, 0, foot_h])
        body_shell();

    // Left foot
    translate([-(foot_gap/2 + foot_w/2), 0, 0])
        foot();
    // Right foot
    translate([(foot_gap/2 + foot_w/2), 0, 0])
        foot();
}

// Back plate (offset)
color("GhostWhite")
    translate([enc_w + 15, 0, 0])
        back_plate();

// Ghost CoreInk for reference
%translate([0, 0, foot_h + wall + tol + hw_h/2])
    cube([hw_w, hw_d, hw_h], center=true);
