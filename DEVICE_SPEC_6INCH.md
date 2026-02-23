# Joan 6" Device Specification

## Identity
| Field | Value |
|-------|-------|
| Device | Joan 6" (V Tablet 2) |
| UUID | 3E005700-1850-4B35-4338-362000000000 |
| GTIN | 3830065463079 |
| Hardware Name ID | 0x5 |
| Hardware Version | 2.4.0 |
| Firmware Version | 6.16.4144 |
| Bootloader Version | 6.16.4144 |
| FW CRC | 0x68738603 |
| Protocol Version | PV3 |

## Architecture (RTOS, not Linux)
- Same thin-client architecture as Joan 13" — bare-metal / RTOS firmware
- Filesystem: ~8 MB total (`PV2_FS_TOTAL_SIZE: 8388608`) — much larger than 13" (128 KB)
- Likely MCU: STM32 or similar ARM Cortex-M

## Display (E-Paper / EPD)
| Field | Value |
|-------|-------|
| Size | 6.0" |
| Resolution | 1024 × 758 |
| Display ID | 0x501100EA |
| EPD Controller | Epson |
| EPD Waveform | 6.0_R234_U1 |
| EPD IC | 6.0_p49000cd0502_NPM |
| EPD PMIC | MAX17135 |
| Temperature Sensor | HDC2080 (22°C at time of query) |
| Humidity Sensor | HDC2080 (64% at time of query) |
| Update Modes | UPD_FULL_AREA, UPD_PART_AREA |

## Touch Screen
| Field | Value |
|-------|-------|
| Type | EKTF2227 (capacitive) |
| Firmware Major | 18 |
| Firmware Minor | 243 |

## Frontlight
| Field | Value |
|-------|-------|
| Controller | MIC3289 |
| Available | Yes (PWM brightness control) |

## Connectivity
| Field | Value |
|-------|-------|
| Active | TI CC3100 WiFi (type 6) |
| WiFi SSID | heero |
| WiFi Security | WPA2 |
| BLE | Available (can be enabled/disabled) |

## Network Config
| Field | Value |
|-------|-------|
| IP Mode | DHCP (mode 1) |
| Server | 192.168.6.6:11113 (local VSS) |
| Heartbeat | 3 min |
| Encryption | Disabled (outbound) |

## Power
| Field | Value |
|-------|-------|
| Charger IC | BQ24023 (TI) |
| Battery Voltage | 3690 mV |
| Battery Current | 914 mA (charging) |
| Battery Level | 42% (at time of query) |

## USB Interface
| Field | Value |
|-------|-------|
| Micro-USB | FTDI FT232R USB UART (data — CLI) |
| FTDI Serial | AH079JUC |
| macOS device | /dev/cu.usbserial-AH079JUC |
| Baud rate | 115200 8N1 |

## Key Differences from Joan 13"

| Feature | Joan 13" | Joan 6" |
|---------|----------|---------|
| Resolution | 1600 × 1200 | 1024 × 758 |
| Aspect ratio | 4:3 (1.333) | ~4:3 (1.351) |
| Firmware | 4.10.2775 | 6.16.4144 |
| Hardware | Place & Play 13" v1.1 | V Tablet 2 v2.4 |
| Touch | None | EKTF2227 capacitive |
| Frontlight | No | Yes (MIC3289) |
| BLE | No | Yes |
| Humidity sensor | No (LM75 temp only) | Yes (HDC2080 temp + humidity) |
| Filesystem | 128 KB | 8 MB |
| VSS Rotation | 2 | 1 |

## CLI Commands (notable additions vs 13")
The 6" device (FW 6.16) has a significantly expanded CLI compared to the 13" (FW 4.10):
- `ble_*` — Bluetooth Low Energy management
- `frontlight_*` — frontlight brightness control
- `touch_*` — touch screen management
- `hmr` / `hms` — humidity/temperature sensor (HDC2080)
- `lsm303_*` — accelerometer/compass (LSM303)
- `app_sleep` / `app_wakeup` — deep sleep management
- `play_music` — built-in speaker/buzzer
