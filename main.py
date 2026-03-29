import streamlit as st
import yfinance as yf
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time # NOUVEAU : Importation pour la fonction de rafraîchissement en temps réel

# ===================== CONFIG ===================== #
st.set_page_config(page_title="Dashboard Boursier", layout="wide")

# ===================== STYLE ===================== #
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #f8f9fa;
    color: #212529;
}
.main {
    background-color: #ffffff;
}
h1, h2, h3, h4, h5, h6 {
    color: #2962ff;
}
.stMetric {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #dee2e6;
}
.metric-positive {
    color: #26a69a !important;
}
.metric-negative {
    color: #ef5350 !important;
}
/* Amélioration de la lisibilité */
.stDataFrame {
    background-color: white;
}
div[data-testid="stExpander"] {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

st.title("Dashboard Boursier")

# ===================== CHARGEMENT DES TICKERS ===================== #
@st.cache_data
def load_sp500():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    table = pd.read_csv(url)
    table["symbol_name"] = table["Symbol"] + " - " + table["Security"]
    return table[["Symbol", "symbol_name"]]

tickers = load_sp500()

# ===================== SIDEBAR ===================== #
with st.sidebar:
    st.header("Contrôles du Dashboard")
    selected = st.multiselect("Choisir des actions", tickers.symbol_name)
    selected_symbols = tickers[tickers.symbol_name.isin(selected)]["Symbol"].tolist()
    # Date de fin définie comme aujourd'hui pour les données historiques (limitées à la dernière clôture)
    start = st.date_input("Date de début", dt.datetime(2023, 1, 1))
    end = st.date_input("Date de fin", dt.datetime.now()) # Correction: .date() pour éviter les problèmes de fuseau horaire
    
    st.markdown("---")
    st.markdown("### Paramètres d'analyse")
    ma_short = st.slider("MA court terme", 5, 50, 20)
    ma_long = st.slider("MA long terme", 20, 200, 50)

# ===================== FONCTIONS ===================== #
@st.cache_data
def load_prices(symbols, start, end):
    if not symbols:
        return None
    # Pour les prix historiques, nous utilisons la date de fin définie par l'utilisateur
    data = yf.download(symbols, start=start, end=end)["Close"].reset_index()
    data = data.melt(id_vars="Date", var_name="ticker", value_name="price")
    data["price_start"] = data.groupby("ticker")["price"].transform("first")
    data["return_pct"] = (data["price"] - data["price_start"]) / data["price_start"]
    return data

@st.cache_data(ttl=60) # Rafraîchissement du cache toutes les 60 secondes pour les données intraday
def load_intraday(symbol):
    """Charge les données intraday pour aujourd'hui avec un intervalle de 5 minutes."""
    ticker = yf.Ticker(symbol)
    # period="1d" assure que nous obtenons les données du jour, si le marché est ouvert
    hist = ticker.history(period="1d", interval="5m")
    return hist

def get_quarterly_financials(ticker_obj):
    """Récupère les données financières trimestrielles"""
    try:
        quarterly_financials = ticker_obj.quarterly_financials
        quarterly_balance = ticker_obj.quarterly_balance_sheet
        quarterly_cashflow = ticker_obj.quarterly_cashflow
        return quarterly_financials, quarterly_balance, quarterly_cashflow
    except:
        return None, None, None

def calculate_seasonality(df):
    """Analyse de saisonnalité"""
    df = df.copy()
    df['month'] = pd.to_datetime(df['Date']).dt.month
    df['return'] = df['price'].pct_change()
    monthly_perf = df.groupby('month')['return'].mean() * 100
    return monthly_perf

# ===================== CHARGEMENT DES DONNÉES ===================== #
df = load_prices(selected_symbols, start, end)

# ===================== TABS ===================== #
if selected_symbols:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Vue d'ensemble",
        "Analyse Technique",
        "Analyse Financière",
        "Corrélation",
        "Données"
    ])

    # ===================== TAB 1 — VUE D'ENSEMBLE (INTRA-DAY LIVE) ===================== #
    with tab1:
        for sym in selected_symbols:
            ticker = yf.Ticker(sym)
            info = ticker.info
            
            # En-tête avec logo et infos entreprise
            col_logo, col_info = st.columns([1, 4])
            
            with col_logo:
                logo_url = info.get('logo_url', '')
                if logo_url:
                    st.image(logo_url, width=100)
                else:
                    st.markdown(f"### {sym}")
            
            with col_info:
                st.markdown(f"## {info.get('longName', sym)}")
                st.markdown(f"**Secteur:** {info.get('sector', 'N/A')} | **Industrie:** {info.get('industry', 'N/A')}")
                st.markdown(f"**Site web:** {info.get('website', 'N/A')}")
            
            st.markdown("---")
            
            # Informations générales de l'entreprise
            with st.expander("ℹ️ Informations générales sur l'entreprise", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Capitalisation", f"${info.get('marketCap', 0)/1e9:.2f}B")
                    st.metric("P/E Ratio", f"{info.get('trailingPE', 0):.2f}")
                
                with col2:
                    st.metric("Employés", f"{info.get('fullTimeEmployees', 0):,}")
                    st.metric("Beta", f"{info.get('beta', 0):.2f}")
                
                with col3:
                    st.metric("Dividende", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A")
                    st.metric("52W High", f"${info.get('fiftyTwoWeekHigh', 0):.2f}")
                
                with col4:
                    st.metric("Volume moy.", f"{info.get('averageVolume', 0):,.0f}")
                    st.metric("52W Low", f"${info.get('fiftyTwoWeekLow', 0):.2f}")
                
                # Description de l'entreprise
                st.markdown("### À propos")
                st.write(info.get('longBusinessSummary', 'Description non disponible'))
            
            st.markdown("---")
            
            # Métriques en temps réel
            st.markdown("### Cotation en temps réel")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            current_price = info.get('currentPrice', 0)
            prev_close = info.get('previousClose', 0)
            change = current_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            col1.metric("Prix actuel", f"${current_price:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
            col2.metric("Ouverture", f"${info.get('open', 0):.2f}")
            col3.metric("Plus haut", f"${info.get('dayHigh', 0):.2f}")
            col4.metric("Plus bas", f"${info.get('dayLow', 0):.2f}")
            col5.metric("Volume", f"{info.get('volume', 0):,.0f}")
            
            # Graphique Intraday SANS prédictions
            st.markdown("### Performance Intraday (Rafraîchissement automatique si marché ouvert)")
            
            try:
                # Comme la fonction load_intraday est cachée avec ttl=60, elle rafraîchira les données toutes les minutes
                intraday_data = load_intraday(sym)
                
                if not intraday_data.empty:
                    fig_intraday = go.Figure()
                    
                    # Chandelier intraday
                    fig_intraday.add_trace(go.Candlestick(
                        x=intraday_data.index,
                        open=intraday_data['Open'],
                        high=intraday_data['High'],
                        low=intraday_data['Low'],
                        close=intraday_data['Close'],
                        name='Prix',
                        increasing_line_color='#26a69a',
                        decreasing_line_color='#ef5350'
                    ))
                    
                    fig_intraday.update_layout(
                        title=f"Graphique intraday - {sym}",
                        yaxis_title="Prix ($)",
                        xaxis_rangeslider_visible=False,
                        height=500,
                        template="plotly_white",
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529')
                    )
                    
                    st.plotly_chart(fig_intraday, use_container_width=True)
                else:
                    st.info("Données intraday non disponibles pour aujourd'hui (marché fermé ou données manquantes)")
            except:
                st.warning(f"Impossible de charger les données intraday pour {sym}")
            
            st.markdown("---")

        # ==================== LOGIQUE DE RAFRAÎCHISSEMENT LIVE ====================
        # Cette logique force l'application à se rafraîchir toutes les 30 secondes.
        # La fonction load_intraday (avec ttl=60) ira chercher de nouvelles données après 60 secondes.
        now = dt.datetime.now()
        
        # Heures d'ouverture approximatives du marché US (9h30 EST - 16h00 EST)
        # Correspond à 15h30 CET à 22h00 CET
        # On vérifie si c'est un jour de semaine (lundi=0 à vendredi=4) ET si l'heure est dans la fenêtre
        is_weekday = now.weekday() < 5
        is_market_time = (now.hour >= 15 and now.hour < 22) or (now.hour == 15 and now.minute >= 30)

        if is_weekday and is_market_time:
            # Indique à l'utilisateur que le rafraîchissement est actif
            st.info(f"Mise à jour automatique : Marché ouvert. Prochain rafraîchissement dans 30 secondes (Dernière mise à jour: {now.strftime('%H:%M:%S')})")
            # Pause l'exécution (bloque Streamlit)
            time.sleep(30)
            # Force le rechargement de l'application Streamlit (démarre le cycle suivant)
            st.rerun() 
        else:
            st.info(f"Mise à jour automatique : Marché fermé ou hors heures. Le rafraîchissement automatique est désactivé.")
        # ==========================================================================
    
    # ===================== TAB 2 — ANALYSE TECHNIQUE ===================== #
    with tab2:
        ticker_tech = st.selectbox("Choisir un ticker", selected_symbols)
        d = df[df["ticker"] == ticker_tech].copy()
        
        # Calcul des indicateurs
        d["SMA_short"] = d.price.rolling(ma_short).mean()
        d["SMA_long"] = d.price.rolling(ma_long).mean()
        d["EMA20"] = d.price.ewm(span=20).mean()
        
        # Bandes de Bollinger
        d["BB_middle"] = d.price.rolling(20).mean()
        d["BB_std"] = d.price.rolling(20).std()
        d["BB_upper"] = d["BB_middle"] + (d["BB_std"] * 2)
        d["BB_lower"] = d["BB_middle"] - (d["BB_std"] * 2)
        
        # Graphique principal
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(x=d["Date"], y=d["price"], 
                                 mode="lines", name="Prix", 
                                 line=dict(color="#2962ff", width=2)))
        
        fig.add_trace(go.Scatter(x=d["Date"], y=d["SMA_short"], 
                                 mode="lines", name=f"SMA{ma_short}",
                                 line=dict(color="#ff6d00", width=1.5)))
        
        fig.add_trace(go.Scatter(x=d["Date"], y=d["SMA_long"], 
                                 mode="lines", name=f"SMA{ma_long}",
                                 line=dict(color="#d500f9", width=1.5)))
        
        fig.add_trace(go.Scatter(x=d["Date"], y=d["BB_upper"], 
                                 mode="lines", name="BB Supérieure",
                                 line=dict(color="rgba(128,128,128,0.5)", width=1, dash="dash")))
        
        fig.add_trace(go.Scatter(x=d["Date"], y=d["BB_lower"], 
                                 mode="lines", name="BB Inférieure",
                                 line=dict(color="rgba(128,128,128,0.5)", width=1, dash="dash"),
                                 fill='tonexty', fillcolor='rgba(128,128,128,0.1)'))
        
        fig.update_layout(
            title=f"Analyse Technique - {ticker_tech}",
            yaxis_title="Prix ($)",
            xaxis_rangeslider_visible=False,
            height=600,
            template="plotly_white",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # RSI & Volume
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### RSI (14)")
            delta = d["price"].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            d["RSI"] = 100 - (100 / (1 + gain / loss))
            
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=d["Date"], y=d["RSI"], 
                                         mode="lines", line=dict(color="#2962ff", width=2)))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef5350", annotation_text="Suracheté")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="#26a69a", annotation_text="Survendu")
            fig_rsi.update_layout(height=300, template="plotly_white", 
                                 plot_bgcolor='white', paper_bgcolor='white',
                                 font=dict(color='#212529'))
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        with col2:
            st.markdown("### Volume")
            ticker_obj = yf.Ticker(ticker_tech)
            hist_volume = ticker_obj.history(start=start, end=end)
            
            fig_vol = go.Figure()
            colors = ['#ef5350' if row['Close'] < row['Open'] else '#26a69a' 
                      for idx, row in hist_volume.iterrows()]
            
            fig_vol.add_trace(go.Bar(x=hist_volume.index, y=hist_volume['Volume'],
                                     marker_color=colors, name="Volume", opacity=0.8))
            fig_vol.update_layout(
                height=300, 
                template="plotly_white",
                plot_bgcolor='white', 
                paper_bgcolor='white',
                font=dict(color='#212529'),
                yaxis=dict(title="Volume", gridcolor='#e0e0e0'),
                xaxis=dict(gridcolor='#e0e0e0')
            )
            st.plotly_chart(fig_vol, use_container_width=True)
    
    # ===================== TAB 3 — ANALYSE FINANCIÈRE (TRIMESTRIELLE) ===================== #
    with tab3:
        st.subheader("Analyse Financière Détaillée (Trimestrielle)")
        
        for sym in selected_symbols:
            st.markdown(f"### {sym}")
            t = yf.Ticker(sym)
            
            # Récupération des données TRIMESTRIELLES
            q_fin, q_bs, q_cf = get_quarterly_financials(t)
            info = t.info
            
            if q_fin is None or q_fin.empty:
                st.warning(f"Données financières trimestrielles non disponibles pour {sym}")
                continue
            
            try:
                # Extraction des données trimestrielles
                revenue = q_fin.loc["Total Revenue"].dropna() if "Total Revenue" in q_fin.index else pd.Series()
                net_income = q_fin.loc["Net Income"].dropna() if "Net Income" in q_fin.index else pd.Series()
                
                if len(revenue) == 0:
                    st.warning(f"Données de revenus insuffisantes pour {sym}")
                    continue
                
                # COGS et marges
                cogs = q_fin.loc["Cost Of Revenue"].reindex(revenue.index) if "Cost Of Revenue" in q_fin.index else pd.Series([0]*len(revenue), index=revenue.index)
                gross_profit = revenue - cogs
                gross_margin = (gross_profit / revenue * 100).fillna(0)
                net_margin = (net_income / revenue * 100).fillna(0)
                
                # Operating Income
                operating_income = q_fin.loc["Operating Income"].reindex(revenue.index) if "Operating Income" in q_fin.index else pd.Series([0]*len(revenue), index=revenue.index)
                
                # Données du bilan
                total_debt = q_bs.loc["Total Debt"].reindex(revenue.index) if q_bs is not None and "Total Debt" in q_bs.index else pd.Series([0]*len(revenue), index=revenue.index)
                cash = q_bs.loc["Cash And Cash Equivalents"].reindex(revenue.index) if q_bs is not None and "Cash And Cash Equivalents" in q_bs.index else pd.Series([0]*len(revenue), index=revenue.index)
                
                # Free Cash Flow
                fcf = q_cf.loc["Free Cash Flow"].reindex(revenue.index) if q_cf is not None and "Free Cash Flow" in q_cf.index else pd.Series([0]*len(revenue), index=revenue.index)
                
                # Affichage en 2 colonnes comme TradingView
                col1, col2 = st.columns(2)
                
                # GRAPHIQUE 1 : Revenue, Net Income, Net Margin
                with col1:
                    st.markdown("**Revenus, Résultat Net & Marge Nette**")
                    
                    fig1 = go.Figure()
                    
                    # Barres pour Revenue et Net Income
                    fig1.add_trace(go.Bar(
                        x=revenue.index.astype(str),
                        y=revenue/1e9,
                        name="Revenus (Mrd $)",
                        marker_color='#2962ff',
                        yaxis='y'
                    ))
                    
                    fig1.add_trace(go.Bar(
                        x=net_income.index.astype(str),
                        y=net_income/1e9,
                        name="Résultat Net (Mrd $)",
                        marker_color='#26a69a',
                        yaxis='y'
                    ))
                    
                    # Ligne pour la marge nette
                    fig1.add_trace(go.Scatter(
                        x=net_margin.index.astype(str),
                        y=net_margin,
                        name="Marge Nette (%)",
                        line=dict(color='#ff6d00', width=3),
                        yaxis='y2',
                        mode='lines+markers'
                    ))
                    
                    fig1.update_layout(
                        yaxis=dict(title="Montants (Mrd $)", side='left'),
                        yaxis2=dict(title="Marge (%)", overlaying="y", side="right"),
                        template="plotly_white",
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529'),
                        barmode='group',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                # GRAPHIQUE 2 : Debt, Free Cash Flow, Cash
                with col2:
                    st.markdown("**Dette, Free Cash Flow & Trésorerie**")
                    
                    fig2 = go.Figure()
                    
                    fig2.add_trace(go.Bar(
                        x=total_debt.index.astype(str),
                        y=pd.to_numeric(total_debt, errors='coerce')/1e9,
                        name="Dette Totale (Mrd $)",
                        marker_color='#ef5350'
                    ))
                    
                    fig2.add_trace(go.Bar(
                        x=fcf.index.astype(str),
                        y=pd.to_numeric(fcf, errors='coerce')/1e9,
                        name="Free Cash Flow (Mrd $)",
                        marker_color='#7cb342'
                    ))
                    
                    fig2.add_trace(go.Bar(
                        x=cash.index.astype(str),
                        y=pd.to_numeric(cash, errors='coerce')/1e9,
                        name="Trésorerie (Mrd $)",
                        marker_color='#42a5f5'
                    ))
                    
                    fig2.update_layout(
                        yaxis_title="Montants (Mrd $)",
                        template="plotly_white",
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529'),
                        barmode='group',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # GRAPHIQUE 3 : Waterfall Chart (Revenue -> Net Income)
                st.markdown("**Conversion CA : Bénéfit**")
                
                latest_idx = revenue.index[0]
                waterfall_data = [
                    ("Revenue", revenue.iloc[0]/1e9),
                    ("COGS", -cogs.iloc[0]/1e9 if len(cogs) > 0 else 0),
                    ("Gross Profit", gross_profit.iloc[0]/1e9 if len(gross_profit) > 0 else 0),
                    ("Operating Income", operating_income.iloc[0]/1e9 if len(operating_income) > 0 else 0),
                    ("Net Income", net_income.iloc[0]/1e9)
                ]
                
                fig3 = go.Figure(go.Waterfall(
                    name="",
                    orientation="v",
                    measure=["absolute", "relative", "total", "relative", "total"],
                    x=[item[0] for item in waterfall_data],
                    y=[item[1] for item in waterfall_data],
                    textposition="outside",
                    text=[f"${val:.2f}B" for _, val in waterfall_data],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    increasing={"marker": {"color": "#26a69a"}},
                    decreasing={"marker": {"color": "#ef5350"}},
                    totals={"marker": {"color": "#2962ff"}}
                ))
                
                fig3.update_layout(
                    title=f"Analyse des revenus (Trimestre {latest_idx})",
                    yaxis_title="Montants (Mrd $)",
                    template="plotly_white",
                    height=400,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#212529')
                )
                st.plotly_chart(fig3, use_container_width=True)
                
                # NOUVEAU : Graphique supplémentaire - Évolution des marges
                st.markdown("**Évolution des Marges (Gross, Operating, Net)**")
                
                operating_margin = (operating_income / revenue * 100).fillna(0)
                
                margins_df = pd.DataFrame({
                    'Quarter': revenue.index.astype(str),
                    'Marge Brute': gross_margin.values,
                    'Marge Opérationnelle': operating_margin.values,
                    'Marge Nette': net_margin.values
                })
                
                fig_margins = go.Figure()
                
                fig_margins.add_trace(go.Scatter(
                    x=margins_df['Quarter'],
                    y=margins_df['Marge Brute'],
                    name='Marge Brute (%)',
                    line=dict(color='#2962ff', width=3),
                    mode='lines+markers'
                ))
                
                fig_margins.add_trace(go.Scatter(
                    x=margins_df['Quarter'],
                    y=margins_df['Marge Opérationnelle'],
                    name='Marge Opérationnelle (%)',
                    line=dict(color='#ff6d00', width=3),
                    mode='lines+markers'
                ))
                
                fig_margins.add_trace(go.Scatter(
                    x=margins_df['Quarter'],
                    y=margins_df['Marge Nette'],
                    name='Marge Nette (%)',
                    line=dict(color='#26a69a', width=3),
                    mode='lines+markers'
                ))
                
                fig_margins.update_layout(
                    yaxis_title="Marges (%)",
                    template="plotly_white",
                    height=400,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#212529'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_margins, use_container_width=True)
                
                # Graphiques en 2 colonnes
                col3, col4 = st.columns(2)
                
                with col3:
                    st.markdown("**Performance Saisonnière (par mois)**")
                    seasonal_data = calculate_seasonality(df[df["ticker"] == sym])
                    
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(
                        x=seasonal_data.index,
                        y=seasonal_data.values,
                        marker_color=['#26a69a' if x > 0 else '#ef5350' for x in seasonal_data.values],
                        text=[f"{x:.2f}%" for x in seasonal_data.values],
                        textposition='outside'
                    ))
                    fig4.update_layout(
                        xaxis_title="Mois",
                        yaxis_title="Rendement moyen (%)",
                        template="plotly_white",
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529')
                    )
                    st.plotly_chart(fig4, use_container_width=True)
                
                with col4:
                    st.markdown("**Revenue vs Net Income**")
                    
                    # Créer dataframe pour le bubble chart
                    bubble_df = pd.DataFrame({
                        'Quarter': revenue.index.astype(str),
                        'Revenue': revenue.values / 1e9,
                        'Net Income': net_income.values / 1e9,
                        'Gross Margin': gross_margin.values
                    })
                    
                    fig_bubble = px.scatter(
                        bubble_df,
                        x='Revenue',
                        y='Net Income',
                        size='Gross Margin',
                        color='Gross Margin',
                        hover_data=['Quarter'],
                        size_max=50,
                        color_continuous_scale='Viridis',
                        labels={
                            'Revenue': 'Chiffre d\'affaires (Mrd $)',
                            'Net Income': 'Résultat Net (Mrd $)',
                            'Gross Margin': 'Marge Brute (%)'
                        }
                    )
                    
                    fig_bubble.update_layout(
                        template="plotly_white",
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529')
                    )
                    st.plotly_chart(fig_bubble, use_container_width=True)
                
                # Prochains résultats
                st.markdown("**Prochains Résultats & Estimations**")
                col_earn1, col_earn2, col_earn3, col_earn4 = st.columns(4)
                
                earnings_dates = info.get('earningsDate', None)
                if earnings_dates:
                    col_earn1.metric("Date publication", str(earnings_dates))
                
                col_earn2.metric("EPS (TTM)", f"${info.get('trailingEps', 0):.2f}")
                col_earn3.metric("EPS Forward", f"${info.get('forwardEps', 0):.2f}")
                col_earn4.metric("P/E Ratio", f"{info.get('trailingPE', 0):.2f}")
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse de {sym}: {str(e)}")
            
            st.markdown("---")
    
    # ===================== TAB 4 — CORRÉLATION ===================== #
    with tab4:
        if df is not None and not df.empty and len(selected_symbols) > 1:
            st.subheader("Comparaison Base 100")
            df_base100 = df.copy()
            df_base100["base100"] = df_base100["price"] / df_base100.groupby("ticker")["price"].transform("first") * 100
            fig_base = px.line(df_base100, x="Date", y="base100", color="ticker")
            fig_base.update_layout(
                template="plotly_white", 
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#212529')
            )
            st.plotly_chart(fig_base, use_container_width=True)
            
            st.subheader("Heatmap de Corrélation")
            corr = df.pivot(index="Date", columns="ticker", values="price").pct_change().corr()
            fig_corr = px.imshow(
                corr, 
                text_auto=".2f", 
                color_continuous_scale="RdBu",
                aspect="auto"
            )
            fig_corr.update_layout(
                template="plotly_white", 
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#212529')
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Sélectionnez au moins 2 actions pour l'analyse de corrélation")
    
    # ===================== TAB 5 — DONNÉES ===================== #
    with tab5:
        st.subheader("Données Brutes")
        if df is not None:
            st.dataframe(df, use_container_width=True)
            
            st.subheader("Statistiques Descriptives")
            stats = df.groupby("ticker")["price"].agg(["mean", "std", "min", "max", "count"])
            st.dataframe(stats, use_container_width=True)

else:
    st.info("Selectionnez des actions dans la barre latérale pour commencer l'analyse")