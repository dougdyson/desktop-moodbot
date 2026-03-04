#include "M5CoreInk.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "config.h"

Ink_Sprite* sprite = nullptr;
Preferences prefs;

static const uint32_t POLL_INTERVAL_MS  = 30000;
static const uint32_t SLEEP_POLL_MS     = 300000;
static const uint32_t OFFLINE_TIMEOUT   = 300000;
static const int      BITMAP_SIZE       = 5000;
static const int      DISPLAY_W         = 200;
static const int      DISPLAY_H         = 200;

String wifi_ssid;
String wifi_pass;
String moodbot_host;
uint16_t moodbot_port;
String agent_name;

bool is_sleeping = false;
unsigned long last_success = 0;
bool showing_offline = false;
String last_display_key;

void loadConfig() {
    prefs.begin("moodbot", true);
    wifi_ssid   = prefs.getString("ssid", WIFI_SSID);
    wifi_pass   = prefs.getString("pass", WIFI_PASS);
    moodbot_host = prefs.getString("host", MOODBOT_HOST);
    moodbot_port = prefs.getUShort("port", MOODBOT_PORT);
    agent_name  = prefs.getString("agent", AGENT_NAME);
    prefs.end();
}

void saveConfig(const char* key, const String& value) {
    prefs.begin("moodbot", false);
    prefs.putString(key, value);
    prefs.end();
}

void printConfig() {
    Serial.println("=== MoodBot Config ===");
    Serial.printf("  ssid:  %s\n", wifi_ssid.c_str());
    Serial.printf("  pass:  %s\n", wifi_pass.length() > 0 ? "****" : "(empty)");
    Serial.printf("  host:  %s\n", moodbot_host.c_str());
    Serial.printf("  port:  %d\n", moodbot_port);
    Serial.printf("  agent: %s\n", agent_name.c_str());
    Serial.println("Commands: ssid:<val>  pass:<val>  host:<val>  port:<val>  agent:<val>  reboot");
    Serial.println("======================");
}

void clearScreen() {
    M5.M5Ink.clear();
}

void showText(const char* line1, const char* line2 = nullptr, const char* line3 = nullptr) {
    sprite->clear();
    sprite->drawString(20, 70, line1);
    if (line2) sprite->drawString(20, 95, line2);
    if (line3) sprite->drawString(20, 120, line3);
    sprite->pushSprite();
}

void connectWiFi() {
    showText("Connecting...", wifi_ssid.c_str());
    Serial.printf("Connecting to WiFi: %s\n", wifi_ssid.c_str());

    WiFi.mode(WIFI_STA);
    WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("Connected! IP: %s\n", WiFi.localIP().toString().c_str());
        char ip_buf[32];
        snprintf(ip_buf, sizeof(ip_buf), "IP: %s", WiFi.localIP().toString().c_str());
        showText("WiFi OK", ip_buf);
        delay(1500);
    } else {
        Serial.println("WiFi connection failed");
        showText("WiFi FAILED", "Check config", "via serial");
    }
}

static const uint8_t B64_LOOKUP[] = {
    64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,
    64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,
    64,64,64,64,64,64,64,64,64,64,64,62,64,64,64,63,
    52,53,54,55,56,57,58,59,60,61,64,64,64, 0,64,64,
    64, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
    15,16,17,18,19,20,21,22,23,24,25,64,64,64,64,64,
    64,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
    41,42,43,44,45,46,47,48,49,50,51,64,64,64,64,64
};

int base64Decode(const char* input, int len, uint8_t* output, int maxOut) {
    int out = 0;
    uint32_t accum = 0;
    int bits = 0;
    for (int i = 0; i < len && out < maxOut; i++) {
        uint8_t ch = (uint8_t)input[i];
        if (ch == '=' || ch == '\n' || ch == '\r') continue;
        if (ch > 127) continue;
        uint8_t val = B64_LOOKUP[ch];
        if (val == 64) continue;
        accum = (accum << 6) | val;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            output[out++] = (accum >> bits) & 0xFF;
        }
    }
    return out;
}

void renderBitmap(const char* b64, int b64Len) {
    uint8_t* bitmap = (uint8_t*)malloc(BITMAP_SIZE);
    if (!bitmap) {
        Serial.println("Failed to allocate bitmap buffer");
        return;
    }

    int decoded = base64Decode(b64, b64Len, bitmap, BITMAP_SIZE);
    if (decoded != BITMAP_SIZE) {
        Serial.printf("Bitmap decode error: got %d bytes, expected %d\n", decoded, BITMAP_SIZE);
        free(bitmap);
        return;
    }

    for (int i = 0; i < BITMAP_SIZE; i++) {
        bitmap[i] = ~bitmap[i];
    }

    sprite->drawFullBuff(bitmap, true);
    sprite->pushSprite();

    free(bitmap);
}

void showFallbackMood(const char* activity, const char* emotion, bool sleeping) {
    sprite->clear();
    if (sleeping) {
        sprite->drawString(60, 60, "Z z z");
        sprite->drawString(30, 100, "sleeping...");
    } else {
        sprite->drawString(20, 70, activity);
        sprite->drawString(20, 110, emotion);
    }
    sprite->pushSprite();
}

void showOffline() {
    if (!showing_offline) {
        showText("OFFLINE", "No server", "connection");
        showing_offline = true;
    }
}

bool pollMoodServer() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi disconnected, reconnecting...");
        WiFi.reconnect();
        delay(3000);
        if (WiFi.status() != WL_CONNECTED) return false;
    }

    HTTPClient http;
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/mood/%s",
             moodbot_host.c_str(), moodbot_port, agent_name.c_str());

    Serial.printf("Polling: %s\n", url);
    http.begin(url);
    http.setTimeout(10000);
    int code = http.GET();

    if (code != 200) {
        Serial.printf("HTTP error: %d\n", code);
        http.end();
        return false;
    }

    String body = http.getString();
    http.end();

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, body);
    if (err) {
        Serial.printf("JSON parse error: %s\n", err.c_str());
        return false;
    }

    const char* activity = doc["activity"] | "unknown";
    const char* emotion  = doc["emotion"]  | "neutral";
    int variant          = doc["variant"]  | 0;
    is_sleeping          = doc["sleeping"]  | false;
    const char* bitmap   = doc["bitmap"]   | (const char*)nullptr;

    char key_buf[64];
    snprintf(key_buf, sizeof(key_buf), "%s_%s_%d_%d", activity, emotion, variant, is_sleeping);
    String display_key(key_buf);

    Serial.printf("Mood: %s / %s (sleeping=%d, bitmap=%s)\n",
                  activity, emotion, is_sleeping,
                  bitmap ? "yes" : "no");

    if (display_key == last_display_key) {
        Serial.println("No change, skipping redraw");
        return true;
    }
    last_display_key = display_key;

    if (bitmap) {
        renderBitmap(bitmap, strlen(bitmap));
    } else {
        showFallbackMood(activity, emotion, is_sleeping);
    }

    showing_offline = false;
    return true;
}

void handleSerial() {
    while (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;

        if (line == "reboot") {
            Serial.println("Rebooting...");
            delay(100);
            ESP.restart();
        }

        int colon = line.indexOf(':');
        if (colon < 0) {
            Serial.println("Format: key:value (ssid, pass, host, port, agent) | reboot");
            continue;
        }

        String key = line.substring(0, colon);
        String val = line.substring(colon + 1);
        key.trim();
        val.trim();

        if (key == "ssid") {
            wifi_ssid = val;
            saveConfig("ssid", val);
            Serial.printf("SSID set to: %s (reboot to apply)\n", val.c_str());
        } else if (key == "pass") {
            wifi_pass = val;
            saveConfig("pass", val);
            Serial.println("Password updated (reboot to apply)");
        } else if (key == "host") {
            moodbot_host = val;
            saveConfig("host", val);
            Serial.printf("Host set to: %s\n", val.c_str());
        } else if (key == "port") {
            moodbot_port = val.toInt();
            prefs.begin("moodbot", false);
            prefs.putUShort("port", moodbot_port);
            prefs.end();
            Serial.printf("Port set to: %d\n", moodbot_port);
        } else if (key == "agent") {
            agent_name = val;
            saveConfig("agent", val);
            Serial.printf("Agent set to: %s\n", val.c_str());
        } else {
            Serial.printf("Unknown key: %s\n", key.c_str());
        }
    }
}

void setup() {
    M5.begin();
    delay(100);
    Serial.begin(115200);
    delay(100);

    Serial.println("\n=== Desktop MoodBot CoreInk ===");

    if (!M5.M5Ink.isInit()) {
        Serial.println("E-ink init failed!");
        while (true) delay(1000);
    }

    sprite = new Ink_Sprite(&M5.M5Ink);
    clearScreen();
    sprite->creatSprite(0, 0, DISPLAY_W, DISPLAY_H);

    loadConfig();
    printConfig();
    connectWiFi();

    last_success = millis();
}

void loop() {
    M5.update();
    handleSerial();

    static unsigned long last_poll = 0;
    unsigned long now = millis();
    uint32_t interval = is_sleeping ? SLEEP_POLL_MS : POLL_INTERVAL_MS;

    if (now - last_poll >= interval) {
        last_poll = now;
        if (pollMoodServer()) {
            last_success = now;
        } else if (now - last_success > OFFLINE_TIMEOUT) {
            showOffline();
        }
    }

    delay(100);
}
