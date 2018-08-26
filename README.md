# cdp-keeper

[![Build Status](https://travis-ci.org/makerdao/cdp-keeper.svg?branch=master)](https://travis-ci.org/makerdao/cdp-keeper)
[![codecov](https://codecov.io/gh/makerdao/cdp-keeper/branch/master/graph/badge.svg)](https://codecov.io/gh/makerdao/cdp-keeper)

The _DAI Stablecoin System_ incentivizes external agents, called _keepers_,
to automate certain operations around the Ethereum blockchain.

`cdp-keeper` is responsible for actively monitoring and managing open CDPs.
At the beginning it was capable only of topping them up if they get too close
to the liquidation level, but now more advances paths are being developed
(like automatically wiping the debt instead of topping-up, managing the SAI
volume within specific range etc.). **This keeper is still under development.**

It only monitors cups owned by the `--eth-from` account. Cups owned by other
accounts are ignored.

<https://chat.makerdao.com/channel/keeper>

## Example

If the CDP collateralization ratio goes below `--min-margin` and at the same time the debt is greater than `--max-sai`, it tries to `wipe` some debt targeting `--avg-sai`. if wiping that debt didn't help to bring collateralization ratio above `--min-margin` (or it wasn't possible to `wipe` at all for some reason, for example the keeper didn't have any Dai), it then tries to `lock` some extra collateral in order to bring collateralization ratio at least to `--top-up-margin`

Both `--min-margin` and `--top-up-margin` are expressed as on top of the current liquidation ratio configured.

If liquidation ratio is `1.50` (= 150%), then if you set `--min-margin 1.0` it will try to top-up if below 250%

## Installation

This project uses *Python 3.6.5*.

In order to clone the project and install required third-party packages please execute:
```
git clone https://github.com/makerdao/cdp-keeper.git
cd cdp-keeper
git submodule update --init --recursive
pip3 install -r requirements.txt
```

For some known Ubuntu and macOS issues see the [pymaker](https://github.com/makerdao/pymaker) README.

## Usage

```
usage: cdp-keeper [-h] [--rpc-host RPC_HOST] [--rpc-port RPC_PORT]
                  [--rpc-timeout RPC_TIMEOUT] --eth-from ETH_FROM
                  --tub-address TUB_ADDRESS --min-margin MIN_MARGIN
                  --top-up-margin TOP_UP_MARGIN --max-sai MAX_SAI --avg-sai
                  AVG_SAI [--gas-price GAS_PRICE] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --rpc-host RPC_HOST   JSON-RPC host (default: `localhost')
  --rpc-port RPC_PORT   JSON-RPC port (default: `8545')
  --rpc-timeout RPC_TIMEOUT
                        JSON-RPC timeout (in seconds, default: 10)
  --eth-from ETH_FROM   Ethereum account from which to send transactions
  --tub-address TUB_ADDRESS
                        Ethereum address of the Tub contract
  --min-margin MIN_MARGIN
                        Margin between the liquidation ratio and the top-up
                        threshold
  --top-up-margin TOP_UP_MARGIN
                        Margin between the liquidation ratio and the top-up
                        target
  --max-sai MAX_SAI
  --avg-sai AVG_SAI
  --gas-price GAS_PRICE
                        Gas price in Wei (default: node default)
  --debug               Enable debug output
```

## License

See [COPYING](https://github.com/makerdao/cdp-keeper/blob/master/COPYING) file.

### Disclaimer

YOU (MEANING ANY INDIVIDUAL OR ENTITY ACCESSING, USING OR BOTH THE SOFTWARE INCLUDED IN THIS GITHUB REPOSITORY) EXPRESSLY UNDERSTAND AND AGREE THAT YOUR USE OF THE SOFTWARE IS AT YOUR SOLE RISK.
THE SOFTWARE IN THIS GITHUB REPOSITORY IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
YOU RELEASE AUTHORS OR COPYRIGHT HOLDERS FROM ALL LIABILITY FOR YOU HAVING ACQUIRED OR NOT ACQUIRED CONTENT IN THIS GITHUB REPOSITORY. THE AUTHORS OR COPYRIGHT HOLDERS MAKE NO REPRESENTATIONS CONCERNING ANY CONTENT CONTAINED IN OR ACCESSED THROUGH THE SERVICE, AND THE AUTHORS OR COPYRIGHT HOLDERS WILL NOT BE RESPONSIBLE OR LIABLE FOR THE ACCURACY, COPYRIGHT COMPLIANCE, LEGALITY OR DECENCY OF MATERIAL CONTAINED IN OR ACCESSED THROUGH THIS GITHUB REPOSITORY. 
