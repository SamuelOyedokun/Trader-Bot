import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import datetime
import io
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def generate_sales_chart(rows, title="Sales Chart"):
    if not rows:
        return None

    daily = {}
    for r in rows:
        date = r["created_at"][:10]
        if date not in daily:
            daily[date] = {"revenue": 0, "profit": 0}
        daily[date]["revenue"] += r["selling_price"] * r["quantity"]
        daily[date]["profit"] += r["profit"]

    dates = sorted(daily.keys())
    revenues = [daily[d]["revenue"] for d in dates]
    profits = [daily[d]["profit"] for d in dates]
    labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%b %d") for d in dates]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(dates))
    width = 0.35

    ax.bar([i - width/2 for i in x], revenues, width, label="Revenue", color="#2196F3")
    ax.bar([i + width/2 for i in x], profits, width, label="Profit", color="#4CAF50")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"₦{v:,.0f}"))
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return buf


def generate_top_products_chart(products, title="Top Products"):
    if not products:
        return None

    names = [p[0] for p in products]
    revenues = [p[1]["revenue"] for p in products]
    rois = [p[1]["roi"] for p in products]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0"]

    ax1.barh(names, revenues, color=colors[:len(names)])
    ax1.set_title("Revenue by Product", fontweight="bold")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"₦{v:,.0f}"))
    ax1.grid(axis="x", alpha=0.3)

    ax2.barh(names, rois, color=colors[:len(names)])
    ax2.set_title("ROI % by Product", fontweight="bold")
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.grid(axis="x", alpha=0.3)

    plt.suptitle(title, fontsize=13, fontweight="bold")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return buf


def upload_chart(image_buf):
    """Upload chart to Cloudinary and return public URL."""
    try:
        image_buf.seek(0)
        result = cloudinary.uploader.upload(
            image_buf,
            folder="traderbot_charts",
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None