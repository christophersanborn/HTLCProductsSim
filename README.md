# HTLCProductsSim
A library for simulating financial products based on hash oracles

## Hash Oracles
A hash oracle is an entity that publishes real-world data (such as price observations) by conditionally revealing the preimage to a previously published hash.  In order for contracts to be built upon these hashes, the hashes need to be published in advance, and their preimages either revealed or not revealed on the target date based on the oracle's assessment of the external condition.

Example:  Oracle publishes hash `H` one month prior to date `D`.  On date `D`, oracle reveals preimage `P : Hash(P)=H` if the price of Bitcoin exceeds $10,000.00, but does _not_ reveal the preimage otherwise.

In practice, a hash oracle would likely publish, in advance, daily (or even hourly) tables of hashes representing sequences of price levels, allowing for a fine-grained representation of price data.

### Are hash oracles trusted or trustless?

They are trusted parties.  An insider with access to the preimages could wreak havoc if they acted inapropriately.  A trusted oracle would need to invest in protecting their reliability and reputation.  There are potential strategies to achieve this.

Products using the hashes could mitigate risk by conditioning their contracts on hashes from mulitple, competing oracles.

## HTLC Products as Options

blah blah blah

## Examples

### Atomic Swaps as Call Options

![fig1](doc/LongCall.png)

### Bounded Stable Coin and corresponding Variability

![fig2](doc/BSC_Stability_USD.png)

![fig3](doc/BSC_Stability_BTS.png)

![fig4](doc/BSC_Variability_BTS.png)
