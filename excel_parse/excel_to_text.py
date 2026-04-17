import sys
import pandas as pd

file_name = sys.argv[1]
df = pd.read_excel(file_name)

date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns
df[date_cols] = df[date_cols].apply(lambda c: c.dt.strftime('%Y-%m-%d'))

print(df.to_csv(index=False))

