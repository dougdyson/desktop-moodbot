// M5Stack CoreInk - Reference Model
// Dimensions from official specs: 56 x 40 x 16mm
// Display: GDEW0154M09, active area 27.6 x 27.6mm, 200x200px

// Overall body
coreink_w = 56;   // width
coreink_h = 40;   // height (short axis)
coreink_d = 16;   // depth

// Display window (active area)
display_w = 27.6;
display_h = 27.6;
display_offset_y = 2;  // display is slightly above center

// USB-C port (bottom center)
usbc_w = 9;
usbc_h = 3.5;

// Side button (left side)
button_w = 3;
button_h = 6;
button_z = 8;  // height from bottom

module coreink_body() {
    color("DimGray")
    cube([coreink_w, coreink_h, coreink_d], center=true);
}

module coreink_display() {
    color("WhiteSmoke")
    translate([0, display_offset_y, coreink_d/2 - 0.5])
        cube([display_w, display_h, 1.1], center=true);
}

module coreink_usbc() {
    color("Silver")
    translate([0, -coreink_h/2, -coreink_d/2 + usbc_h/2 + 2])
        rotate([90, 0, 0])
            cube([usbc_w, usbc_h, 4], center=true);
}

module coreink_button() {
    color("DarkGray")
    translate([-coreink_w/2, 0, -coreink_d/2 + button_z])
        rotate([0, 90, 0])
            cylinder(d=button_h, h=button_w, center=true, $fn=20);
}

module coreink() {
    coreink_body();
    coreink_display();
    coreink_usbc();
    coreink_button();
}

coreink();
