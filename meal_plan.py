import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import seaborn as sns
from wordcloud import WordCloud
import io
from flask import Flask, Response, render_template, request, redirect, url_for,session
import base64
import os
import tempfile





app = Flask(__name__)
app.secret_key = "space100"
@app.route('/')
def index():
	return render_template("index.html")

def clean(df):
	#df = pd.read_excel(file)
	#remove empty columns
	df = df.dropna(axis=1, how='all')

	#remove sales ID
	df.drop('_item_card_itemdetails_chylw_23 3', axis = 1, inplace = True)

	#convert second column to date
	df['Date'] = pd.to_datetime(df['_item_card_itemdetails_chylw_23 2'],errors = 'coerce')

	#remove column and remain with date
	df.drop('_item_card_itemdetails_chylw_23 2', axis = 1, inplace=True)

	#remove null values from date
	df.dropna(subset=['Date'], inplace = True)

	#rename Cafe column
	df = df.rename(columns={'_item_card_itemdetails_chylw_23 4': 'Cafe'})

	#replace Akorno Services Ltd - Main Cafe with Arkono
	df['Cafe'] = df['Cafe'].replace({'Akorno Services Ltd - Main Cafe':'Arkono',
									'Akorno Services Ltd - Hakuna Matata':'Hakuna',
									'Munchies Services Ltd': 'Munchies'})

	#change first column to details
	df = df.rename(columns={'_item_card_itemdetails_chylw_23': 'details'})

	#extract items
	df[['Items','other']] = df['details'].str.split(':', expand=True)
	df['Items'] = df['Items'].str.strip()

	#remove details column
	df.drop('details',axis=1,inplace=True)

	#extract quantity and amount paid and convert each to numbers for calculations
	df[['Quantity','Amount Paid (GHC)']] = df['other'].str.split('-',expand=True)
	df['Quantity'] = df['Quantity'].str.strip()
	df['Amount Paid (GHC)'] = df['Amount Paid (GHC)'].str.strip()
	#remain with numeric number for each
	df['Quantity'] = df['Quantity'].str.replace(r'[^0-9]','',regex=True)
	df['Amount Paid (GHC)'] = df['Amount Paid (GHC)'].str.replace(r'[^0-9.]','',regex=True)
	df['Amount Paid (GHC)'] = pd.to_numeric(df['Amount Paid (GHC)'],errors='coerce')
	df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
	#remove 'other' column
	df.drop('other', axis=1,inplace=True)
	return df

def clean_items(df):
	df['Items'] = df['Items'].str.lower()
	df['Items'] = df['Items'].replace({'small bottle water': 'water 0.5l',
		'deluxe protein': 'deluxe',
		'jollof protein':'jollof',
		'mini don simon': 'don simon 0.5l',
		'indomie protein': 'indomie',
		'big bottle water': 'water 1.5l',
		'fresh pineapple juice': 'pineapple juice',
		'fries & protein': 'fries',
		'paper pack': 'pack'})
	df.loc[df['Items'].str.contains('staff discount', case=False, na=False), 'Items'] = 'staff discount'
	df.loc[df['Items'].str.contains('splash', case=False, na=False), 'Items'] = 'splash'
	df.loc[df['Items'].str.contains('pack', case=False, na=False), 'Items'] = 'pack'
	df.loc[df['Items'].str.contains('arkono regular', case=False, na=False), 'Items'] = 'arkono regular'
	df.loc[df['Items'].str.contains('yam chips', case=False, na=False), 'Items'] = 'yam chips'
	return df


def add_columns(df):
	#separate date elements
	df['Day'] =df['Date'].dt.date
	df['Weekday']=df['Date'].dt.day_name()
	df['Hour'] = df['Date'].dt.hour

	return df

@app.route("/upload", methods= ["POST"])
def upload_file():
    file = request.files["file"]
    if file.filename.endswith(".xlsx"):
        df = pd.read_excel(file)
        df = clean(df)
        df = clean_items(df)
        df = add_columns(df)

        # Save to temporary CSV so it's not lost
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        df.to_csv(tmp_file, index=False)
        session["data_file"] = tmp_file

        return redirect(url_for("index"))
    return "Invalid file type"

def get_df():
    tmp_file = session.get("data_file")
    if tmp_file and os.path.exists(tmp_file):
        return pd.read_csv(tmp_file, parse_dates=["Date"])
    return None


def render_matplotlib():
    '''img = io.BytesIO()
                  plt.savefig(img, format="png", bbox_inches="tight")
                  img.seek(0)
                  plt.close()
                  plot_url = base64.b64encode(img.getvalue()).decode()''' 
    img = io.BytesIO()

    # 🔹 Force larger and higher resolution output
    plt.gcf().set_size_inches(14, 7)   # width=14in, height=7in
    plt.savefig(img, format="png", dpi=150, bbox_inches="tight")

    img.seek(0)
    plt.close()
    plot_url = base64.b64encode(img.getvalue()).decode() 
    return render_template("plot.html", plot_url=plot_url)


@app.route('/cafe_spendings')

def cafe_spendings():
	df = get_df()
	if df is None:
		return "No data uploaded yet."
	''' show amount spent per cafe over a period of time'''
	cafe_spending = df.groupby('Cafe')['Amount Paid (GHC)'].sum().reset_index()
	
	sns.barplot(data=cafe_spending, x="Cafe", y="Amount Paid (GHC)")
	plt.title("Cafe Spendings")
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	return render_matplotlib()

@app.route('/cafe_demographics')

def cafe_demographics():
	df = get_df()
	if df is None:
		return "No data uploaded yet."
	''' display percentage of money spent on each cafe'''
	cafe_spending = df.groupby('Cafe')['Amount Paid (GHC)'].sum()
	plt.pie(cafe_spending, labels=cafe_spending.index, autopct='%1.1f%%', startangle=90)
	plt.title("Spending by Cafe")
	plt.axis('equal')
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	return render_matplotlib()
	
@app.route('/cafe_hourly_visits')

def cafe_hourly_visits():
	df = get_df()
	if df is None:
		return "No data uploaded yet."
	''' display visits on each cafe per hour of day'''

	'''cafe_visits = df.groupby(['Cafe','Hour']).size().reset_index(name ='Visits')
				sns.lineplot(data=cafe_visits,x='Hour',y='Visits',hue='Cafe',marker='o',markersize=5)
				plt.title("Cafe Visits by hour of day in 24 hour notation")
				plt.xlabel("Hour of Day")
				plt.ylabel("Number of Visits")
				
				plt.grid(True, linestyle='--', alpha=0.5)
				plt.xticks(rotation=45, ha="right")
				plt.tight_layout()'''
	cafe_visits = df.groupby(['Cafe','Hour']).size().reset_index(name='Visits')
	hours = range(24)
	cafes = cafe_visits['Cafe'].unique()
	full_index = pd.MultiIndex.from_product([cafes, hours], names=['Cafe','Hour'])
	cafe_visits = cafe_visits.set_index(['Cafe','Hour']).reindex(full_index, fill_value=0).reset_index()
	plt.figure(figsize=(14,7))
	sns.lineplot(data=cafe_visits, x='Hour', y='Visits', hue='Cafe',
                 marker='o', markersize=6, linewidth=2)
	plt.title("Cafe Visits by Hour (24h)", fontsize=16, weight="bold")
	plt.xlabel("Hour of Day", fontsize=12)
	plt.ylabel("Number of Visits", fontsize=12)
	plt.xticks(range(0,24)) 
	plt.grid(True, linestyle='--', alpha=0.5)
	plt.tight_layout()
	return render_matplotlib()


@app.route('/cafe_daily_visits')

def cafe_daily_visits():
	df = get_df()
	if df is None:
		return "No data uploaded yet."
	''' display visits on each cafe per day of week'''
	weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
	df['Weekday'] = pd.Categorical(df['Weekday'], categories=weekday_order, ordered=True)

	cafe_visits = df.groupby(['Cafe','Weekday']).size().reset_index(name ='Visits')
	sns.lineplot(data=cafe_visits,x='Weekday',y='Visits',hue='Cafe',marker='o')

	plt.title("Cafe Visits by Day of week")
	plt.xlabel("Day of week")
	plt.ylabel("Number of Visits")
	plt.xticks(rotation=45)
	plt.grid(True, linestyle='--', alpha=0.5)
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	

	
	return render_matplotlib()
@app.route('/cafe_product')

def cafe_product():
	''' display favorite product per cafe excluding water'''
	df = get_df()
	if df is None:
		return "No data uploaded yet."

	def mode_products(x):
		modes = x.mode()
		for item in modes:
			if item.lower() not in ['staff discount','top up','water 0.5l']:
				return item
		return None
	common_product = df.groupby('Cafe')['Items'].agg(mode_products).reset_index(name = 'Regular purchase')
	common_product_html = common_product.to_html(classes="table table-striped", index=False)
	return render_template("table.html", table=common_product_html)

@app.route('/water_intake')

def water_intake():
	''' show amount of of water bought on a specific period'''
	df = get_df()
	if df is None:
		return "No data uploaded yet."

	small_water = df[df['Items']=='water 0.5l']['Quantity'].sum()
	big_water = df[df['Items']=='water 1.5l']['Quantity'].sum()
	water_bought= f'Over this period you bought {small_water} 500mls and {big_water} 1.5Ls of water'
	total_water = (0.5*small_water) + (1.5*big_water)
	total_litres =f'In total you drank {total_water} litres of water'
	return f'{water_bought} <br> {total_litres}'

@app.route('/spending_wordcloud')

def spending_wordcloud():
	''' display popular products'''
	df = get_df()
	if df is None:
		return "No data uploaded yet."

	weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
	df['Weekday'] = pd.Categorical(df['Weekday'], categories=weekday_order, ordered=True)
	def edit_data(item):
		if pd.isna(item) or item == 'staff discount':
			return None
		return item.replace(' ','')
	df['Items1'] = df['Items'].apply(edit_data)
	items = ' '.join(df['Items1'].dropna().astype('str'))
	w_cloud = WordCloud(width=800, height=400, background_color='white').generate(items)

	plt.imshow(w_cloud, interpolation="bilinear")
	plt.axis("off")
	plt.title("Most Common Products")

	return render_matplotlib()


@app.route('/spending_per_hour')

def spending_per_hour():
	''' display amount spent on each day of the week'''
	df = get_df()
	if df is None:
		return "No data uploaded yet."
	spend_time = df.groupby('Hour')['Amount Paid (GHC)'].sum().reset_index(name ='Total Spending')
	sns.barplot(data = spend_time,x='Hour',y='Total Spending')
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	

	
	return render_matplotlib()


@app.route('/meals')

def meals():
	''' display to ten meals'''
	df = get_df()
	if df is None:
		return "No data uploaded yet."

	exclude = ['staff discount','top up']
	meal_freq = df.groupby('Items')['Quantity'].sum().reset_index(name='Total Purchases')
	meal_freq = meal_freq[~meal_freq['Items'].isin(exclude)].sort_values(by = 'Total Purchases', ascending = False).head(10)
	sns.barplot(data=meal_freq,x='Items', y='Total Purchases')
	plt.title('Top ten most purchased items')
	plt.xlabel('Item')
	plt.ylabel('Total Purchases')
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()

	
	return render_matplotlib()

if __name__ == "__main__":
	app.run(debug=True)






