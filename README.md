# nus-fintech-summit-2026
# ChainGig – Instant, Milestone-Based Freelancer Payments on XRPL

ChainGig is a pay-per-task gig economy platform that uses the XRP Ledger to release RLUSD payments instantly via on-chain escrows, eliminating long freelancer payout delays.

## Problem

Freelancers often wait 1–4 weeks to receive payment after completing work.
This delay causes cash flow issues, reduces trust, and disproportionately affects
early-career and global freelancers.

## Key Features

### Escrow Payments
- Funds are locked in XRPL Escrow objects
- Payments are released instantly upon approval

### RLUSD-Based Payments
- Jobs are funded using an issued RLUSD token on XRPL Testnet
- Demonstrates stablecoin-based payment flows
- Extremely fast

### On-Chain Freelancer Credentials (DID Logic) - MVP limitation, not implemented directly into the code but for future implementation
- After completing a gig, freelancers receive a verifiable credential
- Credentials are linked to XRPL transaction hashes
- Builds a tamper-proof, on-chain work history

### Dispute Handling (Concept) - MVP limitation, not implemented directly into the code but for future implementation
- Clients can trigger a dispute before escrow release
- Future implementation includes token-based dispute jury voting


## Intended workflow

1. Client posts a job and defines optional milestones
2. Client funds the job using RLUSD
3. Backend creates XRPL Escrow transactions
4. Freelancer submits work
5. Client approves work
6. Escrow is finished and payment is released instantly
7. Freelancer receives an on-chain credential

## Demo Flow
1. Fund client wallet via XRPL faucet
2. Create a job
3. Fund escrow
4. Release payment


Testing flow:
1. Create freelancer and client wallets
2. Create escrow on the ledger (generates and print transaction hash as well as the escrow sequence for validity)
3. Deducts from client's balance
4. Once escrow is complete, funds released to freelancer's wallet
5. Prints the final balances for both client and freelancer to show that transaction has been complete

