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

# --- FUNCIÓN MATEMÁTICA CENTRAL ---
# Extraemos el cálculo a una función para usarla tanto en el círculo como en el gráfico
def calcular_fases(fecha_dia):
    s_today = sun(loc.observer, date=fecha_dia, tzinfo=tz)
    s_yesterday = sun(loc.observer, date=fecha_dia - datetime.timedelta(days=1), tzinfo=tz)
    s_tomorrow = sun(loc.observer, date=fecha_dia + datetime.timedelta(days=1), tzinfo=tz)

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

    t1 = to_decimal_hours(P_yesterday + datetime.timedelta(hours=2 * L_n3_yesterday))
    t2 = to_decimal_hours(A_today)
    t3 = to_decimal_hours(A_today + datetime.timedelta(hours=L_d3))
    t4 = to_decimal_hours(A_today + datetime.timedelta(hours=2 * L_d3))
    t5 = to_decimal_hours(P_today)
    t6 = to_decimal_hours(P_today + datetime.timedelta(hours=L_n3_today))
    
    # Brahma Muhurta (1.6h antes del amanecer)
    bm = to_decimal_hours(A_today - datetime.timedelta(hours=1.6))
    
    return t1, t2, t3, t4, t5, t6, bm

# --- CREAMOS LAS PESTAÑAS (TABS) ---
tab_circulo, tab_grafo = st.tabs(["⭕ Reloj Circular (Hoy)", "📈 Ciclo Anual (Primavera)"])

# ---------------------------------------------------------
# PESTAÑA 1: RELOJ CIRCULAR DE HOY
# ---------------------------------------------------------
with tab_circulo:
    st.subheader(f"Tu reloj biológico para hoy en {ubicacion.split(' ')[0]}")
    
    # Calculamos datos de hoy
    hoy = datetime.datetime.now(tz).date()
    t1, t2, t3, t4, t5, t6, bm = calcular_fases(hoy)
    
    # Calculamos la duración de cada fase para los "trozos" del pastel
    duraciones = [
        t1,              # 00:00 a Inicio Vatta N.
        t2 - t1,         # Vatta Noche
        t3 - t2,         # Kapha Mañana
        t4 - t3,         # Pitta Día
        t5 - t4,         # Vatta Tarde
        t6 - t5,         # Kapha Noche
        24.0 - t6        # Pitta Noche hasta 24:00
    ]
    
    nombres = ['Pitta Noche', 'Vatta Noche', 'Kapha Mañana', 'Pitta Día', 'Vatta Tarde', 'Kapha Noche', 'Pitta Noche ']
    # Colores base ligeramente más vivos para el círculo
    colores_circulo = ['#A52A2A', '#4B0082', '#90EE90', '#FF4500', '#87CEFA', '#228B22', '#A52A2A']

    # Dibujamos el gráfico de donut (Pie chart)
    fig_circulo = go.Figure(go.Pie(
        values=duraciones,
        labels=nombres,
        marker_colors=colores_circulo,
        hole=0.4, # Hace que sea un anillo
        sort=False, # Mantiene el orden cronológico
        direction='clockwise', # Gira como un reloj
        rotation=270, # Hace que las 00:00h queden abajo del todo
        textinfo='label',
        hoverinfo='label+value',
        hovertemplate="<b>%{label}</b><br>Duración: %{value:.1f}h<extra></extra>"
    ))

    fig_circulo.update_layout(
        template="plotly_dark",
        height=600,
        showlegend=False,
        annotations=[dict(text='24 H', x=0.5, y=0.5, font_size=30, showarrow=False)]
    )
    
    st.plotly_chart(fig_circulo, use_container_width=True)

# ---------------------------------------------------------
# PESTAÑA 2: GRÁFICO ANUAL (DE PRIMAVERA A PRIMAVERA)
# ---------------------------------------------------------
with tab_grafo:
    with st.spinner('Procesando ciclo anual...'):
        # Empezamos el 20 de Marzo (Equinoccio de Primavera)
        año_actual = datetime.datetime.now().year
        dates = pd.date_range(start=f'{año_actual}-03-20', end=f'{año_actual+1}-03-19', freq='D')

        v_t1, v_t2, v_t3, v_t4, v_t5, v_t6, v_bm = [], [], [], [], [], [], []

        for d in dates:
            t1, t2, t3, t4, t5, t6, bm = calcular_fases(d.date())
            v_t1.append(t1)
            v_t2.append(t2)
            v_t3.append(t3)
            v_t4.append(t4)
            v_t5.append(t5)
            v_t6.append(t6)
            v_bm.append(bm)

        fig_grafo = go.Figure()
        
        # Para evitar el bug de sombras en verano, usamos fechas "puras" sin zona horaria en el eje X
        x = [d.date() for d in dates]

        # Colores con opacidad fija para evitar el problema de superposición
        c_pitta_n = 'rgba(139, 0, 0, 0.4)'
        c_vatta_n = 'rgba(75, 0, 130, 0.4)'
        c_kapha_d = 'rgba(144, 238, 144, 0.4)'
        c_pitta_d = 'rgba(255, 69, 0, 0.4)'
        c_vatta_d = 'rgba(135, 206, 250, 0.4)'
        c_kapha_n = 'rgba(34, 139, 34, 0.4)'

        fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t1, fill='tonexty', mode='lines', name='Pitta Noche', fillcolor=c_pitta_n, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t2, fill='tonexty', mode='lines', name='Vatta N.', fillcolor=c_vatta_n, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t3, fill='tonexty', mode='lines', name='Kapha', fillcolor=c_kapha_d, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t4, fill='tonexty', mode='lines', name='Pitta', fillcolor=c_pitta_d, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t5, fill='tonexty', mode='lines', name='Vatta', fillcolor=c_vatta_d, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=v_t6, fill='tonexty', mode='lines', name='Kapha Noche', fillcolor=c_kapha_n, line=dict(width=0)))
        fig_grafo.add_trace(go.Scatter(x=x, y=[24]*len(x), fill='tonexty', mode='lines', name='Pitta Noche', fillcolor=c_pitta_n, line=dict(width=0)))
        
        fig_grafo.add_trace(go.Scatter(x=x, y=v_bm, mode='lines', name='Brahma Time', line=dict(color='gold', width=2, dash='dash')))

        tickvals = list(range(0, 25))
        ticktexts = [f"{h}h" for h in tickvals]

        fig_grafo.update_layout(
            xaxis=dict(
                tickformat="%d %b", # Formato: "20 Mar" (Oculta el año)
                title='Ciclo Perpetuo'
            ),
            yaxis_title='Hora Local',
            yaxis=dict(range=[0, 24], tickvals=tickvals, ticktext=ticktexts, gridcolor='rgba(128, 128, 128, 0.2)'),
            hovermode="x unified",
            template="plotly_dark",
            height=700,
            margin=dict(l=0, r=0, t=30, b=0)
        )

        st.plotly_chart(fig_grafo, use_container_width=True)
