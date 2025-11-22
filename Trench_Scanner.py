import requests
from datetime import datetime, timezone, timedelta

# define interval/cat
intervals = ["5m", "1h", "6h", "24h"]
categories = ["toporganicscore", "toptraded", "toptrending"]

# input for market cap filtering
min_mcap = int(input("Enter minimum market cap : "))
max_mcap = int(input("Enter maximum market cap : "))

# Get creation date
def get_created_at(token):
    ts = token.get("firstPool", {}).get("createdAt")
    if ts:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None

# relative time ago 
def time_ago(dt):
    if not dt:
        return "N/A"
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    days = hours // 24
    return f"{days} days ago"

# DexScreener
def check_dex_paid_status(token_address, chain="solana"):
    try:
        url = f"https://api.dexscreener.com/orders/v1/{chain}/{token_address}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        arr = res.json()

        if not isinstance(arr, list) or len(arr) == 0:
            return "unknown"

        for entry in arr:
            if (
                entry.get("type") == "tokenProfile"
                and entry.get("status") == "approved"
            ):
                return "approved"

        valid_entries = [
            entry for entry in arr
            if isinstance(entry.get("paymentTimestamp"), (int, float))
        ]

        if valid_entries:
            latest = max(valid_entries, key=lambda e: e["paymentTimestamp"])
            return latest.get("status", "unknown")

        return "unknown"

    except Exception:
        return "error"

# get all tokens from interval/cat
all_tokens = []

for category in categories:
    for interval in intervals:
        url = f"https://lite-api.jup.ag/tokens/v2/{category}/{interval}?limit=100"
        try:
            res = requests.get(url)
            res.raise_for_status()
            tokens = res.json()
            all_tokens.extend(tokens)
        except Exception as e:
            print(f"Failed to fetch {category} for {interval}: {e}")

# deduplicate by token ID 
unique_tokens = {token["id"]: token for token in all_tokens}.values()

# filter by market cap
filtered_tokens = []
for token in unique_tokens:
    mcap = token.get("mcap")
    try:
        mcap_value = float(mcap)
        if min_mcap <= mcap_value <= max_mcap:
            filtered_tokens.append(token)
    except (ValueError, TypeError):
        continue

filtered_tokens.sort(key=lambda t: float(t.get("mcap", 0) or 0))

now = datetime.now(timezone.utc)
cutoff_24h = now - timedelta(hours=24)

# Avg market cap of all tokens created in last 24h
recent_24h_all_tokens = [
    token for token in unique_tokens
    if (created := get_created_at(token)) and created >= cutoff_24h and token.get("mcap")
]

if recent_24h_all_tokens:
    total_all = sum(float(token["mcap"]) for token in recent_24h_all_tokens)
    avg_mcap_all_24h = total_all / len(recent_24h_all_tokens)
    print(f"Average Market Cap of ALL tokens created in last 24 hours: {int(avg_mcap_all_24h):,}")
else:
    print("No tokens found created in last 24 hours (ALL tokens).")

# Avg market cap of filtered tokens
if filtered_tokens:
    total_filtered = sum(float(token["mcap"]) for token in filtered_tokens)
    avg_mcap_filtered = total_filtered / len(filtered_tokens)
    print(f"Average Market Cap of ALL tokens matching your filters: {int(avg_mcap_filtered):,}\n")
else:
    print("No tokens found matching your filters.\n")

# Top 5 by Mcap created in last 24h
recent_tokens_24h = [
    token for token in unique_tokens
    if (created := get_created_at(token)) and created >= cutoff_24h and token.get("mcap")
]

recent_tokens_24h.sort(key=lambda t: float(t.get("mcap", 0) or 0), reverse=True)
top_5_recent = recent_tokens_24h[:5]

border_line = "=" * 70
print(f"\n{border_line}")
print(f"Top 5 Tokens Created in Last 24 Hours by Market Cap")
print(f"{border_line}\n")

for idx, token in enumerate(top_5_recent, 1):
    name = token.get("name", "N/A")
    symbol = token.get("symbol", "N/A")
    ca = token.get("id", "N/A")
    liquidity = int(token.get("liquidity", 0) or 0)
    holders = token.get("holderCount", "N/A")
    mcap = int(float(token.get("mcap", 0) or 0))
    created_at_dt = get_created_at(token)
    created_at = time_ago(created_at_dt)
    launchpad = token.get("launchpad", "Unknown")

    if ca.endswith("time") and launchpad == "met-dbc":
        launchpad = "timedotfun"

    payment_status = check_dex_paid_status(ca)

    print(f"{idx}. {name}")
    print(f"Ticker: {symbol}")
    print(f"ca: {ca}")
    print(f"Created: {created_at}")
    print(f"Launchpad: {launchpad}")
    print(f"Liquidity: {liquidity:,} | Holders: {holders} | Market Cap: {mcap:,}")
    print(f"DEX Paid: {'✅' if payment_status == 'approved' else payment_status}")
    print("")

print(border_line)

# Top 5 tokens by 24h Volume (created in last 24h) 
volume_tokens = []
for token in unique_tokens:
    created_at = get_created_at(token)
    if created_at and created_at >= cutoff_24h:
        stats24h = token.get("stats24h", {})
        buy_volume = stats24h.get("buyVolume", 0) or 0
        sell_volume = stats24h.get("sellVolume", 0) or 0
        total_volume = buy_volume + sell_volume
        if total_volume > 0:
            token["total_volume"] = total_volume
            volume_tokens.append(token)

volume_tokens.sort(key=lambda x: x["total_volume"], reverse=True)
top_5_volume = volume_tokens[:5]

print(f"\n{border_line}")
print(f"Top 5 Tokens Created in Last 24 Hours by Volume")
print(f"{border_line}\n")

for idx, token in enumerate(top_5_volume, 1):
    name = token.get("name", "N/A")
    symbol = token.get("symbol", "N/A")
    ca = token.get("id", "N/A")
    liquidity = int(token.get("liquidity", 0) or 0)
    holders = token.get("holderCount", "N/A")
    mcap = int(float(token.get("mcap", 0) or 0))
    volume = int(token.get("total_volume", 0) or 0)
    created_at_dt = get_created_at(token)
    created_at = time_ago(created_at_dt)
    launchpad = token.get("launchpad", "Unknown")

    if ca.endswith("time") and launchpad == "met-dbc":
        launchpad = "timedotfun"

    payment_status = check_dex_paid_status(ca)

    print(f"{idx}. {name}")
    print(f"Ticker: {symbol}")
    print(f"ca: {ca}")
    print(f"Created: {created_at}")
    print(f"Launchpad: {launchpad}")
    print(f"Liquidity: {liquidity:,} | Holders: {holders} | Market Cap: {mcap:,}")
    print(f"Volume (24h): {volume:,}")
    print(f"DEX Paid: {'✅' if payment_status == 'approved' else payment_status}")
    print("")

print(border_line)

# Filtered Output
print(f"{len(filtered_tokens)} Tokens Matching Market Cap Filter ({min_mcap:,} - {max_mcap:,}), Sorted by Market Cap (Ascending):\n")

for idx, token in enumerate(filtered_tokens, 1):
    name = token.get("name", "N/A")
    symbol = token.get("symbol", "N/A")
    ca = token.get("id", "N/A")
    liquidity = int(token.get("liquidity", "N/A"))
    holders = token.get("holderCount", "N/A")
    mcap = int(token.get("mcap", "N/A"))
    created_at_dt = get_created_at(token)
    created_at = time_ago(created_at_dt)
    launchpad = token.get("launchpad", "Unknown")

    if ca.endswith("time") and launchpad == "met-dbc":
        launchpad = "timedotfun"

    payment_status = check_dex_paid_status(ca)

    print(f"{idx}. {name}")
    print (f"Ticker: {symbol}")
    print(f"ca: {ca}")
    print(f"Created: {created_at}")
    print(f"Launchpad: {launchpad}")
    print(f"Liquidity: {liquidity:,} | Holders: {holders} | Market Cap: {mcap:,}")
    print(f"DEX Paid: {'✅' if payment_status == 'approved' else payment_status}")
    print("")

input("Press Enter to exit...")
