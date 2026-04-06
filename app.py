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

# --- FUNCIÓN DE FORMATEO DE HORA ---
# Convierte un decimal (ej. 8.5) en texto (08:30)
def formato_hhmm(hora_decimal):
    h = int(hora_decimal) % 24
    m = int(round((hora_decimal - int(hora_decimal)) * 60))
    if m == 60:
        h = (h + 1) % 24
        m = 0
    return f"{h:02d}:{m:02d}"

# --- FUNCIÓN MATEMÁTICA CENTRAL ---
def calcular_fases(fecha_dia):
    # Forzamos la medianoche exacta del día solicitado
    medianoche = datetime.datetime.combine(fecha_dia, datetime.time.min).replace(tzinfo=tz)
    
    s_today = sun(loc.observer, date=fecha_dia, tzinfo=tz)
    s_yesterday = sun(loc.observer, date=fecha_dia - datetime.timedelta(days=1), tzinfo=tz)
    s_tomorrow = sun(loc.observer, date=fecha_dia + datetime.timedelta(days=1), tzinfo=tz)

    A_today = s_today['sunrise']
    P_today = s_today['sunset']
    P_yesterday = s_yesterday['sunset']
    A_tomorrow = s_tomorrow['sunrise']

    # Función para sacar horas desde la medianoche de ESTE día
    def horas_desde_medianoche(dt):
        return (dt - medianoche).total_seconds() / 3600.0

    L_day_today = (P_today - A_today).total_seconds() / 3600.0
    L_night_today = (A_tomorrow - P_today).total_seconds() / 3600.0
    L_night_yesterday = (A_today - P_yesterday).total_seconds() / 3600.0

    L_d3 = L_day_today / 3
    L_n3_yesterday = L_night_yesterday / 3
    L_n3_today = L_night_today / 3

    t1 = horas_desde_medianoche(P_yesterday + datetime.timedelta(hours=2 * L_n3_yesterday))
    t2 = horas_desde_medianoche(A_today)
    t3 = horas_desde_medianoche(A_today + datetime.timedelta(hours=L_d3))
    t4 = horas_desde_medianoche(A_today + datetime.timedelta(hours=2 * L_d3))
    t5 = horas_desde_medianoche(P_today)
    t6 = horas_desde_medianoche(P_today + datetime.timedelta(hours=L_n3_today))
    
    bm = horas_desde_medianoche(A_today - datetime.timedelta(hours=1.6))
    
    return t1, t2, t3, t4, t5, t6, bm

# --- PESTAÑAS ---
tab_circulo, tab_grafo = st.tabs(["⭕ Reloj Circular (Hoy)", "📈 Ciclo Anual (Primavera)"])

# ---------------------------------------------------------
# PESTAÑA 1: RELOJ CIRCULAR DE HOY
# ---------------------------------------------------------
with tab_circulo:
    st.subheader(f"Tu reloj biológico para hoy en {ubicacion.split(' ')[0]}")
    
    hoy = datetime.datetime.now(tz).date()
    t1, t2, t3, t4, t5, t6, bm = calcular_fases(hoy)
    
    # Calculamos las rebanadas asegurándonos de que nunca sumen más de 24h
    t6_limitado = min(24.0, t6) # Si t6 pasa de medianoche, lo cortamos en 24 para el gráfico
    
    duraciones = [
        t1,              
        t2 - t1,         
        t3 - t2,         
        t4 - t3,         
        t5 - t4,         
        t6_limitado - t5 
    ]
    nombres = ['Pitta Madrugada', 'Vatta Noche', 'Kapha Mañana', 'Pitta Día', 'Vatta Tarde', 'Kapha Noche']
    colores = ['#A52A2A', '#4B0082', '#90EE90', '#FF4500', '#87CEFA', '#228B22']
    
    # Si t6 no sobrepasó la medianoche, añadimos el trozo final de Pitta Noche
    if t6 < 24.0:
        duraciones.append(24.0 - t6)
        nombres.append('Pitta Noche')
        colores.append('#A52A2A')

    fig_circulo = go.Figure(go.Pie(
        values=duraciones,
        labels=nombres,
        marker_colors=colores,
        hole=0.4,
        sort=False,
        direction='clockwise',
        rotation=270,
        textinfo='label',
        hovertemplate="<b>%{label}</b><br>Duración: %{value:.1f}h<extra></extra>"
    ))

    fig_circulo.update_layout(
        template="plotly_dark", height=600, showlegend=False,
        annotations=[dict(text='24 H', x=0.5, y=0.5, font_size=30, showarrow=False)]
    )
    
    st.plotly_chart(fig_circulo, use_container_width=True)

# ---------------------------------------------------------
# PESTAÑA 2: GRÁFICO ANUAL
# ---------------------------------------------------------
with tab_grafo:
    with st.spinner('Procesando ciclo anual sin solapamientos...'):
        año_actual = datetime.datetime.now().year
        dates = pd.date_range(start=f'{año_actual}-03-20', end=f'{año_actual+1}-03-19', freq='D')

        # Variables para los ejes Y matemáticos
        v_t1, v_t2, v_t3, v_t4, v_t5, v_t6, v_bm = [], [], [], [], [], [], []
        # Variables de texto para mostrar "HH:MM" al pasar el ratón
        s_t1, s_t2, s_t3, s_t4, s_t5, s_t6, s_bm = [], [], [], [], [], [], []

        for d in dates:
            t1, t2, t3, t4, t5, t6, bm = calcular_fases(d.date())
            
            # Guardamos los valores matemáticos (capeando t6 a 24 para que NO oscurezca el verano)
            v_t1.append(t1); v_t2.append(t2); v_t3.append(t3)
            v_t4.append(t4); v_t5.append(t5); v_t6.append(min(24.0, t6)); v_bm.append(bm)
            
            # Guardamos los textos limpios para el ratón (usando el t6 real, aunque sea > 24)
            s_t1.append(formato_hhmm(t1)); s_t2.append(formato_hhmm(t2))
            s_t3.append(formato_hhmm(t3)); s_t4.append(formato_hhmm(t4))
            s_t5.append(formato_hhmm(t5)); s_t6.append(formato_hhmm(t6))
            s_bm.append(formato_hhmm(bm))

        fig_grafo = go.Figure()
        x = [d.date() for d in dates]

        # Función para añadir áreas al gráfico con hover personalizado
        def add_area(y_data, text_data, name, color):
            fig_grafo.add_trace(go.Scatter(
                x=x, y=y_data, customdata=text_data, fill='tonexty', mode='lines',
                name=name, fillcolor=color, line=dict(width=0),
                hovertemplate="<b>" + name + "</b>: %{customdata}<extra></extra>"
            ))

        # Línea base invisible
        fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
        
        # Añadimos todas las capas
        add_area(v_t1, s_t1, 'Fin Pitta Madrugada', 'rgba(139, 0, 0, 0.4)')
        add_area(v_t2, s_t2, 'Amanecer (Inicio Kapha)', 'rgba(75, 0, 130, 0.4)')
        add_area(v_t3, s_t3, 'Inicio Pitta Día', 'rgba(144, 238, 144, 0.4)')
        add_area(v_t4, s_t4, 'Inicio Vatta Tarde', 'rgba(255, 69, 0, 0.4)')
        add_area(v_t5, s_t5, 'Atardecer (Inicio Kapha)', 'rgba(135, 206, 250, 0.4)')
        add_area(v_t6, s_t6, 'Inicio Pitta Noche', 'rgba(34, 139, 34, 0.4)')
        
        # El techo de 24h ahora es mudo (hoverinfo='skip') para que no te moleste con el "24h"
        fig_grafo.add_trace(go.Scatter(
            x=x, y=[24]*len(x), fill='tonexty', mode='lines', name='Pitta Noche',
            fillcolor='rgba(139, 0, 0, 0.4)', line=dict(width=0), hoverinfo='skip'
        ))
        
        # Brahma Muhurta (con hover limpio)
        fig_grafo.add_trace(go.Scatter(
            x=x, y=v_bm, customdata=s_bm, mode='lines', name='Brahma Time',
            line=dict(color='gold', width=2, dash='dash'), hovertemplate="<b>Brahma M.</b>: %{customdata}<extra></extra>"
        ))

        fig_grafo.update_layout(
            xaxis=dict(tickformat="%d %b", title='Ciclo Perpetuo'),
            yaxis_title='Hora Local',
            yaxis=dict(range=[0, 24], tickvals=list(range(0, 25)), gridcolor='rgba(128, 128, 128, 0.2)'),
            hovermode="x unified", template="plotly_dark", height=700, margin=dict(l=0, r=0, t=30, b=0)
        )

        st.plotly_chart(fig_grafo, use_container_width=True)
