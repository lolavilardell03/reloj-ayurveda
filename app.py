import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🧘‍♂️", layout="wide")
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

# --- CÁLCULOS MATEMÁTICOS ---
def calcular_fases(fecha_dia):
    # Usamos try/except para evitar colapsos los días de cambio de hora (DST)
    try:
        medianoche = tz.localize(datetime.datetime.combine(fecha_dia, datetime.time.min), is_dst=False)
    except Exception:
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
    
    t_vn = horas_desde_medianoche(P_today + datetime.timedelta(hours=2 * L_n3_today))
    bm = horas_desde_medianoche(A_today - datetime.timedelta(hours=1.6))

    return t1, t2, t3, t4, t5, t6, t_vn, bm

# --- COLORES COMPARTIDOS ---
c_pitta_n = 'rgba(139, 0, 0, 0.6)'
c_vatta_n = 'rgba(75, 0, 130, 0.6)'
c_kapha_d = 'rgba(144, 238, 144, 0.6)'
c_pitta_d = 'rgba(255, 69, 0, 0.6)'
c_vatta_d = 'rgba(135, 206, 250, 0.6)'
c_kapha_n = 'rgba(34, 139, 34, 0.6)'

tab_circulo, tab_grafo = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)"])

# ---------------------------------------------------------
# PESTAÑA 1: RELOJ CIRCULAR + TEXTO
# ---------------------------------------------------------
with tab_circulo:
    hoy = datetime.datetime.now(tz).date()
    t1, t2, t3, t4, t5, t6, t_vn, bm = calcular_fases(hoy)
    
    col_texto, col_circulo = st.columns([1, 2])
    
    with col_texto:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"### Horario en {ubicacion.split(' ')[0]}")
        st.markdown(f"**Brahma Muhurta:** `{formato_hhmm(bm)}`")
        st.markdown(f"**Amanecer (Kapha):** `{formato_hhmm(t2)}`")
        st.markdown(f"**Inicio Pitta:** `{formato_hhmm(t3)}`")
        st.markdown(f"**Inicio Vata:** `{formato_hhmm(t4)}`")
        st.markdown(f"**Atardecer (Kapha):** `{formato_hhmm(t5)}`")
        st.markdown(f"**Pitta Noche:** `{formato_hhmm(t6)}`")
        st.markdown(f"**Vata Noche:** `{formato_hhmm(t_vn)}`")

    with col_circulo:
        t6_limitado = min(24.0, t6)
        
        duraciones = [t1, t2 - t1, t3 - t2, t4 - t3, t5 - t4, t6_limitado - t5]
        nombres = ['Pitta Noche', 'Vatta Noche', 'Kapha Mañana', 'Pitta Día', 'Vatta Tarde', 'Kapha Noche']
        colores = [c_pitta_n, c_vatta_n, c_kapha_d, c_pitta_d, c_vatta_d, c_kapha_n]
        
        if t6 < 24.0:
            duraciones.append(24.0 - t6)
            nombres.append('Pitta Noche')
            colores.append(c_pitta_n)

        fig_circulo = go.Figure(go.Pie(
            values=duraciones,
            labels=nombres,
            marker=dict(colors=colores, line=dict(width=0)), 
            hole=0.4,
            sort=False,
            direction='clockwise',
            rotation=270,
            textinfo='label',
            hovertemplate="<b>%{label}</b><br>Duración: %{value:.1f}h<extra></extra>"
        ))

        fig_circulo.update_layout(
            template="plotly_dark", height=500, showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0),
            annotations=[dict(text='24 H', x=0.5, y=0.5, font_size=30, showarrow=False)]
        )
        st.plotly_chart(fig_circulo, use_container_width=True)

# ---------------------------------------------------------
# PESTAÑA 2: GRÁFICO ANUAL (CON CACHÉ DE MEMORIA)
# ---------------------------------------------------------
# Esta función guarda los datos para que la pestaña no vuelva a colapsar
@st.cache_data
def obtener_datos_anuales(ubicacion_nombre, año):
    dates = pd.date_range(start=f'{año}-03-20', end=f'{año+1}-03-19', freq='D')
    
    v_t1, v_t2, v_t3, v_t4, v_t5, v_t6, v_bm = [], [], [], [], [], [], []
    s_t1, s_t2, s_t3, s_t4, s_t5, s_t6, s_bm = [], [], [], [], [], [], []

    for d in dates:
        t1, t2, t3, t4, t5, t6, t_vn, bm = calcular_fases(d.date())
        
        v_t1.append(t1); v_t2.append(t2); v_t3.append(t3)
        v_t4.append(t4); v_t5.append(t5); v_t6.append(min(24.0, t6)); v_bm.append(bm)
        
        s_t1.append(formato_hhmm(t1)); s_t2.append(formato_hhmm(t2))
        s_t3.append(formato_hhmm(t3)); s_t4.append(formato_hhmm(t4))
        s_t5.append(formato_hhmm(t5)); s_t6.append(formato_hhmm(t6))
        s_bm.append(formato_hhmm(bm))
        
    return dates, v_t1, v_t2, v_t3, v_t4, v_t5, v_t6, v_bm, s_t1, s_t2, s_t3, s_t4, s_t5, s_t6, s_bm

with tab_grafo:
    with st.spinner('Procesando ciclo anual...'):
        año_actual = datetime.datetime.now().year
        
        (dates, v_t1, v_t2, v_t3, v_t4, v_t5, v_t6, v_bm, 
         s_t1, s_t2, s_t3, s_t4, s_t5, s_t6, s_bm) = obtener_datos_anuales(ubicacion, año_actual)

        fig_grafo = go.Figure()
        x = [d.date() for d in dates]

        def add_area(y_data, text_data, name, color):
            fig_grafo.add_trace(go.Scatter(
                x=x, y=y_data, customdata=text_data, fill='tonexty', mode='lines',
                name=name, fillcolor=color, line=dict(width=0),
                hovertemplate="<b>" + name + "</b>: %{customdata}<extra></extra>"
            ))

        fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
        
        add_area(v_t1, s_t1, 'Fin Pitta Madrugada', c_pitta_n)
        add_area(v_t2, s_t2, 'Amanecer (Inicio Kapha)', c_vatta_n)
        add_area(v_t3, s_t3, 'Inicio Pitta Día', c_kapha_d)
        add_area(v_t4, s_t4, 'Inicio Vata Tarde', c_pitta_d)
        add_area(v_t5, s_t5, 'Atardecer (Inicio Kapha)', c_vatta_d)
        add_area(v_t6, s_t6, 'Inicio Pitta Noche', c_kapha_n)
        
        fig_grafo.add_trace(go.Scatter(
            x=x, y=[24]*len(x), fill='tonexty', mode='lines', name='Pitta Noche',
            fillcolor=c_pitta_n, line=dict(width=0), hoverinfo='skip'
        ))
        
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
