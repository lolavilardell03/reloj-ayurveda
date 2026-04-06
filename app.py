import streamlit as st
import pandas as pd
import datetime
import pytz
import plotly.graph_objects as go
from astral import LocationInfo
from astral.sun import sun
import traceback

try:
    st.set_page_config(page_title="Reloj Ayurvédico", layout="wide")
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

    tab_circulo, tab_grafo = st.tabs(["Reloj Circular (Hoy)", "Ciclo Anual (Primavera)"])

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
                annotations=[dict(text='24 H', x=0.5, y=0.5, font=dict(size=30), showarrow=False)])
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
        
        # Para extremos del mediodía (Ecuación del tiempo)
        # Usamos el valor M matemático (UTC) para encontrar los extremos reales sin saltos de DST
        max_m_val, min_m_val = -1, 999
        d_max_noon, d_min_noon = None, None
        # Puntos secundarios (relativos)
        rel_max_val, rel_min_val = -1, 999
        d_rel_max_noon, d_rel_min_noon = None, None

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

            # Lógica para extremos del mediodía (Analema)
            if M > max_m_val: max_m_val, d_max_noon = M, d.date()
            if M < min_m_val: min_m_val, d_min_noon = M, d.date()
            # Inflexiones secundarias (Mayo y Julio aprox)
            mes = d.month
            if mes in [5, 6] and M < rel_min_val: rel_min_val, d_rel_min_noon = M, d.date()
            if mes in [7, 8] and M > rel_max_val: rel_max_val, d_rel_max_noon = M, d.date()

            for k, val in zip(claves, [t1, t2, t3, t4, t5, t6, bm, M]):
                v[k].append(min(24.0, val) if k == 't6' else val)
                s[k].append(formato_hhmm(val + offset))
            
        return dates, v, s, dst_dates, date_max_sunset, date_min_sunset, date_max_sunrise, date_min_sunrise, d_max_noon, d_min_noon, d_rel_max_noon, d_rel_min_noon

    with tab_grafo:
        with st.spinner('Procesando ciclo anual...'):
            año_act = datetime.datetime.now().year
            res = obtener_datos_anuales(ubicacion, año_act)
            dates, v, s, dst_dates, d_max_set, d_min_set, d_max_rise, d_min_rise, d_max_n, d_min_n, d_rel_max, d_rel_min = res
            
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
            
            # Extremos del Cénit (Amarillo)
            for d_noon in [d_max_n, d_min_n, d_rel_max, d_rel_min]:
                add_vline(d_noon, "yellow", "dot")
            
            for d_dst in dst_dates: add_vline(d_dst, "white", "solid")

            fig_grafo.update_layout(xaxis=dict(tickformat="%d %b", title='Ciclo Perpetuo'), yaxis_title='Hora Local',
                yaxis=dict(range=[0, 24], tickvals=list(range(0, 25)), gridcolor='rgba(128, 128, 128, 0.2)'),
                hovermode="x unified", template="plotly_dark", height=650, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_grafo, use_container_width=True)

            st.markdown("---")
            st.markdown("**1. Solsticios:** Naranja (Verano), Cian (Invierno).")
            st.markdown("**2. Cénit Solar:** Línea naranja continua. Marcadores amarillos en sus máximos y mínimos anuales.")
            st.markdown("**3. Amanecer:** Magenta (tardío), Verde (temprano).")
            st.markdown("**4. Atardecer:** Rojo (tardío), Azul (temprano).")
            st.markdown("**5. Reloj:** Líneas blancas (cambio de hora social).")

except Exception as e:
    st.error("¡Oops! Ha ocurrido un error técnico interno:")
    st.code(traceback.format_exc())
