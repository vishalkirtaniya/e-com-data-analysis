import pandas as pd
import sqlite3

conn = sqlite3.connect("olist_dataset.db")

# Creating SQLite database
# adding sqlite database, and uploading everything into the sqlite database

table_list = [
    {
        "name": "customers",
        "csv": "olist_customers_dataset.csv",
    },
    {
        "name": "geolocation",
        "csv": "olist_geolocation_dataset.csv",
    },
    {
        "name": "orders",
        "csv": "olist_orders_dataset.csv",
    },
    {
        "name": "order_items",
        "csv": "olist_order_items_dataset.csv",
    },
    {
        "name": "order_reviews",
        "csv": "olist_order_reviews_dataset.csv",
    },
    {
        "name": "order_payments",
        "csv": "olist_order_payments_dataset.csv",
    },
    {
        "name": "sellers",
        "csv": "olist_sellers_dataset.csv",
    }
]

# pre processing the products and replacing portugal categories into english category column
products = pd.read_csv("olist_products_dataset.csv")
products_category = pd.read_csv("product_category_name_translation.csv")

merged_products = pd.merge(products, products_category, on="product_category_name", how="left")
del merged_products["product_category_name"]
merged_products.rename(columns={"product_category_name_english" :"product_category_name"}, inplace=True)
merged_products.to_sql("products", conn, if_exists="replace", index=False)

# reading the csv of every dataset and adding it to sqlite
for table in table_list:
    df = pd.read_csv(table["csv"])
    df.to_sql(table["name"], conn, if_exists='replace', index=False)

# # Starting Analysis from Here on Out

## Calculating the Revenue per Customer, Total Revenue (Cumulative) and Revenue per Order

# here we are actually checking the revenue, and number of customers who are one time or repeat customers, and which customer actually buys more per order.

total_revenue = """
        SELECT 
            "c"."customer_unique_id", 
            COUNT(DISTINCT "o"."order_id") as "order_count", 
            SUM("ot"."price" + "ot"."freight_value") as total_revenue
        FROM "customers" "c"
        LEFT JOIN "orders" "o"
            ON "c"."customer_id" = "o"."customer_id"
        LEFT JOIN "order_items" "ot"
            ON "o"."order_id" = "ot"."order_id"
        WHERE "o"."order_status" = 'delivered'
        GROUP BY "c"."customer_unique_id"
    """

revenue_df = pd.read_sql_query(total_revenue, conn)

repeat_revenue_df = revenue_df.loc[revenue_df["order_count"] > 1].copy()
new_revenue_df = revenue_df.loc[revenue_df["order_count"] == 1].copy()

no_of_repeat_customers = repeat_revenue_df["customer_unique_id"].count()
no_of_all_customers = revenue_df["customer_unique_id"].count()

repeat_customers_percent = no_of_repeat_customers / no_of_all_customers * 100
new_customers_percent = 100 - repeat_customers_percent
repeat_customers_mean_revenue = repeat_revenue_df["total_revenue"].mean()
repeat_revenue_df["avg_order_value"] = repeat_revenue_df["total_revenue"] / repeat_revenue_df["order_count"]

new_customers_mean_revenue = new_revenue_df["total_revenue"].mean()
repeat_customers_mean_revenue = repeat_revenue_df["avg_order_value"].mean()

# Plotting a Visual Graph for representing revenue from one time vs repeat customers

import matplotlib.pyplot as plt

one_time = new_revenue_df["total_revenue"]
repeat = repeat_revenue_df["total_revenue"]
avg_repeat = repeat_revenue_df["avg_order_value"]

fig, axes = plt.subplots(1,2, sharex=True, figsize=(10,5))
fig.suptitle("Total Revenue: One-Time vs Repeat Buyers")

categories_0 = ["One-time buyers", "Repeat buyers"]
values_0 = [one_time.mean(), repeat.mean()]
axes[0].bar(categories_0, values_0)
axes[0].set_title("Total Revenue (Cumulative)")
axes[0].set_ylabel("Average Total Revenue ($)")

categories_1 = ["One-time buyers", "Repeat buyers"]
values_1 = [new_customers_mean_revenue, repeat_customers_mean_revenue]
axes[1].bar(categories_1, values_1)
axes[1].set_title("Revenue per Order")
axes[1].set_ylabel("Average total Revenue ($)")


cart_value_query = """
        SELECT 
            "o"."order_id",
            SUM("ot"."price" + "ot"."freight_value") as "total_revenue"
        FROM "orders" "o"
        LEFT JOIN "order_items" "ot"
            ON "o"."order_id" = "ot"."order_id"
        WHERE "o"."order_status" = 'delivered'
        GROUP BY "o"."order_id"
    """
revenue_per_order = pd.read_sql_query(cart_value_query, conn)

mean_revenue_per_order = revenue_per_order["total_revenue"].mean()
median_revenue_per_order = revenue_per_order["total_revenue"].median()

# Average cart value

import numpy as np

bins = np.logspace(np.log10(revenue_per_order["total_revenue"].min()), np.log10(revenue_per_order["total_revenue"].max()), 50)
plt.hist(revenue_per_order["total_revenue"], bins=bins)
plt.xscale('log')
plt.xlabel("Order Total Revenue ($, log scale)")
plt.ylabel("Number of Orders")
plt.title("Distribution of Order Values (Log Scale)")

##  geo revenue vs. customer concentration

revenue_query = """
        SELECT
            "c"."customer_state",
            COUNT(DISTINCT "c"."customer_unique_id") as "customer_count",
            COUNT(DISTINCT "o"."order_id") as "order_count",
            SUM("ot"."price" + "ot"."freight_value") as "state_revenue"
        FROM "customers" "c"
        LEFT JOIN "orders" "o"
            ON "c"."customer_id" = "o"."customer_id"
        LEFT JOIN "order_items" "ot"
            on "o"."order_id" = "ot"."order_id"
        WHERE "o"."order_status" = 'delivered'
        GROUP BY "c"."customer_state"
    """

state_revenue_df = pd.read_sql_query(revenue_query, conn)

state_revenue_df["revenue_per_customer"] = state_revenue_df["state_revenue"] / state_revenue_df["customer_count"]


revenue_per_customer = state_revenue_df[state_revenue_df["customer_count"] >= 300].sort_values("revenue_per_customer", ascending=False)
state_revenue = state_revenue_df.sort_values("state_revenue", ascending=False)

print(state_revenue.head(5))
print(revenue_per_customer.head(5))