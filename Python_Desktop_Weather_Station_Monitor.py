import tkinter as tk
import requests
from datetime import datetime
from collections import deque

# --- THINGSPEAK SETTINGS ---
CHANNEL_NUMBER = "xxxxxxx"
READ_API_KEY = "xxxxxxxxxxxx"

# --- GLOBAL VARIABLES ---
in_temp = 0.0
out_temp = 0.0
pressure = 0.0

# JAVÍTVA: Matematikailag pontos méretű gördülő sorok (deque) használata.
# A 61 elem biztosítja, hogy a 60. (legfrissebb) és a 0. (legrégebbi) index között pontosan 60 perc teljen el.
pressure_history = deque([0.0] * 61, maxlen=61)
pressure_ma = deque([0.0] * 61, maxlen=61)
temp_in_history = deque([0.0] * 11, maxlen=11)
temp_out_history = deque([0.0] * 11, maxlen=11)
MA_WINDOW = 3

current_wind_dir = "N"
is_barometric_crash = False
history_ready = False
is_summer = True
current_screen = 1

# --- FUNCTIONS ---

def update_season():
    global is_summer
    month = datetime.now().month
    is_summer = (3 <= month <= 9)

def fetch_wind_direction():
    global current_wind_dir
    try:
        url = "http://api.open-meteo.com/v1/forecast?latitude=47.4979&longitude=19.0402&current_weather=true"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            wind_deg = data["current_weather"]["winddirection"]
            
            if 337.5 <= wind_deg or wind_deg < 22.5:       current_wind_dir = "N"
            elif 22.5 <= wind_deg and wind_deg < 67.5:   current_wind_dir = "NE"
            elif 67.5 <= wind_deg and wind_deg < 112.5:  current_wind_dir = "E"
            elif 112.5 <= wind_deg and wind_deg < 157.5: current_wind_dir = "SE"
            elif 157.5 <= wind_deg and wind_deg < 202.5: current_wind_dir = "S"
            elif 202.5 <= wind_deg and wind_deg < 247.5: current_wind_dir = "SW"
            elif 247.5 <= wind_deg and wind_deg < 292.5: current_wind_dir = "W"
            else:                                        current_wind_dir = "NW"
            return "OK"
    except:
        pass
    return "NOK"

def fetch_latest_data():
    global in_temp, out_temp, pressure
    try:
        url_last = f"https://api.thingspeak.com/channels/{CHANNEL_NUMBER}/feeds/last.json?api_key={READ_API_KEY}"
        response = requests.get(url_last, timeout=5)
        
        has_any_data = False
        outdoor_found = False
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("field1") is not None and str(data["field1"]).lower() != "null":
                in_temp = float(str(data["field1"]).replace(',', '.'))
                has_any_data = True
                
            if data.get("field3") is not None and str(data["field3"]).lower() != "null":
                p = float(str(data["field3"]).replace(',', '.'))
                if 950.0 < p < 1050.0:
                    pressure = p
                    has_any_data = True
                    
            if data.get("field5") is not None and str(data["field5"]).lower() != "null":
                out_temp = float(str(data["field5"]).replace(',', '.'))
                outdoor_found = True
                has_any_data = True

        if not outdoor_found:
            url_field5 = f"https://api.thingspeak.com/channels/{CHANNEL_NUMBER}/fields/5/last.json?api_key={READ_API_KEY}"
            res_f5 = requests.get(url_field5, timeout=5)
            if res_f5.status_code == 200:
                data_f5 = res_f5.json()
                if data_f5.get("field5") is not None and str(data_f5["field5"]).lower() != "null":
                    out_temp = float(str(data_f5["field5"]).replace(',', '.'))
                    has_any_data = True

        if has_any_data:
            return "OK"
        else:
            return "NODATA"
            
    except Exception as e:
        print(f"Hiba részletei: {e}")
        return "CONN_ERR"

def update_local_history():
    global history_ready, is_barometric_crash
    
    # JAVÍTVA: A dequek automatikusan eldobják a régi elemet az append hatására
    temp_in_history.append(in_temp)
    temp_out_history.append(out_temp)
    pressure_history.append(pressure)

    # JAVÍTVA: Mozgóátlag számítása az utolsó 3 elemre a 61 elemű sorban (58, 59, 60. indexek)
    sum_p = 0.0
    count = 0
    for i in range(61 - MA_WINDOW, 61):
        if pressure_history[i] > 950.0:
            sum_p += pressure_history[i]
            count += 1
    
    ma_val = sum_p / count if count > 0 else pressure
    pressure_ma.append(ma_val)

    # JAVÍTVA: Barometric crash pontosan 5 perces ablakban (60. index vs 55. index)
    short_trend = pressure_ma[60] - pressure_ma[55]
    is_barometric_crash = (short_trend <= -0.7 and pressure_ma[55] > 950.0)

    # Inicializációs ellenőrzés
    valid = sum(1 for p in pressure_history if p > 950.0)
    if valid >= MA_WINDOW:
        history_ready = True

# JAVÍTVA: Bevezetve a változó küszöbérték (threshold), hogy külön lehessen választani a nyomás és hőmérséklet érzékenységét
def get_trend_char(current, past, threshold):
    if past == 0.0: return '-'
    delta = current - past
    if delta >= threshold: return '^'
    if delta <= -threshold: return 'v'
    return '-'

def get_forecast_text():
    # JAVÍTVA: Index igazítása 60-ra
    if not history_ready or pressure_ma[60] < 950.0: return "COLLECTING..."
    if is_barometric_crash: return "STORM WARNING"
    
    p = pressure_ma[60]
    # JAVÍTVA: Pontosan 1 órás időablak különbsége (60. index - 0. index)
    raw_trend = pressure_ma[60] - pressure_ma[0]
    wind_mod = 0
    
    if current_wind_dir in ["S", "SW", "SE"]: wind_mod = 2
    elif current_wind_dir in ["W", "E"]:      wind_mod = 1
    
    trend = raw_trend - (wind_mod * 0.4)
    seasonal_factor = -0.3 if is_summer else 0.3
    
    if trend <= -1.5 + seasonal_factor: return "STORMY RAIN" if p < 1005 else "RAIN/WEATHER"
    if trend <= -0.6: return "BAD WEATHER"
    if trend >= 1.2 + seasonal_factor: return "SUNNY/CLEAR"
    if trend >= 0.5: return "SLOW IMPROV."
    
    if p >= 1020: return "STABLE SUNNY"
    if p >= 1013: return "SUNNY/DRY" if is_summer else "CLOUDY/DRY"
    if p >= 1005: return "CLOUDY/STAB."
    return "LOW/CLOUDY"

# --- TIMERS & UI UPDATES ---

def network_update_loop():
    ts_status = fetch_latest_data()
    if ts_status == "OK":
        update_local_history()
    fetch_wind_direction()
    update_season()
    update_display()
    root.after(60000, network_update_loop)

def screen_switch_loop():
    global current_screen
    if current_screen == 1:
        current_screen = 2
        delay = 4000
    else:
        current_screen = 1
        delay = 7000
    update_display()
    root.after(delay, screen_switch_loop)

def update_display():
    if current_screen == 1:
        # JAVÍTVA: Pontos 10 perces delta a hőmérsékleteknél (10. index - 0. index) 0.20 °C küszöbbel
        trend_in = get_trend_char(in_temp, temp_in_history[0], 0.20)
        trend_out = get_trend_char(out_temp, temp_out_history[0], 0.20)
        
        # JAVÍTVA: Pontos 10 perces delta a légnyomásnál a simított adatokból (60. index - 50. index) 0.10 hPa küszöbbel
        trend_p = get_trend_char(pressure_ma[60], pressure_ma[50], 0.10)
        
        diff = in_temp - out_temp
        diff_sign = "+" if diff >= 0 else ""
        
        text = (
            f"Indoor:  {in_temp:.1f} C {trend_in}\n\n"
            f"Outdoor: {out_temp:.1f} C {trend_out}\n\n"
            f"Delta:   {diff_sign}{diff:.1f} C\n\n"
            f"Baro:    {pressure:.1f} hPa {trend_p}"
        )
    else:
        season_str = "ZAMB(SUMMER)" if is_summer else "ZAMB(WINTER)"
        text = (
            f"{season_str} | Wind: {current_wind_dir}\n"
            f"-------------------------------------\n\n"
            f"FORECAST:\n"
            f"{get_forecast_text()}"
        )
    lbl_display.config(text=text)

def boot_sequence():
    global temp_in_history, temp_out_history, pressure_history, pressure_ma
    update_season()
    
    lbl_display.config(text="--- SYSTEM START ---\n\n> Open-Meteo fetch...")
    root.update()
    om_status = fetch_wind_direction()
    
    lbl_display.config(text=f"--- SYSTEM START ---\n\nOpen-Meteo: {om_status}\n> ThingSpeak fetch...")
    root.update()
    ts_status = fetch_latest_data()
    
    if ts_status != "OK":
        lbl_display.config(text=f"--- SYSTEM START ---\n\nOpen-Meteo: {om_status}\nThingSpeak: {ts_status}\n\nHIBA: {ts_status}\nNem sikerült adatot fogadni.")
        return

    lbl_display.config(text=f"--- SYSTEM START ---\n\nOpen-Meteo: {om_status}\nThingSpeak: {ts_status}\n\n> All ready!")
    root.update()
    
    # JAVÍTVA: Sorok feltöltése és inicializálása az új méretekkel (11 és 61)
    temp_in_history = deque([in_temp] * 11, maxlen=11)
    temp_out_history = deque([out_temp] * 11, maxlen=11)
    pressure_history = deque([pressure] * 61, maxlen=61)
    pressure_ma = deque([pressure] * 61, maxlen=61)
            
    root.after(2000, start_loops)

def start_loops():
    update_display()
    root.after(60000, network_update_loop)
    root.after(7000, screen_switch_loop)

# --- GUI SETUP ---
root = tk.Tk()
root.title("Időjárás Állomás Monitor")
root.geometry("420x260")
root.configure(bg="black")
root.resizable(False, False)

lbl_display = tk.Label(
    root, 
    text="--- SYSTEM START ---\n\nSystem booting...", 
    font=("Consolas", 14, "bold"), 
    fg="cyan", 
    bg="black", 
    justify="left",
    anchor="nw",
    padx=25,
    pady=25
)
lbl_display.pack(fill="both", expand=True)

root.after(500, boot_sequence)
root.mainloop()