from machine import SoftI2C
import time

# MAX30102 Register Addresses
REG_INTR_STATUS_1 = 0x00
REG_INTR_STATUS_2 = 0x01
REG_INTR_ENABLE_1 = 0x02
REG_INTR_ENABLE_2 = 0x03
REG_FIFO_WR_PTR = 0x04
REG_OVF_COUNTER = 0x05
REG_FIFO_RD_PTR = 0x06
REG_FIFO_DATA = 0x07
REG_FIFO_CONFIG = 0x08
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A
REG_LED1_PA = 0x0C
REG_LED2_PA = 0x0D
REG_PILOT_PA = 0x10
REG_MULTI_LED_CTRL1 = 0x11
REG_MULTI_LED_CTRL2 = 0x12
REG_TEMP_INTR = 0x1F
REG_TEMP_FRAC = 0x20
REG_TEMP_CONFIG = 0x21
REG_PROX_INT_THRESH = 0x30
REG_REVISION_ID = 0xFE
REG_PART_ID = 0xFF

# Configuration constants
FIFO_DEPTH = 32

class MAX30102:
    def __init__(self, i2c, addr=0x57):
        self.i2c = i2c
        self.addr = addr
        self.red_led_current = 0x1F  # Default LED current
        self.ir_led_current = 0x1F
        
        # Verify device presence
        if not self._check_device():
            raise RuntimeError("MAX30102 not found!")
            
        self.reset()
        
    def _check_device(self):
        """Verify MAX30102 device is present"""
        try:
            part_id = self._read_reg(REG_PART_ID)
            return part_id == 0x15  # MAX30102 Part ID
        except:
            return False
        
    def reset(self):
        """Reset the device"""
        self._write_reg(REG_MODE_CONFIG, 0x40)  # Reset bit
        time.sleep_ms(100)
        
        # Wait for reset to complete
        timeout = 50
        while timeout > 0:
            if not (self._read_reg(REG_MODE_CONFIG) & 0x40):
                break
            time.sleep_ms(10)
            timeout -= 1
            
        if timeout <= 0:
            raise RuntimeError("Device reset timeout")
            
    def setup(self, led_mode=2, sample_rate=100, pulse_width=411, adc_range=4096):
        """
        Configure sensor for HR and SpO2 reading
        
        Args:
            led_mode: 1=Red only, 2=Red+IR, 3=Red+IR+Green
            sample_rate: 50, 100, 200, 400, 800, 1000, 1600, 3200 Hz
            pulse_width: 69, 118, 215, 411 μs
            adc_range: 2048, 4096, 8192, 16384 nA
        """
        
        # Clear any existing interrupts
        self._read_reg(REG_INTR_STATUS_1)
        self._read_reg(REG_INTR_STATUS_2)
        
        # FIFO Configuration
        # Bit 7:5 - Sample Averaging (000 = no averaging, 001 = 2, 010 = 4, 011 = 8, 100 = 16, 101 = 32)
        # Bit 4 - FIFO Rollover Enable (1 = allow rollover)
        # Bit 3:0 - FIFO Almost Full Value (0x0F = interrupt when 17 samples remain)
        fifo_config = (0x02 << 5) | (1 << 4) | 0x0F  # 4 sample averaging, rollover enabled
        self._write_reg(REG_FIFO_CONFIG, fifo_config)
        
        # Mode Configuration
        # Bit 6 - Reset (0 = normal operation)
        # Bit 3 - Shutdown (0 = normal operation) 
        # Bit 2:0 - Mode (001 = Heart Rate, 010 = SpO2, 011 = Multi-LED)
        mode_config = led_mode
        self._write_reg(REG_MODE_CONFIG, mode_config)
        
        # SpO2 Configuration
        spo2_config = self._encode_spo2_config(adc_range, sample_rate, pulse_width)
        self._write_reg(REG_SPO2_CONFIG, spo2_config)
        
        # LED Pulse Amplitude Configuration
        self._write_reg(REG_LED1_PA, self.red_led_current)  # Red LED
        self._write_reg(REG_LED2_PA, self.ir_led_current)   # IR LED
        
        # Multi-LED Mode Control (if using mode 3)
        if led_mode == 3:
            self._write_reg(REG_MULTI_LED_CTRL1, 0x21)  # Slot 1: Red, Slot 2: IR
            self._write_reg(REG_MULTI_LED_CTRL2, 0x00)  # Slot 3: None, Slot 4: None
            
        # Clear FIFO pointers
        self._write_reg(REG_FIFO_WR_PTR, 0x00)
        self._write_reg(REG_OVF_COUNTER, 0x00)
        self._write_reg(REG_FIFO_RD_PTR, 0x00)
        
        time.sleep_ms(100)  # Allow configuration to settle
        
    def _encode_spo2_config(self, adc_range, sample_rate, pulse_width):
        """Encode SpO2 configuration register"""
        # ADC Range encoding
        adc_range_map = {2048: 0, 4096: 1, 8192: 2, 16384: 3}
        adc_bits = adc_range_map.get(adc_range, 1) << 5
        
        # Sample Rate encoding  
        sample_rate_map = {50: 0, 100: 1, 200: 2, 400: 3, 800: 4, 1000: 5, 1600: 6, 3200: 7}
        sample_rate_bits = sample_rate_map.get(sample_rate, 1) << 2
        
        # Pulse Width encoding
        pulse_width_map = {69: 0, 118: 1, 215: 2, 411: 3}
        pulse_width_bits = pulse_width_map.get(pulse_width, 3)
        
        return adc_bits | sample_rate_bits | pulse_width_bits
        
    def set_led_current(self, red_current=None, ir_current=None):
        """Set LED current (0-255, where 255 = 51mA)"""
        if red_current is not None:
            self.red_led_current = min(255, max(0, red_current))
            self._write_reg(REG_LED1_PA, self.red_led_current)
            
        if ir_current is not None:
            self.ir_led_current = min(255, max(0, ir_current))
            self._write_reg(REG_LED2_PA, self.ir_led_current)
            
    def get_fifo_available(self):
        """Get number of available samples in FIFO"""
        wr_ptr = self._read_reg(REG_FIFO_WR_PTR) & 0x1F
        rd_ptr = self._read_reg(REG_FIFO_RD_PTR) & 0x1F
        
        if wr_ptr >= rd_ptr:
            return wr_ptr - rd_ptr
        else:
            return (FIFO_DEPTH - rd_ptr) + wr_ptr
            
    def read_sensor(self, max_samples=None):
        """
        Read sensor data from FIFO
        
        Returns:
            tuple: (red_data, ir_data) lists of samples
        """
        red_data = []
        ir_data = []
        
        # Get available samples
        available = self.get_fifo_available()
        
        if available == 0:
            return red_data, ir_data
            
        # Limit samples if requested
        if max_samples is not None:
            available = min(available, max_samples)
            
        # Read samples from FIFO
        for _ in range(available):
            try:
                # Each sample is 6 bytes (3 bytes per LED, 18-bit resolution)
                data = self.i2c.readfrom_mem(self.addr, REG_FIFO_DATA, 6)
                
                # Extract 18-bit values and mask unused bits
                red_value = ((data[0] << 16) | (data[1] << 8) | data[2]) & 0x3FFFF
                ir_value = ((data[3] << 16) | (data[4] << 8) | data[5]) & 0x3FFFF
                
                red_data.append(red_value)
                ir_data.append(ir_value)
                
            except Exception as e:
                print(f"FIFO read error: {e}")
                break
                
        return red_data, ir_data
        
    def read_temperature(self):
        """Read temperature from sensor"""
        # Enable temperature measurement
        self._write_reg(REG_TEMP_CONFIG, 0x01)
        
        # Wait for measurement to complete
        timeout = 100
        while timeout > 0:
            if not (self._read_reg(REG_TEMP_CONFIG) & 0x01):
                break
            time.sleep_ms(10)
            timeout -= 1
            
        if timeout <= 0:
            return None
            
        # Read temperature registers
        temp_int = self._read_reg(REG_TEMP_INTR)
        temp_frac = self._read_reg(REG_TEMP_FRAC)
        
        # Handle signed integer part
        if temp_int > 127:
            temp_int = temp_int - 256
            
        # Calculate final temperature
        temperature = temp_int + (temp_frac * 0.0625)
        return temperature
        
    def clear_fifo(self):
        """Clear FIFO buffer"""
        self._write_reg(REG_FIFO_WR_PTR, 0x00)
        self._write_reg(REG_OVF_COUNTER, 0x00)
        self._write_reg(REG_FIFO_RD_PTR, 0x00)
        
    def shutdown(self):
        """Put device in shutdown mode to save power"""
        mode_config = self._read_reg(REG_MODE_CONFIG)
        self._write_reg(REG_MODE_CONFIG, mode_config | 0x80)
        
    def wakeup(self):
        """Wake device from shutdown mode"""
        mode_config = self._read_reg(REG_MODE_CONFIG)
        self._write_reg(REG_MODE_CONFIG, mode_config & 0x7F)
        
    def get_part_id(self):
        """Get device part ID"""
        return self._read_reg(REG_PART_ID)
        
    def get_revision_id(self):
        """Get device revision ID"""
        return self._read_reg(REG_REVISION_ID)
        
    def _write_reg(self, reg_addr, data):
        """Write data to register"""
        try:
            self.i2c.writeto_mem(self.addr, reg_addr, bytes([data]))
        except Exception as e:
            raise RuntimeError(f"I2C write error: {e}")
            
    def _read_reg(self, reg_addr):
        """Read data from register"""
        try:
            return self.i2c.readfrom_mem(self.addr, reg_addr, 1)[0]
        except Exception as e:
            raise RuntimeError(f"I2C read error: {e}")
            
    def _read_multi_reg(self, reg_addr, length):
        """Read multiple registers"""
        try:
            return self.i2c.readfrom_mem(self.addr, reg_addr, length)
        except Exception as e:
            raise RuntimeError(f"I2C multi-read error: {e}")