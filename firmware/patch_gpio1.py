Import("env")

import os

def patch_m5coreink(source, target, env):
    lib_dir = os.path.join(env["PROJECT_LIBDEPS_DIR"], env["PIOENV"], "M5Core-Ink", "src")
    cpp_file = os.path.join(lib_dir, "M5CoreInk.cpp")
    if not os.path.exists(cpp_file):
        return
    with open(cpp_file, "r") as f:
        content = f.read()
    bad_line = "    pinMode(1, OUTPUT);"
    if bad_line in content:
        content = content.replace(bad_line, "    // pinMode(1, OUTPUT); // PATCHED: GPIO 1 is UART TX")
        with open(cpp_file, "w") as f:
            f.write(content)
        print("PATCHED: M5CoreInk.cpp — removed pinMode(1, OUTPUT) that kills serial TX")

env.AddPreAction("buildprog", patch_m5coreink)
