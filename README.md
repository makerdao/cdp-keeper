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

## Installation

This project uses *Python 3.6.2*.

In order to clone the project and install required third-party packages please execute:
```
git clone https://github.com/makerdao/cdp-keeper.git
git submodule update --init --recursive
pip3 install -r requirements.txt
```

### Known macOS issues

In order for the Python requirements to install correctly on _macOS_, please install
`openssl`, `libtool` and `pkg-config` using [Homebrew](https://brew.sh/):
```
brew install openssl libtool pkg-config
```

and set the `LDFLAGS` environment variable before you run `pip3 install -r requirements.txt`:
```
export LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include" 
```

## Usage

```
usage: cdp-keeper [-h] [--rpc-host RPC_HOST] [--rpc-port RPC_PORT] --eth-from
                  ETH_FROM --tub-address TUB_ADDRESS --min-margin MIN_MARGIN
                  --top-up-margin TOP_UP_MARGIN --max-sai MAX_SAI --avg-sai
                  AVG_SAI [--gas-price GAS_PRICE] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --rpc-host RPC_HOST   JSON-RPC host (default: `localhost')
  --rpc-port RPC_PORT   JSON-RPC port (default: `8545')
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
