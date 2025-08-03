# main.py for ESP32 - WiFi Heart Rate Music System with Enhanced Debugging
# Upload this to your ESP32 using Thonny or similar

from machine import Pin, SoftI2C
import json
import time
import network
import socket
import gc
try:
    from lib.max30102_corrected import MAX30102  # Try from lib folder first
except ImportError:
    try:
        from max30102_corrected import MAX30102  # Try from root folder
    except ImportError:
        print("❌ MAX30102 library not found!")
        print("🔧 Make sure max30102_corrected.py is uploaded to ESP32")
        print("📁 Check file location: /lib/max30102_corrected.py or /max30102_corrected.py")
        raise

# WiFi Configuration - VERIFY THESE ARE CORRECT!
WIFI_SSID = "corona_yahi_hai"        # Your WiFi name
WIFI_PASSWORD = "madRascals@300125"       # Your WiFi password
SERVER_IP = "192.168.1.7"                # Your PC's IP (from music server)
SERVER_PORT = 8888

# Enable more detailed debugging
DEBUG = True

print(f"🔧 WiFi SSID: {WIFI_SSID}")
print(f"🔧 Server: {SERVER_IP}:{SERVER_PORT}")

# I2C setup
scl_pin = 22  # GPIO22 for SCL
sda_pin = 21  # GPIO21 for SDA
i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))

# Music file paths (on your PC)
MUSIC_PATHS = {
    'calm': r"C:\Users\jaysa\OneDrive\Desktop\server\calm.mp3",
    'anxiety': r"C:\Users\jaysa\OneDrive\Desktop\server\anxiety.mp3", 
    'exercise': r"C:\Users\jaysa\OneDrive\Desktop\server\exercise.mp3"
}

class WiFiManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False
        
    def scan_networks(self):
        """Scan for available WiFi networks"""
        print("🔍 Scanning for WiFi networks...")
        try:
            self.wlan.active(True)
            networks = self.wlan.scan()
            print(f"📡 Found {len(networks)} networks:")
            target_found = False
            for net in networks:
                ssid = net[0].decode('utf-8')
                signal = net[3]
                print(f"   📶 {ssid} (Signal: {signal} dBm)")
                if ssid == WIFI_SSID:
                    target_found = True
                    print(f"   ✅ Target network '{WIFI_SSID}' found!")
            
            if not target_found:
                print(f"   ❌ Target network '{WIFI_SSID}' not found!")
                print("   🔧 Check SSID spelling or move closer to router")
            
            return target_found
        except Exception as e:
            print(f"❌ Network scan failed: {e}")
            return False
        
    def connect_wifi(self):
        print("🌐 Connecting to WiFi...")
        self.wlan.active(True)
        
        if self.wlan.isconnected():
            print(f"✅ Already connected to WiFi")
            config = self.wlan.ifconfig()
            print(f"📍 ESP32 IP: {config[0]}")
            print(f"🌐 Gateway: {config[2]}")
            self.connected = True
            return True
        
        # Scan for target network first
        if not self.scan_networks():
            return False
        
        print(f"🔗 Connecting to: {WIFI_SSID}")
        try:
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        except Exception as e:
            print(f"❌ Connection attempt failed: {e}")
            return False
        
        # Wait for connection with detailed status
        timeout = 30  # Increased timeout
        while not self.wlan.isconnected() and timeout > 0:
            status = self.wlan.status()
            status_msgs = {
                network.STAT_IDLE: "Idle",
                network.STAT_CONNECTING: "Connecting...",
                network.STAT_WRONG_PASSWORD: "Wrong password!",
                network.STAT_NO_AP_FOUND: "Network not found!",
                network.STAT_CONNECT_FAIL: "Connection failed!",
                network.STAT_GOT_IP: "Got IP address"
            }
            status_msg = status_msgs.get(status, f"Unknown status: {status}")
            print(f"⏳ {status_msg} ({timeout}s remaining)")
            
            if status in [network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL]:
                print(f"❌ Connection failed: {status_msg}")
                return False
            
            time.sleep(1)
            timeout -= 1
        
        if self.wlan.isconnected():
            config = self.wlan.ifconfig()
            print(f"✅ WiFi connected successfully!")
            print(f"📍 ESP32 IP: {config[0]}")
            print(f"🌐 Gateway: {config[2]}")
            print(f"🔗 DNS: {config[3]}")
            print(f"🎯 Will connect to server: {SERVER_IP}:{SERVER_PORT}")
            self.connected = True
            
            # Test basic connectivity
            try:
                import socket
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(3)
                test_socket.connect((config[2], 53))  # Try DNS port on gateway
                test_socket.close()
                print("✅ Network connectivity test passed")
            except:
                print("⚠️  Network connectivity test failed (but WiFi is connected)")
            
            return True
        else:
            print("❌ WiFi connection timeout!")
            print("🔧 Troubleshooting:")
            print("   📶 Check signal strength")
            print("   🔑 Verify password")
            print("   🌐 Check if network is 2.4GHz (ESP32 doesn't support 5GHz)")
            return False
    
    def is_connected(self):
        return self.wlan.isconnected()

def quick_wifi_test():
    """Quick test to check WiFi status"""
    print("\n📡 Quick WiFi Test:")
    wlan = network.WLAN(network.STA_IF)
    print("WiFi Active:", wlan.active())
    print("Connected:", wlan.isconnected())
    if wlan.isconnected():
        config = wlan.ifconfig()
        print("ESP32 IP:", config[0])
        print("Subnet Mask:", config[1])
        print("Gateway:", config[2])
        print("DNS:", config[3])
    return wlan.isconnected()

class WiFiMusicController:
    def __init__(self):
        self.current_zone = None
        self.music_start_time = 0
        self.is_playing = False
        self.socket = None
        self.server_connected = False
        
    def test_server_reachability(self):
        """Test if server is reachable"""
        try:
            print(f"🔍 Testing server reachability: {SERVER_IP}:{SERVER_PORT}")
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(5)
            test_socket.connect((SERVER_IP, SERVER_PORT))
            test_socket.close()
            print("✅ Server is reachable")
            return True
        except Exception as e:
            print(f"❌ Server not reachable: {e}")
            print("🔧 Make sure music_server_wifi.py is running on your PC")
            return False
        
    def connect_to_server(self):
        try:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            
            # First test if server is reachable
            if not self.test_server_reachability():
                return False
            
            print(f"🔌 Connecting to music server {SERVER_IP}:{SERVER_PORT}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)  # Increased timeout
            self.socket.connect((SERVER_IP, SERVER_PORT))
            self.server_connected = True
            print(f"✅ Connected to music server!")
            
            # Send a test command to verify connection
            test_data = {'command': 'status'}
            test_message = json.dumps(test_data) + '\n'
            self.socket.send(test_message.encode('utf-8'))
            
            # Wait for response
            self.socket.settimeout(3.0)
            response = self.socket.recv(1024).decode('utf-8').strip()
            if response:
                print("✅ Server communication test successful")
                return True
            else:
                print("❌ No response from server")
                return False
            
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            print("🔧 Troubleshooting:")
            print(f"   📍 Verify server IP: {SERVER_IP}")
            print(f"   🔌 Verify server port: {SERVER_PORT}")
            print("   💻 Make sure music_server_wifi.py is running")
            print("   🔥 Check Windows firewall settings")
            self.server_connected = False
            return False
    
    def send_command(self, command, music_path=None, heart_rate=0, zone='unknown'):
        # Try to reconnect if not connected
        if not self.server_connected:
            print(f"📡 Reconnecting to server for command: {command}")
            if not self.connect_to_server():
                return False
        
        try:
            data = {
                'command': command,
                'music_path': music_path,
                'heart_rate': heart_rate,
                'zone': zone
            }
            message = json.dumps(data) + '\n'
            
            print(f"📤 Sending: {command} (HR: {heart_rate}, Zone: {zone})")
            self.socket.send(message.encode('utf-8'))
            
            # Wait for response
            self.socket.settimeout(5.0)
            response = self.socket.recv(1024).decode('utf-8').strip()
            
            if response:
                response_data = json.loads(response)
                success = response_data.get('status') == 'OK'
                message_text = response_data.get('message', '')
                
                if success:
                    print(f"✅ Server response: {message_text}")
                else:
                    print(f"❌ Server error: {message_text}")
                return success
            
            print("❌ No response from server")
            return False
            
        except Exception as e:
            print(f"❌ Send command error: {e}")
            self.server_connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
    
    def determine_hr_zone(self, heart_rate):
        if heart_rate < 60:
            return 'calm'
        elif 60 <= heart_rate <= 100:
            return 'calm'
        elif heart_rate > 100:
            return 'exercise' if heart_rate > 120 else 'anxiety'
        return 'calm'
    
    def play_music_for_zone(self, zone, heart_rate):
        if zone not in MUSIC_PATHS:
            print(f"Unknown zone: {zone}")
            return False
        
        music_path = MUSIC_PATHS[zone]
        if self.is_playing:
            print("🔇 Stopping current music...")
            self.send_command('stop')
            time.sleep(0.5)
        
        success = self.send_command('play', music_path, heart_rate, zone)
        if success:
            self.current_zone = zone
            self.music_start_time = time.time()
            self.is_playing = True
            print(f"🎵 Playing {zone} music for HR: {heart_rate}")
            return True
        else:
            print(f"❌ Failed to start {zone} music")
            return False
    
    def should_change_music(self, new_zone, min_play_time=30):
        if not self.is_playing:
            return True
        play_duration = time.time() - self.music_start_time
        return new_zone != self.current_zone and play_duration >= min_play_time
    
    def stop_music(self):
        if self.is_playing:
            self.send_command('stop')
            self.is_playing = False
            self.current_zone = None

# Include the HeartRateCalculator and other utility functions from your original code
class HeartRateCalculator:
    def __init__(self, sample_rate=100):
        self.sample_rate = sample_rate
        self.buffer_size = 500  # 5 seconds of data
        self.ir_buffer = []
        self.last_peak_time = 0
        self.peak_intervals = []
        self.max_intervals = 10
        
    def add_sample(self, ir_value):
        """Add new IR sample to buffer"""
        self.ir_buffer.append(ir_value)
        if len(self.ir_buffer) > self.buffer_size:
            self.ir_buffer.pop(0)
    
    def apply_bandpass_filter(self, data):
        """Simple moving average filter to remove noise"""
        if len(data) < 5:
            return data
            
        filtered = []
        window = 5
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            filtered.append(sum(data[start:end]) / (end - start))
        return filtered
    
    def find_peaks(self, data, min_distance=50):
        """Find peaks in the signal with minimum distance constraint"""
        if len(data) < 100:
            return []
            
        # Apply simple filtering
        filtered_data = self.apply_bandpass_filter(data)
        
        # Calculate dynamic threshold
        mean_val = sum(filtered_data) / len(filtered_data)
        std_dev = (sum([(x - mean_val) ** 2 for x in filtered_data]) / len(filtered_data)) ** 0.5
        threshold = mean_val + 0.5 * std_dev
        
        peaks = []
        last_peak_idx = -min_distance
        
        for i in range(1, len(filtered_data) - 1):
            # Check if current point is a local maximum
            if (filtered_data[i] > filtered_data[i-1] and 
                filtered_data[i] > filtered_data[i+1] and 
                filtered_data[i] > threshold and
                i - last_peak_idx >= min_distance):
                
                peaks.append(i)
                last_peak_idx = i
                
        return peaks
    
    def calculate_heart_rate(self):
        """Calculate heart rate using improved peak detection"""
        if len(self.ir_buffer) < 200:  # Need at least 2 seconds of data
            return 0
            
        # Find peaks in the IR signal
        peaks = self.find_peaks(self.ir_buffer[-200:])  # Use last 2 seconds
        
        if len(peaks) < 2:
            return 0
            
        # Calculate intervals between peaks
        intervals = []
        for i in range(1, len(peaks)):
            interval = (peaks[i] - peaks[i-1]) / self.sample_rate  # Convert to seconds
            # Filter out unrealistic intervals (30-200 BPM range)
            if 0.3 <= interval <= 2.0:  # 30-200 BPM
                intervals.append(interval)
        
        if not intervals:
            return 0
            
        # Average the intervals and convert to BPM
        avg_interval = sum(intervals) / len(intervals)
        heart_rate = 60 / avg_interval
        
        # Additional filtering: maintain running average
        self.peak_intervals.append(heart_rate)
        if len(self.peak_intervals) > self.max_intervals:
            self.peak_intervals.pop(0)
            
        # Return smoothed heart rate
        return int(sum(self.peak_intervals) / len(self.peak_intervals))

def check_finger_present(ir_data):
    """Check if finger is present on sensor"""
    if not ir_data or len(ir_data) < 10:
        return False
    avg_ir = sum(ir_data) / len(ir_data)
    if avg_ir < 50000:
        return False
    mean_val = avg_ir
    variance = sum([(x - mean_val) ** 2 for x in ir_data]) / len(ir_data)
    std_dev = variance ** 0.5
    return std_dev > 1000

def calculate_spo2(red_data, ir_data):
    """Improved SpO2 calculation"""
    if not red_data or not ir_data or len(red_data) < 10:
        return 0
        
    # Calculate AC and DC components for both signals
    red_ac = max(red_data) - min(red_data)
    red_dc = sum(red_data) / len(red_data)
    ir_ac = max(ir_data) - min(ir_data)
    ir_dc = sum(ir_data) / len(ir_data)
    
    # Avoid division by zero
    if red_dc == 0 or ir_dc == 0 or ir_ac == 0:
        return 0
        
    # Calculate R ratio
    r_ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
    
    # Improved SpO2 calculation (still simplified)
    if r_ratio < 0.4:
        spo2 = 100
    elif r_ratio < 2.0:
        spo2 = 110 - 25 * r_ratio
    else:
        spo2 = 60
        
    return min(100, max(85, spo2))  # Clamp to realistic range

def get_zone_emoji_and_message(zone):
    """Get emoji and message for each zone"""
    zone_info = {
        'calm': ('😌', 'Normal/Relaxed state'),
        'anxiety': ('😰', 'Stress/Anxiety detected'),
        'exercise': ('💪', 'Exercise/High activity')
    }
    return zone_info.get(zone, ('❓', 'Unknown state'))

def main():
    """Main function to run the heart rate monitoring system"""
    print("🎵 Starting WiFi Heart Rate Music System...")
    print("=" * 70)
    
    # Show memory status
    gc.collect()
    print(f"💾 Free memory: {gc.mem_free()} bytes")
    
    # Initialize WiFi
    wifi = WiFiManager()
    if not wifi.connect_wifi():
        print("❌ Cannot continue without WiFi connection")
        print("🔧 Check WiFi credentials and network availability")
        return
    
    # Initialize sensor
    print("\n🔧 Initializing MAX30102 sensor...")
    try:
        sensor = MAX30102(i2c)
        sensor.setup()
        print("✅ MAX30102 sensor initialized")
        
        # Test sensor reading
        test_red, test_ir = sensor.read_sensor()
        print(f"✅ Sensor test - Red: {len(test_red)} samples, IR: {len(test_ir)} samples")
        
    except Exception as e:
        print(f"❌ MAX30102 initialization failed: {e}")
        print("🔧 Check I2C connections:")
        print("   SCL → GPIO22")
        print("   SDA → GPIO21") 
        print("   VCC → 3.3V")
        print("   GND → GND")
        print("🔧 Check if max30102_corrected.py is uploaded")
        return
    
    hr_calculator = HeartRateCalculator()
    music_controller = WiFiMusicController()
    
    stable_readings = 0
    last_zone_change = 0
    connection_retries = 0
    max_retries = 3
    
    # Connect to music server
    print(f"\n🌐 Connecting to music server at {SERVER_IP}:{SERVER_PORT}")
    while connection_retries < max_retries:
        if music_controller.connect_to_server():
            break
        connection_retries += 1
        if connection_retries < max_retries:
            print(f"🔄 Retry {connection_retries}/{max_retries} in 5 seconds...")
            time.sleep(5)
    
    if not music_controller.server_connected:
        print("❌ Could not connect to music server!")
        print("🔧 Troubleshooting checklist:")
        print(f"   📍 Server IP correct: {SERVER_IP}")
        print(f"   🔌 Server port correct: {SERVER_PORT}")
        print("   💻 Music server running on PC")
        print("   🌐 Both devices on same WiFi network")
        print("   🔥 Windows firewall allows connections")
        return
    
    print("\n✅ All systems ready!")
    print("📱 Place your finger on the MAX30102 sensor...")
    print("🎵 Music will automatically play based on heart rate zones")
    print("=" * 70)
    
    time.sleep(2)  # Warm up time
    
    # Main monitoring loop
    loop_count = 0
    while True:
        try:
            loop_count += 1
            
            # Periodic memory cleanup
            if loop_count % 100 == 0:
                gc.collect()
                print(f"💾 Memory cleanup - Free: {gc.mem_free()} bytes")
            
            # Check WiFi connection
            if not wifi.is_connected():
                print("❌ WiFi disconnected! Reconnecting...")
                if not wifi.connect_wifi():
                    time.sleep(5)
                    continue
                # Reconnect to server after WiFi reconnection
                music_controller.server_connected = False
            
            # Read sensor data
            red_data, ir_data = sensor.read_sensor()
            
            if red_data and ir_data:
                # Add samples to calculator
                for ir_val in ir_data:
                    hr_calculator.add_sample(ir_val)
                
                # Check if finger is present
                if not check_finger_present(ir_data):
                    if stable_readings > 0:  # Only show message if we had readings before
                        print("👆 No finger detected. Please place finger on sensor.")
                    stable_readings = 0
                    time.sleep(1)
                    continue
                
                # Calculate heart rate
                heart_rate = hr_calculator.calculate_heart_rate()
                
                # Calculate SpO2
                spo2 = calculate_spo2(red_data, ir_data)
                
                # Get temperature
                try:
                    temperature = sensor.read_temperature()
                except:
                    temperature = 0.0
                
                # Only process if we have reasonable HR values
                if 30 <= heart_rate <= 200:  # Realistic HR range
                    stable_readings += 1
                    
                    # Determine heart rate zone
                    current_zone = music_controller.determine_hr_zone(heart_rate)
                    emoji, message = get_zone_emoji_and_message(current_zone)
                    
                    # Display current status
                    status = "Stabilizing..." if stable_readings < 10 else "Stable"
                    print(f"❤️  HR: {heart_rate} BPM | 🩸 SpO2: {spo2:.1f}% | 🌡️  {temperature:.1f}°C")
                    print(f"{emoji} Zone: {current_zone.upper()} - {message}")
                    print(f"📊 Status: {status} (Reading #{stable_readings})")
                    
                    # Music control logic
                    if stable_readings >= 10:  # Only control music when stable
                        current_time = time.time()
                        
                        # Check if we should change music
                        if (not music_controller.is_playing or 
                            music_controller.should_change_music(current_zone)):
                            
                            # Prevent too frequent changes
                            if current_time - last_zone_change >= 30:  # 30 seconds minimum
                                print(f"🎵 Attempting to play {current_zone} music...")
                                if music_controller.play_music_for_zone(current_zone, heart_rate):
                                    last_zone_change = current_time
                        
                        # Show music status
                        if music_controller.is_playing:
                            play_time = int(current_time - music_controller.music_start_time)
                            print(f"🎵 Currently playing: {music_controller.current_zone} music ({play_time}s)")
                        
                else:
                    if stable_readings > 0:  # Only reset if we had stable readings
                        stable_readings = 0
                        print("📊 Calculating... please keep finger still")
                
                print("-" * 70)
                
            time.sleep(0.5)  # Sampling interval
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping music and monitoring...")
            music_controller.stop_music()
            break
            
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print(f"📊 Loop count: {loop_count}")
            time.sleep(1)

if __name__ == "__main__":
    print("=" * 70)
    print("🎵 WIFI HEART RATE MUSIC SYSTEM - ESP32")
    print("=" * 70)
    print("\n📋 CONFIGURATION:")
    print(f"🌐 WiFi SSID: {WIFI_SSID}")
    print(f"📍 Server IP: {SERVER_IP}:{SERVER_PORT}")
    print("\n🔌 Hardware connections:")
    print("   MAX30102 SCL → GPIO22")
    print("   MAX30102 SDA → GPIO21")
    print("   MAX30102 VCC → 3.3V")
    print("   MAX30102 GND → GND")
    print("=" * 70)
    
    try:
        main()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print("🔧 Check hardware connections and WiFi settings")
        print(f"💾 Free memory: {gc.mem_free()} bytes")