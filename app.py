import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="SufraEats Executive Intelligence Deck",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 PREMIUM LUXURY BOARDROOM PALETTE
SUFRA_CRIMSON  = "#E11D48" # High-vibrancy primary accent
DEEP_SLATE     = "#0F172A" # Dark luxury corporate backgrounds
METRIC_BG      = "#1E293B" # Soft slate for dark metric tiles
SAGE_MINT      = "#10B981" # Safe green for growth/success
MUTED_AMBER    = "#F59E0B" # Deep gold for warnings/secondary targets
LIGHT_BG       = "#F8FAFC" # Clean, professional content backdrop
BORDER_COLOR   = "#E2E8F0" # Crisp card boundaries

# Custom CSS for executive presentation layout
st.markdown(f"""
<style>
    /* Main Background layout setup */
    .stApp {{ background-color: {LIGHT_BG}; }}
    h1, h2, h3, h4 {{ font-family: 'Inter', system-ui, sans-serif !important; color: {DEEP_SLATE} !important; font-weight: 700 !important; }}
    
    /* Premium Dropped Shadow Display Cards */
    .board-card {{
        background-color: #ffffff;
        padding: 26px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.05), 0 8px 10px -6px rgba(15, 23, 42, 0.05);
        border: 1px solid {BORDER_COLOR};
        margin-bottom: 24px;
    }}
    .board-card-accent {{
        border-left: 6px solid {SUFRA_CRIMSON};
    }}
    
    /* Dark Premium Metric Display Tiles */
    .metric-tile {{
        background-color: {METRIC_BG};
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }}
    .metric-tile p {{
        margin: 0;
        font-size: 11px;
        letter-spacing: 1.5px;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
    }}
    .metric-tile h2 {{
        margin: 8px 0 0 0 !important;
        font-size: 30px !important;
        font-weight: 800 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING & CACHING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    orders_path = os.path.join(BASE_DIR, "sufraeats_orders.csv")
    restaurants_path = os.path.join(BASE_DIR, "sufraeats_restaurants.csv")
    
    orders = pd.read_csv(orders_path)
    restaurants = pd.read_csv(restaurants_path)
    
    # Text Standardization
    restaurants['zone'] = restaurants['zone'].astype(str).str.strip().str.lower()
    restaurants['cuisine'] = restaurants['cuisine'].astype(str).str.strip().str.lower()
    
    zone_mapping = {'jlt': 'jumeirah lake towers', 'marina': 'dubai marina'}
    restaurants['zone'] = restaurants['zone'].replace(zone_mapping)
    
    for col in ['order_status', 'customer_type', 'order_channel', 'payment_method', 'device_platform']:
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.strip().str.lower()
            
    # Deduplication
    orders = orders.drop_duplicates(subset=['order_id'], keep='first')
    restaurants = restaurants.drop_duplicates(subset=['restaurant_id'], keep='first')
    
    # Merging via Inner Join
    df_clean = pd.merge(orders, restaurants, on='restaurant_id', how='inner')
    
    # Imputations & Anomalies Filtering
    df_clean['promo_code'] = df_clean['promo_code'].fillna('no promo').str.strip().str.lower()
    df_clean['discount_amount'] = df_clean['discount_amount'].fillna(0.0)
    
    df_clean['rating'] = df_clean.groupby('restaurant_id')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean.groupby('zone')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean['rating'].fillna(df_clean['rating'].median())
    
    valid_condition = (
        (df_clean['basket_value'] >= 0) &
        (df_clean['delivery_time_min'] >= 0) &
        (df_clean['hour'] >= 0) & (df_clean['hour'] <= 23)
    )
    df_clean = df_clean[valid_condition]
    
    df_clean['is_completed'] = df_clean['order_status'] == 'delivered'
    df_clean['is_cancelled'] = df_clean['order_status'] == 'cancelled'
    df_clean['is_refunded'] = df_clean['order_status'] == 'refunded'
    
    # Financial Revenue Pipeline Calculations
    df_clean['realised_revenue'] = np.where(
        df_clean['is_completed'],
        (df_clean['basket_value'] * df_clean['commission_rate']) + df_clean['delivery_fee'],
        0.0
    )
    df_clean['net_profit'] = np.where(
        df_clean['is_completed'],
        df_clean['realised_revenue'] - df_clean['discount_amount'],
        0.0  
    )
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['month_num'] = df_clean['date'].dt.month
    df_clean['month'] = df_clean['date'].dt.strftime('%B')
    df_clean['day_of_week'] = df_clean['date'].dt.strftime('%A')
    
    return df_clean

try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(f"Error executing data loading pipeline: {e}. Make sure CSVs are pushed to GitHub in the same directory.")
    st.stop()

# Applies premium uniform styling across all board presentation charts
def apply_board_theme(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=DEEP_SLATE),
        title=dict(font=dict(size=15, color=DEEP_SLATE, weight='bold'), x=0.02),
        margin=dict(t=60, b=50, l=50, r=50),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Inter")
    )
    return fig

# ==========================================
# SIDEBAR NAVIGATION & CONTROLS
# ==========================================
st.sidebar.markdown(f"<br><h2 style='text-align: center; color: {SUFRA_CRIMSON}; font-size: 24px; letter-spacing: -0.5px;'>🍔 SufraEats Hub</h2>", unsafe_allow_html=True)
page = st.sidebar.radio("Executive Deck Navigation:", [
    "📌 Expansion Strategy Mandate", 
    "👥 Target Customer Insights", 
    "📈 Operational Velocities", 
    "💰 Net Financial Performance"
])

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 11px; font-weight: bold; text-transform: uppercase; color: #64748B; letter-spacing: 1px;'>Global Presentation Filters</p>", unsafe_allow_html=True)
selected_zones = st.sidebar.multiselect("Zone Focus:", options=df_clean['zone'].unique().tolist(), default=df_clean['zone'].unique().tolist())
selected_cuisines = st.sidebar.multiselect("Cuisine Focus:", options=df_clean['cuisine'].unique().tolist(), default=df_clean['cuisine'].unique().tolist())

df_filtered = df_clean[(df_clean['zone'].isin(selected_zones)) & (df_clean['cuisine'].isin(selected_cuisines))]

# ==========================================
# PAGE 1: EXPANSION STRATEGY MANDATE
# ==========================================
if page == "📌 Expansion Strategy Mandate":
    st.title("🎯 Strategic Capital Expansion Framework")
    st.markdown("---")
    
    zone_perf = df_clean.groupby('zone').agg(
        orders=('order_id', 'count'),
        total_profit=('net_profit', 'sum'),
        avg_rating=('rating', 'mean'),
        del_time=('delivery_time_min', 'mean')
    ).reset_index()
    
    recommended_zone = zone_perf.sort_values(by='total_profit', ascending=False).iloc[0]['zone']
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="board-card board-card-accent">
            <h3 style='margin-top: 0;'>🏆 STRATEGIC FOCUS LOCATION RECOMMENDED</h3>
            <p style='color: #475569;'>Based on verified multi-tiered operational data and net profit calculations across 5 months, the optimal hub selection is:</p>
            <h2 style='color: {SUFRA_CRIMSON}; margin: 15px 0; font-size: 38px; letter-spacing: -1px;'>{recommended_zone.upper()}</h2>
            <hr style='border-color: {BORDER_COLOR}; margin: 18px 0;'>
            <table style='width: 100%; font-size: 14px; color: #475569; border-spacing: 0 8px;'>
                <tr><td><b>Net Profit Yield:</b></td><td style='text-align: right; color: {DEEP_SLATE}; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['total_profit'].values[0]:,.2f} AED</td></tr>
                <tr><td><b>Quality Benchmark Index:</b></td><td style='text-align: right; color: {DEEP_SLATE}; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['avg_rating'].values[0]:.2f} ⭐</td></tr>
                <tr><td><b>Logistical Delivery Time:</b></td><td style='text-align: right; color: {DEEP_SLATE}; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['del_time'].values[0]:.1f} Mins</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="board-card" style="height: 100%; background: linear-gradient(135deg, {DEEP_SLATE} 0%, #1E293B 100%); color: #E2E8F0;">
            <h4 style='color: #FFFFFF !important; margin-top: 0;'>📊 Strategic Justification Summary</h4>
            <p style='font-size: 14px; line-height: 1.6; color: #94A3B8;'>Top-line indicators such as total orders or gross values are frequently deceptive in delivery business models. 
            A zone can process significant volume while generating minimal net margin due to aggressive voucher marketing loops, high cancellation liabilities, and service friction. 
            Our architecture optimizes strictly for <b>protected net revenue</b>, positioning <b>{recommended_zone.upper()}</b> as the highest-yielding operational territory.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    fig_zone_prof = px.bar(zone_perf, x='zone', y='total_profit', color='avg_rating',
                           labels={'total_profit': 'Net Profit Yield (AED)', 'zone': 'Dubai Operating Zone', 'avg_rating': 'Avg Rating'},
                           title="Net Profit Contribution Margin by Territory vs Customer Experience Rating",
                           color_continuous_scale=[DEEP_SLATE, SUFRA_CRIMSON], text_auto=',.2f')
    fig_zone_prof.update_traces(textposition='outside', cliponaxis=False)
    fig_zone_prof = apply_board_theme(fig_zone_prof)
    st.plotly_chart(fig_zone_prof, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 2: TARGET CUSTOMER INSIGHTS
# ==========================================
elif page == "👥 Target Customer Insights":
    st.title("👥 Cohort Architecture, Demographics & Interface Preferences")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        cohort_counts = df_filtered['customer_type'].value_counts().reset_index()
        fig1 = go.Figure(data=[go.Pie(
            labels=cohort_counts['customer_type'].str.upper(), 
            values=cohort_counts['count'],
            hole=.45,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[DEEP_SLATE, SAGE_MINT], line=dict(color='#ffffff', width=2))
        )])
        fig1.update_layout(title="1. Order Contribution Mix: New vs. Repeat Cohorts")
        fig1 = apply_board_theme(fig1)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        channel_counts = df_filtered['order_channel'].value_counts().reset_index()
        fig3 = go.Figure(data=[go.Pie(
            labels=channel_counts['order_channel'].str.upper(), 
            values=channel_counts['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[SUFRA_CRIMSON, DEEP_SLATE, MUTED_AMBER], line=dict(color='#ffffff', width=2))
        )])
        fig3.update_layout(title="3. Preferable Distribution Channel Share Evaluation")
        fig3 = apply_board_theme(fig3)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        pay_mix = df_filtered.groupby(['customer_type', 'payment_method']).size().reset_index(name='order_volume')
        fig2 = px.bar(pay_mix, x='payment_method', y='order_volume', color='customer_type', 
                     barmode='group', text_auto=True,
                     color_discrete_map={'new': DEEP_SLATE, 'repeat': SAGE_MINT},
                     title="2. Payment Framework Mix by Customer Category Target",
                     labels={'order_volume': 'Total Confirmed Orders', 'payment_method': 'Settlement Method', 'customer_type': 'Cohort'})
        fig2.update_traces(textposition='outside', cliponaxis=False)
        fig2 = apply_board_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c4:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        device_mix = df_filtered['device_platform'].value_counts().reset_index()
        fig4 = go.Figure(data=[go.Pie(
            labels=device_mix['device_platform'].str.upper(), 
            values=device_mix['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[DEEP_SLATE, SUFRA_CRIMSON, MUTED_AMBER], line=dict(color='#ffffff', width=2))
        )])
        fig4.update_layout(title="4. Ecosystem Access Device Point Share")
        fig4 = apply_board_theme(fig4)
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 3: OPERATIONAL VELOCITIES
# ==========================================
elif page == "📈 Operational Velocities":
    st.title("📈 Logistical Velocities & Service Quality Metrics")
    st.markdown("---")
    
    avg_del_time = df_filtered['delivery_time_min'].mean()
    success_rate = (df_filtered['is_completed'].sum() / len(df_filtered)) * 100
    refunded_rate = (df_filtered['is_refunded'].sum() / len(df_filtered)) * 100
    cancelled_rate = (df_filtered['is_cancelled'].sum() / len(df_filtered)) * 100
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"<div class='metric-tile'><p>5. Avg Delivery Time</p><h2 style='color:#FFFFFF;'>{avg_del_time:.1f} Min</h2></div>", unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"<div class='metric-tile'><p>8. Success Delivery Rate</p><h2 style='color:{SAGE_MINT};'>{success_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"<div class='metric-tile'><p>8. Refunded Order Rate</p><h2 style='color:{MUTED_AMBER};'>{refunded_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"<div class='metric-tile'><p>8. Cancellation Rate</p><h2 style='color:{SUFRA_CRIMSON};'>{cancelled_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🍽️ 6. Merchant Dominance & Cuisine Preferences")
    rest_perf = df_filtered.groupby(['restaurant_name', 'cuisine']).agg(
        total_orders=('order_id', 'count'),
        avg_overall_rating=('rating', 'mean')
    ).reset_index().sort_values(by='total_orders', ascending=False)
    
    top_merchant = rest_perf.iloc[0]
    
    # 🌟 FIXED LINE: Added unsafe_allow_html=True so HTML formatting doesn't break into string text
    st.markdown(f"**Top Performing Asset:** The most preferred establishment is <b style='color:{SUFRA_CRIMSON};'>{top_merchant['restaurant_name'].upper()}</b> specializing in <b style='color:{MUTED_AMBER};'>{top_merchant['cuisine'].upper()}</b> with <b style='color:{SAGE_MINT};'>{top_merchant['total_orders']:,}</b> total finalized volume orders.", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("#### 11. Multi-Tiered Quality Performance Ledger Matrix")
    rating_pivot = df_filtered.pivot_table(
        values='rating', index=['zone', 'restaurant_name'], columns='customer_type', aggfunc='mean'
    ).reset_index()
    st.dataframe(rating_pivot.style.format({'new': '{:.2f} ⭐', 'repeat': '{:.2f} ⭐'}), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 4: NET FINANCIAL PERFORMANCE
# ==========================================
elif page == "💰 Net Financial Performance":
    st.title("💰 Protected Financial Ledger & Marketing Acquisition Optimization")
    st.markdown("---")
    
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 9. 5-Month Consolidated Operations Profile Ledger")
    monthly_ledger = df_filtered.groupby(['month_num', 'month']).agg(
        expenditure=('discount_amount', 'sum'),
        revenue=('realised_revenue', 'sum'),
        profit=('net_profit', 'sum'),
        total_orders=('order_id', 'count')
    ).reset_index().sort_values(by='month_num')
    
    st.dataframe(monthly_ledger.style.format({
        'expenditure': '{:,.2f} AED', 'revenue': '{:,.2f} AED', 'profit': '{:,.2f} AED', 'total_orders': '{:,}'
    }), use_container_width=True)
    
    total_5m_profit = monthly_ledger['profit'].sum()
    st.markdown(f"<h3 style='color:{SAGE_MINT} !important; margin-top: 15px;'>📊 Total Consolidated 5-Month Realized Profit: {total_5m_profit:,.2f} AED</h3>", unsafe_allow_html=True)
    
    highest_month = monthly_ledger.sort_values(by='total_orders', ascending=False).iloc[0]
    lowest_month = monthly_ledger.sort_values(by='total_orders', ascending=True).iloc[0]
    st.markdown(f"📈 **Volume Fluctuations:** The highest operational volume peaked in **{highest_month['month'].upper()}** ({highest_month['total_orders']:,} orders). The lowest baseline volume occurred in **{lowest_month['month'].upper()}** ({lowest_month['total_orders']:,} orders).")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        hourly_peaks = df_filtered.groupby('hour').size().reset_index(name='orders')
        fig_hr = px.line(hourly_peaks, x='hour', y='orders', markers=True, 
                        line_shape='spline', color_discrete_sequence=[SUFRA_CRIMSON],
                        title="10. Diurnal Structural Hourly Order Distribution Curve")
        fig_hr.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        fig_hr = apply_board_theme(fig_hr)
        st.plotly_chart(fig_hr, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c6:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        day_peaks = df_filtered.groupby(['day_of_week', 'customer_type']).size().reset_index(name='orders')
        fig_day = px.bar(day_peaks, x='day_of_week', y='orders', color='customer_type', 
                         barmode='group', text_auto=True,
                         color_discrete_map={'new': DEEP_SLATE, 'repeat': SAGE_MINT},
                         title="10. Weekly Performance Curve Distributed by Cohort Category")
        fig_day.update_traces(textposition='outside', cliponaxis=False)
        fig_day = apply_board_theme(fig_day)
        st.plotly_chart(fig_day, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 7. Voucher Campaign Acquisition Performance ROI Evaluation")
    promo_perf = df_filtered[df_filtered['promo_code'] != 'no promo'].groupby('promo_code').agg(
        usages=('order_id', 'count'),
        total_discount_borne=('discount_amount', 'sum'),
        acquired_new_users=('customer_type', lambda x: (x == 'new').sum())
    ).reset_index().sort_values(by='usages', ascending=False)
    
    st.dataframe(promo_perf.style.format({'total_discount_borne': '{:,.2f} AED', 'usages': '{:,}', 'acquired_new_users': '{:,}'}), use_container_width=True)
    st.write("💡 *Executive Strategy Pointer:* Ensure that your marketing framework tracks vouchers where the `acquired_new_users` conversion scale is high relative to the `total_discount_borne`. If the ratio falls too flat, the voucher is subsidizing regular users rather than acquiring long-term customer pipelines.")
    st.markdown("</div>", unsafe_allow_html=True)
