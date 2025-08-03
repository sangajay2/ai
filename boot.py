# boot.py - ESP32 WiFi Heart Rate Music System Boot File
# Upload this file to your ESP32 root directory

import time
import gc
import network

print("🔄 Boot.py starting...")
print("🔧 ESP32 WiFi Heart Rate Music System v2.0")
print("🌐 WiFi Communication Mode")

# Enable garbage collection for memory management
gc.enable()
gc.collect()

# Wait for system to stabilize
print("⏳ Initializing system...")
time.sleep(2)

# Show memory status
print(f"💾 Free memory: {gc.mem_free()} bytes")

# Initialize WiFi interface (but don't connect yet - main.py will handle that)
try:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("✅ WiFi interface initialized")
except Exception as e:
    print(f"❌ WiFi initialization error: {e}")

print("🚀 Ready to start main.py...")
print("=" * 50)

# Note: Don't execute main.py here for WiFi version
# Let the REPL or IDE handle it for better debugging