import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun
import traceback

# Envolvemos TODO en un bloque de seguridad para que nunca se quede en blanco
try:
    st.set_page_config(page_title="Reloj Ayurvédico", layout="wide")
    st.title("Tu Reloj Ayurvédico Personal")

    # --- 1. SELECTOR DE UBICACIÓN ---
    ubicacion = st.selectbox("Selecciona tu ubicación:", ["Palma (Islas Baleares)", "Alcoy (Alicante)"])

    if "Palma" in ubicacion:
        loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502)
    else:
        loc = LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)

    tz = pytz.timezone(loc.timezone)

    # --- FORMATO DE HORA (Con protección contra errores) ---
    def formato_hhmm(hora_decimal):
        hora_decimal = hora_decimal % 24 # Fuerza a que siempre sea un reloj de 24h
        h = int(hora_decimal)
        m = int(round((hora_decimal - h) * 60))
        if m == 60:
            h = (h + 1) % 24
            m = 0
        return f"{h:02d}:{m:02d}"

    # --- CÁLCULOS MATEMÁTICOS ---
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
        
        return (t1, t2, t3, t4, t5, t6, bm), offset_verano, P

    # --- COLORES EXACTOS DE GEOGEBRA ---
    c_pitta_n = 'rgba(220, 100, 220, 0.5)'  # Magenta suave
    c_vatta_n = 'rgba(100, 100, 255, 0.5)'  # Índigo / Azul
    c_kapha_d = 'rgba(180, 255, 150, 0.5)'  # Verde Lima
    c_pitta_d = 'rgba(255, 200, 150, 0.5)'  # Naranja Melocotón
    c_vatta_d = 'rgba(150, 200, 255, 0.5)'  # Azul Cielo
    c_kapha_n = 'rgba(180, 255, 150, 0.5)'  # Verde Lima (igual que mañana)

    tab_circulo, tab_grafo = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)"])

    # ---------------------------------------------------------
    # PESTAÑA 1: RELOJ CIRCULAR + TEXTO
    # ---------------------------------------------------------
    with tab_circulo:
        hoy = datetime.datetime.now(tz).date()
        (t1, t2, t3, t4, t5, t6, bm), offset, _ = get_solar_events(hoy)
        
        col_texto, col_circulo = st.columns([1, 2])
        
        with col_texto:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown(f"### Horario en {ubicacion.split(' ')[0]}")
            st.markdown(f"**Brahma Muhurta:** `{formato_hhmm(bm + offset)}`")
            st.markdown(f"**Amanecer (Kapha):** `{formato_hhmm(t2 + offset)}`")
            st.markdown(f"**Inicio Pitta:** `{formato_hhmm(t3 + offset)}`")
            st.markdown(f"**Inicio Vata:** `{formato_hhmm(t4 + offset)}`")
            st.markdown(f"**Atardecer (Kapha):** `{formato_hhmm(t5 + offset)}`")
            st.markdown(f"**Pitta Noche:** `{formato_hhmm(t6 + offset)}`")
            st.markdown(f"**Vata Noche:** `{formato_hhmm(t1 + offset)}`")

        with col_circulo:
            t6_limitado = min(24.0, t6)
            
            # max(0.001, ...) asegura que Plotly nunca reciba un número negativo y colapse
            duraciones = [
                max(0.001, t1), 
                max(0.001, t2 - t1), 
                max(0.001, t3 - t2), 
                max(0.001, t4 - t3), 
                max(0.001, t5 - t4), 
                max(0.001, t6_limitado - t5)
            ]
            nombres = ['Pitta Noche', 'Vata Noche', 'Kapha Mañana', 'Pitta Día', 'Vata Tarde', 'Kapha Noche']
            colores = [c_pitta_n, c_vatta_n, c_kapha_d, c_pitta_d, c_vatta_d, c_kapha_n]
            
            if t6 < 24.0:
                duraciones.append(max(0.001, 24.0 - t6))
                nombres.append('Pitta Noche')
                colores.append(c_pitta_n)

            fig_circulo = go.Figure(go.Pie(
                values=duraciones, labels=nombres,
                marker=dict(colors=colores, line=dict(width=0)), 
                hole=0.4, sort=False, direction='clockwise', rotation=270,
                textinfo='label', hovertemplate="<b>%{label}</b><br>Duración: %{value:.1f}h<extra></extra>"
            ))

            fig_circulo.update_layout(
                template="plotly_dark", height=500, showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
                annotations=[dict(text='24 H', x=0.5, y=0.5, font=dict(size=30), showarrow=False)]
            )
            st.plotly_chart(fig_circulo, use_container_width=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: GRÁFICO ANUAL
    # ---------------------------------------------------------
    def obtener_datos_anuales(ubicacion_nombre, año):
        dates = pd.date_range(start=f'{año}-03-20', end=f'{año+1}-03-19', freq='D')
        
        claves = ['t1', 't2', 't3', 't4', 't5', 't6', 'bm']
        v = {k: [] for k in claves}
        s = {k: [] for k in claves}
        
        dst_dates = []
        max_sunset, min_sunset = -1, 999
        date_max_sunset, date_min_sunset = None, None
        prev_offset = None

        for d in dates:
            (t1, t2, t3, t4, t5, t6, bm), offset, P_val = get_solar_events(d.date())
            
            if prev_offset is not None and offset != prev_offset:
                dst_dates.append(d.date())
            prev_offset = offset
            
            if P_val > max_sunset:
                max_sunset, date_max_sunset = P_val, d.date()
            if P_val < min_sunset:
                min_sunset, date_min_sunset = P_val, d.date()
            
            v['t1'].append(t1); v['t2'].append(t2); v['t3'].append(t3)
            v['t4'].append(t4); v['t5'].append(t5); v['t6'].append(min(24.0, t6)); v['bm'].append(bm)
            
            s['t1'].append(formato_hhmm(t1+offset)); s['t2'].append(formato_hhmm(t2+offset))
            s['t3'].append(formato_hhmm(t3+offset)); s['t4'].append(formato_hhmm(t4+offset))
            s['t5'].append(formato_hhmm(t5+offset)); s['t6'].append(formato_hhmm(t6+offset))
            s['bm'].append(formato_hhmm(bm+offset))
            
        return dates, v, s, dst_dates, date_max_sunset, date_min_sunset

    with tab_grafo:
        with st.spinner('Procesando ciclo anual...'):
            año_act = datetime.datetime.now().year
            dates, v, s, dst_dates, d_max, d_min = obtener_datos_anuales(ubicacion, año_act)
            x = [d.date() for d in dates]
            fig_grafo = go.Figure()

            def add_area(y_data, color, name):
                fig_grafo.add_trace(go.Scatter(
                    x=x, y=y_data, fill='tonexty', mode='lines', line=dict(width=0),
                    fillcolor=color, hoverinfo='skip', showlegend=False, name=name
                ))
                
            fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
            add_area(v['t1'], c_pitta_n, 'Pitta Noche')
            add_area(v['t2'], c_vatta_n, 'Vata Noche')
            add_area(v['t3'], c_kapha_d, 'Kapha Mañana')
            add_area(v['t4'], c_pitta_d, 'Pitta Día')
            add_area(v['t5'], c_vatta_d, 'Vata Tarde')
            add_area(v['t6'], c_kapha_n, 'Kapha Noche')
            add_area([24]*len(x), c_pitta_n, 'Pitta
