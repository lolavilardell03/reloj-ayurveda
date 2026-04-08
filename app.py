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

# --- CONFIGURACIÓN DE BASE DE DATOS ---
def gestionar_db():
    # Crea el archivo de la base de datos
    conn = sqlite3.connect('datos_personales.db', check_same_thread=False)
    c = conn.cursor()
    # Crea las tablas necesarias si no existen
    c.execute('CREATE TABLE IF NOT EXISTS notas (fecha TEXT PRIMARY KEY, texto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS regla (fecha TEXT PRIMARY KEY)')
    conn.commit()
    return conn, c

# Aquí es donde definimos 'conn' y 'cursor' para que el resto del código los reconozca
conn, cursor = gestionar_db()

try:
    st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🌺", layout="wide")
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
        
        midnight_utc = datetime.datetime.combine(fecha_dia, datetime.time.min).replace(tzinfo=pytz.UTC)
        
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

    tab_circulo, tab_grafo, tab_lunar = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)", "Ciclo Lunar"])

    with tab_circulo:
        hoy = datetime.datetime.now(tz).date()
        (t1, t2, t3, t4, t5, t6, bm, M), offset, _ = get_solar_events(hoy)
        col_texto, col_circulo = st.columns([1, 2])
        
        with col_texto:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown(f"### Horario en {ubicacion.split(' ')[0]}")
            st.markdown(f"**Brahma Muhurta:** `{formato_hhmm(bm + offset)}`")
            st.markdown(f"**Amanecer (Kapha):** `{formato_hhmm(t2 + offset)}`")
            st.markdown(f"**Inicio Pitta:** `{formato_hhmm(t3 + offset)}`")
            st.markdown(f"**Mediodía Solar:** `{formato_hhmm(M + offset)}`")
            st.markdown(f"**Inicio Vata:** `{formato_hhmm(t4 + offset)}`")
            st.markdown(f"**Atardecer (Kapha):** `{formato_hhmm(t5 + offset)}`")
            st.markdown(f"**Pitta Noche:** `{formato_hhmm(t6 + offset)}`")
            st.markdown(f"**Vata Noche:** `{formato_hhmm(t1 + offset)}`")

        with col_circulo:
            t6_limitado = min(24.0, t6)
            duraciones = [max(0.001, t1), max(0.001, t2-t1), max(0.001, t3-t2), max(0.001, t4-t3), max(0.001, t5-t4), max(0.001, t6_limitado-t5)]
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
            fig_circulo.update_layout(template="plotly_dark", height=500, showlegend=False, margin=dict(t=0, b=0, l=0, r=0),
                annotations=[dict(text='🦀', x=0.5, y=0.5, font=dict(size=35), showarrow=False)])
            st.plotly_chart(fig_circulo, use_container_width=True)

    def obtener_datos_anuales(ubicacion_nombre, año):
        dates = pd.date_range(start=f'{año}-03-20', end=f'{año+1}-03-19', freq='D')
        claves = ['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']
        v = {k: [] for k in claves}
        s = {k: [] for k in claves}
        dst_dates = []
        prev_offset = None

        max_sunset, min_sunset = -1, 999
        date_max_sunset, date_min_sunset = None, None
        max_sunrise, min_sunrise = -1, 999
        date_max_sunrise, date_min_sunrise = None, None
        
        # Inicializamos variables para evitar el error 'UnboundLocalError'
        max_m_val, min_m_val = -1, 999
        d_max_noon, d_min_noon = None, None
        
        # Lista para capturar los 8 puntos del analema (4 picos + 4 cruces)
        puntos_8_analema = []
        # Lista para guardar los 8 puntos críticos (máximos, mínimos y sillas)
        puntos_criticos_cenit = []
        valores_m = [] # Necesitamos primero recolectar todos los valores

        for d in dates:
            (t1, t2, t3, t4, t5, t6, bm, M), offset, P_val = get_solar_events(d.date())
            if prev_offset is not None and offset != prev_offset:
                dst_dates.append(d.date())
            prev_offset = offset
            
            h_rise, h_set = t2 + offset, t5 + offset
            if h_set > max_sunset: max_sunset, date_max_sunset = h_set, d.date()
            if h_set < min_sunset: min_sunset, date_min_sunset = h_set, d.date()
            if h_rise > max_sunrise: max_sunrise, date_max_sunrise = h_rise, d.date()
            if h_rise < min_sunrise: min_sunrise, date_min_sunrise = h_rise, d.date()

            # Máximos y mínimos absolutos (Febrero y Noviembre)
            if M > max_m_val: max_m_val, d_max_noon = M, d.date()
            if M < min_m_val: min_m_val, d_min_noon = M, d.date()
            
            # Guardamos el valor matemático del cénit
            v['M'].append(M)
            s['M'].append(formato_hhmm(M + offset))
            
            for k, val in zip(claves, [t1, t2, t3, t4, t5, t6, bm, M]):
                if k != 'M':
                    v[k].append(min(24.0, val) if k == 't6' else val)
                    s[k].append(formato_hhmm(val + offset))
            
        # Al salir del bucle, detectamos los 8 puntos (4 extremos y 4 cruces de cero)
        promedio_m = sum(v['M']) / len(v['M'])
        for i in range(1, len(v['M']) - 1):
            prev, curr, post = v['M'][i-1], v['M'][i], v['M'][i+1]
            
            # Detectar los 4 Extremos (Máximos y Mínimos)
            if (curr > prev and curr > post) or (curr < prev and curr < post):
                puntos_8_analema.append(dates[i].date())
                
            # Detectar los 4 Puntos de cruce / Silla (donde cruza el promedio)
            elif (prev < promedio_m < curr) or (prev > promedio_m > curr):
                if len(puntos_8_analema) < 8:
                    puntos_8_analema.append(dates[i].date())
    
        return dates, v, s, dst_dates, date_max_sunset, date_min_sunset, date_max_sunrise, date_min_sunrise, puntos_8_analema
        
    with tab_grafo:
        with st.spinner('Procesando ciclo anual...'):
            año_act = datetime.datetime.now().year
            res = obtener_datos_anuales(ubicacion, año_act)
            dates, v, s, dst_dates, d_max_set, d_min_set, d_max_rise, d_min_rise, puntos_8_analema = res
            
            x = [d.date() for d in dates]
            fig_grafo = go.Figure()

            def add_area(y_data, color, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=color, hoverinfo='skip', showlegend=False, name=name))
                
            fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
            add_area(v['t1'], c_pitta_n, "Pitta Noche")
            add_area(v['t2'], c_vatta_n, "Vata Noche")
            add_area(v['t3'], c_kapha_d, "Kapha Mañana")
            add_area(v['t4'], c_pitta_d, "Pitta Día")
            add_area(v['t5'], c_vatta_d, "Vata Tarde")
            add_area(v['t6'], c_kapha_n, "Kapha Noche")
            add_area([24]*len(x), c_pitta_n, "Pitta Noche")
            
            # Curvas dinámicas
            fig_grafo.add_trace(go.Scatter(x=x, y=v['bm'], mode='lines', line=dict(color='gold', width=2, dash='dash'), hoverinfo='skip', showlegend=False))
            fig_grafo.add_trace(go.Scatter(x=x, y=v['M'], mode='lines', line=dict(color='#FF8C00', width=2), hoverinfo='skip', showlegend=False))

            def add_hover(y_data, text_data, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, customdata=text_data, mode='lines', line=dict(width=0), hovertemplate=f"<b>{name}</b>: %{{customdata}}<extra></extra>"))
                
            add_hover(v['bm'], s['bm'], "Brahma Muhurta")
            add_hover(v['t2'], s['t2'], "Amanecer (Kapha)")
            add_hover(v['t3'], s['t3'], "Inicio Pitta")
            add_hover(v['M'], s['M'], "Cénit Solar")
            add_hover(v['t4'], s['t4'], "Inicio Vata")
            add_hover(v['t5'], s['t5'], "Atardecer (Kapha)")
            add_hover(v['t6'], s['t6'], "Pitta Noche")
            add_hover(v['t1'], s['t1'], "Vata Noche")

            def add_vline(d_val, color, dash='dot'):
                if d_val: fig_grafo.add_vline(x=str(d_val), line_dash=dash, line_color=color, opacity=0.7)
            
            # Solsticios
            s_ver, s_inv = datetime.date(año_act, 6, 21), datetime.date(año_act, 12, 21)
            if s_ver < dates[0].date(): s_ver = datetime.date(año_act+1, 6, 21)
            if s_inv < dates[0].date(): s_inv = datetime.date(año_act+1, 12, 21)
            add_vline(s_ver, "orange", "dash")
            add_vline(s_inv, "cyan", "dash")
            
            # Extremos de Amanecer / Atardecer
            add_vline(d_max_rise, "magenta", "dot"); add_vline(d_min_rise, "lightgreen", "dot")
            add_vline(d_max_set, "red", "dot"); add_vline(d_min_set, "blue", "dot")
            
            # Dibujamos los 8 marcadores amarillos detectados
            for fecha_punto in puntos_8_analema:
                add_vline(fecha_punto, "yellow", "dot")
            
            for d_dst in dst_dates: add_vline(d_dst, "white", "solid")

            fig_grafo.update_layout(xaxis=dict(tickformat="%d %b", title='Ciclo Perpetuo'), yaxis_title='Hora Local',
                yaxis=dict(range=[0, 24], tickvals=list(range(0, 25)), gridcolor='rgba(128, 128, 128, 0.2)'),
                hovermode="x unified", template="plotly_dark", height=650, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_grafo, use_container_width=True)

            st.markdown("---")
            st.markdown("**1. Solsticios:** Naranja (Verano), Cian (Invierno).")
            st.markdown("**2. Cénit Solar:** Línea naranja continua. Marcadores amarillos en sus 8 puntos críticos (máximos, mínimos y puntos de silla anuales).")
            st.markdown("**3. Amanecer:** Magenta (tardío), Verde (temprano).")
            st.markdown("**4. Atardecer:** Rojo (tardío), Azul (temprano).")
            st.markdown("**5. Reloj:** Líneas blancas (cambio de hora social).")

    with tab_lunar:
        
        st.subheader("Ciclo Lunar y Diario Personal")
        
        # 1. Selector de año para que sea una base de datos "para siempre"
        año_lunar = st.number_input("Selecciona el año a visualizar:", min_value=2020, max_value=2100, value=2026, step=1)
        
        col_reg, col_nota = st.columns(2)
        with col_reg:
            f_r = st.date_input("Marcar día de regla:", value=datetime.date.today())
            if st.button("Guardar regla"): 
                cursor.execute('INSERT OR IGNORE INTO regla (fecha) VALUES (?)', (str(f_r),))
                conn.commit()
                st.success("Día guardado")
        with col_nota:
            f_n = st.date_input("Fecha de la nota:", value=datetime.date.today(), key="f_n")
            t_n = st.text_input("Nota breve:")
            if st.button("Guardar nota"): 
                cursor.execute('INSERT OR REPLACE INTO notas (fecha, texto) VALUES (?, ?)', (str(f_n), t_n))
                conn.commit()
                st.info("Nota guardada")
        
        # 2. Recuperar datos de la base de datos
        cursor.execute('SELECT fecha FROM regla')
        dias_r = [f[0] for f in cursor.fetchall()]
        cursor.execute('SELECT * FROM notas')
        notas_dict = dict(cursor.fetchall())
        
        # 3. Generar fechas para TODO el año seleccionado
        dates_lunar = pd.date_range(start=f'{año_lunar}-01-01', end=f'{año_lunar}-12-31', freq='D')
        x_lunar = [d.date() for d in dates_lunar]
        
        # Calcular los datos solares solo para este año
        v_l = {k: [] for k in ['t1', 't2', 't3', 't4', 't5', 't6', 'M']}
        for d in dates_lunar:
            ev, _ = get_solar_events(d.date())
            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']):
                if k in v_l:
                    v_l[k].append(min(24.0, ev[i]) if k == 't6' else ev[i])
                    
        fig3 = go.Figure()
        
        # --- DIBUJAR LAS ÁREAS AYURVÉDICAS ---
        def add_area_lunar(y_data, color):
            fig3.add_trace(go.Scatter(x=x_lunar, y=y_data, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=color, hoverinfo='skip', showlegend=False))
            
        fig3.add_trace(go.Scatter(x=x_lunar, y=[0]*len(x_lunar), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
        add_area_lunar(v_l['t1'], c_pitta_n)
        add_area_lunar(v_l['t2'], c_vatta_n)
        add_area_lunar(v_l['t3'], c_kapha_d)
        add_area_lunar(v_l['t4'], c_pitta_d)
        add_area_lunar(v_l['t5'], c_vatta_d)
        add_area_lunar(v_l['t6'], c_kapha_n)
        add_area_lunar([24]*len(x_lunar), c_pitta_n)
        
        # Línea del Cénit
        fig3.add_trace(go.Scatter(x=x_lunar, y=v_l['M'], line=dict(color='#FF8C00', width=2), name="Cénit"))
        
        # --- DÍAS DE REGLA ---
        for d in dias_r: 
            fig3.add_vline(x=d, line_color="rgba(255, 100, 100, 0.4)", line_width=4)
            
        # --- FASES LUNARES (Lógica Astronómica Corregida) ---
        for i in range(1, len(dates_lunar)):
            d_prev = dates_lunar[i-1].date()
            d_curr = dates_lunar[i].date()
            fase_prev = moon.phase(d_prev)
            fase_curr = moon.phase(d_curr)
            
            # Luna Nueva (cuando la fase se reinicia de ~27 a 0)
            if fase_curr < fase_prev:
                fig3.add_vline(x=str(d_curr), line_dash="dot", line_color="gray", opacity=0.6)
            # Luna Llena (cuando cruza la mitad del ciclo, el día 14)
            elif fase_prev < 14 and fase_curr >= 14:
                fig3.add_vline(x=str(d_curr), line_dash="dot", line_color="white", opacity=0.6)
                
        # --- EQUINOCCIOS Y SOLSTICIOS ---
        estaciones = [
            datetime.date(año_lunar, 3, 20), # Equinoccio Primavera
            datetime.date(año_lunar, 6, 21), # Solsticio Verano
            datetime.date(año_lunar, 9, 22), # Equinoccio Otoño
            datetime.date(año_lunar, 12, 21) # Solsticio Invierno
        ]
        for f_est in estaciones:
            fig3.add_vline(x=str(f_est), line_dash="dash", line_color="lightgreen", opacity=0.7)
            
        # --- NOTAS PERSONALES ---
        for f_nota, txt in notas_dict.items():
            # Filtramos para que solo se dibujen las notas del año seleccionado
            if f_nota.startswith(str(año_lunar)):
                fig3.add_trace(go.Scatter(x=[f_nota], y=[12], mode='markers', marker=dict(size=12, color='white', symbol='star'), hovertext=txt, name="Nota"))
        
        fig3.update_layout(
            template="plotly_dark", 
            height=600, 
            margin=dict(l=0,r=0,t=30,b=0), 
            yaxis=dict(range=[0,24], gridcolor='rgba(128, 128, 128, 0.2)'),
            xaxis=dict(tickformat="%d %b"),
            showlegend=False,
            hovermode="x unified"
        )
        st.plotly_chart(fig3, use_container_width=True)
        
except Exception as e:
    st.error("¡Oops! Ha ocurrido un error técnico interno:")
    st.code(traceback.format_exc())
