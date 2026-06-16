# Python-Desktop-Weather-Station-Monitor


A lightweight, asynchronous desktop GUI application built in Python using `tkinter`. This application acts as a dedicated monitoring station, fetching live indoor and outdoor environmental telemetry from a ThingSpeak channel, retrieving real-time wind vectors from the Open-Meteo API, and displaying a mathematically optimized 1-hour meteorological forecast.


Use with this tuning program:
https://github.com/zuzalite/Thingspeak_weather_tuner_Version1

---

## Features & Software Architecture

Unlike standard polling scripts, this application is designed for long-term, memory-stable desktop execution:

* **Automated Rolling Memory via `collections.deque`:** Replaces manual array shifting with hardware-optimized, C-level double-ended queues. Setting a strict `maxlen` ensures that older data points are automatically dropped in $O(1)$ time complexity when new data arrives.
* **Mathematical Off-by-One Correction:** Arrays are sized to exactly 61 and 11 slots. This ensures the index gap between the oldest (`[0]`) and newest (`[60]`) element spans precisely 60 minutes and 10 minutes respectively, making trends perfectly accurate.
* **Non-Blocking Asynchronous UI:** Utilizes `tkinter`'s internal event loop (`root.after()`) instead of thread-blocking `time.sleep()`. The UI remains fully responsive, smooth, and window-manager compliant while network threads execute.
* **Dynamic Multi-Threshold Trend Arrows:** The trend detection engine dynamically shifts its sensitivity depending on the data type—applying a strict $0.10\text{ hPa}$ filter for barometric trends and a $0.20\text{°C}$ filter for thermal shifts over a 10-minute horizon.

---

## Installation & Running

### Prerequisites
Python 3.x must be installed on your system. `tkinter` comes pre-installed with standard Python distributions on Windows and macOS.

### Dependencies
The project relies on the `requests` library to manage HTTP API transactions. Install it via terminal/command prompt:

```bash
pip install requests
