# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import logging
import sys

from web3 import Web3, HTTPProvider

from pymaker import Contract, Address
from pymaker.approval import directly
from pymaker.gas import FixedGasPrice, DefaultGasPrice
from pymaker.lifecycle import Lifecycle as Web3Lifecycle
from pymaker.numeric import Wad, Ray
from pymaker.sai import Tub
from pymaker.token import ERC20Token
from pymaker.util import eth_balance, chain


class CdpKeeper:
    """Keeper to actively manage open CDPs."""

    logger = logging.getLogger('cdp-keeper')

    def __init__(self, args: list, **kwargs):
        parser = argparse.ArgumentParser(prog='cdp-keeper')
        parser.add_argument("--rpc-host", help="JSON-RPC host (default: `localhost')", default="localhost", type=str)
        parser.add_argument("--rpc-port", help="JSON-RPC port (default: `8545')", default=8545, type=int)
        parser.add_argument("--rpc-timeout", help="JSON-RPC timeout (in seconds, default: 10)", default=10, type=int)
        parser.add_argument("--eth-from", help="Ethereum account from which to send transactions", required=True, type=str)
        parser.add_argument("--tub-address", help="Ethereum address of the Tub contract", required=True, type=str)
        parser.add_argument("--min-margin", help="Margin between the liquidation ratio and the top-up threshold", type=float, required=True)
        parser.add_argument("--top-up-margin", help="Margin between the liquidation ratio and the top-up target", type=float, required=True)
        parser.add_argument("--max-sai", type=float, required=True)
        parser.add_argument("--avg-sai", type=float, required=True)
        parser.add_argument("--gas-price", help="Gas price in Wei (default: node default)", default=0, type=int)
        parser.add_argument("--debug", help="Enable debug output", dest='debug', action='store_true')
        self.arguments = parser.parse_args(args)

        self.web3 = kwargs['web3'] if 'web3' in kwargs else Web3(HTTPProvider(endpoint_uri=f"http://{self.arguments.rpc_host}:{self.arguments.rpc_port}",
                                                                              request_kwargs={"timeout": self.arguments.rpc_timeout}))
        self.web3.eth.defaultAccount = self.arguments.eth_from
        self.our_address = Address(self.arguments.eth_from)
        self.tub = Tub(web3=self.web3, address=Address(self.arguments.tub_address))
        self.sai = ERC20Token(web3=self.web3, address=self.tub.sai())

        self.liquidation_ratio = self.tub.mat()
        self.minimum_ratio = self.liquidation_ratio + Ray.from_number(self.arguments.min_margin)
        self.target_ratio = self.liquidation_ratio + Ray.from_number(self.arguments.top_up_margin)
        self.max_sai = Wad.from_number(self.arguments.max_sai)
        self.avg_sai = Wad.from_number(self.arguments.avg_sai)

        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s',
                            level=(logging.DEBUG if self.arguments.debug else logging.INFO))

    def main(self):
        with Web3Lifecycle(self.web3) as lifecycle:
            lifecycle.on_startup(self.startup)
            lifecycle.on_block(self.check_all_cups)

    def startup(self):
        self.approve()

    def approve(self):
        self.tub.approve(directly(gas_price=self.gas_price()))

    def check_all_cups(self):
        for cup in self.our_cups():
            self.check_cup(cup.cup_id)

    def check_cup(self, cup_id: int):
        assert(isinstance(cup_id, int))

        # If cup is undercollateralized and the amount of SAI we are holding is more than `--max-sai`
        # then we wipe some debt first so our balance reaches `--avg-sai`. Bear in mind that it is
        # possible that we pay all out debt this way and our SAI balance will still be higher
        # than `--max-sai`.
        if self.is_undercollateralized(cup_id) and self.sai.balance_of(self.our_address) > self.max_sai:
            amount_of_sai_to_wipe = self.calculate_sai_wipe()
            if amount_of_sai_to_wipe > Wad(0):
                self.tub.wipe(cup_id, amount_of_sai_to_wipe).transact(gas_price=self.gas_price())

        # If cup is still undercollateralized, calculate the amount of SKR needed to top it up so
        # the collateralization level reaches `--top-up-margin`. If we have enough ETH, exchange
        # in to SKR and then top-up the cup.
        if self.is_undercollateralized(cup_id):
            top_up_amount = self.calculate_skr_top_up(cup_id)
            if top_up_amount <= eth_balance(self.web3, self.our_address):
                # TODO we do not always join with the same amount as the one we lock!
                self.tub.join(top_up_amount).transact(gas_price=self.gas_price())
                self.tub.lock(cup_id, top_up_amount).transact(gas_price=self.gas_price())
            else:
                self.logger.info(f"Cannot top-up as our balance is less than {top_up_amount} ETH.")

    def our_cups(self):
        for cup_id in range(1, self.tub.cupi()+1):
            cup = self.tub.cups(cup_id)
            if cup.lad == self.our_address:
                yield cup

    def is_undercollateralized(self, cup_id) -> bool:
        pro = self.tub.ink(cup_id)*self.tub.tag()
        tab = self.tub.tab(cup_id)
        if tab > Wad(0):
            current_ratio = Ray(pro / tab)
            # Prints the Current CDP Ratio and the Minimum Ratio specified under --min-margin
            print(f'Current Ratio {current_ratio}')
            print(f'Minimum Ratio {self.minimum_ratio}')
            return current_ratio < self.minimum_ratio
        else:
            return False

    def calculate_sai_wipe(self) -> Wad:
        """Calculates the amount of SAI that can be wiped.

        Calculates the amount of SAI than can be wiped in order to bring the SAI holdings
        to `--avg-sai`.
        """
        return Wad.max(self.sai.balance_of(self.our_address) - self.avg_sai, Wad(0))

    def calculate_skr_top_up(self, cup_id) -> Wad:
        """Calculates the required top-up in SKR.

        Calculates the required top-up in SKR in order to bring the collateralization level
        of the cup to `--target-ratio`.
        """
        pro = self.tub.ink(cup_id)*self.tub.tag()
        tab = self.tub.tab(cup_id)
        if tab > Wad(0):
            current_ratio = Ray(pro / tab)
            return Wad.max(tab * (Wad(self.target_ratio - current_ratio) / self.tub.tag()), Wad(0))
        else:
            return Wad(0)

    def gas_price(self):
        if self.arguments.gas_price > 0:
            return FixedGasPrice(self.arguments.gas_price)
        else:
            return DefaultGasPrice()


if __name__ == '__main__':
    CdpKeeper(sys.argv[1:]).main()
