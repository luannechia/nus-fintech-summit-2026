import time
from datetime import datetime, timedelta, timezone

from xrpl.clients import JsonRpcClient
from xrpl.wallet import generate_faucet_wallet
from xrpl.models.transactions import EscrowCreate, EscrowFinish
from xrpl.transaction import submit_and_wait
from xrpl.utils import datetime_to_ripple_time, xrp_to_drops
from xrpl.account import get_balance
from xrpl.models.requests import ServerInfo

# XRPL Client (Testnet)
client = JsonRpcClient("https://s.altnet.rippletest.net:51234")


# Helpers
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def balance(address: str) -> float:
    return int(get_balance(address, client)) / 1_000_000


def parse_ledger_time(time_str: str) -> datetime:
    """
    Parse XRPL ledger time string to datetime.
    Handles formats like: '2026-Jan-08 14:48:23.601094 UTC'
    """
    if time_str.endswith(' UTC'):
        time_str = time_str[:-4]
    
    try:
        # try parsing the format: '2026-Jan-08 14:48:23.601094'
        dt = datetime.strptime(time_str, '%Y-%b-%d %H:%M:%S.%f')
    except ValueError:
        try:
            # try without microseconds
            dt = datetime.strptime(time_str, '%Y-%b-%d %H:%M:%S')
        except ValueError:
            # try ISO format as fallback
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    
    return dt.replace(tzinfo=timezone.utc)


def wait_until_ledger_time(target_ripple_time: int):
    """
    Block until XRPL ledger time >= target Ripple time
    """
    log(f"Waiting for ledger time {target_ripple_time}...")
    
    # get the initial ledger time
    info = client.request(ServerInfo()).result
    ledger_time_str = info["info"]["time"]
    log(f"Initial ledger time string: {ledger_time_str}")
    
    while True:
        try:
            info = client.request(ServerInfo()).result
            ledger_time_str = info["info"]["time"]
            
            ledger_dt = parse_ledger_time(ledger_time_str)
            ledger_ripple_time = datetime_to_ripple_time(ledger_dt)

            log(f"Current ledger time: {ledger_ripple_time}, Target: {target_ripple_time}")
            
            if ledger_ripple_time >= target_ripple_time:
                log("Target ledger time reached!")
                return
            
            # calculate how long to wait
            current_ripple = datetime_to_ripple_time(datetime.now(timezone.utc))
            seconds_remaining = target_ripple_time - ledger_ripple_time
            
            if seconds_remaining > 10:
                sleep_time = min(seconds_remaining, 10)
                log(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                # if less than 10 seconds remaining, check more frequently
                time.sleep(2)
            
        except Exception as e:
            log(f"Error checking ledger time: {e}")
            log(f"Raw time string: {ledger_time_str}")
            time.sleep(5)



# Main Flow
def main():
    print("\n" + "="*50)
    print("CHAIN GIG: REAL XRPL ESCROW")
    print("="*50 + "\n")

    try:
        #create & fund wallets
        log("Creating CLIENT wallet...")
        client_wallet = generate_faucet_wallet(client, debug=False)
        time.sleep(2)  # Wait for wallet funding

        log("Creating FREELANCER wallet...")
        freelancer_wallet = generate_faucet_wallet(client, debug=False)
        time.sleep(2)  # waiting for wallet funding

        log(f"Client:     {client_wallet.classic_address}")
        log(f"Freelancer: {freelancer_wallet.classic_address}")

        print("\n Initial Balances:")
        print(f"  Client:     {balance(client_wallet.classic_address):.2f} XRP")
        print(f"  Freelancer: {balance(freelancer_wallet.classic_address):.2f} XRP")

        #2 escrow parameters
        gig_amount = 25.0
        finish_after_seconds = 30  # 30 seconds
        cancel_after_seconds = 120  # 2 minutes to cancel if needed

        # calculate finish and cancel times
        finish_after_dt = datetime.now(timezone.utc) + timedelta(seconds=finish_after_seconds)
        cancel_after_dt = datetime.now(timezone.utc) + timedelta(seconds=cancel_after_seconds)

        # convert to Ripple time
        finish_after = datetime_to_ripple_time(finish_after_dt)
        cancel_after = datetime_to_ripple_time(cancel_after_dt)

        log(f"\n Escrow timing:")
        log(f"  Current UTC time: {datetime.now(timezone.utc).strftime('%H:%M:%S')}")
        log(f"  Will be finishable after: {finish_after_dt.strftime('%H:%M:%S UTC')}")
        log(f"  Will expire (cancelable) after: {cancel_after_dt.strftime('%H:%M:%S UTC')}")
        log(f"  Finish after (Ripple time): {finish_after}")

        #3 create escrow
        log("\n Creating escrow on-ledger...")
        
        escrow_tx = EscrowCreate(
            account=client_wallet.classic_address,
            destination=freelancer_wallet.classic_address,
            amount=xrp_to_drops(gig_amount),
            finish_after=finish_after,
            cancel_after=cancel_after,
        )

        # submit the transaction
        res = submit_and_wait(escrow_tx, client, client_wallet)

        if not res.is_successful():
            error_msg = res.result.get("engine_result_message", "Unknown error")
            raise Exception(f"Escrow creation failed: {error_msg}")

        log(f" Escrow created successfully!")
        log(f"   Transaction Hash: {res.result.get('hash')}")
        
        # get the escrow sequence from the transaction metadata
        metadata = res.result.get("meta", {})
        sequence = None
        
        # look for the escrow creation sequence
        for node in metadata.get("AffectedNodes", []):
            if "CreatedNode" in node:
                created_node = node["CreatedNode"]
                if created_node.get("LedgerEntryType") == "Escrow":
                    # Get the sequence from the NewFields
                    new_fields = created_node.get("NewFields", {})
                    sequence = new_fields.get("Sequence")
                    break
        
        if not sequence:
            # fallback to transaction sequence
            sequence = res.result["tx_json"]["Sequence"]
        
        log(f"   Escrow Sequence: {sequence}")

        print(f"\n Client balance after escrow creation: {balance(client_wallet.classic_address):.2f} XRP")

        log(f"\n Waiting for XRPL ledger time to pass finish_after ({finish_after})...")
        
        # check current ledger time
        info = client.request(ServerInfo()).result
        current_ledger_str = info["info"]["time"]
        current_ledger_dt = parse_ledger_time(current_ledger_str)
        current_ledger_ripple = datetime_to_ripple_time(current_ledger_dt)
        
        log(f"Current ledger time (Ripple): {current_ledger_ripple}")
        log(f"Time difference: {finish_after - current_ledger_ripple} seconds")
        
        # wait for ledger time
        wait_until_ledger_time(finish_after)

        #5 finish escrow (release funds)
        log("\n Releasing funds to freelancer...")

        finish_tx = EscrowFinish(
            account=client_wallet.classic_address,
            owner=client_wallet.classic_address,
            offer_sequence=sequence,
        )

        finish_res = submit_and_wait(finish_tx, client, client_wallet)

        if not finish_res.is_successful():
            error_msg = finish_res.result.get("engine_result_message", "Unknown error")
            raise Exception(f"Escrow finish failed: {error_msg}")

        log(" Escrow finished successfully! Funds released to freelancer.")

        #6 print final balances to check
        print("\n Final Balances:")
        print(f"  Client:     {balance(client_wallet.classic_address):.2f} XRP")
        print(f"  Freelancer: {balance(freelancer_wallet.classic_address):.2f} XRP")
        
        print("\n" + "="*50)
        print("ESCROW COMPLETED SUCCESSFULLY!")
        print("="*50)

    except Exception as e:
        log(f" Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*50)
        print("ESCROW FAILED")
        print("="*50)

if __name__ == "__main__":
    main()
