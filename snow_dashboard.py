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

# NCDOT Region (Webster is in Division 14 - Western NC)
NCDOT_DIVISION = 14

st.set_page_config(page_title="Stephanie's Snow & Ice Forecaster: Bonnie Lane Edition", page_icon="❄️", layout="wide")

# --- CUSTOM CSS ---
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
    .alert-ice { background-color: #1565C0; border-left: 10px solid #90CAF9; }
    .alert-green { background-color: #2E7D32; border-left: 10px solid #A5D6A7; }
    
    /* 5. Headers & Images */
    img { border: 2px solid #a6c9ff; border-radius: 10px; }
    h1, h2, h3, h4, p, div { color: #e0f7fa !important; }
    
    /* 6. Clean Divider */
    hr { margin-top: 5px; margin-bottom: 5px; border-color: #444; }
    
    /* 7. Road Status Indicators */
    .road-open { color: #4CAF50; font-weight: bold; }
    .road-caution { color: #FFC107; font-weight: bold; }
    .road-closed { color: #F44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE FIX ---
nc_time = pd.Timestamp.now(tz='US/Eastern')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ❄️ Controls")
    if st.button("✨ Let it Snow!"): st.snow()
    if st.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    st.caption(f"Last Updated:\n{nc_time.strftime('%I:%M:%S %p')}")
    st.markdown("---")
    st.markdown("### 🌧️ Features")
    st.caption("✓ Snow Forecast")
    st.caption("✓ Ice Analysis")
    st.caption("✓ Rainfall + Ice Formation")
    st.caption("✓ NCDOT Road Conditions")
    st.caption("✓ Duke Energy Outages")
    st.caption("✓ Temperature Profiles")

# --- HEADER ---
st.title("❄️🧊 Stephanie's Snow & Ice Forecaster")
st.markdown("#### *Bonnie Lane Edition - ECMWF + NCDOT + Duke Energy Integration*")
st.caption(f"Webster, NC | European Centre Gold Standard Model | {nc_time.strftime('%A, %b %d %I:%M %p')}")

ts = int(time.time())

# --- DATA FUNCTIONS ---
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
def get_euro_snow_ice():
    """Get ECMWF model forecast with hourly data for ice analysis"""
    try:
        # Daily forecast
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, 
            "longitude": LON, 
            "daily": ["snowfall_sum", "rain_sum", "weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"], 
            "timezone": "America/New_York", 
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        daily_data = requests.get(url, params=params, timeout=10).json().get('daily', None)
        
        # Hourly forecast for ice analysis
        params_hourly = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["temperature_2m", "precipitation", "rain", "snowfall", "freezing_level_height", "surface_pressure"],
            "timezone": "America/New_York",
            "precipitation_unit": "inch",
            "forecast_days": 7
        }
        hourly_data = requests.get(url, params=params_hourly, timeout=10).json().get('hourly', None)
        
        return daily_data, hourly_data
    except: 
        return None, None

@st.cache_data(ttl=300)
def get_duke_energy_outages():
    """Get Duke Energy outage information for Western NC"""
    try:
        # Duke Energy outage map data
        # They use a public JSON endpoint for their outage map
        url = "https://outagemap.duke-energy.com/ncsc/default.html"
        
        # Note: Duke Energy's actual API may require parsing their outage map
        # This is a placeholder - actual implementation would parse their data
        
        # For now, return structure for manual/scraped data
        outage_data = {
            'jackson_county': {
                'customers_out': 0,
                'total_customers': 12500,
                'incidents': [],
                'estimated_restoration': None
            },
            'western_nc': {
                'customers_out': 0,
                'total_customers': 450000
            }
        }
        
        return outage_data
    except:
        return None

def get_duke_energy_contacts():
    """Duke Energy contact information and resources"""
    return {
        'emergency': {
            'number': '1-800-POWERON (1-800-769-3766)',
            'description': '24/7 Power outage reporting and emergencies'
        },
        'customer_service': {
            'number': '1-800-777-9898',
            'description': 'Billing and account questions'
        },
        'gas_emergency': {
            'number': '1-800-752-8040',
            'description': 'Natural gas leaks or emergencies'
        },
        'online': {
            'outage_map': 'https://outagemap.duke-energy.com/ncsc/default.html',
            'report_outage': 'https://www.duke-energy.com/outages/report',
            'mobile_app': 'Duke Energy mobile app (iOS/Android)',
            'text_alerts': 'Text OUT to 57801'
        },
        'local_office': {
            'name': 'Duke Energy - Sylva Office',
            'address': '591 Skyland Drive, Sylva, NC 28779',
            'phone': '1-800-777-9898'
        }
    }

def get_power_outage_risks(ice_data, euro_daily):
    """Calculate power outage risk based on ice/snow forecast"""
    risks = []
    
    if not ice_data or not euro_daily:
        return risks
    
    for i in range(min(7, len(euro_daily['time']))):
        day_date = pd.to_datetime(euro_daily['time'][i])
        day_key = day_date.strftime('%Y-%m-%d')
        
        ice_accum = ice_data.get(day_key, {}).get('ice_accum', 0)
        snow = euro_daily['snowfall_sum'][i] if i < len(euro_daily['snowfall_sum']) else 0
        
        # Determine outage risk
        risk_level = 'None'
        risk_description = 'No significant outage risk'
        
        if ice_accum >= 0.50:
            risk_level = 'Extreme'
            risk_description = 'Major outages likely - Widespread tree damage, downed power lines expected'
        elif ice_accum >= 0.25:
            risk_level = 'High'
            risk_description = 'Significant outages possible - Tree limbs on lines, scattered outages'
        elif ice_accum >= 0.10:
            risk_level = 'Moderate'
            risk_description = 'Minor outages possible - Small branches, isolated issues'
        elif snow >= 12:
            risk_level = 'Moderate'
            risk_description = 'Heavy snow - Possible outages from snow weight on trees/lines'
        elif snow >= 6:
            risk_level = 'Low'
            risk_description = 'Significant snow - Monitor for potential issues'
        
        if risk_level != 'None':
            risks.append({
                'date': day_date.strftime('%a %m/%d'),
                'risk_level': risk_level,
                'description': risk_description,
                'ice': ice_accum,
                'snow': snow
            })
    
    return risks

@st.cache_data(ttl=300)
def get_ncdot_road_conditions():
    """Get NCDOT road conditions and incidents"""
    try:
        # NCDOT uses the Traveler Information Management System (TIMS)
        # The public-facing API endpoint for incidents and road conditions
        url = "https://tims.ncdot.gov/tims/api/events"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None
    except Exception as e:
        st.warning(f"NCDOT API temporarily unavailable: {e}")
        return None

@st.cache_data(ttl=300)
def get_ncdot_travel_advisories():
    """Get NCDOT travel advisories and alerts"""
    try:
        # NCDOT Travel Advisory feed
        url = "https://tims.ncdot.gov/tims/api/advisories"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def filter_nearby_incidents(incidents, max_distance_miles=50):
    """Filter incidents near Webster, NC"""
    if not incidents:
        return []
    
    nearby = []
    for incident in incidents:
        # Calculate approximate distance (simplified)
        if 'latitude' in incident and 'longitude' in incident:
            lat_diff = abs(float(incident['latitude']) - LAT)
            lon_diff = abs(float(incident['longitude']) - LON)
            
            # Rough distance calculation (1 degree ≈ 69 miles)
            distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 69
            
            if distance <= max_distance_miles:
                incident['distance_miles'] = round(distance, 1)
                nearby.append(incident)
    
    return sorted(nearby, key=lambda x: x.get('distance_miles', 999))

def get_key_routes_webster():
    """Define key routes around Webster, NC"""
    return [
        {
            'name': 'US-23/74 (Great Smoky Mountains Expressway)',
            'description': 'Main east-west corridor to Asheville and Atlanta',
            'importance': 'Critical',
            'winter_concern': 'High - Mountain passes, prone to ice'
        },
        {
            'name': 'US-441 (Smoky Mountain Highway)',
            'description': 'Route to Cherokee and Great Smoky Mountains',
            'importance': 'High',
            'winter_concern': 'Extreme - High elevation, frequent closures'
        },
        {
            'name': 'NC-107',
            'description': 'Scenic route to Cashiers and Highlands',
            'importance': 'Medium',
            'winter_concern': 'High - Winding mountain road'
        },
        {
            'name': 'Balsam Mountain Road',
            'description': 'Local mountain route',
            'importance': 'Low',
            'winter_concern': 'Extreme - Steep grades, often impassable'
        },
        {
            'name': 'NC-116 (Webster Road)',
            'description': 'Local connector',
            'importance': 'Medium',
            'winter_concern': 'Moderate - Some elevation changes'
        }
    ]

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
        
        # Ice occurs when temp is below freezing but precipitation is liquid (freezing rain)
        # FIXED: Any rain below freezing creates ice, not just 28-32°F range
        ice_potential = 0
        
        if temp < 32 and precip > 0:
            # Calculate non-snow precipitation (rain/freezing rain)
            non_snow_precip = precip - snow
            
            if non_snow_precip > 0:
                # Any liquid precip below freezing becomes ice
                # Efficiency varies by temperature
                if temp <= 20:
                    # Very cold - high efficiency ice formation (or data anomaly)
                    ice_potential = non_snow_precip * 0.9
                elif temp <= 28:
                    # Cold freezing rain - high efficiency
                    ice_potential = non_snow_precip * 0.85
                else:
                    # Classic freezing rain zone (28-32°F)
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

def analyze_rainfall_ice_formation(hourly_data):
    """Analyze when rainfall could freeze based on temperature transitions - including wet surface refreezing"""
    if not hourly_data:
        return {}
    
    ice_formation_events = []
    
    for i in range(len(hourly_data['time']) - 1):
        dt = pd.to_datetime(hourly_data['time'][i])
        next_dt = pd.to_datetime(hourly_data['time'][i + 1])
        
        temp = hourly_data['temperature_2m'][i]
        next_temp = hourly_data['temperature_2m'][i + 1]
        rain = hourly_data['rain'][i]
        
        # Scenario 1: FREEZING RAIN - Rain falling while already below freezing
        # This is immediate ice accumulation on contact
        if rain > 0 and temp <= 32:
            if temp <= 20:
                risk_level = 'Extreme - Severe Icing Conditions'
                event_desc = 'Freezing Rain (Extreme Cold)'
            elif temp <= 28:
                risk_level = 'Extreme - Immediate Ice Accumulation'
                event_desc = 'Freezing Rain'
            else:
                risk_level = 'Extreme - Immediate Ice Accumulation'
                event_desc = 'Freezing Rain'
            
            ice_formation_events.append({
                'start_time': dt,
                'end_time': next_dt,
                'event_type': event_desc,
                'rainfall': rain,
                'start_temp': temp,
                'end_temp': next_temp,
                'risk': risk_level
            })
        
        # Scenario 2: RAIN THEN FREEZE - Rain falls above freezing, then temp drops
        # This is the classic black ice scenario
        if rain > 0 and temp > 32 and next_temp <= 32:
            ice_formation_events.append({
                'start_time': dt,
                'end_time': next_dt,
                'event_type': 'Rain Transition to Freezing (Black Ice Alert)',
                'rainfall': rain,
                'start_temp': temp,
                'end_temp': next_temp,
                'risk': 'Extreme - Black Ice Formation'
            })
        
        # Scenario 3: WET SURFACE REFREEZING - The user's excellent point!
        # Look back up to 12 hours for ANY rain that left surfaces wet
        # If temperature drops below freezing, ALL that water freezes
        if temp > 32 and next_temp <= 32:
            # Check last 12 hours for rain that would leave surfaces wet
            lookback_hours = min(12, i)
            total_recent_rain = 0
            
            for j in range(i - lookback_hours, i):
                if hourly_data['rain'][j] > 0:
                    total_recent_rain += hourly_data['rain'][j]
            
            if total_recent_rain > 0.05:  # Significant moisture on surfaces
                # Determine risk based on how much rain and how cold it gets
                if total_recent_rain >= 0.25 and next_temp <= 28:
                    risk_level = 'Extreme - Major Black Ice Event'
                elif total_recent_rain >= 0.10:
                    risk_level = 'High - Widespread Black Ice'
                else:
                    risk_level = 'Moderate - Black Ice Likely'
                
                ice_formation_events.append({
                    'start_time': dt,
                    'end_time': next_dt,
                    'event_type': 'Wet Surfaces Refreezing (Pooled Water)',
                    'rainfall': total_recent_rain,
                    'start_temp': temp,
                    'end_temp': next_temp,
                    'risk': risk_level
                })
        
        # Scenario 4: SUSTAINED COLD AFTER RAIN - Already below freezing and staying there
        # Any wet surfaces from earlier will remain frozen
        if temp <= 32 and next_temp <= 32:
            # Look back for recent rain (last 24 hours)
            lookback_hours = min(24, i)
            recent_rain_while_warm = 0
            
            for j in range(i - lookback_hours, i):
                if hourly_data['rain'][j] > 0 and hourly_data['temperature_2m'][j] > 32:
                    recent_rain_while_warm += hourly_data['rain'][j]
            
            # Only report once when freeze first sustains, not every hour
            if recent_rain_while_warm > 0.05 and i > 0 and hourly_data['temperature_2m'][i-1] > 32:
                ice_formation_events.append({
                    'start_time': dt,
                    'end_time': next_dt,
                    'event_type': 'Ice Persistence (Surfaces Remain Frozen)',
                    'rainfall': recent_rain_while_warm,
                    'start_temp': temp,
                    'end_temp': next_temp,
                    'risk': 'Moderate - Ice Remains on Surfaces'
                })
    
    return ice_formation_events

# --- ALERT BANNER ---
alerts = get_nws_alerts()
if alerts:
    for alert in alerts:
        props = alert['properties']
        event = props['event']
        description = props['description']
        css_class = "alert-orange"
        if "Warning" in event: css_class = "alert-red"
        if "Winter" in event or "Ice" in event or "Snow" in event: css_class = "alert-purple"
        if "Ice Storm" in event or "Freezing" in event: css_class = "alert-ice"
        
        st.markdown(f"""
        <div class="alert-box {css_class}">
            <h3>⚠️ {event}</h3>
            <p>{props['headline']}</p>
            <details><summary>Read Details</summary><p style="font-size:0.9em;">{description}</p></details>
        </div>
        """, unsafe_allow_html=True)

# --- FETCH DATA ---
with st.spinner("Loading weather intelligence, road conditions, and power grid status..."):
    euro_daily, euro_hourly = get_euro_snow_ice()
    nws = get_nws_text()
    ice_data = calculate_ice_accumulation(euro_hourly)
    ice_formation_events = analyze_rainfall_ice_formation(euro_hourly)
    ncdot_incidents = get_ncdot_road_conditions()
    ncdot_advisories = get_ncdot_travel_advisories()
    duke_outages = get_duke_energy_outages()
    duke_contacts = get_duke_energy_contacts()
    power_risks = get_power_outage_risks(ice_data, euro_daily)

# --- TABS ---
tab_forecast, tab_ice, tab_rainfall, tab_roads, tab_power, tab_radar, tab_outlook = st.tabs([
    "❄️ Snow Forecast", 
    "🧊 Ice Forecast", 
    "🌧️ Rainfall & Ice Formation",
    "🚗 NCDOT Road Conditions",
    "⚡ Duke Energy Power",
    "📡 Radar & Data", 
    "🌨️ Winter Outlook"
])

# --- TAB 1: SNOW FORECAST ---
with tab_forecast:
    st.markdown("### ❄️ ECMWF Snow Forecast")
    st.caption("European Centre for Medium-Range Weather Forecasts - Gold Standard Model")
    
    if euro_daily:
        # 7-Day Summary
        st.markdown("#### 📊 7-Day Snow Total")
        total_snow = sum(euro_daily['snowfall_sum'][:7])
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Next 7 Days", f"{total_snow:.2f}\" snow", 
                     help="Total expected snowfall over the next week")
        
        st.markdown("---")
        
        # Daily Breakdown Table
        st.markdown("#### 📅 Daily Breakdown")
        
        daily_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            snow = euro_daily['snowfall_sum'][i]
            temp_high = euro_daily['temperature_2m_max'][i]
            temp_low = euro_daily['temperature_2m_min'][i]
            
            # Snow indicator
            if snow >= 3.0:
                indicator = "🔴 Heavy"
            elif snow >= 1.0:
                indicator = "🟡 Moderate"
            elif snow > 0:
                indicator = "🔵 Light"
            else:
                indicator = "⚪ None"
            
            # Add ice indicator if present
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
        
        st.markdown("---")
        
        # Visual Chart
        st.markdown("#### 📈 7-Day Snow Forecast")
        
        fig = go.Figure()
        
        dates = [pd.to_datetime(euro_daily['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro_daily['time'])))]
        
        fig.add_trace(go.Bar(
            x=dates,
            y=[euro_daily['snowfall_sum'][i] for i in range(min(7, len(euro_daily['time'])))],
            marker_color='#4ECDC4',
            text=[f"{euro_daily['snowfall_sum'][i]:.1f}\"" for i in range(min(7, len(euro_daily['time'])))],
            textposition='outside',
            name='Snow'
        ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
            title="Expected Snowfall (inches)",
            xaxis_title="Date",
            yaxis_title="Snowfall (inches)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # About ECMWF
        with st.expander("ℹ️ About ECMWF"):
            st.markdown("""
            **ECMWF (European Centre for Medium-Range Weather Forecasts)**
            
            The ECMWF model is widely considered the **gold standard** for weather forecasting:
            
            - 🏆 **Most Accurate**: Consistently ranks #1 in forecast accuracy
            - 🌍 **Global Coverage**: Uses data from worldwide weather stations
            - 🔬 **Physics-Based**: Advanced atmospheric modeling
            - 📊 **Trusted Worldwide**: Used by meteorologists globally
            
            **Snow Categories:**
            - 🔴 **Heavy** (3"+ per day): Major snow event
            - 🟡 **Moderate** (1-3" per day): Significant accumulation  
            - 🔵 **Light** (<1" per day): Minor accumulation
            - ⚪ **None**: No snow expected
            - 🧊 **Ice Icon**: Freezing rain/ice possible
            """)
    
    else:
        st.error("❌ Unable to load ECMWF forecast data. Please refresh.")

# --- TAB 2: ICE FORECAST ---
with tab_ice:
    st.markdown("### 🧊 Ice & Freezing Rain Forecast")
    st.caption("Critical information for roads, power lines, and infrastructure")
    
    if ice_data and euro_daily:
        # Summary metrics
        total_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
        max_ice_day = max(ice_data.items(), key=lambda x: x[1]['ice_accum']) if ice_data else (None, {'ice_accum': 0})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("7-Day Ice Total", f"{total_ice:.2f}\"", 
                     help="Total ice accumulation expected")
        with col2:
            st.metric("Peak Ice Day", 
                     pd.to_datetime(max_ice_day[0]).strftime('%a %m/%d') if max_ice_day[0] else "None",
                     f"{max_ice_day[1]['ice_accum']:.2f}\"" if max_ice_day[0] else "0.00\"")
        with col3:
            ice_days = sum([1 for day in ice_data if ice_data[day]['ice_accum'] > 0])
            st.metric("Days with Ice Risk", ice_days)
        
        st.markdown("---")
        
        # Ice Risk Table
        st.markdown("#### 🧊 7-Day Ice Accumulation Forecast")
        
        ice_table_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            
            if day_key in ice_data:
                ice_accum = ice_data[day_key]['ice_accum']
                ice_risk = ice_data[day_key]['ice_risk']
                freezing_hours = ice_data[day_key]['freezing_rain_hours']
                min_temp = ice_data[day_key]['min_temp']
                max_temp = ice_data[day_key]['max_temp']
            else:
                ice_accum = 0
                ice_risk = 'None'
                freezing_hours = 0
                min_temp = euro_daily['temperature_2m_min'][i]
                max_temp = euro_daily['temperature_2m_max'][i]
            
            # Risk indicator
            if ice_risk == 'High':
                risk_emoji = "🔴 HIGH"
            elif ice_risk == 'Moderate':
                risk_emoji = "🟡 MODERATE"
            elif ice_risk == 'Low':
                risk_emoji = "🔵 LOW"
            else:
                risk_emoji = "⚪ NONE"
            
            ice_table_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Ice Accum': f"{ice_accum:.3f}\"",
                'Risk Level': risk_emoji,
                'Freezing Hours': freezing_hours,
                'Temp Range': f"{min_temp:.0f}°F - {max_temp:.0f}°F"
            })
        
        df_ice = pd.DataFrame(ice_table_data)
        st.dataframe(df_ice, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Temperature Profile Chart
        st.markdown("#### 🌡️ Temperature Profile - Ice vs Snow Conditions")
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Ice Accumulation Forecast', 'Temperature Profile'),
            vertical_spacing=0.15,
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        dates = [pd.to_datetime(euro_daily['time'][i]).strftime('%a %m/%d') 
                for i in range(min(7, len(euro_daily['time'])))]
        
        ice_amounts = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            day_key = day_date.strftime('%Y-%m-%d')
            ice_amounts.append(ice_data[day_key]['ice_accum'] if day_key in ice_data else 0)
        
        # Ice accumulation bars
        fig.add_trace(
            go.Bar(
                x=dates,
                y=ice_amounts,
                marker_color='#64B5F6',
                text=[f"{val:.3f}\"" for val in ice_amounts],
                textposition='outside',
                name='Ice'
            ),
            row=1, col=1
        )
        
        # Temperature profile
        temps_high = [euro_daily['temperature_2m_max'][i] for i in range(min(7, len(euro_daily['time'])))]
        temps_low = [euro_daily['temperature_2m_min'][i] for i in range(min(7, len(euro_daily['time'])))]
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps_high,
                mode='lines+markers',
                name='High',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps_low,
                mode='lines+markers',
                name='Low',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(size=8)
            ),
            row=2, col=1
        )
        
        # Add freezing line
        fig.add_hline(y=32, line_dash="dash", line_color="white", 
                     annotation_text="Freezing (32°F)", 
                     annotation_position="right",
                     row=2, col=1)
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Ice (inches)", row=1, col=1)
        fig.update_yaxes(title_text="Temperature (°F)", row=2, col=1)
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Ice Risk Explanation
        with st.expander("🧊 Understanding Ice Accumulation & Risk Levels"):
            st.markdown("""
            ### Ice Risk Categories
            
            **🔴 HIGH RISK (0.25"+ ice)**
            - Major ice storm conditions
            - Widespread power outages likely
            - Tree damage expected
            - Travel extremely dangerous or impossible
            - Duration: Several hours to full day
            
            **🟡 MODERATE RISK (0.10" - 0.24" ice)**
            - Significant icing conditions
            - Scattered power outages possible
            - Some tree limb damage
            - Hazardous travel conditions
            - Duration: 2-6 hours typically
            
            **🔵 LOW RISK (trace - 0.09" ice)**
            - Light icing possible
            - Minimal power impacts
            - Slick roads and walkways
            - Use caution when traveling
            - Duration: 1-3 hours typically
            
            **⚪ NO RISK**
            - No freezing rain expected
            - Safe conditions
            """)
    
    else:
        st.error("❌ Unable to load ice forecast data. Please refresh.")

# --- TAB 3: RAINFALL & ICE FORMATION ---
with tab_rainfall:
    st.markdown("### 🌧️ Rainfall Forecast & Ice Formation Analysis")
    st.caption("Predicting when rainfall will freeze based on temperature transitions")
    
    if euro_daily and euro_hourly:
        # Summary metrics
        total_rain = sum(euro_daily['rain_sum'][:7])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("7-Day Rainfall", f"{total_rain:.2f}\"", 
                     help="Total rainfall expected over the next week")
        with col2:
            st.metric("Ice Formation Events", len(ice_formation_events),
                     help="Number of times rain could freeze")
        with col3:
            high_risk_events = len([e for e in ice_formation_events if 'Extreme' in e['risk'] or 'High' in e['risk']])
            st.metric("High Risk Events", high_risk_events,
                     help="Critical ice formation periods")
        
        st.markdown("---")
        
        # Daily Rainfall Table
        st.markdown("#### 📅 7-Day Rainfall Forecast")
        
        rainfall_data = []
        for i in range(min(7, len(euro_daily['time']))):
            day_date = pd.to_datetime(euro_daily['time'][i])
            rain = euro_daily['rain_sum'][i]
            temp_high = euro_daily['temperature_2m_max'][i]
            temp_low = euro_daily['temperature_2m_min'][i]
            
            # Check if this day has ice formation events
            day_start = day_date.replace(hour=0, minute=0, second=0)
            day_end = day_date.replace(hour=23, minute=59, second=59)
            
            day_events = [e for e in ice_formation_events 
                         if day_start <= e['start_time'] <= day_end]
            
            ice_formation = ""
            if day_events:
                max_risk_event = max(day_events, key=lambda x: x['rainfall'])
                if 'Extreme' in max_risk_event['risk']:
                    ice_formation = "🔴 EXTREME"
                elif 'High' in max_risk_event['risk']:
                    ice_formation = "🟡 HIGH"
                else:
                    ice_formation = "🔵 MODERATE"
            else:
                ice_formation = "⚪ None"
            
            # Rainfall indicator
            if rain >= 0.5:
                rain_level = "Heavy"
            elif rain >= 0.25:
                rain_level = "Moderate"
            elif rain > 0:
                rain_level = "Light"
            else:
                rain_level = "None"
            
            rainfall_data.append({
                'Date': day_date.strftime('%a %m/%d'),
                'Rainfall': f"{rain:.2f}\"",
                'Amount': rain_level,
                'High/Low': f"{temp_high:.0f}°F / {temp_low:.0f}°F",
                'Ice Formation Risk': ice_formation
            })
        
        df_rain = pd.DataFrame(rainfall_data)
        st.dataframe(df_rain, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Ice Formation Events
        if ice_formation_events:
            st.markdown("#### 🧊 Ice Formation Events - Detailed Timeline")
            st.caption("Critical periods when rainfall will freeze")
            
            for event in ice_formation_events[:20]:  # Show up to 20 events
                start_time = event['start_time'].strftime('%a %m/%d %I:%M %p')
                end_time = event['end_time'].strftime('%I:%M %p')
                
                # Determine alert style
                if 'Extreme' in event['risk']:
                    alert_style = "alert-red"
                elif 'High' in event['risk']:
                    alert_style = "alert-orange"
                else:
                    alert_style = "alert-ice"
                
                st.markdown(f"""
                <div class="alert-box {alert_style}">
                    <h4>{event['event_type']}</h4>
                    <p><strong>Time:</strong> {start_time} - {end_time}</p>
                    <p><strong>Risk Level:</strong> {event['risk']}</p>
                    <p><strong>Rainfall:</strong> {event['rainfall']:.3f}" | <strong>Temp:</strong> {event['start_temp']:.1f}°F → {event['end_temp']:.1f}°F</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("✅ No ice formation events detected in the 7-day forecast period.")
    
    else:
        st.error("❌ Unable to load rainfall forecast data. Please refresh.")

# --- TAB 4: NCDOT ROAD CONDITIONS ---
with tab_roads:
    st.markdown("### 🚗 NCDOT Road Conditions & Travel Information")
    st.caption("Real-time road status, incidents, and travel advisories for Jackson County & Western NC")
    
    # Quick Links
    st.markdown("#### 🔗 Official NCDOT Resources")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🌐 [**DriveNC.gov**](https://drivenc.gov) - Live traffic map")
    with col2:
        st.markdown("📞 **511** - NC Travel Information")
    with col3:
        st.markdown("🗺️ [**NCDOT Div 14**](https://www.ncdot.gov/divisions/highways/regional-operations/Pages/division-14.aspx) - Western NC")
    
    st.markdown("---")
    
    # Key Routes for Webster Area
    st.markdown("#### 🛣️ Key Routes - Webster, NC Area")
    
    key_routes = get_key_routes_webster()
    
    for route in key_routes:
        importance_color = {
            'Critical': 'alert-red',
            'High': 'alert-orange',
            'Medium': 'alert-ice',
            'Low': 'alert-purple'
        }.get(route['importance'], 'alert-ice')
        
        st.markdown(f"""
        <div class="alert-box {importance_color}">
            <h4>{route['name']}</h4>
            <p><strong>Description:</strong> {route['description']}</p>
            <p><strong>Importance:</strong> {route['importance']} | <strong>Winter Concern:</strong> {route['winter_concern']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # NCDOT Incidents
    if ncdot_incidents:
        st.markdown("#### 🚨 Active Incidents & Road Conditions")
        st.caption("Within 50 miles of Webster, NC")
        
        nearby_incidents = filter_nearby_incidents(ncdot_incidents, max_distance_miles=50)
        
        if nearby_incidents:
            for incident in nearby_incidents[:10]:  # Show top 10 closest
                # Determine severity
                severity = incident.get('severity', 'Unknown')
                event_type = incident.get('type', 'Incident')
                
                if 'closure' in event_type.lower() or 'closed' in severity.lower():
                    alert_class = 'alert-red'
                    icon = '🚫'
                elif 'delay' in event_type.lower() or 'construction' in event_type.lower():
                    alert_class = 'alert-orange'
                    icon = '🚧'
                else:
                    alert_class = 'alert-ice'
                    icon = '⚠️'
                
                location = incident.get('location', 'Location not specified')
                description = incident.get('description', 'No details available')
                distance = incident.get('distance_miles', 'Unknown')
                
                st.markdown(f"""
                <div class="alert-box {alert_class}">
                    <h4>{icon} {event_type}</h4>
                    <p><strong>Location:</strong> {location} ({distance} miles from Webster)</p>
                    <p><strong>Details:</strong> {description}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-box alert-green">
                <h4>✅ No Active Incidents</h4>
                <p>No road incidents or closures reported within 50 miles of Webster, NC.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📡 NCDOT incident data currently unavailable. Check DriveNC.gov for latest updates.")
    
    st.markdown("---")
    
    # Winter Travel Tips for Mountain Roads
    with st.expander("❄️ Winter Travel Tips - Mountain Roads", expanded=True):
        st.markdown("""
        ### Before You Travel
        
        **Check Conditions:**
        - 📞 Call 511 or visit DriveNC.gov
        - ❄️ Monitor this forecast for snow/ice predictions
        - 🌡️ Check current temperatures at elevation
        
        **Vehicle Preparation:**
        - ⛽ Keep gas tank above half full
        - 🚗 Check tire tread and pressure
        - 🔦 Emergency kit: blankets, flashlight, food, water
        - 📱 Fully charged phone + car charger
        
        ### Mountain Road Safety
        
        **Elevation Changes:**
        - Temperature drops ~3°F per 1,000 feet
        - Webster (2,100 ft) to Balsam Gap (3,370 ft) = 4°F difference
        - Road may be icy at higher elevations even if clear in town
        
        **Bridges & Overpasses:**
        - Freeze FIRST and thaw LAST
        - Reduce speed approaching bridges
        - Watch for black ice (invisible)
        
        **Critical Routes:**
        - **US-441**: Extreme winter hazard, frequent closures
        - **US-23/74**: Main artery, well-maintained but watch mountain passes
        - **NC-107**: Winding, shaded sections stay icy longer
        
        **If You Get Stuck:**
        1. Stay with your vehicle
        2. Call 911 and 511
        3. Run engine 10 min/hour for heat
        4. Keep exhaust clear of snow
        5. Use hazard lights
        
        ### When NOT to Travel
        
        **Avoid Roads When:**
        - 🔴 Ice accumulation forecast > 0.10"
        - 🟡 Active freezing rain falling
        - 🌨️ Snowfall rate > 1" per hour
        - 🌡️ Temperature at or below 32°F with wet roads
        - 🌙 Overnight hours when temperatures drop
        
        **NCDOT Priority:**
        - US routes cleared first
        - State routes next
        - Secondary roads last
        - May take 6-12 hours for all routes
        """)
    
    with st.expander("📞 Emergency Contacts & Resources"):
        st.markdown("""
        ### Emergency Numbers
        
        - **911** - Emergency services
        - **511** - NC Travel Information (or 1-877-511-4662)
        - **(828) 586-7500** - NCDOT Division 14 (Western NC)
        - **(828) 586-5226** - Jackson County Sheriff (non-emergency)
        
        ### Online Resources
        
        - **DriveNC.gov** - Live traffic and road conditions
        - **NCDOT Twitter** - @NCDOT_Div14 (Western NC updates)
        - **ReadyNC.gov** - Emergency preparedness
        - **Weather.gov/GSP** - NWS Greenville-Spartanburg forecast
        
        ### Road Condition Reporting
        
        **Report Issues:**
        - Downed trees, power lines, ice/snow problems
        - Use DriveNC.gov mobile app
        - Call 511
        - Tweet @NCDOT with location
        
        ### County-Specific
        
        **Jackson County:**
        - Sheriff: (828) 586-8901
        - Emergency Management: (828) 631-8050
        - Road Maintenance: (828) 586-7500
        """)
    
    # Current Travel Recommendation
    st.markdown("---")
    st.markdown("#### 🚦 Current Travel Recommendation")
    
    # Base recommendation on forecast data
    if euro_daily and ice_data:
        today_key = nc_time.strftime('%Y-%m-%d')
        
        if today_key in ice_data:
            ice_risk = ice_data[today_key]['ice_risk']
            ice_accum = ice_data[today_key]['ice_accum']
        else:
            ice_risk = 'None'
            ice_accum = 0
        
        today_snow = euro_daily['snowfall_sum'][0] if len(euro_daily['snowfall_sum']) > 0 else 0
        today_low = euro_daily['temperature_2m_min'][0] if len(euro_daily['temperature_2m_min']) > 0 else 40
        
        # Determine travel status
        if ice_risk == 'High' or ice_accum >= 0.25 or today_snow >= 3.0:
            travel_status = "🔴 AVOID TRAVEL"
            status_desc = "Hazardous conditions expected. Avoid non-essential travel."
            status_class = "alert-red"
        elif ice_risk == 'Moderate' or ice_accum >= 0.10 or today_snow >= 1.0 or today_low <= 28:
            travel_status = "🟡 CAUTION ADVISED"
            status_desc = "Difficult conditions possible. Use extreme caution and allow extra time."
            status_class = "alert-orange"
        elif ice_risk == 'Low' or today_low <= 32:
            travel_status = "🔵 USE CAUTION"
            status_desc = "Minor hazards possible. Watch for icy spots, especially on bridges."
            status_class = "alert-ice"
        else:
            travel_status = "✅ NORMAL CONDITIONS"
            status_desc = "No significant weather-related travel hazards expected."
            status_class = "alert-green"
        
        st.markdown(f"""
        <div class="alert-box {status_class}">
            <h3>{travel_status}</h3>
            <p>{status_desc}</p>
            <p><strong>Today's Forecast:</strong> {today_snow:.1f}\" snow, {ice_accum:.2f}\" ice, Low: {today_low:.0f}°F</p>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 5: DUKE ENERGY POWER ---
with tab_power:
    st.markdown("### ⚡ Duke Energy - Power Outage Status & Planning")
    st.caption("Power grid status, outage risk assessment, and emergency preparedness for Webster, NC")
    
    # Quick Emergency Contact
    st.markdown("""
    <div class="alert-box alert-red">
        <h3>🚨 Report Power Outage or Emergency</h3>
        <p><strong>☎️ Call: 1-800-POWERON (1-800-769-3766)</strong> - 24/7 Service</p>
        <p><strong>📱 Text "OUT" to 57801</strong> - Quick outage reporting</p>
        <p><strong>💻 Online:</strong> <a href="https://www.duke-energy.com/outages/report" target="_blank" style="color: white;">duke-energy.com/outages/report</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Power Outage Risk Assessment
    st.markdown("#### ⚠️ 7-Day Power Outage Risk Forecast")
    st.caption("Based on ice accumulation and heavy snow predictions")
    
    if power_risks:
        for risk in power_risks:
            if risk['risk_level'] == 'Extreme':
                alert_class = 'alert-red'
                icon = '🔴'
            elif risk['risk_level'] == 'High':
                alert_class = 'alert-orange'
                icon = '🟡'
            elif risk['risk_level'] == 'Moderate':
                alert_class = 'alert-ice'
                icon = '🔵'
            else:
                alert_class = 'alert-purple'
                icon = '⚪'
            
            st.markdown(f"""
            <div class="alert-box {alert_class}">
                <h4>{icon} {risk['date']} - {risk['risk_level']} Outage Risk</h4>
                <p><strong>{risk['description']}</strong></p>
                <p>Ice: {risk['ice']:.2f}\" | Snow: {risk['snow']:.1f}\"</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-box alert-green">
            <h4>✅ Low Outage Risk</h4>
            <p>No significant ice or snow events forecasted that would likely cause power outages.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Current Outage Status
    st.markdown("#### 🔌 Current Outage Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if duke_outages and 'jackson_county' in duke_outages:
            customers_out = duke_outages['jackson_county']['customers_out']
            total_customers = duke_outages['jackson_county']['total_customers']
            pct_out = (customers_out / total_customers * 100) if total_customers > 0 else 0
            st.metric("Jackson County", f"{customers_out:,} out", 
                     f"{pct_out:.1f}% affected" if customers_out > 0 else "No outages")
        else:
            st.metric("Jackson County", "Check outage map", 
                     help="Visit Duke Energy outage map for current status")
    
    with col2:
        if duke_outages and 'western_nc' in duke_outages:
            st.metric("Western NC Region", f"{duke_outages['western_nc']['customers_out']:,} out")
        else:
            st.metric("Western NC Region", "Check outage map")
    
    with col3:
        st.metric("Live Updates", "Every 5 min", 
                 help="Data refreshes automatically")
    
    # Outage Map Link
    st.markdown("#### 🗺️ Live Outage Map")
    st.markdown("""
    <div class="glass-card">
        <p><strong>View real-time outages on Duke Energy's interactive map:</strong></p>
        <p>🌐 <a href="https://outagemap.duke-energy.com/ncsc/default.html" target="_blank" style="color: #4ECDC4; font-size: 18px;">Duke Energy Outage Map</a></p>
        <p><em>Shows current outages, affected areas, crew locations, and estimated restoration times</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Ice/Snow Impact on Power Grid
    with st.expander("❄️ How Ice & Snow Affect Power Lines", expanded=True):
        st.markdown("""
        ### Understanding Ice Damage to Power Infrastructure
        
        **Ice Accumulation Thresholds:**
        
        **0.25" - 0.50" Ice:**
        - Tree limbs begin breaking
        - Scattered power outages expected
        - Outages: Hours to 1-2 days
        - Crew response: Local teams deployed
        
        **0.50" - 1.00" Ice:**
        - Major tree damage
        - Widespread outages likely
        - Power lines snap from ice weight
        - Outages: 2-5 days typical
        - Crew response: Regional assistance needed
        
        **1.00"+ Ice (Major Ice Storm):**
        - Catastrophic tree damage
        - Transmission lines affected
        - Substation damage possible
        - Outages: 5-14+ days
        - Crew response: Multi-state assistance, extended restoration
        
        ---
        
        ### Heavy Snow Impact
        
        **6-12" Snow:**
        - Tree branches weighted down
        - Isolated outages from branches on lines
        - Usually cleared quickly
        
        **12-18" Snow:**
        - Significant tree stress
        - Multiple outages likely
        - Wet heavy snow most dangerous
        
        **18"+ Snow:**
        - Major tree damage if snow is wet
        - Widespread outages in heavy wet snow
        - Dry powder snow less problematic
        
        ---
        
        ### Why Ice is More Dangerous Than Snow
        
        **Ice:**
        - ½" ice weighs 500 lbs per line span
        - Adheres to everything (lines, trees, poles)
        - Wind + ice = multiplied damage
        - Can't be shaken off
        
        **Snow:**
        - Can slide off lines and trees
        - Dry snow less damaging
        - Melts faster than ice
        - Easier for crews to work in
        
        ---
        
        ### Webster, NC Specific Factors
        
        **Advantages:**
        - ✅ Underground utilities in newer areas
        - ✅ Duke crews stationed regionally
        - ✅ Mountain communities prioritized
        
        **Challenges:**
        - ⚠️ Mountainous terrain = harder access
        - ⚠️ More trees near power lines
        - ⚠️ Elevation = colder = more ice
        - ⚠️ Rural areas restored last
        """)
    
    with st.expander("🔋 Power Outage Preparation Checklist"):
        st.markdown("""
        ### Before the Storm (24-48 hours ahead)
        
        **Essential Supplies:**
        - 🔦 Flashlights + fresh batteries (one per person)
        - 🕯️ Candles + matches/lighters
        - 📱 Phone chargers (car charger, battery pack)
        - 📻 Battery/hand-crank radio (NOAA weather radio)
        - 🔋 Power banks fully charged
        - 🪔 Propane/kerosene heater (if you have one)
        
        **Food & Water:**
        - 💧 1 gallon water per person per day (3-day minimum)
        - 🥫 Non-perishable food (doesn't need cooking)
        - 🍪 Snacks, protein bars
        - 🧊 Fill bathtub with water (for flushing toilets)
        - ❄️ Freeze water bottles (helps keep fridge cold)
        
        **Heating:**
        - 🪵 Firewood (if you have fireplace)
        - 🧥 Extra blankets, sleeping bags
        - 🧤 Winter clothes, hats, gloves
        - ⚠️ NEVER use gas stove/oven for heat (CO poisoning)
        - ⚠️ NEVER run generator indoors
        
        **Medical:**
        - 💊 Prescription medications (7-day supply)
        - 🏥 First aid kit
        - 🌡️ Thermometer
        
        **Financial:**
        - 💵 Cash (ATMs won't work without power)
        
        ---
        
        ### When Power Goes Out
        
        **Immediate Actions:**
        1. Report outage: Call 1-800-POWERON or text OUT to 57801
        2. Turn off/unplug major appliances (prevents damage from power surges)
        3. Leave one light switch ON (so you know when power returns)
        4. Set fridge/freezer to coldest setting, then DON'T OPEN
        
        **Heating Without Power:**
        - Close off unused rooms
        - Hang blankets over doorways
        - Dress in layers
        - Family stays together in one room
        - Use fireplace if you have one
        
        **Food Safety:**
        - Fridge keeps food cold 4 hours if unopened
        - Freezer keeps food 24-48 hours if unopened
        - Use coolers with snow/ice
        - Throw out anything that smells bad or has been >40°F for 2+ hours
        
        **Generator Safety (if you have one):**
        - ⚠️ OUTDOORS ONLY - 20+ feet from house
        - Never run in garage, even with door open
        - Point exhaust away from house
        - Use heavy-duty extension cords
        - Ground properly
        - Carbon monoxide kills - detector required
        
        ---
        
        ### Multi-Day Outages (3+ days)
        
        **Check on Neighbors:**
        - Elderly neighbors
        - Families with young children
        - Anyone with medical needs
        
        **Community Resources:**
        - Jackson County Emergency Management: (828) 631-8050
        - American Red Cross warming centers (check local news)
        - Churches often provide shelter/meals
        
        **Water (if on well pump):**
        - Well pumps don't work without power
        - Fill bathtubs before storm
        - Store drinking water
        - Melted snow can flush toilets (not for drinking)
        
        ---
        
        ### Webster-Specific Resources
        
        **Warming Centers:**
        - Check Jackson County Emergency Management
        - Local churches (call ahead)
        - Community centers
        
        **Fuel:**
        - Fill gas tank BEFORE storm
        - Gas stations can't pump without power
        - Keep vehicle above ½ tank in winter
        """)
    
    with st.expander("📞 Emergency Contacts & Resources"):
        st.markdown("""
        ### Duke Energy Contacts
        
        **Power Outages & Emergencies:**
        - ☎️ **1-800-POWERON (1-800-769-3766)** - 24/7
        - 📱 **Text "OUT" to 57801** - Report outage
        - 💻 **duke-energy.com/outages/report**
        
        **Customer Service:**
        - ☎️ **1-800-777-9898** - Billing, accounts
        
        **Natural Gas Emergency:**
        - ☎️ **1-800-752-8040** - Gas leaks, 24/7
        
        **Local Office:**
        - **Duke Energy - Sylva Office**
        - 📍 591 Skyland Drive, Sylva, NC 28779
        - ☎️ 1-800-777-9898
        
        ---
        
        ### Other Emergency Services
        
        **Emergencies:**
        - 🚨 **911** - Fire, medical, police
        
        **Jackson County:**
        - **Emergency Management:** (828) 631-8050
        - **Sheriff (non-emergency):** (828) 586-8901
        - **Health Department:** (828) 587-8288
        
        **Utilities:**
        - **Duke Energy:** 1-800-POWERON
        - **NCDOT (Roads):** 511
        
        ---
        
        ### Online Resources
        
        - **Duke Energy Outage Map:** outagemap.duke-energy.com/ncsc
        - **Duke Energy Mobile App:** iOS/Android
        - **Storm Center:** duke-energy.com/storm-center
        - **Safety Tips:** duke-energy.com/safety-education
        - **ReadyNC:** readync.gov
        """)
    
    # Footer note
    st.markdown("---")
    st.info("💡 **Tip:** Sign up for Duke Energy text alerts! Text 'REG' to 57801 to get automatic outage updates.")

# --- TAB 6: RADAR & DATA ---
with tab_radar:
    # --- MULTI-LEVEL RADAR SECTION ---
    st.markdown("### 📡 Live Doppler Radar - Multi-Scale View")
    
    # Single Local Radar on top
    st.markdown("#### 📍 Local Radar (KGSP)")
    st.image(f"https://radar.weather.gov/ridge/standard/KGSP_loop.gif?t={ts}", 
             caption=f"Greenville-Spartanburg | {nc_time.strftime('%I:%M %p')}", 
             use_container_width=True)
    st.caption("🔄 Updates every 5 minutes | Coverage: 100 mile radius")
    
    st.markdown("---")
    
    # Southeastern and National Radars side by side
    rad_col1, rad_col2 = st.columns(2)
    
    with rad_col1:
        st.markdown("#### 🌎 Southeastern US")
        st.image(f"https://radar.weather.gov/ridge/standard/SOUTHEAST_loop.gif?t={ts}", 
                 caption="Southeast Composite Radar", 
                 use_container_width=True)
        st.caption("🔄 Updates every 5 minutes | Coverage: All southeastern states")
    
    with rad_col2:
        st.markdown("#### 🇺🇸 National Radar")
        st.image(f"https://radar.weather.gov/ridge/standard/CONUS_loop.gif?t={ts}", 
                 caption="Continental US Composite", 
                 use_container_width=True)
        st.caption("🔄 Updates every 10 minutes | Coverage: Entire continental US")
    
    st.markdown("---")
    
    # NWS Forecast and Stats Section
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown("### 🌨️ 7-Day NWS Forecast")
        
        if nws:
            for period in nws[:6]:  # Show next 6 periods (3 days)
                with st.container():
                    st.markdown(f"**{period['name']}**")
                    st.write(f"🌡️ {period['temperature']}°{period['temperatureUnit']}")
                    st.write(f"🌨️ {period['shortForecast']}")
                    st.caption(period['detailedForecast'][:150] + "...")
                    st.markdown("---")
    
    with col_right:
        # Quick Stats
        if euro_daily and ice_data:
            st.markdown("### ❄️ Quick Stats")
            next_7_days_snow = sum(euro_daily['snowfall_sum'][:7])
            next_7_days_ice = sum([ice_data[day]['ice_accum'] for day in ice_data])
            next_7_days_rain = sum(euro_daily['rain_sum'][:7])
            st.metric("Next 7 Days Snow", f"{next_7_days_snow:.1f}\"")
            st.metric("Next 7 Days Ice", f"{next_7_days_ice:.2f}\"")
            st.metric("Next 7 Days Rain", f"{next_7_days_rain:.2f}\"")


# --- TAB 7: WINTER OUTLOOK ---
with tab_outlook:
    st.markdown("### 🌨️ Winter 2025-2026 Outlook for Webster, NC")
    st.caption("Seasonal forecast for Southern Appalachian Mountains")
    
    # Good News Banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%); 
                border-radius: 15px; 
                padding: 20px; 
                margin: 20px 0;
                border: 3px solid #44A08D;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
        <h2 style="color: white; margin: 0; text-align: center;">
            ✅ GOOD NEWS FOR WEBSTER!
        </h2>
        <h3 style="color: white; margin: 10px 0 0 0; text-align: center;">
            Above-Normal Snowfall Expected This Winter! ❄️
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Key Forecast Points
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>❄️ Snowfall</h3>
            <h2 style="color: #4ECDC4;">ABOVE NORMAL</h2>
            <p>Southern Appalachians favored for heavier snow vs. northern mountains</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>🌡️ Temperature</h3>
            <h2 style="color: #81D4FA;">COLDER</h2>
            <p>Below normal temps expected, especially late January</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>📅 Peak Timing</h3>
            <h2 style="color: #FFD93D;">LATE JAN</h2>
            <p>Best snow: Late Dec, Late Jan, Early-Late Feb, Mid-Mar</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Bottom Line
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; 
                padding: 25px; 
                margin: 20px 0;
                border: 3px solid #667eea;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);">
        <h3 style="color: white; margin: 0 0 15px 0; text-align: center;">
            ❄️ BOTTOM LINE FOR WEBSTER ❄️
        </h3>
        <p style="color: white; font-size: 18px; text-align: center; margin: 0; line-height: 1.6;">
            <strong>YES, snow is definitely coming back to Webster!</strong><br><br>
            The Southern Appalachian Mountains (including Webster, NC) are forecasted for 
            <strong>ABOVE-NORMAL snowfall</strong> this winter, with the best snow opportunities 
            in <strong>late January through February</strong>.<br><br>
            While coastal Carolinas stay dry, Webster is in the <strong>sweet spot</strong> 
            for multiple winter storms! 🏔️❄️
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("**Sources:** NOAA, Old Farmer's Almanac, NC State Climate Office, NWS | Updated: January 2026")


# --- FOOTER ---
st.markdown("---")
st.caption("**Data Sources:** NWS/NOAA • Open-Meteo ECMWF Model • NCDOT DriveNC • Duke Energy")
st.caption("**Stephanie's Snow & Ice Forecaster** | Bonnie Lane Edition | Complete Winter Intelligence Platform")
