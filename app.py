import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun
from astral import moon
import traceback
import sqlite3

# --- 1. CONFIGURACIÓN DE BASE DE DATOS ---
def gestionar_db():
    conn = sqlite3.connect('datos_personales.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS notas (fecha TEXT PRIMARY KEY, texto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS regla (fecha TEXT PRIMARY KEY)')
    conn.commit()
    return conn, c

conn, cursor = gestionar_db()

# --- 2. CONFIGURACIÓN DE PÁGINA ---
try:
    st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🌺", layout="wide")
    st.title("Tu Reloj Ayurvédico Personal")

    ubicacion = st.selectbox(
        "Selecciona tu ubicación:", 
        ["Palma (Islas Baleares)", "Alcoy (Alicante)"]
    )

    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502) if "Palma" in ubicacion else LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)
    tz = pytz.timezone(loc.timezone)

    def formato_hhmm(hora_decimal):
        h = int(hora_decimal % 24)
        m = int(round((hora_decimal % 24 - h) * 60))
        if m == 60: h = (h + 1) % 24; m = 0
        return f"{h:02d}:{m:02d}"

    def get_solar_events(fecha_dia):
        s_today = sun(loc.observer, date=fecha_dia, tzinfo=pytz.UTC)
        s_tomorrow = sun(loc.observer, date=fecha_dia + datetime.timedelta(days=1), tzinfo=pytz.UTC)
        s_yesterday = sun(loc.observer, date=fecha_dia - datetime.timedelta(days=1), tzinfo=pytz.UTC)
        mid_utc = datetime.datetime.combine(fecha_dia, datetime.time.min).replace(tzinfo=pytz.UTC)
        
        def h_mid(dt): return (dt - mid_utc).total_seconds() / 3600.0 + 1.0
        
        A, P, M = h_mid(s_today['sunrise']), h_mid(s_today['sunset']), h_mid(s_today['noon'])
        A_tom, P_yest = h_mid(s_tomorrow['sunrise']), h_mid(s_yesterday['sunset'])
        L_day, L_night, L_night_yest = P - A, A_tom - P, A - P_yest
        
        t1, t2, t3 = P_yest + 2*(L_night_yest/3.0), A, A + L_day/3.0
        t4, t5, t6 = A + 2*(L_day/3.0), P, P + L_night/3.0
        bm = A - 1.6
        
        offset = 1.0 if tz.localize(datetime.datetime.combine(fecha_dia, datetime.time(12,0))).dst().total_seconds() > 0 else 0.0
        return (t1, t2, t3, t4, t5, t6, bm, M), offset

    c_pitta_n, c_vatta_n, c_kapha_d = 'rgba(210, 130, 210, 0.5)', 'rgba(150, 150, 255, 0.5)', 'rgba(220, 255, 170, 0.5)'
    c_pitta_d, c_vatta_d, c_kapha_n = 'rgba(255, 220, 170, 0.5)', 'rgba(170, 220, 255, 0.5)', 'rgba(170, 220, 170, 0.5)'

    tab_circulo, tab_grafo, tab_lunar = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)", "🌙 Ciclo Lunar"])

    # --- PESTAÑA 1: RELOJ DIARIO ---
    with tab_circulo:
        hoy = datetime.date.today()
        (t1, t2, t3, t4, t5, t6, bm, M), offset = get_solar_events(hoy)
        col_t, col_c = st.columns([1, 2])
        with col_t:
            st.markdown(f"### {ubicacion.split(' ')[0]}")
            st.markdown(f"**Brahma Muhurta:** `{formato_hhmm(bm+offset)}`  \n**Amanecer:** `{formato_hhmm(t2+offset)}`  \n**Inicio Pitta:** `{formato_hhmm(t3+offset)}`  \n**Cénit Solar:** `{formato_hhmm(M+offset)}`  \n**Inicio Vata:** `{formato_hhmm(t4+offset)}`  \n**Atardecer:** `{formato_hhmm(t5+offset)}`  \n**Pitta Noche:** `{formato_hhmm(t6+offset)}`  \n**Vata Noche:** `{formato_hhmm(t1+offset)}` ")
        with col_c:
            fig = go.Figure(go.Pie(values=[max(0.1, t1), t2-t1, t3-t2, t4-t3, t5-t4, min(24.0, t6)-t5], labels=['Pitta Noche', 'Vata Noche', 'Kapha Mañana', 'Pitta Día', 'Vata Tarde', 'Kapha Noche'], marker=dict(colors=[c_pitta_n, c_vatta_n, c_kapha_d, c_pitta_d, c_vatta_d, c_kapha_n]), hole=0.4, sort=False, direction='clockwise', rotation=270, textinfo='label'))
            fig.update_layout(template="plotly_dark", height=500, showlegend=False, annotations=[dict(text='🦀', x=0.5, y=0.5, font=dict(size=35), showarrow=False)])
            st.plotly_chart(fig, use_container_width=True)

    # --- FUNCIÓN DATOS ANUALES (CON 8 MARCADORES) ---
    def obtener_datos_anuales(año_inf):
        dates = pd.date_range(start=f'{año_inf}-01-01', end=f'{año_inf}-12-31', freq='D')
        v, s = {k: [] for k in ['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']}, {k: [] for k in ['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']}
        dst_dates, puntos_8 = [], []
        prev_off = None
        m_set, m_rise, m_val = (-1, 999, None, None), (-1, 999, None, None), (-1, 999)

        for d in dates:
            ev, off = get_solar_events(d.date())
            if prev_off is not None and off != prev_off: dst_dates.append(d.date())
            prev_off = off
            
            h_rise, h_set = ev[1] + off, ev[4] + off
            if h_set > m_set[0]: m_set = (h_set, m_set[1], d.date(), m_set[3])
            if h_set < m_set[1]: m_set = (m_set[0], h_set, m_set[2], d.date())
            if h_rise > m_rise[0]: m_rise = (h_rise, m_rise[1], d.date(), m_rise[3])
            if h_rise < m_rise[1]: m_rise = (m_rise[0], h_rise, m_rise[2], d.date())
            
            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']):
                v[k].append(min(24.0, ev[i]) if k == 't6' else ev[i])
                s[k].append(formato_hhmm(ev[i] + off))

        promedio_m = sum(v['M']) / len(v['M'])
        for i in range(1, len(v['M']) - 1):
            prev, curr, post = v['M'][i-1], v['M'][i], v['M'][i+1]
            if (curr > prev and curr > post) or (curr < prev and curr < post): puntos_8.append(dates[i].date())
            elif (prev < promedio_m < curr) or (prev > promedio_m > curr):
                if len(puntos_8) < 8: puntos_8.append(dates[i].date())
        
        return dates, v, s, dst_dates, m_set[2], m_set[3], m_rise[2], m_rise[3], puntos_8

    # --- PESTAÑA 2: CICLO ANUAL ---
    with tab_grafo:
        dates_s, v_s, s_s, dst_s, d_max_s, d_min_s, d_max_r, d_min_r, p8_s = obtener_datos_anuales(2026)
        x_s = [d.date() for d in dates_s]
        fig2 = go.Figure()
        def add_a(y, c, n): fig2.add_trace(go.Scatter(x=x_s, y=y, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=c, name=n, hoverinfo='skip'))
        fig2.add_trace(go.Scatter(x=x_s, y=[0]*len(x_s), mode='lines', line=dict(width=0), showlegend=False))
        add_a(v_s['t1'], c_pitta_n, "Pitta N."); add_a(v_s['t2'], c_vatta_n, "Vata N."); add_a(v_s['t3'], c_kapha_d, "Kapha M.")
        add_a(v_s['t4'], c_pitta_d, "Pitta D."); add_a(v_s['t5'], c_vatta_d, "Vata T."); add_a(v_s['t6'], c_kapha_n, "Kapha N."); add_a([24]*len(x_s), c_pitta_n, "Pitta N.")
        fig2.add_trace(go.Scatter(x=x_s, y=v_s['M'], line=dict(color='#FF8C00', width=2), name="Cénit"))
        for p in p8_s: fig2.add_vline(x=str(p), line_dash="dot", line_color="yellow")
        for d in [d_max_s, d_min_s]: fig2.add_vline(x=str(d), line_dash="dot", line_color="red" if d==d_max_s else "blue")
        fig2.update_layout(template="plotly_dark", height=600, yaxis=dict(range=[0, 24]), margin=dict(l=0,r=0,t=30,b=0), hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("**1. Solsticios:** Naranja/Cian. | **2. Cénit Solar:** Línea naranja. 8 marcadores amarillos. | **3. Amanecer:** Magenta/Verde. | **4. Atardecer:** Rojo/Azul.")

    # --- PESTAÑA 3: LUNAR Y PERSONAL ---
    with tab_lunar:
        st.subheader("Ciclo Lunar y Diario Personal")
        
        # Selector de año
        año_lunar = st.number_input("Selecciona el año a visualizar:", min_value=2020, max_value=2100, value=2026, step=1)
        
        col_reg, col_nota = st.columns(2)
        
        with col_reg:
            f_r = st.date_input("Día de regla:", value=datetime.date.today())
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Guardar regla"): 
                    cursor.execute('INSERT OR IGNORE INTO regla (fecha) VALUES (?)', (str(f_r),))
                    conn.commit()
                    st.success("Día guardado")
            with c2:
                # BOTÓN PARA DESHACER/BORRAR REGLA
                if st.button("Borrar regla", key="del_reg"):
                    cursor.execute('DELETE FROM regla WHERE fecha = ?', (str(f_r),))
                    conn.commit()
                    st.warning("Día eliminado")

        with col_nota:
            f_n = st.date_input("Fecha de la nota:", value=datetime.date.today(), key="f_n")
            t_n = st.text_input("Nota breve:")
            c3, c4 = st.columns(2)
            with c3:
                if st.button("Guardar nota"): 
                    cursor.execute('INSERT OR REPLACE INTO notas (fecha, texto) VALUES (?, ?)', (str(f_n), t_n))
                    conn.commit()
                    st.info("Nota guardada")
            with c4:
                # BOTÓN PARA DESHACER/BORRAR NOTA
                if st.button("Borrar nota", key="del_nota"):
                    cursor.execute('DELETE FROM notas WHERE fecha = ?', (str(f_n),))
                    conn.commit()
                    st.warning("Nota eliminada")
        
        # --- EL RESTO DEL CÓDIGO (DIBUJO DE GRÁFICO) SIGUE IGUAL ---
        # ... (copia aquí el resto de la lógica de dibujo de áreas, lunas y notas que ya tienes)
       
except Exception:
    st.error("Error técnico:")
    st.code(traceback.format_exc())
