import requests
import time
import threading

# alert sound
try:
    import winsound
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False

# user input
poll_interval = 10  # seconds between checks (user input?)
chain = input("Enter chain (e.g., solana, ethereum): ").strip().lower()

tokens = []

print("\nEnter token contract addresses and target prices (one per line):")
print("Format: <contract_address>, <target_price>")
print("Press Enter on an empty line to start tracking...\n")

while True:
    line = input("Token and price: ").strip()
    if not line:
        break
    try:
        address, price = line.split(",")
        tokens.append({
            "address": address.strip(),
            "target": float(price.strip()),
            "hit": False
        })
    except:
        print("Invalid format. Use: <contract_address>, <target_price>")

# fetch price
def get_token_price_usd(chain, address):
    url = f"https://api.geckoterminal.com/api/v2/networks/{chain}/tokens/{address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price_str = data["data"]["attributes"]["price_usd"]
        return float(price_str) if price_str else None
    except Exception as e:
        print(f"Error fetching price for {address[:6]}...: {e}")
        return None

# loop Beep Thread 
def beep_until_ok():
    def beep_loop():
        while not stop_beep_event.is_set():
            if SOUND_ENABLED:
                winsound.Beep(1000, 500)
            time.sleep(0.5)

    stop_beep_event.clear()
    thread = threading.Thread(target=beep_loop)
    thread.start()

    while True:
        user_input = input("Type 'ok' to stop the alarm and continue: ").strip().lower()
        if user_input == "ok":
            stop_beep_event.set()
            thread.join()
            break

# add new token 
def add_new_token():
    while True:
        line = input("\n Enter new token and target (or leave blank to skip): ").strip()
        if not line:
            break
        try:
            address, price = line.split(",")
            tokens.append({
                "address": address.strip(),
                "target": float(price.strip()),
                "hit": False
            })
            break
        except:
            print("Invalid format. Use: <contract_address>, <target_price>")

# beep control 
stop_beep_event = threading.Event()

# Main Loop
print(f"\nTracking {len(tokens)} tokens on {chain}...")

while True:
    for token in tokens:
        if token["hit"]:
            continue

        price = get_token_price_usd(chain, token["address"])
        if price is not None:
            print(f"[{time.strftime('%H:%M:%S')}] {token['address'][:6]}... → ${price:.6f}")
            if price >= token["target"]:
                print(f"\nALERT: {token['address'][:6]}... reached ${price:.6f} (target: ${token['target']})")

                token["hit"] = True
                beep_until_ok()  # Start beep loop until "ok"
                add_new_token()  # Prompt to add next token
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to retrieve price for {token['address'][:6]}...")

    time.sleep(poll_interval)
