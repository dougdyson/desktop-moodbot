include <BOSL2/std.scad>

// === DTMB Enclosure v1 — "Apple White" Default Line ===
// Designed for M5Stack CoreInk (56 x 40 x 16mm)
// Style: Clean, minimal, Apple-inspired

// --- CoreInk dimensions ---
ci_w = 56;
ci_h = 40;
ci_d = 16;

// --- Display window ---
disp_w = 28.5;   // slightly larger than 27.6 active area
disp_h = 28.5;
disp_y_offset = 2;

// --- Enclosure parameters ---
wall = 2.0;       // wall thickness (good for Ender 3)
tol = 0.3;        // tolerance for fit
corner_r = 4;     // corner radius (Apple-esque)
lip = 1.5;        // lip height for top/bottom mating

// --- Derived dimensions ---
enc_w = ci_w + 2*wall + 2*tol;
enc_h = ci_h + 2*wall + 2*tol;
enc_d = ci_d + 2*wall + 2*tol;

// --- USB-C cutout ---
usbc_w = 10;
usbc_h = 4.5;

// --- Side button cutout ---
btn_w = 8;
btn_h = 5;
btn_z = 8;

// --- Split height (where top meets bottom) ---
split_z = enc_d * 0.6;  // 60% bottom, 40% top

// =====================
// BOTTOM SHELL
// =====================
module bottom_shell() {
    difference() {
        // Outer shell
        cuboid([enc_w, enc_h, split_z],
               rounding=corner_r,
               edges="Z",
               anchor=BOTTOM);

        // Inner cavity
        translate([0, 0, wall])
            cuboid([enc_w - 2*wall, enc_h - 2*wall, split_z],
                   rounding=corner_r - wall,
                   edges="Z",
                   anchor=BOTTOM);

        // USB-C port cutout (front/bottom edge)
        translate([0, -enc_h/2, wall + 2])
            cuboid([usbc_w, wall*3, usbc_h], anchor=CENTER);

        // Side button cutout (left side)
        translate([-enc_w/2, 0, wall + btn_z])
            cuboid([wall*3, btn_w, btn_h], anchor=CENTER);
    }

    // Mating lip (inner ridge for top to sit on)
    difference() {
        translate([0, 0, split_z - lip])
            cuboid([enc_w - wall, enc_h - wall, lip],
                   rounding=corner_r - wall/2,
                   edges="Z",
                   anchor=BOTTOM);
        translate([0, 0, split_z - lip - 0.01])
            cuboid([enc_w - 2*wall - tol, enc_h - 2*wall - tol, lip + 0.02],
                   rounding=corner_r - wall,
                   edges="Z",
                   anchor=BOTTOM);
    }
}

// =====================
// TOP SHELL (LID)
// =====================
module top_shell() {
    top_z = enc_d - split_z;

    difference() {
        // Outer shell
        cuboid([enc_w, enc_h, top_z],
               rounding=corner_r,
               edges="Z",
               anchor=BOTTOM);

        // Inner cavity
        translate([0, 0, -0.01])
            cuboid([enc_w - 2*wall, enc_h - 2*wall, top_z - wall + 0.01],
                   rounding=corner_r - wall,
                   edges="Z",
                   anchor=BOTTOM);

        // Display window cutout
        translate([0, disp_y_offset, top_z - wall - 0.01])
            cuboid([disp_w, disp_h, wall + 0.02], anchor=BOTTOM);
    }
}

// =====================
// ASSEMBLY VIEW
// =====================

// Show both parts side by side for printing orientation
// (or comment out one to export individually)

// Bottom shell
color("WhiteSmoke")
    bottom_shell();

// Top shell — shown offset for viewing (move next to bottom for print layout)
color("GhostWhite")
    translate([enc_w + 10, 0, 0])
        top_shell();

// Ghost CoreInk for reference (comment out before export)
%translate([0, 0, wall + tol])
    cube([ci_w, ci_h, ci_d], center=true);
