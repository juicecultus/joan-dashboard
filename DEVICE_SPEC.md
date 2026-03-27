# Joan 13" Device Specification

## Identity
| Field | Value |
|-------|-------|
| Device | Joan 13" |
| UUID | 35005A00-0150-4D35-5232-312000000000 |
| GTIN | 3830065463086 |
| Hardware Name ID | 0x7 |
| Hardware Version | 1.1.1 |
| Firmware Version | 4.10.2775 |
| Bootloader Version | 6.11.4055 |
| CLI Version | 1.1 |
| FW CRC | 0x43FB3BB8 |
| Protocol Version | PV3 |

## Architecture (RTOS, not Linux)
- **NOT Linux** — this is a bare-metal / RTOS firmware
- RTOS tasks: `event_timer_task`, `Main_task`, `cli_USB`, `Connectivity_task`, `pv2`, `vp_debounce`, `ethernet`, `cc3100`, `pv2_tx`
- Filesystem: ~128KB total (`PV2_FS_TOTAL_SIZE: 130988`)
- Likely MCU: STM32 or similar ARM Cortex-M (TI ecosystem peripherals, Epson EPD, FreeRTOS-style tasks)

## Display (E-Paper / EPD)
| Field | Value |
|-------|-------|
| Resolution | 1600 × 1200 |
| Display ID | 0x97110099 |
| Display Type | 2534473881 |
| EPD Controller | Epson (I2C, register read/write via `err`/`erw`/`eir`/`eiw`) |
| EPD PMIC | MAX17135 |
| Temperature Sensor | LM75 (22°C at time of query) |
| Border | White (supported) |
| Update Modes | UPD_FULL_AREA, UPD_PART_AREA |
| Encoding | 0x4 |

## Connectivity
| Field | Value |
|-------|-------|
| Active | TI CC3100 WiFi (type 6) |
| Available | W5500 Ethernet (type 3), CC3100 (type 6), None (type 0) |
| CC3100 NWP | v2.11.0.1 |
| CC3100 MAC FW | 31.1.5.0.2 |
| CC3100 PHY | 1.0.3.37 |
| CC3100 ChipId | 67108864 |
| CC3100 ROM | 13107 |
| WiFi MAC | 34:03:de:1b:78:ef |
| WiFi MAC (cfg) | 00:00:00:00:00:00 |
| WiFi SSID | heero |
| WiFi Security | WPA2 |
| Ethernet MAC | 02:3B:C0:6C:05:60 |

## Network Config
| Field | Value |
|-------|-------|
| IP | 192.168.101.31 |
| Netmask | 255.255.255.0 |
| Gateway | 192.168.101.250 |
| DNS | 0.0.0.0 |
| Mode | 1 (DHCP) |
| Server | we3.gw.getjoan.com:11113 |
| Heartbeat | 3 min |
| Encryption | Enabled (outbound) |

## Power
| Field | Value |
|-------|-------|
| Charger IC | BQ24023 (TI) |
| Charge Mode | Fast charge |
| Battery Voltage | 4206 mV |
| Battery Current | 856 mA (charging) |
| Battery Level | 100% |
| Threshold OFF | 3500 mV |
| Threshold ON | 3400 mV |

## USB Interface
| Field | Value |
|-------|-------|
| Micro-USB | FTDI FT232R USB UART (data — CLI + TLV protocol) |
| USB-C | Power only (no data interface detected) |
| FTDI VID:PID | 0x0403:0x6001 |
| FTDI Serial | A507MY5N |
| macOS device | /dev/cu.usbserial-A507MY5N |
| Baud rate | 115200 8N1 (confirmed working) |

## TLV Protocol (Configurator ↔ Device)
Binary protocol used by "Joan configurator" app over UART.

### Frame format
```
[type:1 byte][flags:2 bytes][length:1 byte][data:N bytes]
```

### Known message types
| Type | Direction | Description | Example response (hex→ASCII) |
|------|-----------|-------------|------------------------------|
| 0x02 | read | Connectivity type | 06000000 → CC3100 |
| 0x0D | read | IP address | → "192.168.101.31" |
| 0x0E | read | Netmask | → "255.255.255.0" |
| 0x0F | read | Gateway | → "192.168.101.250" |
| 0x10 | read | DNS | → "0.0.0.0" |
| 0x11 | read | IP mode | 01000000 |
| 0x12 | read | Server URL | → "we3.gw.getjoan.com" |
| 0x13 | read | Server port | 692B → 11113 (LE uint16) |
| 0x33 | write | Unknown (flags=0x0001) | |
| 0x3C | read | Unknown | 0000000000000000 |
| 0x3D | read | Unknown | 0100000000000000 |
| 0x3E | read | Unknown | 0200000000000000 |
| 0x41 | read | WiFi SSID | → "heero" |
| 0x42 | read | WiFi security | → "wpa2" |
| 0x43 | read | WiFi PSK | → (password) |
| 0x45 | read | M2M server | → "m2m.tag.com" |
| 0x46 | read | M2M field1 | → "chap" |
| 0x47 | read | M2M field2 | → "tagm2m" |
| 0x48 | read | M2M field3 | → "m2m572" |
| 0x4A | read | Unknown | 00000000 |
| 0x4B | read | Unknown | → "test1234" |
| 0x4C | read | Unknown | → "test" |
| 0x50 | write | Set connectivity state (flags=0x0001) | |
| 0x51 | read | Connectivity state | 01000000=disconnected, 03000000=connected |
| 0x54 | read | Unknown | 48000000 |
| 0x56 | read | HW version string | → "7.1.1.1" |
| 0x57 | read | Firmware version | → "4.10.2775" |
| 0x58 | read | Bootloader version | → "6.11.4055" |
| 0x59 | read | UUID | → "35005A00-0150-..." |
| 0x6E | read | WiFi MAC | → "00:00:00:00:00:00" |
| 0x81 | read | Unknown | 01000000 |
| 0x90 | read | Unknown | 00005600 |

### Notes
- flags=0x0000 appears to be "read/get"
- flags=0x0001 appears to be "write/set"
- String responses are ASCII-encoded hex in the tclv_response

## CLI Commands (from `help`)
Full list of 80+ commands available — see help output in logs.

### Key commands for firmware work
- `reboot` — reboot device
- `fw_version_get` — show firmware version
- `fw_checksum_get` — show firmware CRC
- `cc3100_fw_upgrade` — upgrade CC3100 WiFi module firmware
- `cc3100_format` — format CC3100 SPI flash
- `flash_save` / `flash_load` — save/reload settings from flash
- `feat_enable <key>` / `feat_disable <key>` — enable/disable features
- `feat_get` — list feature flags (currently: touch=enabled, EAP=enabled)

### Missing (not in help)
- No `fw_upgrade` or `fw_update` for main MCU firmware
- No `bootloader` or `dfu` command
- No `flash_dump` or `flash_read` command

## Boot Sequence (captured via UART)

### Phase 1: Bootloader
```
UUID: 0x35 0x00 0x5a 0x00 ...
FW Version: 4.10.2775, Build date: 9 3 2019
FW Crc=0x43fb3bb8, Hash=0x7bab52f1, Length=365488
BL Version: 6.11.4055, Build date: 7 22 2023
HW: Thirteen v1.1, BOM: 1, APP: Bootloader
Starting bootloader!
CR: 0x03037283  (RCC register → confirms STM32 MCU)
CSR: 0x1e000003
```
- Bootloader has CLI prompt `bl>` but **zero registered commands** (`help` returns `rv: 0`)
- Connects to WiFi → server → sends status → receives ACK/NACK → boots app
- Firmware image: **365,488 bytes** (~357 KB)

### Phase 2: Application
```
HW: Thirteen v1.1, BOM: 1, APP: Joan
EPD: 13.3",1600x1200,WF=13.3_R153_AD,IC=13.3_p205rev0050
RCC: 0x03037283
```
- Epson EPD controller init: SDRAM check, waveform load (95,104 bytes)
- PSU: revision 1, product code 0x4F
- Display: 75Hz refresh, 4-bit encoding

## Bootloader Firmware Update Protocol (PV2/PV3)

### Flow
1. Bootloader connects to server via TCP (port 11113)
2. Encryption enabled (`--EN` flag) — **bootloader uses its own encryption, independent of app settings**
3. Sends 88-byte status packet (device UUID, FW version/CRC, HW info)
4. Server responds: **NACK** (16 bytes, no update) or **ACK** (firmware available)
5. If NACK → boots app. If ACK → downloads firmware in blocks

### 88-byte Bootloader Status Packet
```
Offset  Size  Field                    Value (this device)
0       1     Packet type              0x02
1-3     3     Protocol flags           0x00 0x00 0xF0
4-7     4     Reserved                 0x00000000
8-11    4     FW CRC (LE)              0x43FB3BB8
12-15   4     HW ID                    0xFFFFFFFF
16-19   4     Unknown                  0x00000A00
20-35   16    UUID                     35005A00-0150-4D35-5232-312000000000
36-39   4     FW major                 4
40-43   4     FW minor                 10
44-47   4     FW revision              2775
48-51   4     BL major                 6
52-55   4     BL minor                 11
56-59   4     BL revision              4055
60-63   4     HW name ID               7
64-67   4     HW version major         1
68-71   4     HW version minor         1
72-75   4     HW version revision      1
76-79   4     HW FW interface          0
80-83   4     Protocol version         3
84-87   4     Display ID               0x97110099
```

### NACK Response (captured via proxy to real server)
```
020000f0 01000000 00000000 00000000  (16 bytes)
```

### Encryption Discovery
- **The bootloader encrypts all PV2 responses** even when app-level encryption is disabled
- Boot log shows `W: TLS cfg defaults` — bootloader uses hardcoded/default crypto config
- Evidence: replaying exact NACK ciphertext from real server → "received NACK" ✓
- Modifying ANY byte (even trailing zeros) → "ack_nack header invalid" ✗
- This means the captured 16-byte NACK is **ciphertext**, not plaintext
- Encryption algorithm: likely AES-128 (per PV3 spec)

### TCLV Protocol (from Joan Configurator source)
Key TCLV IDs extracted from the Electron app:
| ID | Name | Description |
|----|------|-------------|
| 53 | CMD_FLASH_SAVE | Save parameters to flash |
| 80 | CONNECT | Force connection establish |
| 86 | HARDWARE_VER | HW version (read-only) |
| 87 | APPLICATION_VER | App version (read-only) |
| 88 | BOOTLOADER_VER | Bootloader version (read-only) |
| 89 | UUID | Device UUID (read-only) |
| 91 | REBOOT | **Reboot: arg 1=upgrade, 0=boot** |
| 92 | JUMP_TO_APP | Jump to app (bootloader command) |

## Thin-Client Architecture (KEY FINDING)

The Joan/Visionect Place & Play 13" is a **thin client display**, NOT a general-purpose
computing device. It does NOT run custom applications locally.

### How it works
1. Device connects to a **Visionect Software Suite (VSS)** server
2. VSS renders any web URL into an image using a headless WebKit renderer
3. Rendered image is pushed to the device over PV2/PV3 protocol
4. Device simply displays the image on its e-ink screen
5. Device periodically reconnects to get updated images (configurable interval)

### Correct approach for custom content
- **No firmware flashing needed** — the stock firmware is the correct one
- Run VSS locally (Docker) → point device at local server → serve any web page
- Device supports: 1600×1200, 16-level grayscale, 4:3 aspect ratio
- Refresh: 750ms full screen (4-bit) / 100ms partial (1-bit)

### Software stack (from weather-joan reference project)
- **Visionect Software Suite v3** — Docker image `visionect/visionect-server-v3` (x86) or `visionect/visionect-server-v3-armhf` (ARM)
- **PostgreSQL** — required by VSS
- **Joan Configurator** — desktop app to configure WiFi + server address (on-premises mode)
- **Web server** (nginx etc.) — serves the web page that VSS renders
- VSS management UI on port **8081**

### Product specs (from Visionect website)
- 13.3" E Ink Carta, 1600×1200, 150 PPI, 16 grayscale
- 2.4 GHz WiFi (802.11 b/g/n), WPA2-PSK, WPA2-EAP
- 10,000 mAh Li-Po battery (up to 12 months autonomy)
- Aluminum casing, 230×297×10.5mm, 950g
- VESA 100×100mm mount compatible

## Viable Custom Firmware Paths (for reference — not recommended)

### Path 1: Visionect Software Suite (Recommended)
- Install Docker → run `visionect/visionect-server-v3`
- Server handles PV2/PV3 encryption and firmware transfer natively
- Upload custom firmware binary through management web UI
- Point device at local server → reboot → bootloader downloads from our server
- **Pros**: Protocol-correct, no crypto reverse engineering needed
- **Cons**: Requires Docker, may need license, firmware binary format must match

### Path 2: Crack Bootloader Encryption
- Extract the AES-128 key from device flash (via TCLV or CLI)
- Determine cipher mode (ECB/CBC/CTR) and any IV/nonce
- Build a server that encrypts ACK responses with the correct key
- **Pros**: Full control, no external dependencies
- **Cons**: Complex, key extraction may be difficult

### Path 3: SWD/JTAG (Hardware)
- Open device case, locate STM32 SWD debug pads
- Use ST-Link or J-Link to read/write flash directly
- Bypass bootloader entirely — flash custom firmware to MCU
- Can also dump existing firmware for analysis
- **Pros**: Most flexible, bypasses all software protections
- **Cons**: Requires opening case, risk of damage, need debug probe

### Path 4: STM32 ROM Bootloader
- STM32 MCUs have a built-in ROM bootloader (UART/USB DFU)
- Activated by holding BOOT0 high during reset
- If BOOT0 pin is accessible, can flash via `stm32flash` tool over UART
- **Pros**: Uses standard STM32 tools, well-documented protocol
- **Cons**: Requires BOOT0 access (hardware mod)
