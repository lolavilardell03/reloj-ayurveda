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

# --- 2. LÓGICA Y FUNCIONES AUXILIARES ---
def formato_hhmm(hora_decimal):
    h = int(hora_decimal % 24)
    m = int(round((hora_decimal % 24 - h) * 60))
    if m == 60: h = (h + 1) % 24; m = 0
    return f"{h:02d}:{m:02d}"

try:
    st.set_page_config(page_title="Reloj Ayurvédico", page_icon="🌺", layout="wide")
    st.title("Tu Reloj Ayurvédico Personal")

    ubicacion = st.selectbox(
        "Selecciona tu ubicación:", 
        ["Palma (Islas Baleares)", "Alcoy (Alicante)"]
    )

    loc = LocationInfo("Palma", "Spain", "Europe/Madrid", 39.5696, 2.6502) if "Palma" in ubicacion else LocationInfo("Alcoy", "Spain", "Europe/Madrid", 38.6983, -0.4736)
    tz = pytz.timezone(loc.timezone)

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

    def obtener_datos_anuales(ubicacion_nombre, año):
        dates = pd.date_range(start=f'{año}-03-20', end=f'{año+1}-03-19', freq='D')
        claves = ['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M', 'bm_e']
        v, s = {k: [] for k in claves}, {k: [] for k in claves}
        dst_dates, puntos_8 = [], []
        prev_off = None
        max_set, min_set = (-1, None), (999, None)
        max_rise, min_rise = (-1, None), (999, None)

        for d in dates:
            ev, off = get_solar_events(d.date())
            if prev_off is not None and off != prev_off: dst_dates.append(d.date())
            prev_off = off
            
            sunrise_raw = ev[1]
            h_rise, h_set = sunrise_raw + off, ev[4] + off
            bm_start, bm_end = ev[6], sunrise_raw - 0.8

            if h_set > max_set[0]: max_set = (h_set, d.date())
            if h_set < min_set[0]: min_set = (h_set, d.date())
            if h_rise > max_rise[0]: max_rise = (h_rise, d.date())
            if h_rise < min_rise[0]: min_rise = (h_rise, d.date())

            v['M'].append(ev[7]); s['M'].append(formato_hhmm(ev[7] + off))
            v['bm'].append(bm_start); s['bm'].append(formato_hhmm(bm_start + off))
            v['bm_e'].append(bm_end); s['bm_e'].append(formato_hhmm(bm_end + off))

            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6']):
                v[k].append(min(24.0, ev[i]) if k == 't6' else ev[i])
                s[k].append(formato_hhmm(ev[i] + off))

        promedio_m = sum(v['M']) / len(v['M'])
        for i in range(1, len(v['M']) - 1):
            prev, curr, post = v['M'][i-1], v['M'][i], v['M'][i+1]
            if (curr > prev and curr > post) or (curr < prev and curr < post): puntos_8.append(dates[i].date())
            elif (prev < promedio_m < curr) or (prev > promedio_m > curr):
                if len(puntos_8) < 8: puntos_8.append(dates[i].date())
        
        return dates, v, s, dst_dates, max_set[1], min_set[1], max_rise[1], min_rise[1], puntos_8

    c_pitta_n, c_vatta_n, c_kapha_d = 'rgba(210, 130, 210, 0.5)', 'rgba(150, 150, 255, 0.5)', 'rgba(220, 255, 170, 0.5)'
    c_pitta_d, c_vatta_d, c_kapha_n = 'rgba(255, 220, 170, 0.5)', 'rgba(170, 220, 255, 0.5)', 'rgba(170, 220, 170, 0.5)'
    c_mystic_blue = 'rgba(100, 130, 255, 0.8)'

    tab_circulo, tab_grafo, tab_lunar = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)", "🌙 Ciclo Lunar"])

    # --- PESTAÑA 1: RELOJ DIARIO ---
    with tab_circulo:
        hoy = datetime.datetime.now(tz).date()
        # Obtenemos los eventos solares
        (t1, t2, t3, t4, t5, t6, bm, M), offset = get_solar_events(hoy)
        
        # Lógica de Brahma Muhurta
        bm_inicio = t2 - 1.6
        bm_final = t2 - 0.8
        c_mystic_blue = 'rgba(100, 130, 255, 0.8)'

        col_t, col_c = st.columns([1, 2])
        
        with col_t:
            st.markdown(f"### {ubicacion.split(' ')[0]}")
            # Leyenda limpia: Solo emojis en BM y Cénit
            st.write(f"**✨ Brahma Muhurta (Inicio):** `{formato_hhmm(bm_inicio + offset)}`")
            st.write(f"**✨ Brahma Muhurta (Final):** `{formato_hhmm(bm_final + offset)}`")
            st.write(f"**✨ Amanecer (Kapha):** `{formato_hhmm(t2 + offset)}`")
            st.markdown("---")
            st.write(f"**Inicio Pitta:** `{formato_hhmm(t3 + offset)}`")
            st.write(f"**☀️ Mediodía:** `{formato_hhmm(M + offset)}`")
            st.write(f"**Inicio Vata:** `{formato_hhmm(t4 + offset)}`")
            st.markdown("---")
            st.write(f"**🌙 Atardecer (Kapha):** `{formato_hhmm(t5 + offset)}`")
            st.write(f"**🌙 Pitta Noche:** `{formato_hhmm(t6 + offset)}`")
            st.write(f"**🌙 Vata Noche:** `{formato_hhmm(t1 + offset)}` ")

        with col_c:
            # Duraciones del gráfico
            duraciones = [
                max(0.1, t1),               # Pitta Noche
                bm_inicio - t1,             # Vata Noche (Silencio)
                0.8,                        # Brahma Muhurta (48 min)
                0.8,                        # Transición (48 min)
                t3 - t2,                    # Kapha Mañana
                t4 - t3,                    # Pitta Día
                t5 - t4,                    # Vata Tarde
                min(24.0, t6) - t5          # Kapha Noche
            ]
            
            # Usamos un espacio en blanco ' ' en lugar de una cadena vacía 
            # para evitar que Plotly asigne un número automáticamente.
            nombres = [
                'Pitta Noche', 'Vata Noche', '✨ Brahma Muhurta', 
                ' ', 'Kapha Mañana', 'Pitta Día', 
                'Vata Tarde', 'Kapha Noche'
            ]
            
            colores = [
                c_pitta_n, c_vatta_n, c_mystic_blue, 
                c_vatta_n, c_kapha_d, c_pitta_d, 
                c_vatta_d, c_kapha_n
            ]
            
            if t6 < 24.0:
                duraciones.append(24.0 - t6)
                nombres.append('Pitta Noche')
                colores.append(c_pitta_n)

            fig = go.Figure(go.Pie(
                values=duraciones, 
                labels=nombres, 
                marker=dict(colors=colores, line=dict(width=0)),
                hole=0.4, 
                sort=False, 
                direction='clockwise', 
                rotation=270, 
                textinfo='label'
            ))
            
            fig.update_layout(
                template="plotly_dark", 
                height=500, 
                showlegend=False, 
                margin=dict(t=0,b=0,l=0,r=0),
                annotations=[dict(text='🦀', x=0.5, y=0.5, font=dict(size=35), showarrow=False)]
            )
            
            st.plotly_chart(fig, use_container_width=True)

    # --- PESTAÑA 2: CICLO ANUAL ---
    with tab_grafo:
        with st.spinner('Procesando ciclo anual...'):
            año_act = datetime.datetime.now(tz).year
            res = obtener_datos_anuales(ubicacion, año_act)
            dates, v, s, dst_dates, d_max_set, d_min_set, d_max_rise, d_min_rise, p8 = res
            x = [d.date() for d in dates]
            fig_grafo = go.Figure()

            # --- LAS HERRAMIENTAS (FUNCIONES INTERNAS) ---
            def add_area(y_data, color, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=color, hoverinfo='skip', showlegend=False, name=name))
            
            def add_hover(y_data, text_data, name):
                fig_grafo.add_trace(go.Scatter(x=x, y=y_data, customdata=text_data, mode='lines', line=dict(width=0), hovertemplate=f"<b>{name}</b>: %{{customdata}}<extra></extra>"))

            def add_vline(d_val, color, dash='dot', op=0.7):
                if d_val: fig_grafo.add_vline(x=str(d_val), line_dash=dash, line_color=color, opacity=op)

            # --- DIBUJO DE ÁREAS ---
            fig_grafo.add_trace(go.Scatter(x=x, y=[0]*len(x), mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
            add_area(v['t1'], c_pitta_n, "Pitta N."); add_area(v['t2'], c_vatta_n, "Vata N."); add_area(v['t3'], c_kapha_d, "Kapha M.")
            add_area(v['t4'], c_pitta_d, "Pitta D."); add_area(v['t5'], c_vatta_d, "Vata T."); add_area(v['t6'], c_kapha_n, "Kapha N."); add_area([24]*len(x), c_pitta_n, "Pitta N.")
            
            # Franja Brahma Muhurta (Mystic Blue)
            c_mystic_blue_area = 'rgba(100, 130, 255, 0.6)'
            fig_grafo.add_trace(go.Scatter(x=list(x) + list(x)[::-1], y=list(v['bm_e']) + list(v['bm'])[::-1], fill='toself', fillcolor=c_mystic_blue_area, mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False))
            
            fig_grafo.add_trace(go.Scatter(x=x, y=v['M'], mode='lines', line=dict(color='#FF8C00', width=2), hoverinfo='skip', showlegend=False))

            # Línea Turquesa Chillona (Hoy)
            hoy_real = datetime.datetime.now(tz).date()
            if dates[0].date() <= hoy_real <= dates[-1].date():
                fig_grafo.add_vline(x=str(hoy_real), line_width=4, line_color="cyan", line_dash="solid", opacity=1.0)

            # --- INFORMACIÓN AL PASAR EL RATÓN (HOVER) ---
            add_hover(v['t1'], s['t1'], "Vata Noche")
            add_hover(v['t6'], s['t6'], "Pitta Noche")
            add_hover(v['t5'], s['t5'], "Atardecer (Kapha)")
            add_hover(v['t4'], s['t4'], "Inicio Vata")
            add_hover(v['M'], s['M'], "Cénit Solar")
            add_hover(v['t3'], s['t3'], "Inicio Pitta")
            add_hover(v['t2'], s['t2'], "Amanecer (Kapha)")
            add_hover(v['bm_e'], s['bm_e'], "Brahma Muhurta (Final)")
            add_hover(v['bm'], s['bm'], "Brahma Muhurta (Inicio)")

            # --- LÍNEAS INFORMATIVAS ---
            s_ver, s_inv = datetime.date(año_act, 6, 21), datetime.date(año_act, 12, 21)
            if s_ver < dates[0].date(): s_ver = datetime.date(año_act+1, 6, 21)
            add_vline(s_ver, "orange", "dash"); add_vline(s_inv, "cyan", "dash")
            
            add_vline(d_max_rise, "magenta"); add_vline(d_min_rise, "lightgreen")
            add_vline(d_max_set, "red"); add_vline(d_min_set, "blue")
            
            for p in p8: add_vline(p, "yellow", op=0.6)
            for dst in dst_dates: add_vline(dst, "white", dash="solid", op=0.3)

            fig_grafo.update_layout(xaxis=dict(tickformat="%d %b"), yaxis=dict(range=[0, 24]), hovermode="x unified", template="plotly_dark", height=600, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_grafo, use_container_width=True)

            st.markdown("---")
            st.markdown("**1. Solsticios:** Naranja (Verano), Cian (Invierno). | **2. Cénit Solar:** 8 marcadores amarillos.")
            st.markdown("**3. Brahma Muhurta:** Franja azul místico. | **4. Amanecer:** Magenta (tardío), Verde (temprano).")
            st.markdown("**5. Atardecer:** Rojo (tardío), Azul (temprano). | **6. Hoy:** Línea cian eléctrica.")
    
    # --- PESTAÑA 3: LUNAR ---
    with tab_lunar:
        st.subheader("🌙 Ciclo Lunar y Diario Personal")
        año_sel = st.number_input("Año:", min_value=2020, max_value=2050, value=2026)
        col_r, col_n = st.columns(2)
        with col_r:
            f_r = st.date_input("Día regla:", value=datetime.date.today())
            if st.button("Guardar regla"): cursor.execute('INSERT OR IGNORE INTO regla (fecha) VALUES (?)', (str(f_r),)); conn.commit(); st.success("OK")
            if st.button("Borrar regla"): cursor.execute('DELETE FROM regla WHERE fecha = ?', (str(f_r),)); conn.commit(); st.warning("Borrado")
        with col_n:
            f_n = st.date_input("Fecha nota:", value=datetime.date.today(), key="f_n")
            t_n = st.text_input("Nota:")
            if st.button("Guardar nota"): cursor.execute('INSERT OR REPLACE INTO notas (fecha, texto) VALUES (?, ?)', (str(f_n), t_n)); conn.commit(); st.info("OK")
            if st.button("Borrar nota"): cursor.execute('DELETE FROM notas WHERE fecha = ?', (str(f_n),)); conn.commit(); st.warning("Borrado")

        f_ini, f_fin = datetime.date(año_sel, 3, 20), datetime.date(año_sel + 1, 3, 19)
        dates_l = pd.date_range(start=f_ini, end=f_fin, freq='D')
        x_l = [d.date() for d in dates_l]
        cursor.execute('SELECT fecha FROM regla WHERE fecha BETWEEN ? AND ?', (str(f_ini), str(f_fin)))
        dias_r = [f[0] for f in cursor.fetchall()]
        cursor.execute('SELECT * FROM notas WHERE fecha BETWEEN ? AND ?', (str(f_ini), str(f_fin)))
        notas_d = dict(cursor.fetchall())
        
        v_l = {k: [] for k in ['t1', 't2', 't3', 't4', 't5', 't6', 'M']}
        for d in dates_l:
            ev_l, _ = get_solar_events(d.date())
            for i, k in enumerate(['t1', 't2', 't3', 't4', 't5', 't6', 'bm', 'M']):
                if k in v_l: v_l[k].append(min(24.0, ev_l[i]) if k == 't6' else ev_l[i])
                    
        fig3 = go.Figure()
        def add_al(y, c): fig3.add_trace(go.Scatter(x=x_l, y=y, fill='tonexty', mode='lines', line=dict(width=0), fillcolor=c, hoverinfo='skip', showlegend=False))
        fig3.add_trace(go.Scatter(x=x_l, y=[0]*len(x_l), mode='lines', line=dict(width=0), showlegend=False))
        add_al(v_l['t1'], c_pitta_n); add_al(v_l['t2'], c_vatta_n); add_al(v_l['t3'], c_kapha_d)
        add_al(v_l['t4'], c_pitta_d); add_al(v_l['t5'], c_vatta_d); add_al(v_l['t6'], c_kapha_n); add_al([24]*len(x_l), c_pitta_n)
        
        for i in range(1, len(dates_l)):
            f_p, f_c = moon.phase(dates_l[i-1].date()), moon.phase(dates_l[i].date())
            if f_c < f_p: fig3.add_vline(x=str(dates_l[i].date()), line_dash="dot", line_color="gray", opacity=0.5)
            elif f_p < 14 <= f_c: fig3.add_vline(x=str(dates_l[i].date()), line_dash="dot", line_color="white", opacity=0.7)
        for dr in dias_r: fig3.add_vline(x=dr, line_color="rgba(255, 100, 100, 0.4)", line_width=4)
        for fn, tx in notas_d.items(): fig3.add_trace(go.Scatter(x=[fn], y=[12], mode='markers', marker=dict(size=12, color='white', symbol='star'), hovertext=tx))

        fig3.update_layout(template="plotly_dark", height=600, yaxis=dict(range=[0,24]), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

except Exception:
    st.error("Error técnico:")
    st.code(traceback.format_exc())
