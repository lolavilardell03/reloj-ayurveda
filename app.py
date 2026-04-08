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
    def obtener_datos_anuales(ubicacion_nombre, año):
        dates = pd.date_range(start=f'{año}-03-20', end=f'{año+1}-03-19', freq='D')
        # Añadimos 'bm_e' (Brahma Muhurta End) a las claves
        claves = ['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M', 'bm_e']
        v = {k: [] for k in claves}
        s = {k: [] for k in claves}
        dst_dates = []
        prev_offset = None

        max_sunset, min_sunset = -1, 999
        date_max_sunset, date_min_sunset = None, None
        max_sunrise, min_sunrise = -1, 999
        date_max_sunrise, date_min_sunrise = None, None
        
        max_m_val, min_m_val = -1, 999
        puntos_8_analema = []

        for d in dates:
            ev, offset = get_solar_events(d.date())
            if prev_offset is not None and offset != prev_offset:
                dst_dates.append(d.date())
            prev_offset = offset
            
            # Sunrise (t2)
            sunrise_raw = ev[1]
            h_rise, h_set = sunrise_raw + offset, ev[4] + offset
            
            # Cálculo exacto de Brahma Muhurta (Inicio bm, Final bm_e)
            # ev[6] ya es Sunrise - 1.6 horas (96 min). Ese es el inicio.
            # El final es Sunrise - 0.8 horas (48 min).
            bm_start = ev[6]
            bm_end = sunrise_raw - 0.8

            if h_set > max_sunset: max_sunset, date_max_sunset = h_set, d.date()
            if h_set < min_sunset: min_sunset, date_min_sunset = h_set, d.date()
            if h_rise > max_sunrise: max_sunrise, date_max_sunrise = h_rise, d.date()
            if h_rise < min_sunrise: min_sunrise, date_min_sunrise = h_rise, d.date()

            # Guardamos M
            v['M'].append(ev[7])
            s['M'].append(formato_hhmm(ev[7] + offset))
            
            # Guardamos bm (Inicio) y bm_e (Final)
            v['bm'].append(bm_start)
            s['bm'].append(formato_hhmm(bm_start + offset))
            v['bm_e'].append(bm_end)
            s['bm_e'].append(formato_hhmm(bm_end + offset))

            # Guardamos el resto
            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6']):
                    v[k].append(min(24.0, ev[i]) if k == 't6' else ev[i])
                    s[k].append(formato_hhmm(ev[i] + offset))

        # Cálculo de los 8 puntos críticos del analema
        promedio_m = sum(v['M']) / len(v['M'])
        for i in range(1, len(v['M']) - 1):
            prev, curr, post = v['M'][i-1], v['M'][i], v['M'][i+1]
            if (curr > prev and curr > post) or (curr < prev and curr < post):
                puntos_8_analema.append(dates[i].date())
            elif (prev < promedio_m < curr) or (prev > promedio_m > curr):
                if len(puntos_8_analema) < 8:
                    puntos_8_analema.append(dates[i].date())
        
        # OJO: La llamada res = obtener_datos_anuales en tab_grafo DEBE unpackear 9 variables.
        # Estamos devolviendo los mismos 9 objetos, pero v y s ahora contienen 'bm_e'.
        return dates, v, s, dst_dates, date_max_sunset, date_min_sunset, date_max_sunrise, date_min_sunrise, puntos_8_analema
        
    # --- PESTAÑA 2: CICLO ANUAL ---
    with tab_grafo:
        with st.spinner('Procesando ciclo anual...'):
            año_act = datetime.datetime.now(tz).year
            # Llamamos a tu función de datos anuales (la que devuelve 9 variables)
            res = obtener_datos_anuales(ubicacion, año_act)
            # Desempaquetamos las 9 variables
            dates, v, s, dst_dates, d_max_set, d_min_set, d_max_rise, d_min_rise, p8 = res
            
            x = [d.date() for d in dates]
            fig_grafo = go.Figure()

            def add_area(y_data, color, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=color, hoverinfo='skip', showlegend=False, name=name))
            
            # --- COLOR COMPLEMENTARIO BRAHMA MUHURTA (Oro Ámbar) ---
            c_brahma_m = 'rgba(255, 191, 0, 0.5)'

            fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
            add_area(v['t1'], c_pitta_n, "Pitta Noche")
            add_area(v['t2'], c_vatta_n, "Vata Noche")
            add_area(v['t3'], c_kapha_d, "Kapha Mañana")
            add_area(v['t4'], c_pitta_d, "Pitta Día")
            add_area(v['t5'], c_vatta_d, "Vata Tarde")
            add_area(v['t6'], c_kapha_n, "Kapha Noche")
            add_area([24]*len(x), c_pitta_n, "Pitta Noche")
            
            # --- DIBUJAR BRAHMA MUHURTA (Intervalo central de 48 min) ---
            # El intervalo está delimitado por Inicio (bm) y Fin (bm_e)
            fig_grafo.add_trace(go.Scatter(
                x=list(x) + list(x)[::-1], # Trazado de ida y vuelta para rellenar área
                y=list(v['bm_e']) + list(v['bm'])[::-1], 
                fill='toself', fillcolor=c_brahma_m, 
                mode='lines', line=dict(width=0), 
                hoverinfo='skip', showlegend=False, name="Brahma Muhurta"
            ))

            # Curvas dinámicas
            # He quitado la línea de 'gold' bm anterior porque ahora tenemos la franja completa.
            # Mantenemos Cénit.
            fig_grafo.add_trace(go.Scatter(x=x, y=v['M'], mode='lines', line=dict(color='#FF8C00', width=2), hoverinfo='skip', showlegend=False))

            # --- LÍNEA DE "HOY" (Turquesa más chillón/intenso) ---
            hoy_real = datetime.datetime.now(tz).date()
            # Si el día de hoy está dentro del rango que muestra el gráfico (Marzo a Marzo)
            if dates[0].date() <= hoy_real <= dates[-1].date():
                # He cambiado el color a 'cyan' (más intenso y chillón) y subido opacidad
                fig_grafo.add_vline(x=str(hoy_real), line_width=4, line_color="cyan", line_dash="solid", opacity=0.95)

            def add_hover(y_data, text_data, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, customdata=text_data, mode='lines', line=dict(width=0), hovertemplate=f"<b>{name}</b>: %{{customdata}}<extra></extra>"))
                
            add_hover(v['bm'], s['bm'], "Brahma Muhurta (Inicio)")
            add_hover(v['bm_e'], s['bm_e'], "Brahma Muhurta (Final)")
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
            
            # Los 8 marcadores amarillos del Cénit
            for fecha_p in p8:
                add_vline(fecha_p, "yellow", "dot")
            
            for d_dst in dst_dates: add_vline(d_dst, "white", "solid")

            fig_grafo.update_layout(xaxis=dict(tickformat="%d %b", title='Ciclo Perpetuo'), yaxis_title='Hora Local',
                yaxis=dict(range=[0, 24], tickvals=list(range(0, 25)), gridcolor='rgba(128, 128, 128, 0.2)'),
                hovermode="x unified", template="plotly_dark", height=650, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_grafo, use_container_width=True)

            st.markdown("---")
            st.markdown("**1. Solsticios:** Naranja (Verano), Cian (Invierno).")
            st.markdown("**2. Cénit Solar:** Línea naranja continua. Marcadores amarillos en sus 8 puntos críticos.")
            # Añadimos Brahma Muhurta a la leyenda de texto
            st.markdown("**3. Brahma Muhurta:** Franja Oro Ámbar. Intervalo central sáttvico (48 min) antes del Amanecer.")
            st.markdown("**4. Amanecer:** Magenta (tardío), Verde (temprano).")
            st.markdown("**5. Atardecer:** Rojo (tardío), Azul (temprano).")
            st.markdown("**6. Reloj:** Líneas blancas (cambio de hora social) y **Línea Turquesa Chillón** (Hoy).")
    
    with tab_lunar:
        st.subheader("🌙 Ciclo Lunar y Diario Personal")
        
        # 1. Selector de año (Base de datos infinita)
        año_sel = st.number_input("Visualizar ciclo (Empezando en Marzo):", min_value=2020, max_value=2050, value=2026, step=1)
        
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
                if st.button("Borrar nota", key="del_nota"):
                    cursor.execute('DELETE FROM notas WHERE fecha = ?', (str(f_n),))
                    conn.commit()
                    st.warning("Nota eliminada")
        
        # 2. DEFINIR RANGO DE UN AÑO (Empieza el 20 de Marzo)
        fecha_inicio = datetime.date(año_sel, 3, 20)
        fecha_fin = datetime.date(año_sel + 1, 3, 19)
        dates_l = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
        x_l = [d.date() for d in dates_l]
        
        # 3. Recuperar datos y filtrar para que SOLO se vea el año seleccionado
        cursor.execute('SELECT fecha FROM regla WHERE fecha BETWEEN ? AND ?', (str(fecha_inicio), str(fecha_fin)))
        dias_r = [f[0] for f in cursor.fetchall()]
        cursor.execute('SELECT * FROM notas WHERE fecha BETWEEN ? AND ?', (str(fecha_inicio), str(fecha_fin)))
        notas_dict = dict(cursor.fetchall())
        
        # Calcular datos solares para el rango seleccionado
        v_l = {k: [] for k in ['t1', 't2', 't3', 't4', 't5', 't6', 'M']}
        for d in dates_l:
            ev_vals, off = get_solar_events(d.date())
            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']):
                if k in v_l:
                    v_l[k].append(min(24.0, ev_vals[i]) if k == 't6' else ev_vals[i])
                    
        fig3 = go.Figure()
        
        # Dibujar áreas de color (Colores infinitos para cualquier año)
        def add_area_lunar(y_data, color):
            fig3.add_trace(go.Scatter(x=x_l, y=y_data, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=color, hoverinfo='skip', showlegend=False))
            
        fig3.add_trace(go.Scatter(x=x_l, y=[0]*len(x_l), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
        add_area_lunar(v_l['t1'], c_pitta_n)
        add_area_lunar(v_l['t2'], c_vatta_n)
        add_area_lunar(v_l['t3'], c_kapha_d)
        add_area_lunar(v_l['t4'], c_pitta_d)
        add_area_lunar(v_l['t5'], c_vatta_d)
        add_area_lunar(v_l['t6'], c_kapha_n)
        add_area_lunar([24]*len(x_l), c_pitta_n)
        
        # Línea Cénit suave
        fig3.add_trace(go.Scatter(x=x_l, y=v_l['M'], line=dict(color='rgba(255, 140, 0, 0.2)'), name="Cénit"))

        # Lunas (Calculadas día a día para el año actual)
        for i in range(1, len(dates_l)):
            f_p, f_c = moon.phase(dates_l[i-1].date()), moon.phase(dates_l[i].date())
            if f_c < f_p: fig3.add_vline(x=str(dates_l[i].date()), line_dash="dot", line_color="gray", opacity=0.5)
            elif f_p < 14 <= f_c: fig3.add_vline(x=str(dates_l[i].date()), line_dash="dot", line_color="white", opacity=0.7)
                
        # Equinoccios y Solsticios del año seleccionado
        estaciones = [(3,20), (6,21), (9,22), (12,21), (3,20)] # Marzo del año siguiente incluido
        for i, (m, d_est) in enumerate(estaciones):
            y_est = año_sel if i < 4 else año_sel + 1
            fig3.add_vline(x=str(datetime.date(y_est, m, d_est)), line_dash="dash", line_color="lightgreen", opacity=0.6)
            
        # Regla y Notas (Solo las que caen en este rango)
        for dr in dias_r: fig3.add_vline(x=dr, line_color="rgba(255, 100, 100, 0.4)", line_width=4)
        for f_n, tx in notas_dict.items():
            fig3.add_trace(go.Scatter(x=[f_n], y=[12], mode='markers', marker=dict(size=12, color='white', symbol='star'), hovertext=tx, name="Nota"))

        fig3.update_layout(
            template="plotly_dark", height=600, margin=dict(l=0,r=0,t=30,b=0), 
            yaxis=dict(range=[0,24], gridcolor='rgba(128, 128, 128, 0.2)'),
            xaxis=dict(tickformat="%d %b", title=f"Ciclo Personal {año_sel}-{año_sel+1}"),
            showlegend=False
        )
        st.plotly_chart(fig3, use_container_width=True)
                                  
except Exception:
    st.error("Error técnico:")
    st.code(traceback.format_exc())
