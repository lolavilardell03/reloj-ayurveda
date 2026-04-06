import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Reloj Ayurvédico", layout="wide")
st.title("Tu Reloj Ayurvédico Personal")

# --- 1. SELECTOR DE UBICACIÓN ---
ubicacion = st.selectbox("Selecciona tu ubicación:", ["Palma (Islas Baleares)", "Alcoy (Alicante)"])

if "Palma" in ubicacion:
    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
else:
    loc = LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)

tz = pytz.timezone(loc.timezone)

# --- FORMATO DE HORA ---
def formato_hhmm(hora_decimal):
    h = int(hora_decimal)
    m = int(round((hora_decimal - h) * 60))
    if m == 60:
        h += 1
        m = 0
    h = h % 24
    return f"{h:02d}:{m:02d}"

# --- CÁLCULOS MATEMÁTICOS (SIN SALTOS VISUALES) ---
def get_solar_events(fecha_dia):
    s_today = sun(loc.observer, date=fecha_dia, tzinfo=pytz.UTC)
    s_yesterday = sun(loc.observer, date=fecha_dia - datetime.timedelta(days=1), tzinfo=pytz.UTC)
    s_tomorrow = sun(loc.observer, date=fecha_dia + datetime.timedelta(days=1), tzinfo=pytz.UTC)
    
    midnight_utc = datetime.datetime.combine(fecha_dia, datetime.time.min).replace(tzinfo=pytz.UTC)
    
    def hours_from_mid(dt_utc):
        return (dt_utc - midnight_utc).total_seconds() / 3600.0 + 1.0 
        
    A = hours_from_mid(s_today['sunrise'])
    P = hours_from_mid(s_today['sunset'])
    A_tom = hours_from_mid(s_tomorrow['sunrise'])
    P_yest = hours_from_mid(s_yesterday['sunset'])
    
    L_day = P - A
    L_night = A_tom
