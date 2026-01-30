import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import json

# --- CONFIGURATION ---
LAT = 35.351630
LON = -83.210029
LOCATION_NAME = "Webster, NC"
NCDOT_DIVISION = 14

st.set_page_config(page_title="Stephanie's Snow & Ice Forecaster", page_icon="❄️", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.8)), 
                          url('https://images.unsplash.com/photo-1516431883744-dc60fa69f927?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }
    
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
    
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }

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
    .alert-ice { background-color: #1565C0; border-left: 10px solid #90CAF9; }
    .alert-green { background-color: #2E7D32; border-left: 10px solid #A5D6A7; }
    
    img { border: 2px solid #a6c9ff; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #e0f7fa !important; }
    hr { margin-top: 5px; margin-bottom: 5px; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")

# --- HEADER ---
st.title("❄️🧊 Stephanie's Snow & Ice Forecaster")
st.markdown("#### *Bonnie Lane Edition - ECMWF Model + NCDOT + Duke Energy*")
st.caption(f"Webster, NC | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=300)
def get_nws_alerts():
    try:
        url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        r = requests.get(url, headers={'User-Agent': '(webster_app)'}, timeout=10).json()
        return r.get('features', [])
    except: return []

@st.cache_data(ttl=3600)
def get_euro_snow_ice():
    """Get ECMWF model forecast with hourly data"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        # Daily forecast
        params_daily = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": ["snowfall_sum", "rain_sum", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"], 
            "timezone": "America/New_York", 
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        daily_data = requests.get(url, params=params_daily, timeout=10).json().get('daily', None)
        
        # Hourly forecast
        params_hourly = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["temperature_2m", "precipitation", "rain", "snowfall", "weather_code", "apparent_temperature"],
            "timezone": "America/New_York",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "forecast_hours": 168
        }
        hourly_data = requests.get(url, params=params_hourly, timeout=10).json().get('hourly', None)
        
        return daily_data, hourly_data
    except Exception as e:
        st.error(f"Error fetching weather data: {e}")
        return None, None

def calculate_ice_accumulation(hourly_data):
    """Calculate ice accumulation from hourly data"""
    if not hourly_data:
        return {}
    
    ice_by_day = {}
    
    for i in range(len(hourly_data['time'])):
        dt = pd.to_datetime(hourly_data['time'][i])
        day_key = dt.strftime('%Y-%m-%d')
        
        temp = hourly_data['temperature_2m'][i]
        precip = hourly_data['precipitation'][i]
        snow = hourly_data['snowfall'][i]
        rain = hourly_data['rain'][i]
        
        # Ice occurs when liquid precip falls below freezing
        ice_potential = 0
        
        if temp < 32 and precip > 0:
            non_snow_precip = precip - snow
            
            if non_snow_precip > 0:
                if temp <= 20:
                    ice_potential = non_snow_precip * 0.9
                elif temp <= 28:
                    ice_potential = non_snow_precip * 0.85
                else:
                    ice_potential = non_snow_precip * 0.8
        
        if day_key not in ice_by_day:
            ice_by_day[day_key] = {
                'ice_accum': 0,
                'freezing_rain_hours': 0,
                'min_temp': temp,
                'max_temp': temp,
                'ice_risk': 'None'
            }
        
        ice_by_day[day_key]['ice_accum'] += ice_potential
        if ice_potential > 0:
            ice_by_day[day_key]['freezing_rain_hours'] += 1
        ice_by_day[day_key]['min_temp'] = min(ice_by_day[day_key]['min_temp'], temp)
        ice_by_day[day_key]['max_temp'] = max(ice_by_day[day_key]['max_temp'], temp)
    
    # Determine ice risk level
    for day in ice_by_day:
        ice_accum = ice_by_day[day]['ice_accum']
        if ice_accum >= 0.25:
            ice_by_day[day]['ice_risk'] = 'High'
        elif ice_accum >= 0.10:
            ice_by_day[day]['ice_risk'] = 'Moderate'
        elif ice_accum > 0:
            ice_by_day[day]['ice_risk'] = 'Low'
    
    return ice_by_day

def get_weather_description(code):
    """Convert weather code to description"""
    weather_codes = {
        0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Foggy", 48: "Rime Fog",
        51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
        61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
        71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
        77: "Snow Grains", 80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
        85: "Light Snow Showers", 86: "Snow Showers",
        95: "Thunderstorm", 96: "Thunderstorm w/ Hail", 99: "Heavy Thunderstorm w/ Hail"
    }
    return weather_codes.get(code, "Unknown")

# --- ALERT BANNER ---
alerts = get_nws_alerts()
if alerts:
    for alert in alerts[:3]:  # Limit to 3 most important
        props = alert['properties']
        event = props['event']
        
        css_class = "alert-orange"
        if "Warning" in event: css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: css_class = "alert-purple"
        
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- FETCH DATA ---
with st.spinner("Loading weather data..."):
    euro_daily, euro_hourly = get_euro_snow_ice()
    ice_data = calculate_ice_accumulation(euro_hourly)

# --- TABS ---
tab_forecast, tab_ice, tab_roads, tab_power, tab_radar = st.tabs([
    "❄️ Snow Forecast", 
    "🧊 Ice Analysis", 
    "🚗 Road Conditions",
    "⚡ Power Status",
    "📡 Radar"
])

# --- TAB 1: SNOW FORECAST ---
with tab_forecast:
    st.markdown("### ❄️ ECMWF Snow Forecast")
    
    if euro_daily and euro_hourly:
        # Calculate today's remaining snow (next 12-24 hours in current calendar day)
        now = pd.Timestamp.now(tz='US/Eastern')
        today_key = now.strftime('%Y-%m-%d')
        tomorrow_key = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        
        today_remaining_snow = 0
        for i in range(len(euro_hourly['time'])):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            if hour_dt >= now and hour_dt.strftime('%Y-%m-%d') == today_key:
                today_remaining_snow += euro_hourly['snowfall'][i]
        
        # Calculate 7-day total from hourly data for accuracy
        total_snow = sum([euro_hourly['snowfall'][i] for i in range(min(168, len(euro_hourly['snowfall'])))])  # 168 hours = 7 days
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rest of Today", f"{today_remaining_snow:.2f}\" snow", 
                     help="Snow expected for remainder of today")
        with col2:
            st.metric("Next 7 Days", f"{total_snow:.2f}\" snow",
                     help="Total snow over next week")
        with col3:
            # Time until next snow
            next_snow_time = None
            for i in range(len(euro_hourly['time'])):
                hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
                if hour_dt >= now and euro_hourly['snowfall'][i] > 0.01:
                    next_snow_time = hour_dt
                    break
            
            if next_snow_time:
                hours_until = int((next_snow_time - now).total_seconds() / 3600)
                if hours_until <= 0:
                    st.metric("Snow Status", "NOW", "❄️", help="Snow is falling or starting soon!")
                else:
                    st.metric("Snow Starts In", f"{hours_until}hr", "⏰", help=f"Expected at {next_snow_time.strftime('%I:%M %p')}")
            else:
                st.metric("Next Snow", "None expected", help="No snow in 7-day forecast")
        
        st.markdown("---")
        
        # HOURLY FORECAST - Next 12 Hours
        st.markdown("#### ⏰ Next 12 Hours - Detailed Forecast")
        
        now = pd.Timestamp.now(tz='US/Eastern')
        hourly_forecast = []
        
        for i in range(min(12, len(euro_hourly['time']))):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            
            # Skip if hour is in the past
            if hour_dt < now:
                continue
                
            temp = euro_hourly['temperature_2m'][i]
            feels_like = euro_hourly['apparent_temperature'][i]
            snow = euro_hourly['snowfall'][i]
            rain = euro_hourly['rain'][i]
            precip = euro_hourly['precipitation'][i]
            weather_code = euro_hourly.get('weather_code', [0] * len(euro_hourly['time']))[i]
            
            # Determine precipitation type
            if temp < 32 and precip > 0:
                if snow > 0:
                    precip_type = "❄️ Snow"
                    amount = f"{snow:.2f}\""
                elif rain > 0:
                    precip_type = "🧊 Freezing Rain"
                    amount = f"{rain:.2f}\""
                else:
                    precip_type = "🌨️ Mix"
                    amount = f"{precip:.2f}\""
            elif rain > 0:
                precip_type = "🌧️ Rain"
                amount = f"{rain:.2f}\""
            elif snow > 0:
                precip_type = "❄️ Snow"
                amount = f"{snow:.2f}\""
            else:
                precip_type = "—"
                amount = "—"
            
            conditions = get_weather_description(weather_code)
            
            hourly_forecast.append({
                'Time': hour_dt.strftime('%I %p'),
                'Temp': f"{temp:.0f}°F",
                'Feels Like': f"{feels_like:.0f}°F",
                'Conditions': conditions,
                'Precip Type': precip_type,
                'Amount': amount
            })
            
            if len(hourly_forecast) >= 12:
                break
        
        if hourly_forecast:
            df_hourly = pd.DataFrame(hourly_forecast)
            st.dataframe(df_hourly, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # DAILY BREAKDOWN - 7 Days (calculated from hourly data for accuracy)
        st.markdown("#### 📅 7-Day Daily Breakdown")
        st.caption("*Snow totals calculated from hourly forecast to show when snow actually falls*")
        
        # Calculate daily totals from hourly data
        daily_totals = {}
        for i in range(len(euro_hourly['time'])):
            hour_dt = pd.to_datetime(euro_hourly['time'][i], utc=True).tz_convert('US/Eastern')
            day_key = hour_dt.strftime('%Y-%m-%d')
            
            if day_key not in daily_totals:
                daily_totals[day_key] = {
                    'snow': 0,
                    'rain': 0,
                    'date': hour_dt.date()
                }
            
            daily_totals[day_key]['snow'] += euro_hourly['snowfall'][i]
            daily_totals[day_key]['rain'] += euro_hourly['rain'][i]
        
        daily_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            # Use hourly-calculated totals for accuracy
            snow = daily_totals.get(day_key, {}).get('snow', 0)
            
            temp_high = euro_daily['temperature_2m_max'][i]
            temp_low = euro_daily['temperature_2m_min'][i]
            
            # Snow indicator
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0.05:  # Lower threshold to catch light snow
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            # Add ice indicator
            ice_indicator = ""
            if day_key in ice_data and ice_data[day_key]['ice_accum'] > 0:
                ice_indicator = " 🧊"
            
            daily_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Snowfall': f"{snow:.2f}\"",
                'High': f"{temp_high:.0f}°F",
                'Low': f"{temp_low:.0f}°F",
                'Type': indicator + ice_indicator
            })
        
        df_daily = pd.DataFrame(daily_data)
        st.dataframe(df_daily, use_container_width=True, hide_index=True)
        
        st.info("💡 **Note:** Snow falling late tonight counts toward today's total, not tomorrow's. This matches the hourly forecast above.")
        
        st.markdown("---")
        
        # Visual Chart
        st.markdown("#### 📈 7-Day Snow Chart")
        
        fig = go.Figure()
        
        # Use hourly-calculated totals for the chart
        chart_dates = []
        chart_snow = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            snow_amount = daily_totals.get(day_key, {}).get('snow', 0)
            
            chart_dates.append(day_date.strftime('%a %m/%d'))
            chart_snow.append(snow_amount)
        
        fig.add_trace(go.Bar(
            x=chart_dates,
            y=chart_snow,
            marker_color='#4ECDC4',
            text=[f"{s:.1f}\"" for s in chart_snow],
            textposition='outside',
            name='Snow'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Expected Snowfall by Day (inches)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.error("❌ Unable to load forecast data. Please refresh.")

# --- TAB 2: ICE ANALYSIS ---
with tab_ice:
    st.markdown("### 🧊 Ice & Freezing Rain Forecast")
    
    if ice_data and euro_daily:
        total_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
        max_ice_day = max(ice_data.items(), key=lambda x: x[1]['ice_accum']) if ice_data else (None, {'ice_accum': 0})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("7-Day Ice Total", f"{total_ice:.2f}\"")
        with col2:
            st.metric("Peak Ice Day", 
                     pd.to_datetime(max_ice_day[0]).strftime('%a %m/%d') if max_ice_day[0] else "None",
                     f"{max_ice_day[1]['ice_accum']:.2f}\"" if max_ice_day[0] else "0.00\"")
        with col3:
            ice_days = sum([1 for day in ice_data if ice_data[day]['ice_accum'] > 0])
            st.metric("Days with Ice Risk", ice_days)
        
        st.markdown("---")
        
        # Ice Table
        ice_table_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            if day_key in ice_data:
                ice_accum = ice_data[day_key]['ice_accum']
                ice_risk = ice_data[day_key]['ice_risk']
                freezing_hours = ice_data[day_key]['freezing_rain_hours']
            else:
                ice_accum = 0
                ice_risk = 'None'
                freezing_hours = 0
            
            # Risk indicator
            risk_emoji = {
                'High': "🔴 HIGH",
                'Moderate': "🟡 MODERATE",
                'Low': "🔵 LOW",
                'None': "⚪ NONE"
            }.get(ice_risk, "⚪ NONE")
            
            ice_table_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Ice Accum': f"{ice_accum:.3f}\"",
                'Risk Level': risk_emoji,
                'Freezing Hours': freezing_hours
            })
        
        df_ice = pd.DataFrame(ice_table_data)
        st.dataframe(df_ice, use_container_width=True, hide_index=True)
        
        with st.expander("🧊 Ice Risk Guide"):
            st.markdown("""
            **🔴 HIGH RISK (0.25"+):** Major ice storm, power outages likely, travel impossible
            
            **🟡 MODERATE RISK (0.10"-0.24"):** Significant icing, scattered outages, hazardous roads
            
            **🔵 LOW RISK (trace-0.09"):** Light icing, slick spots, use caution
            
            **⚪ NO RISK:** No freezing rain expected
            """)
    else:
        st.error("❌ Unable to load ice data.")

# --- TAB 3: ROAD CONDITIONS ---
with tab_roads:
    st.markdown("### 🚗 NCDOT Road Conditions")
    
    st.markdown("""
    #### 🔗 Official Resources
    - 🌐 [DriveNC.gov](https://drivenc.gov) - Live traffic map
    - 📞 **511** - NC Travel Information
    - 🗺️ [NCDOT Division 14](https://www.ncdot.gov/divisions/highways/regional-operations/Pages/division-14.aspx)
    """)
    
    st.markdown("---")
    
    # Current travel recommendation
    if euro_daily and ice_data:
        today_key = nc_time.strftime('%Y-%m-%d')
        ice_risk = ice_data.get(today_key, {}).get('ice_risk', 'None')
        ice_accum = ice_data.get(today_key, {}).get('ice_accum', 0)
        today_snow = euro_daily['snowfall_sum'][0] if len(euro_daily['snowfall_sum']) > 0 else 0
        today_low = euro_daily['temperature_2m_min'][0] if len(euro_daily['temperature_2m_min']) > 0 else 40
        
        # Determine travel status
        if ice_risk == 'High' or ice_accum >= 0.25 or today_snow >= 3.0:
            status = "🔴 AVOID TRAVEL"
            desc = "Hazardous conditions expected."
            css = "alert-red"
        elif ice_risk == 'Moderate' or ice_accum >= 0.10 or today_snow >= 1.0 or today_low <= 28:
            status = "🟡 CAUTION ADVISED"
            desc = "Difficult conditions possible."
            css = "alert-orange"
        elif ice_risk == 'Low' or today_low <= 32:
            status = "🔵 USE CAUTION"
            desc = "Watch for icy spots."
            css = "alert-ice"
        else:
            status = "✅ NORMAL CONDITIONS"
            desc = "No significant hazards."
            css = "alert-green"
        
        st.markdown(f"""
        <div class="alert-box {css}">
            <h3>{status}</h3>
            <p>{desc}</p>
            <p><strong>Today:</strong> {today_snow:.1f}\" snow, {ice_accum:.2f}\" ice, Low: {today_low:.0f}°F</p>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 4: POWER STATUS ---
with tab_power:
    st.markdown("### ⚡ Duke Energy - Power Status")
    
    st.markdown("""
    <div class="alert-box alert-red">
        <h3>🚨 Report Power Outage</h3>
        <p><strong>☎️ 1-800-POWERON (1-800-769-3766)</strong> - 24/7</p>
        <p><strong>📱 Text "OUT" to 57801</strong></p>
        <p><strong>💻 <a href="https://www.duke-energy.com/outages/report" target="_blank" style="color:white;">duke-energy.com/outages/report</a></strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    #### 🗺️ Live Outage Map
    🌐 [Duke Energy Outage Map](https://outagemap.duke-energy.com/#/current-outages/ncsc)
    
    Shows current outages, affected areas, and estimated restoration times.
    """)

# --- TAB 5: RADAR ---
with tab_radar:
    st.markdown("### 📡 Live Doppler Radar")
    
    # Local radar
    st.markdown("#### KGSP (Greenville-Spartanburg)")
    local_radar = f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}"
    st.image(local_radar, caption=f"Local Radar | {nc_time.strftime('%I:%M %p')}", width=600)
    
    st.markdown("""
    🔗 [View Full Interactive Radar](https://radar.weather.gov/station/kgsp/standard)
    """)

# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF • NCDOT • Duke Energy")
st.caption("**Stephanie's Snow & Ice Forecaster** | Bonnie Lane Edition")
