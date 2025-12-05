import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import json

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"
LAT_MTN = 35.5845
LON_MTN = -83.0620
MTN_NAME = "Mountain Top (4800')"

st.set_page_config(
    page_title="Stephanie's Snow Forecaster: Bonnie Lane Edition", 
    page_icon="❄️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ENHANCED CSS ---
st.markdown("""
<style>
    /* 1. Main Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.8)), 
                          url('https://images.unsplash.com/photo-1516431883744-dc60fa69f927?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }
    
    /* 2. Glass Cards */
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
    
    /* 3. Metric Boxes */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
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
    .alert-blue { background-color: #1976D2; border-left: 10px solid #90CAF9; }
    
    /* 5. Headers & Images */
    img { border: 2px solid #a6c9ff; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #e0f7fa !important; }
    
    /* 6. Clean Divider */
    hr { margin-top: 5px; margin-bottom: 5px; border-color: #444; }
    
    /* 7. Progress Bar */
    .snow-progress {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        height: 30px;
        position: relative;
        overflow: hidden;
        margin: 10px 0;
    }
    .snow-progress-fill {
        background: linear-gradient(90deg, #4fc3f7, #81d4fa);
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
    }
    
    /* 8. Status Indicators */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-ok { background-color: #4caf50; }
    .status-error { background-color: #f44336; }
    .status-loading { background-color: #ff9800; }
    
    /* 9. Snow Probability Badge */
    .snow-prob {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .prob-high { background-color: #1976D2; }
    .prob-med { background-color: #FFA726; }
    .prob-low { background-color: #66BB6A; }
    
    /* 10. Comparison Table */
    .compare-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    .compare-table th {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 10px;
        text-align: left;
        border-bottom: 2px solid rgba(255, 255, 255, 0.3);
    }
    .compare-table td {
        padding: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .snow-day { background-color: rgba(33, 150, 243, 0.2); }
    
    /* 11. Mobile Optimization */
    @media (max-width: 768px) {
        .stApp { background-attachment: scroll; }
        .glass-card { padding: 15px; }
        h1 { font-size: 1.5em !important; }
        h2 { font-size: 1.3em !important; }
    }
    
    /* 12. Interactive elements */
    .clickable-card {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .clickable-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- INITIALIZE SESSION STATE ---
if 'favorite_locations' not in st.session_state:
    st.session_state.favorite_locations = [
        {"name": "Webster Valley", "lat": LAT, "lon": LON},
        {"name": "Mountain Top", "lat": LAT_MTN, "lon": LON_MTN}
    ]

if 'snow_alerts_enabled' not in st.session_state:
    st.session_state.snow_alerts_enabled = True

if 'alert_threshold' not in st.session_state:
    st.session_state.alert_threshold = 2.0  # inches

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://64.media.tumblr.com/f722ffb4624171f3ab2e727913e93ae2/tumblr_p14oecN2Wx1ro8ysbo1_500.gif", 
             caption="Bonnie Lane Snow Patrol")
    
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!", use_container_width=True): 
        st.snow()
    if st.button("🔄 Force Refresh", use_container_width=True): 
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    
    # Alert threshold
    st.session_state.alert_threshold = st.slider(
        "Snow Alert Threshold (inches)",
        min_value=0.5,
        max_value=6.0,
        value=st.session_state.alert_threshold,
        step=0.5,
        help="Get notified when forecasted snow exceeds this amount"
    )
    
    # Temperature units
    temp_unit = st.radio("Temperature Units", ["°F", "°C"], index=0)
    
    # Show/hide features
    show_hourly = st.checkbox("Show Hourly Forecast", value=True)
    show_comparison = st.checkbox("Show Valley vs Mountain", value=True)
    
    st.markdown("---")
    
    # System Status
    st.markdown("### 📊 System Status")
    status_container = st.empty()
    
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")
    st.caption("Auto-refresh: 5 min")

# --- HEADER ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("❄️ Stephanie's Snow Forecaster")
    st.markdown("#### *Bonnie Lane Edition*") 
    st.caption(f"Webster, NC Radar & Intelligence | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
system_status = {
    "nws_alerts": "loading", 
    "nws_forecast": "loading", 
    "euro_model": "loading", 
    "history": "loading",
    "hourly": "loading"
}

@st.cache_data(ttl=300)
def get_nws_alerts():
    try:
        url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        r = requests.get(url, headers={'User-Agent': '(webster_snow_app, contact@example.com)'}, timeout=10)
        r.raise_for_status()
        return r.json().get('features', []), True
    except Exception as e:
        return [], False

@st.cache_data(ttl=900)
def get_nws_text():
    try:
        r = requests.get(f"https://api.weather.gov/points/{LAT},{LON}", 
                        headers={'User-Agent': '(webster_snow_app, contact@example.com)'}, timeout=10)
        r.raise_for_status()
        data = r.json()
        grid_id, x, y = data['properties']['gridId'], data['properties']['gridX'], data['properties']['gridY']
        f = requests.get(f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast", 
                        headers={'User-Agent': '(webster_snow_app, contact@example.com)'}, timeout=10)
        f.raise_for_status()
        return f.json()['properties']['periods'], True
    except Exception as e:
        return [], False

@st.cache_data(ttl=1800)
def get_hourly_forecast(target_lat, target_lon):
    """Get hourly forecast including temperature, precipitation, and snow"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": target_lat, 
            "longitude": target_lon,
            "hourly": [
                "temperature_2m", 
                "precipitation", 
                "snowfall",
                "precipitation_probability",
                "weather_code",
                "cloud_cover"
            ],
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
            "forecast_days": 3
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get('hourly', None), True
    except Exception as e:
        return None, False

@st.cache_data(ttl=3600)
def get_daily_forecast(target_lat, target_lon):
    """Get daily forecast with enhanced details"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": target_lat, 
            "longitude": target_lon, 
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "snowfall_sum", 
                "precipitation_sum",
                "precipitation_probability_max",
                "weather_code",
                "wind_speed_10m_max"
            ], 
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "America/New_York"
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get('daily', None), True
    except Exception as e:
        return None, False

@st.cache_data(ttl=3600)
def get_season_accumulation():
    """Get current winter season accumulation (Nov 1 - Apr 30)"""
    try:
        today = datetime.now()
        if today.month >= 11:
            season_start = datetime(today.year, 11, 1)
        else:
            season_start = datetime(today.year - 1, 11, 1)
        
        start_date = season_start.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "start_date": start_date, 
            "end_date": end_date,
            "daily": "snowfall_sum", 
            "timezone": "America/New_York", 
            "precipitation_unit": "inch"
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json()['daily'])
        total = df['snowfall_sum'].sum()
        days_with_snow = len(df[df['snowfall_sum'] > 0])
        max_daily = df['snowfall_sum'].max()
        
        return {
            'total': total,
            'days_with_snow': days_with_snow,
            'max_daily': max_daily,
            'data': df
        }, True
    except Exception as e:
        return {'total': 0, 'days_with_snow': 0, 'max_daily': 0}, False

@st.cache_data(ttl=86400)
def get_history_facts():
    """Get 10-year historical data"""
    try:
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
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json()['daily'])
        df['time'] = pd.to_datetime(df['time'])
        return df, True
    except Exception as e:
        return None, False

@st.cache_data(ttl=86400)
def get_seasonal_stats():
    """Get comprehensive seasonal statistics"""
    try:
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
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json()['daily'])
        df['time'] = pd.to_datetime(df['time'])
        df['year'] = df['time'].dt.year
        df['month'] = df['time'].dt.month
        
        # Calculate seasonal totals
        df['season'] = df.apply(lambda x: x['year'] if x['month'] < 7 else x['year'] + 1, axis=1)
        seasonal = df[(df['month'] >= 11) | (df['month'] <= 4)].groupby('season')['snowfall_sum'].sum()
        
        avg_seasonal = seasonal.mean()
        max_seasonal = seasonal.max()
        min_seasonal = seasonal.min()
        
        # Snow days per season
        snow_days = df[df['snowfall_sum'] > 0].copy()
        days_per_season = snow_days.groupby('season').size().mean()
        
        # Find first and last snow dates
        snow_days['doy'] = snow_days['time'].dt.dayofyear
        snow_days['adjusted_doy'] = snow_days.apply(
            lambda x: x['doy'] if x['month'] <= 6 else x['doy'] - 365, axis=1
        )
        
        first_snow_avg = snow_days['adjusted_doy'].quantile(0.25)
        last_snow_avg = snow_days['adjusted_doy'].quantile(0.75)
        
        # Biggest snowstorm in 10 years
        max_storm = df.loc[df['snowfall_sum'].idxmax()]
        
        return {
            'avg_seasonal': avg_seasonal,
            'max_seasonal': max_seasonal,
            'min_seasonal': min_seasonal,
            'avg_snow_days': days_per_season,
            'first_snow_doy': first_snow_avg,
            'last_snow_doy': last_snow_avg,
            'biggest_storm': {
                'date': max_storm['time'],
                'amount': max_storm['snowfall_sum']
            }
        }, True
    except Exception as e:
        return None, False

def get_weather_emoji(code):
    """Convert weather code to emoji"""
    if code in [71, 73, 75, 77, 85, 86]:  # Snow
        return "❄️"
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:  # Rain
        return "🌧️"
    elif code in [95, 96, 99]:  # Thunderstorm
        return "⛈️"
    elif code in [1, 2, 3]:  # Partly cloudy
        return "⛅"
    elif code == 0:  # Clear
        return "☀️"
    else:
        return "☁️"

# --- FETCH ALL DATA ---
with st.spinner("Loading weather intelligence..."):
    alerts, alerts_ok = get_nws_alerts()
    nws, nws_ok = get_nws_text()
    
    # Fetch both valley and mountain forecasts
    euro_valley, euro_valley_ok = get_daily_forecast(LAT, LON)
    euro_mtn, euro_mtn_ok = get_daily_forecast(LAT_MTN, LON_MTN)
    
    # Hourly forecasts
    hourly_valley, hourly_valley_ok = get_hourly_forecast(LAT, LON)
    hourly_mtn, hourly_mtn_ok = get_hourly_forecast(LAT_MTN, LON_MTN)
    
    # Historical data
    season_data, season_ok = get_season_accumulation()
    seasonal_stats, stats_ok = get_seasonal_stats()
    hist_data, hist_ok = get_history_facts()

# Update status
system_status['nws_alerts'] = 'ok' if alerts_ok else 'error'
system_status['nws_forecast'] = 'ok' if nws_ok else 'error'
system_status['euro_model'] = 'ok' if (euro_valley_ok and euro_mtn_ok) else 'error'
system_status['hourly'] = 'ok' if (hourly_valley_ok and hourly_mtn_ok) else 'error'
system_status['history'] = 'ok' if (season_ok and stats_ok) else 'error'

# Display status in sidebar
with status_container:
    for service, status in system_status.items():
        dot_class = 'status-ok' if status == 'ok' else 'status-error'
        service_name = service.replace("_", " ").title()
        st.markdown(f'<span class="status-dot {dot_class}"></span> {service_name}', 
                   unsafe_allow_html=True)

# --- CHECK FOR SNOW ALERTS ---
snow_alert_days = []
if euro_valley_ok and euro_valley:
    for i in range(min(3, len(euro_valley['time']))):
        snow_amt = euro_valley['snowfall_sum'][i]
        if snow_amt >= st.session_state.alert_threshold:
            day_date = pd.to_datetime(euro_valley['time'][i])
            snow_alert_days.append({
                'date': day_date,
                'amount': snow_amt,
                'day_name': day_date.strftime('%A')
            })

# Display snow alert banner
if snow_alert_days and st.session_state.snow_alerts_enabled:
    st.markdown(f"""
    <div class="alert-box alert-blue">
        <h3>❄️ SNOW ALERT: {len(snow_alert_days)} Day(s) Above {st.session_state.alert_threshold}" Threshold</h3>
        <p>{'• '.join([f"<strong>{d['day_name']}</strong>: {d['amount']:.1f}\" forecasted" for d in snow_alert_days])}</p>
    </div>
    """, unsafe_allow_html=True)

# --- NWS ALERT BANNER ---
if alerts:
    for alert in alerts:
        props = alert['properties']
        event = props['event']
        description = props.get('description', 'No details available')
        css_class = "alert-orange"
        if "Warning" in event: 
            css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: 
            css_class = "alert-purple"
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props.get('headline', '')}</p>
            <details><summary>Read Full Details</summary><p style="font-size:0.9em;">{description}</p></details>
        </div>
        """, unsafe_allow_html=True)

# --- SEASON TRACKER BANNER ---
if seasonal_stats and season_ok:
    avg_seasonal = seasonal_stats['avg_seasonal']
    season_total = season_data['total']
    percent_of_avg = (season_total / avg_seasonal * 100) if avg_seasonal > 0 else 0
    
    days_into_season = (datetime.now() - datetime(datetime.now().year if datetime.now().month >= 11 else datetime.now().year - 1, 11, 1)).days
    
    st.markdown(f"""
    <div class="glass-card">
        <h3>❄️ 2024-2025 Season Tracker ({days_into_season} days in)</h3>
        <p><strong>{season_total:.1f}"</strong> so far | Average: <strong>{avg_seasonal:.1f}"</strong> | Record: <strong>{seasonal_stats['max_seasonal']:.1f}"</strong> | Snow Days: <strong>{season_data['days_with_snow']}</strong> | Biggest Storm: <strong>{season_data['max_daily']:.1f}"</strong></p>
        <div class="snow-progress">
            <div class="snow-progress-fill" style="width: {min(percent_of_avg, 100):.0f}%">
                {percent_of_avg:.0f}% of Average
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN TABS ---
tab_overview, tab_hourly, tab_forecast, tab_comparison, tab_radar, tab_webcams, tab_cartier, tab_movie, tab_santa, tab_history, tab_export = st.tabs([
    "🏠 Overview", 
    "⏰ Hourly", 
    "📅 7-Day", 
    "⚖️ Compare",
    "📡 Radar", 
    "🎥 Webcams",
    "🐕 Cartier",
    "🎬 Movie",
    "🎅 Santa",
    "📜 History",
    "💾 Export"
])

# --- TAB 1: OVERVIEW ---
with tab_overview:
    st.subheader("Quick Snapshot")
    
    # Current conditions
    col1, col2, col3, col4 = st.columns(4)
    
    if nws_ok and nws:
        current = nws[0]
        col1.metric(
            "Current Temp", 
            f"{current.get('temperature', 'N/A')}°{current.get('temperatureUnit', 'F')}"
        )
        col2.metric(
            "Wind", 
            f"{current.get('windSpeed', 'N/A')}"
        )
        col3.metric(
            "Conditions",
            current.get('shortForecast', 'N/A')
        )
    
    if euro_valley_ok and euro_valley:
        next_7_days_snow = sum(euro_valley['snowfall_sum'][:7])
        col4.metric(
            "7-Day Snow Total",
            f"{next_7_days_snow:.1f}\""
        )
    
    st.markdown("---")
    
    # Next 48 hours visualization
    if hourly_valley_ok and hourly_valley and show_hourly:
        st.markdown("### 📊 Next 48 Hours (Valley)")
        
        hourly_df = pd.DataFrame(hourly_valley)
        hourly_df['time'] = pd.to_datetime(hourly_df['time'])
        hourly_df_48 = hourly_df.head(48)
        
        # Create subplot with temp and snow
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Temperature & Precipitation Probability", "Snowfall Accumulation"),
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
            vertical_spacing=0.15,
            row_heights=[0.5, 0.5]
        )
        
        # Temperature line
        fig.add_trace(
            go.Scatter(
                x=hourly_df_48['time'], 
                y=hourly_df_48['temperature_2m'],
                name="Temperature",
                line=dict(color='#FF6B6B', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.1)'
            ),
            row=1, col=1, secondary_y=False
        )
        
        # Precipitation probability
        fig.add_trace(
            go.Scatter(
                x=hourly_df_48['time'],
                y=hourly_df_48['precipitation_probability'],
                name="Precip %",
                line=dict(color='#4ECDC4', width=2, dash='dot')
            ),
            row=1, col=1, secondary_y=True
        )
        
        # Snowfall bars
        fig.add_trace(
            go.Bar(
                x=hourly_df_48['time'],
                y=hourly_df_48['snowfall'],
                name="Snowfall",
                marker_color='#95E1D3'
            ),
            row=2, col=1
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Temperature (°F)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Probability (%)", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Snow (inches)", row=2, col=1)
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Next 3 days quick view
    st.markdown("### 🔮 Next 3 Days")
    
    if euro_valley_ok and euro_valley:
        cols = st.columns(3)
        for i in range(min(3, len(euro_valley['time']))):
            day_date = pd.to_datetime(euro_valley['time'][i])
            with cols[i]:
                snow_amt = euro_valley['snowfall_sum'][i]
                temp_max = euro_valley['temperature_2m_max'][i]
                temp_min = euro_valley['temperature_2m_min'][i]
                weather_code = euro_valley['weather_code'][i]
                emoji = get_weather_emoji(weather_code)
                
                st.markdown(f"### {emoji} {day_date.strftime('%A')}")
                st.caption(day_date.strftime('%b %d'))
                
                if snow_amt > 0:
                    st.markdown(f"### ❄️ {snow_amt:.1f}\"")
                else:
                    st.markdown(f"### 0\"")
                
                st.write(f"↑ {temp_max:.0f}°F  ↓ {temp_min:.0f}°F")

# --- TAB 2: HOURLY FORECAST ---
with tab_hourly:
    if show_hourly and hourly_valley_ok and hourly_valley:
        st.subheader("⏰ Hourly Forecast - Next 72 Hours")
        
        # Location selector
        location_choice = st.radio("Location", ["🏠 Valley (Webster)", "⛰️ Mountain Top"], horizontal=True)
        
        hourly_data = hourly_valley if location_choice == "🏠 Valley (Webster)" else hourly_mtn
        
        if hourly_data:
            hourly_df = pd.DataFrame(hourly_data)
            hourly_df['time'] = pd.to_datetime(hourly_df['time'])
            hourly_df['hour'] = hourly_df['time'].dt.strftime('%a %I%p')
            
            # Display table
            st.markdown("#### Detailed Hourly Breakdown")
            
            display_df = hourly_df[['hour', 'temperature_2m', 'precipitation_probability', 'snowfall', 'precipitation']].copy()
            display_df.columns = ['Time', 'Temp (°F)', 'Precip %', 'Snow (in)', 'Rain (in)']
            display_df = display_df.head(72)
            
            # Highlight snow hours
            def highlight_snow(row):
                if row['Snow (in)'] > 0:
                    return ['background-color: rgba(33, 150, 243, 0.2)'] * len(row)
                return [''] * len(row)
            
            styled_df = display_df.style.apply(highlight_snow, axis=1).format({
                'Temp (°F)': '{:.0f}',
                'Precip %': '{:.0f}',
                'Snow (in)': '{:.2f}',
                'Rain (in)': '{:.2f}'
            })
            
            st.dataframe(styled_df, use_container_width=True, height=600)
    else:
        st.info("Enable 'Show Hourly Forecast' in sidebar settings to view this data.")

# --- TAB 3: 7-DAY FORECAST ---
with tab_forecast:
    st.subheader("📅 7-Day Snow Outlook (ECMWF Model)")
    
    # Location selector
    forecast_location = st.radio("View Forecast For:", ["🏠 Valley (Webster)", "⛰️ Mountain Top"], horizontal=True, key="forecast_loc")
    
    euro_data = euro_valley if forecast_location == "🏠 Valley (Webster)" else euro_mtn
    euro_ok = euro_valley_ok if forecast_location == "🏠 Valley (Webster)" else euro_mtn_ok
    
    if euro_ok and euro_data:
        # Create detailed forecast cards
        total_snow = 0
        
        for i in range(len(euro_data['time'])):
            day_date = pd.to_datetime(euro_data['time'][i])
            day_name = day_date.strftime('%A')
            short_date = day_date.strftime('%b %d, %Y')
            
            snow_amt = euro_data['snowfall_sum'][i]
            precip_amt = euro_data['precipitation_sum'][i]
            temp_max = euro_data['temperature_2m_max'][i]
            temp_min = euro_data['temperature_2m_min'][i]
            prob = euro_data['precipitation_probability_max'][i]
            wind = euro_data['wind_speed_10m_max'][i]
            weather_code = euro_data['weather_code'][i]
            
            total_snow += snow_amt
            
            emoji = get_weather_emoji(weather_code)
            
            # Determine if this is a snow day
            is_snow_day = snow_amt > 0
            card_class = "glass-card snow-day" if is_snow_day else "glass-card"
            
            with st.container():
                st.markdown(f"""
                <div class="{card_class}">
                    <h3>{emoji} {day_name} - {short_date}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3, c4, c5 = st.columns(5)
                
                if is_snow_day:
                    c1.metric("❄️ Snow", f"{snow_amt:.1f}\"", delta=None)
                else:
                    c1.metric("Snow", "0\"")
                
                c2.metric("🌡️ High/Low", f"{temp_max:.0f}° / {temp_min:.0f}°")
                c3.metric("💧 Total Precip", f"{precip_amt:.2f}\"")
                c4.metric("☔ Probability", f"{prob:.0f}%")
                c5.metric("💨 Wind", f"{wind:.0f} mph")
        
        st.markdown("---")
        st.markdown(f"### Total 7-Day Snow: **{total_snow:.1f}\"**")
        
        # Add NWS text forecast
        st.markdown("---")
        st.markdown("### 🇺🇸 National Weather Service Text Forecast")
        
        if nws_ok and nws:
            for p in nws[:5]:
                with st.expander(f"{p['name']} - {p.get('temperature', 'N/A')}°{p.get('temperatureUnit', 'F')}"):
                    st.write(p['detailedForecast'])
        else:
            st.error("❌ NWS forecast unavailable")
    else:
        st.error("❌ Unable to load forecast data")

# --- TAB 4: VALLEY VS MOUNTAIN COMPARISON ---
with tab_comparison:
    if show_comparison and euro_valley_ok and euro_mtn_ok:
        st.subheader("⚖️ Valley vs Mountain Comparison")
        st.caption(f"Valley: {LOCATION_NAME} ({LAT:.4f}, {LON:.4f}) | Mountain: {MTN_NAME} ({LAT_MTN:.4f}, {LON_MTN:.4f})")
        
        # Summary metrics
        valley_total = sum(euro_valley['snowfall_sum'][:7])
        mtn_total = sum(euro_mtn['snowfall_sum'][:7])
        difference = mtn_total - valley_total
        
        m1, m2, m3 = st.columns(3)
        m1.metric("🏠 Valley Total (7-day)", f"{valley_total:.1f}\"")
        m2.metric("⛰️ Mountain Total (7-day)", f"{mtn_total:.1f}\"")
        m3.metric("📊 Difference", f"{difference:.1f}\"", delta=f"{(difference/valley_total*100):.0f}% more" if valley_total > 0 else "N/A")
        
        st.markdown("---")
        
        # Side-by-side comparison table
        st.markdown("### Daily Comparison")
        
        comparison_data = []
        for i in range(len(euro_valley['time'])):
            day_date = pd.to_datetime(euro_valley['time'][i])
            comparison_data.append({
                'Date': day_date.strftime('%a %b %d'),
                'Valley Snow': f"{euro_valley['snowfall_sum'][i]:.1f}\"",
                'Mountain Snow': f"{euro_mtn['snowfall_sum'][i]:.1f}\"",
                'Difference': f"{euro_mtn['snowfall_sum'][i] - euro_valley['snowfall_sum'][i]:.1f}\"",
                'Valley Temp': f"{euro_valley['temperature_2m_max'][i]:.0f}° / {euro_valley['temperature_2m_min'][i]:.0f}°",
                'Mountain Temp': f"{euro_mtn['temperature_2m_max'][i]:.0f}° / {euro_mtn['temperature_2m_min'][i]:.0f}°"
            })
        
        comp_df = pd.DataFrame(comparison_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        
        # Visualization
        st.markdown("---")
        st.markdown("### 📊 Visual Comparison")
        
        fig = go.Figure()
        
        dates = [pd.to_datetime(d).strftime('%a %m/%d') for d in euro_valley['time']]
        
        fig.add_trace(go.Bar(
            name='🏠 Valley',
            x=dates,
            y=euro_valley['snowfall_sum'],
            marker_color='#4FC3F7'
        ))
        
        fig.add_trace(go.Bar(
            name='⛰️ Mountain',
            x=dates,
            y=euro_mtn['snowfall_sum'],
            marker_color='#0288D1'
        ))
        
        fig.update_layout(
            barmode='group',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            yaxis_title="Snowfall (inches)",
            xaxis_title="Date",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Enable 'Show Valley vs Mountain' in sidebar settings to view comparison.")

# --- TAB 5: RADAR ---
with tab_radar:
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown("### 📡 Live Doppler Radar")
        st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
                 caption=f"KGSP Radar | Updated: {nc_time.strftime('%I:%M %p')}", 
                 use_container_width=True)
        st.caption("🔄 Auto-refreshes every 5 minutes")
        
        # Add radar legend
        with st.expander("📖 Radar Legend"):
            st.markdown("""
            - **Green**: Light precipitation
            - **Yellow**: Moderate precipitation  
            - **Red**: Heavy precipitation
            - **Pink/Purple**: Very heavy precipitation or hail
            - **Blue**: Snow (when temperatures are freezing)
            """)
    
    with col_right:
        st.markdown("### 🎯 Radar Stats")
        
        if hourly_valley_ok and hourly_valley:
            hourly_df = pd.DataFrame(hourly_valley)
            next_6h = hourly_df.head(6)
            
            precip_next_6h = next_6h['precipitation'].sum()
            snow_next_6h = next_6h['snowfall'].sum()
            max_prob = next_6h['precipitation_probability'].max()
            
            st.metric("Next 6 Hours - Precip", f"{precip_next_6h:.2f}\"")
            st.metric("Next 6 Hours - Snow", f"{snow_next_6h:.2f}\"")
            st.metric("Max Probability", f"{max_prob:.0f}%")
        
        st.markdown("---")
        st.markdown("### 🌡️ Current Conditions")
        
        if nws_ok and nws:
            current = nws[0]
            st.write(f"**Temperature:** {current.get('temperature', 'N/A')}°{current.get('temperatureUnit', 'F')}")
            st.write(f"**Wind:** {current.get('windSpeed', 'N/A')} {current.get('windDirection', '')}")
            st.write(f"**Conditions:** {current.get('shortForecast', 'N/A')}")
            st.write(f"**Forecast:** {current.get('detailedForecast', 'N/A')}")

# --- TAB 6: WEBCAMS ---
with tab_webcams:
    st.subheader("🎥 Live Regional Webcams")
    st.caption("View current conditions from nearby cameras")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**🏞️ Silver Creek (Lake Glenville)**")
        st.caption("Closest webcam to Webster - ~15 miles")
        st.video("https://youtu.be/l_sNHKVUp2c", autoplay=False, muted=True)
        
    with c2:
        st.markdown("**⛷️ Sugar Mountain Resort**")
        st.caption("Regional mountain conditions - ~80 miles")
        st.video("https://www.youtube.com/watch?v=gIV_NX2dYow", autoplay=False, muted=True)
    
    st.markdown("---")
    st.info("💡 Tip: These webcams update continuously. Refresh the page to see the latest conditions.")

# --- TAB 7: CARTIER ---
with tab_cartier:
    st.markdown("""
    <div class="glass-card">
        <h2 style="text-align: center;">🐕 Cartier - Guardian of Bonnie Lane 🐕</h2>
        <p style="text-align: center; font-size: 1.1em;">The goodest boy watching over the snow!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the video
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.video("https://youtu.be/5I8KfuKgKsw?si=bDsNPL76JpcJFN6e", autoplay=False, loop=True)
    
    st.markdown("---")
    
    # Fun Cartier stats
    st.markdown("### 🦴 Cartier's Snow Stats")
    
    cartier_col1, cartier_col2, cartier_col3, cartier_col4 = st.columns(4)
    
    with cartier_col1:
        if season_ok and season_data:
            st.metric("🐾 Paw Prints in Snow", f"{season_data['days_with_snow'] * 100}+")
        else:
            st.metric("🐾 Paw Prints in Snow", "1000+")
    
    with cartier_col2:
        st.metric("❄️ Snowballs Chased", "∞")
    
    with cartier_col3:
        st.metric("⭐ Good Boy Rating", "15/10")
    
    with cartier_col4:
        if euro_valley_ok and euro_valley:
            next_snow = 0
            for i in range(len(euro_valley['time'])):
                if euro_valley['snowfall_sum'][i] > 0:
                    next_snow = i
                    break
            if next_snow == 0 and euro_valley['snowfall_sum'][0] > 0:
                st.metric("🎾 Next Play Day", "TODAY!")
            elif next_snow > 0:
                st.metric("🎾 Next Play Day", f"{next_snow} days")
            else:
                st.metric("🎾 Next Play Day", "Soon!")
        else:
            st.metric("🎾 Next Play Day", "Soon!")
    
    st.markdown("---")
    
    # Cartier weather preferences
    with st.expander("🐕 What Cartier Thinks About the Weather"):
        st.markdown("""
        **Cartier's Weather Guide:**
        
        - **0-2" of snow:** "Perfect for zoomies!" 🏃‍♂️
        - **2-4" of snow:** "Maximum snowball potential!" ⚾
        - **4-6" of snow:** "Deep snow adventures!" 🗻
        - **6"+ of snow:** "BEST DAY EVER!" 🎉
        - **No snow:** "Still a good day for walks!" 🦴
        
        **Fun Fact:** Cartier can detect incoming snow storms 24 hours in advance by getting extra playful!
        """)
    
    st.markdown("---")
    
    # Show if there's snow forecasted
    if euro_valley_ok and euro_valley:
        upcoming_snow_days = []
        for i in range(min(7, len(euro_valley['time']))):
            if euro_valley['snowfall_sum'][i] > 0:
                day_date = pd.to_datetime(euro_valley['time'][i])
                upcoming_snow_days.append({
                    'day': day_date.strftime('%A'),
                    'date': day_date.strftime('%b %d'),
                    'amount': euro_valley['snowfall_sum'][i]
                })
        
        if upcoming_snow_days:
            st.success(f"🎉 **Cartier Alert:** {len(upcoming_snow_days)} snow day(s) forecasted this week!")
            for snow_day in upcoming_snow_days:
                st.info(f"🐕 **{snow_day['day']}, {snow_day['date']}** - {snow_day['amount']:.1f}\" of playtime expected!")
        else:
            st.info("🐕 No snow in the 7-day forecast, but Cartier is still ready for adventures!")

# --- TAB 8: PRIVATE EYES MOVIE ---
with tab_movie:
    st.markdown("""
    <div class="glass-card">
        <h2 style="text-align: center;">🎬 Private Eyes (1980) 🏰</h2>
        <p style="text-align: center; font-size: 1.1em;">A comedy mystery filmed at the magnificent Biltmore Estate!</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Embed the movie
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.video("https://youtu.be/a5bNNkSj1O4?si=C5vB8yz9NLngjchp")
    
    st.markdown("---")
    
    # Movie info and Biltmore connection
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎥 Movie Info")
        st.markdown("""
        **Private Eyes** (1980)
        
        - **Starring:** Tim Conway, Don Knotts
        - **Director:** Lang Elliott
        - **Runtime:** 91 minutes
        - **Rating:** PG
        - **Location:** Filmed at Biltmore Estate, Asheville, NC
        
        Scotland Yard sends a bumbling pair to check on foul play at a mansion close to the house that inspired the Sherlock Holmes stories. The movie showcases the stunning Biltmore House throughout!
        """)
        
        st.markdown("### 🏰 Biltmore Estate Facts")
        st.markdown("""
        **America's Largest Home:**
        - **Built:** 1889-1895
        - **Rooms:** 250 (35 bedrooms, 43 bathrooms)
        - **Square Footage:** 178,926 sq ft
        - **Owner:** George Vanderbilt II
        - **Architect:** Richard Morris Hunt
        - **Distance from Webster:** ~50 miles
        
        The Biltmore Estate is a National Historic Landmark and remains the largest privately-owned house in the United States!
        """)
    
    with col2:
        st.markdown("### ❄️ Perfect Viewing Weather")
        
        if euro_valley_ok and euro_valley:
            # Find best movie-watching days (snowy days!)
            movie_days = []
            for i in range(min(7, len(euro_valley['time']))):
                if euro_valley['snowfall_sum'][i] > 0:
                    day_date = pd.to_datetime(euro_valley['time'][i])
                    movie_days.append({
                        'day': day_date.strftime('%A'),
                        'date': day_date.strftime('%b %d'),
                        'snow': euro_valley['snowfall_sum'][i]
                    })
            
            if movie_days:
                st.success(f"🎬 {len(movie_days)} perfect movie day(s) coming up!")
                for day in movie_days:
                    st.info(f"**{day['day']}, {day['date']}** - {day['snow']:.1f}\" ❄️")
            else:
                st.info("Any day is a good day for Private Eyes!")
        else:
            st.info("Any day is a good day for Private Eyes!")
        
        st.markdown("---")
        st.markdown("### 🎄 Biltmore at Christmas")
        st.markdown("""
        The Biltmore Estate transforms into a winter wonderland during the holidays:
        
        - 🎄 **55+ Christmas trees** throughout the house
        - 🕯️ **Thousands of lights** illuminate the estate
        - 🎵 **Live music** and holiday events
        - ❄️ **Winter in the gardens** - stunning even in snow
        - 🍷 **Biltmore Winery** open year-round
        
        **Pro Tip:** The estate is especially magical after a fresh snowfall - just like Webster!
        """)
    
    st.markdown("---")
    
    # Biltmore Trivia
    with st.expander("🏰 Biltmore House Trivia & Fun Facts"):
        st.markdown("""
        **Did You Know?**
        
        📍 **Location Connection:**
        - Biltmore is only ~50 miles from Webster, NC on Bonnie Lane!
        - Both areas get beautiful mountain snowfall in winter
        - Perfect day trip destination from your location
        
        🎬 **Movies Filmed at Biltmore:**
        - *Private Eyes* (1980) - Tim Conway & Don Knotts
        - *The Last of the Mohicans* (1992) - Daniel Day-Lewis
        - *Forrest Gump* (1994) - Some scenes
        - *Richie Rich* (1994) - Macaulay Culkin
        - *Hannibal* (2001) - Anthony Hopkins
        
        🏗️ **Construction Facts:**
        - Took **6 years** to build (1889-1895)
        - Required **1,000+ workers** at peak construction
        - Used **millions of bricks** made on-site
        - Features a **70,000-gallon indoor swimming pool**
        - Has its own **bowling alley** in the basement
        
        🌲 **The Grounds:**
        - **8,000 acres** of estate (originally 125,000!)
        - Landscaped by **Frederick Law Olmsted** (designer of Central Park)
        - Estate includes working farm, winery, and gardens
        
        💰 **Cost:**
        - Original construction cost: **$6 million** (1895)
        - Equivalent to about **$200+ million today**
        
        👻 **Ghost Stories:**
        - Many visitors report paranormal experiences
        - George Vanderbilt's presence allegedly felt in the library
        - The pool area has numerous ghost sightings
        
        🎄 **Christmas Tradition:**
        - Biltmore's Christmas celebration tradition started in **1895**
        - George Vanderbilt opened the house to friends and family on Christmas Eve 1895
        - Today's Christmas at Biltmore attracts **thousands of visitors**
        """)
    
    st.markdown("---")
    st.info("🚗 **Local Tip:** When there's snow in Webster, there's likely snow at Biltmore too - making it even more spectacular to visit!")

# --- TAB 9: SANTA TRACKER ---
with tab_santa:
    st.subheader("🎅 NORAD Santa Tracker")
    st.caption("Track Santa's journey around the world on Christmas Eve!")
    
    # Check if it's close to Christmas
    today = datetime.now()
    christmas = datetime(today.year, 12, 25)
    days_until_christmas = (christmas - today).days
    
    if days_until_christmas > 0:
        st.info(f"🎄 **{days_until_christmas} days until Christmas!** Santa will begin his journey on Christmas Eve (December 24th).")
    elif days_until_christmas == 0:
        st.success("🎅 **It's Christmas Day!** Check if Santa visited Webster last night!")
    else:
        days_since_christmas = abs(days_until_christmas)
        st.info(f"🎄 Christmas was {days_since_christmas} days ago. Santa tracker will be active again next December 24th!")
    
    # Add some festive stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🎁 Days to Christmas", f"{max(0, days_until_christmas)}")
    
    with col2:
        if euro_valley_ok and euro_valley:
            # Check if there's snow in the Christmas forecast
            christmas_snow = 0
            for i in range(len(euro_valley['time'])):
                forecast_date = pd.to_datetime(euro_valley['time'][i])
                if forecast_date.month == 12 and forecast_date.day == 25:
                    christmas_snow = euro_valley['snowfall_sum'][i]
                    break
            st.metric("❄️ Christmas Snow Forecast", f"{christmas_snow:.1f}\"")
        else:
            st.metric("❄️ Christmas Snow", "Loading...")
    
    with col3:
        # Show if we've had snow this season for a White Christmas potential
        if season_ok and season_data:
            st.metric("⛄ Snow Days This Season", season_data['days_with_snow'])
    
    st.markdown("---")
    
    # NORAD Santa Tracker iframe
    st.markdown("### 🌍 Live Santa Tracker")
    
    # Create the iframe embed
    st.components.v1.iframe(
        "https://www.noradsanta.org/en/map",
        height=800,
        scrolling=True
    )
    
    st.markdown("---")
    
    # Fun facts section
    with st.expander("🎅 Santa Tracker Fun Facts"):
        st.markdown("""
        **About NORAD Tracks Santa:**
        - NORAD (North American Aerospace Defense Command) has been tracking Santa since 1955
        - It started by accident when a department store misprinted a phone number, and kids called NORAD instead!
        - NORAD uses radar, satellites, Santa Cams, and fighter jets to track Santa
        - Santa travels at approximately 650 miles per SECOND to visit all children in one night
        - Santa's sleigh must be able to carry over 60,000 tons of toys
        
        **Webster, NC Snow History on Christmas:**
        - Check the History tab to see historical Christmas Day snowfall data!
        - White Christmases are magical in the mountains of North Carolina
        """)
    
    # Link to official site
    st.markdown("---")
    st.markdown("🔗 **Visit the official site:** [NORAD Tracks Santa](https://www.noradsanta.org/)")

# --- TAB 10: HISTORY ---
with tab_history:
    st.subheader("📜 Historical Snowfall Analysis")
    
    if hist_ok and hist_data is not None and not hist_data.empty:
        # Today in history
        today_md = datetime.now().strftime('%m-%d')
        hist_data['md'] = hist_data['time'].dt.strftime('%m-%d')
        today_hist = hist_data[hist_data['md'] == today_md]
        
        if not today_hist.empty:
            st.markdown(f"### 📅 On {datetime.now().strftime('%B %d')} in History (Last 10 Years)")
            
            max_snow = today_hist['snowfall_sum'].max()
            snowy_years = len(today_hist[today_hist['snowfall_sum'] > 0])
            avg_snow = today_hist['snowfall_sum'].mean()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Record Snow", f"{max_snow:.1f}\"")
            m2.metric("Years w/ Snow", f"{snowy_years}/10")
            m3.metric("Average", f"{avg_snow:.2f}\"")
            
            # Bar chart
            fig = go.Figure(data=[go.Bar(
                x=today_hist['time'].dt.year, 
                y=today_hist['snowfall_sum'], 
                marker_color='#64B5F6',
                text=today_hist['snowfall_sum'].apply(lambda x: f"{x:.1f}\"" if x > 0 else ""),
                textposition='outside'
            )])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'), 
                height=300, 
                margin=dict(l=20,r=20,t=20,b=40),
                yaxis_title="Inches",
                xaxis_title="Year",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Seasonal statistics
        if stats_ok and seasonal_stats:
            st.markdown("### 📊 10-Year Seasonal Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Average Season", f"{seasonal_stats['avg_seasonal']:.1f}\"")
            col2.metric("Record Season", f"{seasonal_stats['max_seasonal']:.1f}\"")
            col3.metric("Minimum Season", f"{seasonal_stats['min_seasonal']:.1f}\"")
            col4.metric("Avg Snow Days", f"{seasonal_stats['avg_snow_days']:.0f}")
            
            st.markdown("---")
            
            # Biggest snowstorm
            biggest = seasonal_stats['biggest_storm']
            st.markdown(f"### 🏆 Biggest Snowstorm in 10 Years")
            st.markdown(f"**{biggest['date'].strftime('%B %d, %Y')}** - **{biggest['amount']:.1f}\" of snow**")
            
            st.markdown("---")
            
            # Monthly breakdown
            st.markdown("### 📈 Average Snowfall by Month (Winter Months)")
            
            hist_data['month'] = hist_data['time'].dt.month
            hist_data['month_name'] = hist_data['time'].dt.strftime('%B')
            monthly = hist_data.groupby(['month', 'month_name'])['snowfall_sum'].mean().reset_index()
            monthly = monthly.sort_values('month')
            
            winter_months = monthly[monthly['month'].isin([11, 12, 1, 2, 3, 4])]
            
            fig2 = go.Figure(data=[go.Bar(
                x=winter_months['month_name'],
                y=winter_months['snowfall_sum'],
                marker_color=['#90CAF9', '#64B5F6', '#42A5F5', '#2196F3', '#1E88E5', '#1976D2'],
                text=winter_months['snowfall_sum'].apply(lambda x: f"{x:.2f}\""),
                textposition='outside'
            )])
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=350,
                margin=dict(l=20,r=20,t=20,b=40),
                yaxis_title="Average Inches",
                xaxis_title="",
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Season-by-season breakdown
            st.markdown("---")
            st.markdown("### 📋 Season-by-Season Totals")
            
            hist_data['season'] = hist_data.apply(
                lambda x: x['time'].year if x['time'].month < 7 else x['time'].year + 1, 
                axis=1
            )
            seasonal_totals = hist_data[
                (hist_data['month'] >= 11) | (hist_data['month'] <= 4)
            ].groupby('season')['snowfall_sum'].sum().reset_index()
            seasonal_totals.columns = ['Season', 'Total Snowfall (inches)']
            seasonal_totals['Season'] = seasonal_totals['Season'].apply(lambda x: f"{x-1}-{x}")
            seasonal_totals = seasonal_totals.sort_values('Season', ascending=False)
            
            st.dataframe(
                seasonal_totals.style.format({'Total Snowfall (inches)': '{:.1f}'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("⚠️ Unable to load seasonal statistics")
    else:
        st.error("❌ Unable to load historical data")

# --- TAB 11: EXPORT ---
with tab_export:
    st.subheader("💾 Export Data & Reports")
    st.caption("Download forecasts and historical data for offline analysis")
    
    # Forecast export
    st.markdown("### 📊 Export Current Forecast")
    
    if euro_valley_ok and euro_valley:
        forecast_df = pd.DataFrame({
            'Date': [pd.to_datetime(d).strftime('%Y-%m-%d') for d in euro_valley['time']],
            'Day': [pd.to_datetime(d).strftime('%A') for d in euro_valley['time']],
            'Valley_Snow_inches': euro_valley['snowfall_sum'],
            'Valley_Temp_High': euro_valley['temperature_2m_max'],
            'Valley_Temp_Low': euro_valley['temperature_2m_min'],
            'Valley_Precip_inches': euro_valley['precipitation_sum'],
            'Valley_Precip_Probability': euro_valley['precipitation_probability_max']
        })
        
        if euro_mtn_ok and euro_mtn:
            forecast_df['Mountain_Snow_inches'] = euro_mtn['snowfall_sum']
            forecast_df['Mountain_Temp_High'] = euro_mtn['temperature_2m_max']
            forecast_df['Mountain_Temp_Low'] = euro_mtn['temperature_2m_min']
        
        csv_forecast = forecast_df.to_csv(index=False)
        st.download_button(
            label="📥 Download 7-Day Forecast (CSV)",
            data=csv_forecast,
            file_name=f"bonnie_lane_forecast_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Season data export
    st.markdown("### 📈 Export Season Data")
    
    if season_ok and season_data.get('data') is not None:
        season_df = season_data['data'].copy()
        season_df['time'] = pd.to_datetime(season_df['time']).dt.strftime('%Y-%m-%d')
        season_df.columns = ['Date', 'Snowfall_inches']
        
        csv_season = season_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Current Season Data (CSV)",
            data=csv_season,
            file_name=f"bonnie_lane_season_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # Summary report
    st.markdown("### 📄 Generate Summary Report")
    
    if st.button("Generate Text Report"):
        report = f"""
BONNIE LANE SNOW REPORT
Generated: {nc_time.strftime('%Y-%m-%d %I:%M %p %Z')}
Location: {LOCATION_NAME}

=== CURRENT SEASON (2024-2025) ===
Total Snowfall: {season_data['total']:.1f}"
Snow Days: {season_data['days_with_snow']}
Largest Storm: {season_data['max_daily']:.1f}"
Percent of Average: {(season_data['total']/seasonal_stats['avg_seasonal']*100):.0f}%

=== 7-DAY FORECAST ===
Valley Total: {sum(euro_valley['snowfall_sum'][:7]) if euro_valley_ok else 'N/A'}"
Mountain Total: {sum(euro_mtn['snowfall_sum'][:7]) if euro_mtn_ok else 'N/A'}"

=== DAILY BREAKDOWN ===
"""
        if euro_valley_ok and euro_valley:
            for i in range(min(7, len(euro_valley['time']))):
                day_date = pd.to_datetime(euro_valley['time'][i])
                snow = euro_valley['snowfall_sum'][i]
                report += f"{day_date.strftime('%A, %b %d')}: {snow:.1f}\" snow\n"
        
        report += f"""
=== HISTORICAL CONTEXT ===
10-Year Average Season: {seasonal_stats['avg_seasonal']:.1f}"
Record Season: {seasonal_stats['max_seasonal']:.1f}"
Biggest Storm: {seasonal_stats['biggest_storm']['amount']:.1f}" on {seasonal_stats['biggest_storm']['date'].strftime('%B %d, %Y')}

Data Sources: NWS, Open-Meteo ECMWF
"""
        
        st.download_button(
            label="📥 Download Report (TXT)",
            data=report,
            file_name=f"bonnie_lane_report_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
        
        with st.expander("Preview Report"):
            st.text(report)

# --- FOOTER ---
st.markdown("---")
col_f1, col_f2 = st.columns(2)

with col_f1:
    st.caption("**Data Sources:** National Weather Service (NOAA) • Open-Meteo ECMWF Model • Historical Archives")
    st.caption("**Disclaimer:** For informational purposes only. Not for safety-critical decisions.")

with col_f2:
    st.caption(f"**Made with ❄️ for Bonnie Lane**")
    st.caption(f"**Last Data Refresh:** {nc_time.strftime('%I:%M:%S %p %Z')}")

# Auto-refresh notice
st.info("💡 **Pro Tip:** This dashboard auto-refreshes data every 5-15 minutes depending on the source. Use the 'Force Refresh' button in the sidebar to update immediately.")
