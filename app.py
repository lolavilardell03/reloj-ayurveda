import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🧘‍♂️", layout="wide")
st.title("Tu Reloj Ayurvédico Personal")

ubicacion = st.selectbox(
    "Selecciona tu ubicación:", 
    ["Palma (Islas Baleares)", "Alcoy (Alicante)"]
)

if "Palma" in ubicacion:
    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
else:
    loc = LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)

tz = pytz.timezone(loc.timezone)

def formato_hhmm(hora_decimal):
    hora_decimal = hora_decimal % 24
    h = int(hora_decimal)
    m = int(round((hora_decimal - h) * 60))
    if m == 60:
        h = (h + 1) % 24
        m = 0
    return f"{h:02d}:{m:02d}"

def get_solar_events(fecha_dia):
    s_today = sun(loc.observer, date=fecha_dia, tzinfo=pytz.UTC)
    ayer = fecha_dia - datetime.timedelta(days=1)
    s_yesterday = sun(loc.observer, date=ayer, tzinfo=pytz.UTC)
    manana = fecha_dia + datetime.timedelta(days=1)
    s_tomorrow = sun(loc.observer, date=manana, tzinfo=pytz.UTC)
    
    midnight_utc = datetime.datetime.combine(
        fecha_dia, 
        datetime.time.min
    ).replace(tzinfo=pytz.UTC)
    
    def hours_from_mid(dt_utc):
        return (dt_utc - midnight_utc).total_seconds() / 3600.0 + 1.0 
        
    A = hours_from_mid(s_today['sunrise'])
    P = hours_from_mid(s_today['sunset'])
    A_tom = hours_from_mid(s_tomorrow['sunrise'])
    P_yest = hours_from_mid(s_yesterday['sunset'])
    M = hours_from_mid(s_today['noon'])
    
    L_day = P - A
    L_night = A_tom - P
    L_night_yest = A - P_yest
    
    t1 = P_yest + 2*(L_night_yest/3.0)
    t2 = A
    t3 = A + L_day/3.0
    t4 = A + 2*(L_day/3.0)
    t5 = P
    t6 = P + L_night/3.0
    bm = A - 1.6
    
    dt_local = tz.localize(datetime.datetime.combine(fecha_dia, datetime.time(12,0)))
    offset_verano = 1.0 if dt_local.dst().total_seconds() > 0 else 0.0
    
    return (t1, t2, t3, t4, t5, t6, bm, M), offset_verano, P

c_pitta_n = 'rgba(210, 130, 210, 0.5)'  
c_vatta_n = 'rgba(150, 150, 255, 0.5)'  
c_kapha_d = 'rgba(220, 255, 170, 0.5)'  
c_pitta_d = 'rgba(255, 220, 170, 0.5)'  
c_vatta_d = 'rgba(170, 220, 255, 0.5)'  
c_kapha_n = 'rgba(170, 220, 170, 0.5)'  

tab_circulo, tab_grafo = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)"])

with tab_circulo:
    hoy = datetime.datetime.now(tz).date()
