import pandas as pd
from pathlib import Path

path = Path(r"d:\Me\UofL\Data Analytics & System Optimization (DASO)\MetroSafe Drone-Project\MetroSafe-UofL_Drone_Optimization\output\clean_and_geocoded_LMPD_data_2025.xlsx")

SPANISH_DOW = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves", 4: "viernes", 5: "sabado", 6: "domingo"}

def spanish_dow(dt):
    return SPANISH_DOW[pd.Timestamp(dt).dayofweek]

df = pd.read_excel(path)
df["date_occurred"] = pd.to_datetime(df["date_occurred"], errors="coerce")
df = df.dropna(subset=["date_occurred"])
df["calendar_date"] = df["date_occurred"].dt.normalize()

total_rows = len(df)
min_date = df["calendar_date"].min()
max_date = df["calendar_date"].max()

daily = df.groupby("calendar_date").size().rename("count").sort_index()
full_range = pd.date_range(min_date, max_date, freq="D")
daily_full = daily.reindex(full_range, fill_value=0)

mean_daily = daily_full.mean()

max_count = int(daily.max())
max_dates = daily[daily == daily.max()].index

min_count_positive = int(daily.min())
min_dates_positive = daily[daily == daily.min()].index

min_count_all = int(daily_full.min())
min_dates_all = daily_full[daily_full == daily_full.min()].index

diff_mean = (daily_full - mean_daily).abs()
closest_mean_dates = daily_full[diff_mean == diff_mean.min()].index
closest_mean_count = int(daily_full.loc[closest_mean_dates[0]])

dow_df = daily_full.reset_index()
dow_df.columns = ["calendar_date", "count"]
dow_df["dow"] = dow_df["calendar_date"].dt.dayofweek
dow_agg = dow_df.groupby("dow")["count"].agg(sum="sum", num_days="count", mean="mean")
dow_mean = dow_agg["mean"]

max_dow = int(dow_mean.idxmax())
min_dow = int(dow_mean.idxmin())
diff_dow_mean = (dow_mean - mean_daily).abs()
closest_dow = int(diff_dow_mean.idxmin())

print("=" * 60)
print("ANALISIS LMPD 2025 - date_occurred")
print("=" * 60)
print()
print("1. TOTAL FILAS Y RANGO DE FECHAS")
print(f"   Total filas (con fecha valida): {total_rows:,}")
print(f"   Fecha minima: {min_date.date()} ({spanish_dow(min_date)})")
print(f"   Fecha maxima: {max_date.date()} ({spanish_dow(max_date)})")
print(f"   Dias en el rango calendario: {len(full_range)}")
print()
print("2. CONTEO DIARIO (resumen)")
print(f"   Dias con al menos 1 incidente: {len(daily)}")
print(f"   Incidentes totales: {int(daily_full.sum()):,}")
print("   Primeras 10 fechas con incidentes:")
for d, c in daily.head(10).items():
    print(f"     {d.date()} ({spanish_dow(d)}): {c}")
print("   Ultimas 5 fechas con incidentes:")
for d, c in daily.tail(5).items():
    print(f"     {d.date()} ({spanish_dow(d)}): {c}")
print()
print("3. FECHA CON MAS INCIDENTES")
print(f"   Conteo: {max_count}")
for d in max_dates:
    print(f"   Fecha: {d.date()} ({spanish_dow(d)})")
print()
print("4. FECHA CON MENOS INCIDENTES")
print("   Entre dias con >= 1 incidente:")
print(f"     Conteo: {min_count_positive}")
for d in min_dates_positive:
    print(f"     Fecha: {d.date()} ({spanish_dow(d)})")
print("   Entre todos los dias del rango (ceros incluidos):")
print(f"     Conteo: {min_count_all}")
for d in min_dates_all:
    print(f"     Fecha: {d.date()} ({spanish_dow(d)})")
print()
print("5. MEDIA DIARIA DE INCIDENTES")
print(f"   Media (todos los dias del rango): {mean_daily:.6f}")
print()
print("6. FECHA MAS CERCANA A LA MEDIA")
print(f"   Media objetivo: {mean_daily:.6f}")
for d in closest_mean_dates:
    c = int(daily_full.loc[d])
    print(f"   Fecha: {d.date()} ({spanish_dow(d)}) | conteo={c} | diff={abs(c-mean_daily):.6f}")
print()
print("7. ANALISIS POR DIA DE LA SEMANA")
print("   Promedio diario por weekday (dias del rango con ceros):")
for dow in range(7):
    print(f"   {SPANISH_DOW[dow].capitalize():10s}: promedio={dow_mean.loc[dow]:.4f}  suma={int(dow_agg.loc[dow,'sum'])}  n_dias={int(dow_agg.loc[dow,'num_days'])}")
print()
print(f"   Mayor promedio: {SPANISH_DOW[max_dow].capitalize()} ({dow_mean[max_dow]:.4f})")
print(f"   Menor promedio: {SPANISH_DOW[min_dow].capitalize()} ({dow_mean[min_dow]:.4f})")
print(f"   Mas cercano a media global ({mean_daily:.4f}): {SPANISH_DOW[closest_dow].capitalize()} ({dow_mean[closest_dow]:.4f})")
print("=" * 60)
