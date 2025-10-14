import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import json
import plotly.express as px

# ---------------------------
# 1. Инициализация Firebase через Streamlit Secrets
# ---------------------------
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            creds = dict(st.secrets["firebase"])
            cred = credentials.Certificate(creds)
            firebase_admin.initialize_app(cred, {
                "databaseURL": creds["databaseURL"]
            })
            st.success("✅ Firebase подключён успешно")
        except Exception as e:
            st.error(f"❌ Ошибка инициализации Firebase: {e}")
            return False
    return True
# ---------------------------
# 2. Загрузка данных из Firebase
# ---------------------------
@st.cache_data
def fetch_historical_data():
    """Загрузка исторических данных из Firebase Realtime Database."""
    if not init_firebase():
        return pd.DataFrame()

    try:
        ref = db.reference("metals_data/historical_prices")
        data_by_date = ref.get()
        if not data_by_date:
            st.warning("Данные в Firebase не найдены.")
            return pd.DataFrame()

        df_list = []
        for date_str, metals in data_by_date.items():
            date = pd.to_datetime(date_str)
            for metal, price_data in metals.items():
                df_list.append({
                    "Date": date,
                    "Metal": metal,
                    "Open": price_data.get("Open"),
                    "High": price_data.get("High"),
                    "Low": price_data.get("Low"),
                    "Close": price_data.get("Close"),
                    "Volume": price_data.get("Volume", 0)
                })

        df = pd.DataFrame(df_list)
        df["Date"] = pd.to_datetime(df["Date"])
        return df.sort_values(by="Date").reset_index(drop=True)
    except Exception as e:
        st.error(f"Ошибка загрузки данных из Firebase: {e}")
        return pd.DataFrame()

# ---------------------------
# 3. Основная функция Dashboard
# ---------------------------
def main():
    st.set_page_config(page_title="Dashboard драгоценных металлов", layout="wide")
    st.title("📊 Dashboard драгоценных металлов")

    df = fetch_historical_data()
    if df.empty:
        st.warning("Нет данных для отображения.")
        return

    metals_list = df["Metal"].unique().tolist()
    selected_metals = st.sidebar.multiselect("Выберите металлы:", metals_list, default=[metals_list[0]])

    # Диапазон дат
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    date_range = st.sidebar.date_input(
        "Выберите период:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Фильтрация по выбору
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    # График
    if selected_metals:
        plot_df = filtered_df[filtered_df["Metal"].isin(selected_metals)]
        fig = px.line(plot_df, x="Date", y="Close", color="Metal", 
                      title="Цены металлов (Close)", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Выберите хотя бы один металл для графика.")

    # Последние N дней
    last_days = st.sidebar.number_input("Количество последних дней для таблицы:", min_value=1, max_value=30, value=5)
    if selected_metals:
        table_df = filtered_df[filtered_df["Metal"].isin(selected_metals)].tail(last_days)
        st.subheader(f"Последние {last_days} дней цен")
        st.dataframe(table_df.pivot(index="Date", columns="Metal", values="Close"))

# ---------------------------
# 4. Запуск
# ---------------------------
if __name__ == "__main__":
    main()
