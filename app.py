import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun

# Configuramos la página en modo "ancho" para que el gráfico se vea espectacular
st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🧘‍♂️", layout="wide")
st.title("🕰️ Gráfico Ayurvédico Interactivo")

# --- 1. SELECTOR DE UBICACIÓN ---
# Esto crea el menú desplegable en tu web
ubicacion = st.selectbox("Selecciona tu ubicación:", ["Palma (Islas Baleares)", "Alcoy (Alicante)"])

if "Palma" in ubicacion:
    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
else:
    loc = LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)

tz = pytz.timezone(loc.timezone)

# --- 2. CALCULAR LOS DATOS DEL AÑO ---
# Ponemos un mensaje de carga mientras hace las matemáticas de los 365 días
with st.spinner(f'Calculando ciclos solares para {ubicacion}...'):
    year = 2026
    dates = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31', freq='D')

    t1_list, t2_list, t3_list, t4_list, t5_list, t6_list, bm_list = [], [], [], [], [], [], []

    for d in dates:
        s_today = sun(loc.observer, date=d.date(), tzinfo=tz)
        s_yesterday = sun(loc.observer, date=(d - datetime.timedelta(days=1)).date(), tzinfo=tz)
        s_tomorrow = sun(loc.observer, date=(d + datetime.timedelta(days=1)).date(), tzinfo=tz)

        A_today = s_today['sunrise']
        P_today = s_today['sunset']
        P_yesterday = s_yesterday['sunset']
        A_tomorrow = s_tomorrow['sunrise']

        def to_decimal_hours(dt):
            return dt.hour + dt.minute / 60 + dt.second / 3600

        L_day_today = (P_today.timestamp() - A_today.timestamp()) / 3600
        L_night_today = (A_tomorrow.timestamp() - P_today.timestamp()) / 3600
        L_night_yesterday = (A_today.timestamp() - P_yesterday.timestamp()) / 3600

        L_d3 = L_day_today / 3
        L_n3_yesterday = L_night_yesterday / 3
        L_n3_today = L_night_today / 3

        # Fases
        pitta_night_end = P_yesterday + datetime.timedelta(hours=2 * L_n3_yesterday)
        t1 = to_decimal_hours(pitta_night_end)
        t2 = to_decimal_hours(A_today)
        t3 = to_decimal_hours(A_today + datetime.timedelta(hours=L_d3))
        t4 = to_decimal_hours(A_today + datetime.timedelta(hours=2 * L_d3))
        t5 = to_decimal_hours(P_today)
        t6 = to_decimal_hours(P_today + datetime.timedelta(hours=L_n3_today))

        t1_list.append(t1)
        t2_list.append(t2)
        t3_list.append(t3)
        t4_list.append(t4)
        t5_list.append(t5)
        t6_list.append(t6)

        # Brahma Muhurta (Usando tu regla de A(x) - 1.6 horas)
        bm_dt = A_today - datetime.timedelta(hours=1.6)
        bm_list.append(to_decimal_hours(bm_dt))

    # --- 3. CONSTRUIR EL GRÁFICO ---
    fig = go.Figure()
    x = dates

    # Línea invisible en la base
    fig.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    
    # Apilamos las capas con tus colores y leyendas exactas
    fig.add_trace(go.Scatter(x=x, y=t1_list, fill='tonexty', mode='lines', name='Pitta Noche', fillcolor='rgba(139, 0, 0, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=t2_list, fill='tonexty', mode='lines', name='Vatta N.', fillcolor='rgba(75, 0, 130, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=t3_list, fill='tonexty', mode='lines', name='Kapha', fillcolor='rgba(144, 238, 144, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=t4_list, fill='tonexty', mode='lines', name='Pitta', fillcolor='rgba(255, 69, 0, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=t5_list, fill='tonexty', mode='lines', name='Vatta', fillcolor='rgba(135, 206, 250, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=t6_list, fill='tonexty', mode='lines', name='Kapha Noche', fillcolor='rgba(34, 139, 34, 0.4)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=x, y=[24]*len(x), fill='tonexty', mode='lines', name='Pitta Noche', fillcolor='rgba(139, 0, 0, 0.4)', line=dict(width=0)))
    
    # La línea dorada para Brahma Time
    fig.add_trace(go.Scatter(x=x, y=bm_list, mode='lines', name='Brahma Time', line=dict(color='gold', width=2, dash='dash')))

    # Formateo para que muestre de 0h a 24h
    tickvals = list(range(0, 25))
    ticktexts = [f"{h}h" for h in tickvals]

    fig.update_layout(
        xaxis_title='Fecha',
        yaxis_title='Hora Estándar Local',
        yaxis=dict(range=[0, 24], tickvals=tickvals, ticktext=ticktexts, gridcolor='rgba(128, 128, 128, 0.2)'),
        hovermode="x unified",
        template="plotly_dark",
        height=700,
        margin=dict(l=0, r=0, t=30, b=0) # Aprovecha al máximo el espacio de la pantalla
    )

    # Renderizar el gráfico en la web
    st.plotly_chart(fig, use_container_width=True)
