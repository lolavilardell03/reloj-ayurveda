import streamlit as st
import datetime
import pytz
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🧘‍♂️", layout="centered")
st.title("🕰️ Mi Reloj Ayurvédico")

# --- 1. CONFIGURACIÓN DE UBICACIÓN ---
# Le decimos a la app que estamos en Palma y usamos su zona horaria
loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
tz = pytz.timezone(loc.timezone)

# Obtenemos la fecha y hora exacta de AHORA
ahora = datetime.datetime.now(tz)
hoy = ahora.date()

# --- 2. CÁLCULO DEL SOL ---
# Calculamos el sol de hoy y de ayer (necesitamos ayer para saber cuándo empezó la noche pasada)
s_hoy = sun(loc.observer, date=hoy, tzinfo=tz)
s_ayer = sun(loc.observer, date=hoy - datetime.timedelta(days=1), tzinfo=tz)

A_hoy = s_hoy['sunrise']
P_hoy = s_hoy['sunset']
P_ayer = s_ayer['sunset']

# --- 3. CÁLCULO DE FASES (TERCIOS) ---
# Duración total en horas usando precisión de segundos
duracion_dia = (P_hoy - A_hoy).total_seconds() / 3600
duracion_noche_pasada = (A_hoy - P_ayer).total_seconds() / 3600

tercio_dia = duracion_dia / 3
tercio_noche = duracion_noche_pasada / 3

# --- 4. CÁLCULO DE LAS HORAS EXACTAS ---
# Usamos timedelta para sumar las horas al amanecer/atardecer de forma perfecta
inicio_pitta_dia = A_hoy + datetime.timedelta(hours=tercio_dia)
inicio_vata_dia = A_hoy + datetime.timedelta(hours=2 * tercio_dia)

# Para el Brahma Muhurta dinámico: buscamos el punto medio de Vata Noche
inicio_vata_noche = P_ayer + datetime.timedelta(hours=2 * tercio_noche)
mitad_vata_noche = (A_hoy - inicio_vata_noche).total_seconds() / 2
brahma_muhurta = inicio_vata_noche + datetime.timedelta(seconds=mitad_vata_noche)

# --- 5. INTERFAZ VISUAL (PROVISIONAL) ---
# Una función rápida para limpiar la hora y mostrar solo "HH:MM"
def formato_hora(dt):
    return dt.strftime("%H:%M")

st.write("✅ *Motor astronómico conectado. Datos de hoy para Palma:*")

st.subheader("☀️ Día (Desde el Amanecer)")
st.write(f"🟢 **Kapha Mañana:** {formato_hora(A_hoy)}")
st.write(f"🔴 **Pitta Día:** {formato_hora(inicio_pitta_dia)}")
st.write(f"🔵 **Vata Tarde:** {formato_hora(inicio_vata_dia)}")
st.write(f"🌅 **Puesta de Sol:** {formato_hora(P_hoy)}")

st.subheader("✨ Tu Despertar Ideal")
st.success(f"🧘‍♂️ **Brahma Muhurta:** {formato_hora(brahma_muhurta)}")
