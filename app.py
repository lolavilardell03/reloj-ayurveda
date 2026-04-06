import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🧘‍♂️", layout="wide")
st.title("🕰️ Tu Reloj Ayurvédico Personal")

# --- 1. SELECTOR DE UBICACIÓN ---
ubicacion = st.selectbox("📍 Selecciona tu ubicación:", ["Palma (Islas Baleares)", "Alcoy (Alicante)"])

if "Palma" in ubicacion:
    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
else:
    loc = LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)

tz = pytz.timezone(loc.timezone)

# --- FORMATO DE HORA ---
def formato_hhmm(hora_decimal):
    h = int(hora_decimal) % 24
    m = int(round((hora_decimal - int(hora_decimal)) * 60))
    if m == 60:
        h = (h + 1) % 24
        m = 0
    return f"{h:02d}:{m:02d}"

# --- CÁLCULOS MATEMÁTICOS ---
def calcular_fases(fecha_dia):
    # SOLUCIÓN AL BUG DE LA ZONA HORARIA: usar tz.localize en lugar de .replace()
    # Esto garantiza que el horario de verano (DST) se aplique perfectamente.
    medianoche = tz.localize(datetime.datetime.combine(fecha_dia, datetime.time.min))

    s_today = sun(loc.observer, date=fecha_dia, tzinfo=tz)
    s_yesterday = sun(loc.observer, date=fecha_dia - datetime.timedelta(days=1), tzinfo=tz)
    s_tomorrow = sun(loc.observer, date=fecha_dia + datetime.timedelta(days=1), tzinfo=tz)

    A_today = s_today['sunrise']
    P_today = s_today['sunset']
    P_yesterday = s_yesterday['sunset']
    A_tomorrow = s_tomorrow['sunrise']

    def horas_desde_medianoche(dt):
        return (dt - medianoche).total_seconds() / 3600.0

    L_day_today = (P_today - A_today).total_seconds() / 3600.0
    L_night_today = (A_tomorrow - P_today).total_seconds() / 3600.0
    L_night_yesterday = (A_today - P_yesterday).total_seconds() / 3600.0

    L_d3 = L_day_today / 3.0
    L_n3_yesterday = L_night_yesterday / 3.0
    L_n3_today = L_night_today / 3.0

    t1 = horas_desde_medianoche(P_yesterday + datetime.timedelta(hours=2 * L_n3_yesterday))
    t2 = horas_desde_medianoche(A_today)
    t3 = horas_desde_medianoche(A_today + datetime.timedelta(hours=L_d3))
    t4 = horas_desde_medianoche(A_today + datetime.timedelta(hours=2 * L_d3))
    t5 = horas_desde_medianoche(P_today)
    t6 = horas_desde_medianoche(P_today + datetime.timedelta(hours=L_n3_today))
    
    # Inicio de Vata Noche (para mostrar en el texto)
    t_vn = horas_desde_medianoche(P_today + datetime.timedelta(hours=2 * L_n3_today))
    
    bm = horas_desde_medianoche(A_today - datetime.timedelta(hours=1.6))

    return t1, t2, t3, t4, t5, t6, t_vn, bm

# COLORES COMPARTIDOS (Ahora son idénticos para gráfico y círculo)
# Usamos una opacidad de 0.6 para que se vean bien sólidos pero mantengan el estilo
c_pitta_n = '
