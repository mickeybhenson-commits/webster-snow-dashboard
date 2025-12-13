import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"

st.set_page_config(page_title="Stephanie's Snow Forecaster (Stable ECMWF)", page_icon="❄️", layout="wide")

# --- WNC WEBCAM LINKS ---
WNC_WEBCAMS = {
    "Sylva (Historic Courthouse)": "https://www.ashevillewx.com/sylva-jackson-county-historic-courthouse",
    "Waynesville (Downtown)": "https://www.ashevillewx.com/waynesville-downtown-live-camera",
    "Franklin (Macon Co. Airport)": "https://www.windfinder.com/webcams/franklin_macon_county_airport",
    "Highlands (Outpost)": "https://www.highlandsoutpost.com/live-webcam/",
    "Cashiers (Intersection)": "https://www.landmarkrg.com/cashiers-webcam",
}
BILTMORE_WINTER_GARDEN_LINK = "https://www.bing.com/videos/riverview/relatedvideo?q=Biltmore%20Estate%20live%20webcam&mid=D398BE68B9891902173CD398BE68B9891902173C&ajaxhist=0"
NORAD_SANTA_LINK = "https://www.noradsanta.org/en/"

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* 1. Main Background - Adjusting opacity for better readability */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.8)), 
                          url('https://images.unsplash.com/photo-1516431883744-dc60fa69f927?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }
    
    /* 2. Glass Cards for Data */
    .glass-card {
        background-color: rgba(20, 30, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* 3. Metric Boxes - Increased Contrast */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        border: 2px solid rgba(255,255,255,0.2);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
    }

    /* 4. Alert Banners */
    .alert-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.2);
        font-weight: bold;
    }
    .alert-purple { background-color: #5E35B1; border-left: 10px solid #B39DDB; }
    .alert-red { background-color: #C62828; border-left: 10px solid #FFCDD2; }
    .alert-orange { background-color: #EF6C00; border-left: 10px solid #FFE0B2; }
    
    /* 5. Headers & Images */
    img { border: 2px solid #4ECDC4; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #ffffff !important; }
    
    /* 6. Clean Divider */
    hr { margin-top: 10px; margin-bottom: 10px; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE FIX ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1544208081-30d07248e359?fit=crop&w=500&h=500", caption="Weather Intelligence Center")
    st.markdown("### ⚙️ System Controls")
    if st.button("🔄 Force Refresh Data"): 
        st.cache_data.clear(); 
        st.rerun()
    st.markdown("---")
    st.caption(f"Location: {LOCATION_NAME}")
    st.caption(f"Last API Fetch:\n{nc_time.strftime('%I:%M:%S %p')}")

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.title("❄️ Stephanie's Snow Forecaster")
    st.markdown("#### *PAWIS 1.0: Stable Forecasting (ECMWF Only)*")
    st.caption(f"Real-time Data & Intelligence | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS (ECMWF ONLY) ---
@st.cache_data(ttl=300)
def get_nws_alerts():
    try:
        url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        r = requests.get(url, headers={'User-Agent': '(webster_app)'}).json()
        return r.get('features', [])
    except: return []

@st.cache_data(ttl=900)
def get_nws_text():
    try:
        r = requests.get(f"https://api.weather.gov/points/{LAT},{LON}", headers={'User-Agent': '(webster_app)'}).json()
        grid_id, x, y = r['properties']['gridId'], r['properties']['gridX'], r['properties']['gridY']
        f = requests.get(f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast", headers={'User-Agent': '(webster_app)'}).json()
        return f['properties']['periods']
    except: return []

@st.cache_data(ttl=3600)
def get_ecmwf_data():
    """Get ECMWF model forecast (Daily metrics, hourly thermal/snow)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": [
                "snowfall_sum", 
                "weather_code", 
                "temperature_2m_max", 
                "temperature_2m_min", 
                "precipitation_sum",
                "wind_gusts_10m_max"
            ], 
            "hourly": [
                "temperature_2m", 
                "dewpoint_2m",
                "snowfall"
            ],
            "timezone": "America/New_York", 
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        r = requests.get(url, params=params, timeout=10).json()
        return {
            'daily': r.get('daily', None),
            'hourly': r.get('hourly', None)
        }
    except: return None

@st.cache_data(ttl=86400)
def get_history_facts():
    today = datetime.now()
    start = (today - timedelta(days=365*10)).strftime('%Y-%m-%d')
    end = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT, 
        "longitude": LON, 
        "start_date": start, 
        "end_date": end, 
        "daily": "snowfall_sum", 
        "timezone": "America/New_York", 
        "precipitation_unit": "inch"
    }
    try:
        r = requests.get(url, params=params).json()
        df = pd.DataFrame(r['daily'])
        df['time'] = pd.to_datetime(df['time'])
        df['md'] = df['time'].dt.strftime('%m-%d')
        return df[df['md'] == today.strftime('%m-%d')]
    except: return None

# --- ALERT BANNER (Keep as is) ---
alerts = get_nws_alerts()
if alerts:
    for alert in alerts:
        props = alert['properties']
        event = props['event']
        description = props['description']
        css_class = "alert-orange"
        if "Warning" in event: css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: css_class = "alert-purple"
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
            <details><summary>Read Details</summary><p style="font-size:0.9em;">{description}</p></details>
        </div>
        """, unsafe_allow_html=True)

# --- FETCH DATA ---
with st.spinner("Loading weather intelligence..."):
    ecmwf_data = get_ecmwf_data()
    nws = get_nws_text()
    history = get_history_facts()

# Extract data for clarity
ecmwf = ecmwf_data['daily'] if ecmwf_data and 'daily' in ecmwf_data else None
hourly_data = ecmwf_data['hourly'] if ecmwf_data and 'hourly' in ecmwf_data else None

# --- TABS (Updated Structure: 6 Tabs) ---
tab_snow_summary, tab_thermal, tab_radar, tab_nws_text, tab_webcams, tab_history, tab_entertainment = st.tabs([
    "❄️ Snow Summary (ECMWF)", 
    "🌡️ Thermal Analysis", 
    "📡 Radar & Maps", 
    "🌨️ NWS Text Forecast", 
    "🎥 WNC Webcams",      
    "📜 History",
    "✨ Seasonal Fun"
])

# --- TAB 1: SNOW SUMMARY (ECMWF Only) ---
with tab_snow_summary:
    st.markdown("### ❄️ 7-Day Snowfall Forecast (ECMWF Model)")
    
    if ecmwf:
        
        # Summary Metrics
        st.markdown("#### 📊 Forecast Overview")
        col1, col2, col3 = st.columns(3)
        
        ecmwf_snow_list = ecmwf['snowfall_sum'][:7] if ecmwf and 'snowfall_sum' in ecmwf else [0]
        ecmwf_7day = sum(ecmwf_snow_list)
        
        col1.metric("7-Day Total Snowfall", f"{ecmwf_7day:.2f}\"")
        col2.metric("Minimum Temperature", f"{min(ecmwf['temperature_2m_min'][:7]):.0f}°F")
        col3.metric("Maximum Wind Gust", f"{max(ecmwf['wind_gusts_10m_max'][:7]):.0f} mph")
        
        st.markdown("---")
        
        # Day-by-Day Summary Table
        st.markdown("#### 📅 Daily Forecast")
        
        summary_data = []
        min_len = min(len(ecmwf_snow_list), len(ecmwf['temperature_2m_max']), 7)
        
        for i in range(min_len):
            day_date = pd.to_datetime(ecmwf['time'][i])
            
            summary_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Snowfall': f"{ecmwf_snow_list[i]:.2f}\"",
                'High/Low Temp': f"{ecmwf['temperature_2m_max'][i]:.0f}°F / {ecmwf['temperature_2m_min'][i]:.0f}°F",
                'Max Wind Gust': f"{ecmwf['wind_gusts_10m_max'][i]:.0f} mph"
            })
        
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Visual Snow Chart
        st.markdown("#### 📈 Visual Snowfall Projection")
        fig = go.Figure()
        dates = [pd.to_datetime(ecmwf['time'][i]).strftime('%a %m/%d') for i in range(min_len)]
        
        fig.add_trace(go.Bar(
            name='🌍 ECMWF Snowfall',
            x=dates,
            y=ecmwf_snow_list[:min_len],
            marker_color='#81D4FA'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="ECMWF Snowfall Forecast (inches)",
            xaxis_title="Date",
            yaxis_title="Snowfall (inches)",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.warning("Data loading. Please ensure your internet connection is stable and try refreshing.")


# --- TAB 2: THERMAL ANALYSIS ---
with tab_thermal:
    st.markdown("### 🌡️ Key Thermal Indicators")
    st.caption("Critical metrics for predicting freezing rain, ice, and atmospheric moisture (ECMWF Hourly)")
    
    if ecmwf and hourly_data:
        # 1. Thermal Metrics
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        
        hourly_df = pd.DataFrame(hourly_data)
        hourly_df['time'] = pd.to_datetime(hourly_df['time'])
        
        # Use first period data for current state estimates
        current_temp = hourly_df['temperature_2m'][0]
        current_dewpoint = hourly_df['dewpoint_2m'][0]
        dewpoint_depression = current_temp - current_dewpoint
        
        max_wind_gust = max(ecmwf['wind_gusts_10m_max'][:7]) if 'wind_gusts_10m_max' in ecmwf else 0
        total_snow_7day = sum(ecmwf['snowfall_sum'][:7]) if ecmwf and 'snowfall_sum' in ecmwf else 0
        
        col_t1.metric("Current Temp", f"{current_temp:.0f}°F")
        col_t2.metric("Current Dew Point", f"{current_dewpoint:.0f}°F")
        col_t3.metric("Min Temp (7 Days)", f"{min(ecmwf['temperature_2m_min'][:7]):.0f}°F")
        col_t4.metric("Current Dew Point Depression", f"{dewpoint_depression:.1f}°F", 
                      help="Difference between air temperature and dew point. Lower number means higher humidity (risk of fog/ice).")


        # 2. Temperature & Dew Point Plot
        st.markdown("---")
        st.markdown("#### Temperature vs. Dew Point (Hourly Forecast)")
        
        try:
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=hourly_df['time'], y=hourly_df['temperature_2m'], mode='lines', 
                                          name='Temperature', line=dict(color='orange', width=3)))
            fig_temp.add_trace(go.Scatter(x=hourly_df['time'], y=hourly_df['dewpoint_2m'], mode='lines', 
                                          name='Dew Point', line=dict(color='#4ECDC4', width=3)))
            
            fig_temp.add_hline(y=32, line_dash="dot", line_color="red", annotation_text="Freezing Line (32°F)")
            
            fig_temp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=450,
                xaxis_title="Time",
                yaxis_title="Temperature (°F)",
                hovermode="x unified"
            )
            st.plotly_chart(fig_temp, use_container_width=True)
            
            st.caption("When the Temperature and Dew Point lines converge, expect fog or heavy moisture.")
        except Exception:
            st.error("Thermal analysis plot not available.")
    
    else:
        st.warning("Data loading. Please ensure your internet connection is stable and try refreshing.")


# --- TAB 3: RADAR & MAPS (Updated) ---
with tab_radar:
    st.markdown("### 📡 Local & Regional Radar")
    
    col_local, col_regional = st.columns(2)
    
    with col_local:
        st.markdown("#### Local Doppler Radar (KGSP)")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"KGSP Radar | {nc_time.strftime('%I:%M %p')}", 
                 use_container_width=True)
        st.caption("🔄 Auto-refreshes every 5 minutes")
    
    with col_regional:
        st.markdown("#### Regional Composite")
        st.image(f"https://radar.weather.gov/ridge/standard/SOUTHEAST_loop.gif?t={ts}", 
                 caption=f"Southeast Regional View | {nc_time.strftime('%I:%M %p')}", 
                 use_container_width=True)
        st.caption("NEXRAD data provided by NOAA/NWS.")

# --- TAB 4: NWS TEXT FORECAST (New Tab) ---
with tab_nws_text:
    st.markdown("### 🌨️ NWS Text Forecast & Summary")
    
    col_text, col_stats = st.columns([2, 1])
    
    with col_text:
        if nws and ecmwf:
            st.markdown("#### Detailed Short-Term Forecast")
            for period in nws[:8]: # Show next 8 periods (4 days)
                with st.container():
                    st.markdown(f"**{period['name']}**")
                    idx = nws.index(period) // 2 
                    if idx < len(ecmwf['wind_gusts_10m_max']):
                        wind_gust = f"{ecmwf['wind_gusts_10m_max'][idx]:.0f} mph"
                    else:
                        wind_gust = "N/A"
                        
                    st.write(f"🌡️ {period['temperature']}°{period['temperatureUnit']} | 💨 Max Gust Est: {wind_gust}")
                    st.write(f"🌨️ {period['shortForecast']}")
                    st.caption(period['detailedForecast'])
                    st.markdown("---")
        else:
            st.warning("NWS text forecast is currently unavailable.")

    with col_stats:
        if ecmwf:
            st.markdown("#### Quick Wind & Temperature Extremes")
            max_gust = max(ecmwf['wind_gusts_10m_max'])
            st.metric("Max Gust Next 7 Days", f"{max_gust:.0f} mph")
            st.metric("Min Temperature Next 7 Days", f"{min(ecmwf['temperature_2m_min'][:7]):.0f}°F")
            st.metric("Max Temperature Next 7 Days", f"{max(ecmwf['temperature_2m_max'][:7]):.0f}°F")

# --- TAB 5: WNC WEBCAMS (New Tab) ---
with tab_webcams:
    st.markdown("### 🎥 WNC Live Webcams & Local Logistics")
    st.caption("Real-time views for travel, snow accumulation, and conditions in surrounding communities.")
    
    webcam_cols = st.columns(3)
    
    i = 0
    for name, link in WNC_WEBCAMS.items():
        with webcam_cols[i % 3]:
            st.markdown(f"**{name}**")
            st.link_button(f"View Live Camera", link, use_container_width=True)
            if "Airport" in name or "Downtown" in name:
                 st.caption("Traffic/Road Conditions")
            else:
                 st.caption("Scenic View/Local Accumulation")
            st.markdown("---")
        i += 1

# --- TAB 6: HISTORY (Keep as is) ---
with tab_history:
    st.markdown("### 📜 Historical Snow Data")
    st.caption(f"What happened on {datetime.now().strftime('%B %d')} in past years?")
    
    if history is not None and not history.empty:
        st.markdown(f"**Found {len(history)} snow events on this date in the last 10 years:**")
        
        history_sorted = history.sort_values('snowfall_sum', ascending=False)
        
        for idx, row in history_sorted.iterrows():
            year = row['time'].year
            amount = row['snowfall_sum']
            if amount > 0:
                st.markdown(f"❄️ **{year}**: {amount:.1f}\" of snow")
        
        if history['snowfall_sum'].sum() == 0:
            st.info("No significant snow recorded on this date in the past 10 years.")
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=history_sorted['time'].dt.year,
            y=history_sorted['snowfall_sum'],
            marker_color='#81D4FA'
        ))
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=300,
            title=f"Snow on {datetime.now().strftime('%B %d')} (Last 10 Years)",
            xaxis_title="Year",
            yaxis_title="Snowfall (inches)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data available for this date.")

# --- TAB 7: SEASONAL & ENTERTAINMENT (NEW) ---
with tab_entertainment:
    st.markdown("### ✨ Seasonal & Special Interest")

    # Biltmore Winter Garden Link
    st.markdown("#### 🌺 Biltmore Estate - Winter Garden View")
    st.link_button(
        "LOOK INSIDE BILTMORE'S WINTER GARDEN (Video/Tour)", 
        BILTMORE_WINTER_GARDEN_LINK,
        use_container_width=True
    )
    st.caption("A seasonal link for a warm virtual break.")

    st.markdown("---")
    
    # NORAD Santa Tracker
    st.markdown("#### 🎅 NORAD Santa Tracker")
    st.link_button(
        "TRACK SANTA'S LOCATION (NORAD)", 
        NORAD_SANTA_LINK,
        use_container_width=True
    )
    st.caption("Available seasonally in December.")

# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF Model")
st.caption("PAWIS 1.0 | Stable Forecasting with Thermal & Wind Intelligence")