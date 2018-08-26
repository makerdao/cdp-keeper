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

import pytest

from cdp_keeper.cdp_keeper import CdpKeeper
from pymaker import Address
from pymaker.deployment import Deployment
from pymaker.feed import DSValue
from pymaker.numeric import Ray, Wad
from tests.helper import args, captured_output


class TestCdpKeeperArguments:
    def test_should_not_start_without_eth_from_argument(self, deployment: Deployment):
        # when
        with captured_output() as (out, err):
            with pytest.raises(SystemExit):
                CdpKeeper(args=args(f""),
                          web3=deployment.web3)

        # then
        assert "error: the following arguments are required: --eth-from" in err.getvalue()

    def test_should_not_start_without_tub_address_argument(self, deployment: Deployment):
        # when
        with captured_output() as (out, err):
            with pytest.raises(SystemExit):
                CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount}"),
                          web3=deployment.web3)

        # then
        assert "error: the following arguments are required: --tub-address" in err.getvalue()

    def test_should_not_start_without_min_margin_argument(self, deployment: Deployment):
        # when
        with captured_output() as (out, err):
            with pytest.raises(SystemExit):
                CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                    f"--tub-address {deployment.tub.address}"),
                          web3=deployment.web3)

        # then
        assert "error: the following arguments are required: --min-margin" in err.getvalue()

    def test_should_not_start_without_top_up_margin_argument(self, deployment: Deployment):
        # when
        with captured_output() as (out, err):
            with pytest.raises(SystemExit):
                CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                    f"--tub-address {deployment.tub.address} "
                                    f"--min-margin 0.2"),
                          web3=deployment.web3)

        # then
        assert "error: the following arguments are required: --top-up-margin" in err.getvalue()


class TestCdpKeeperBehaviour:
    @staticmethod
    def set_price(deployment: Deployment, new_price):
        DSValue(web3=deployment.web3, address=deployment.tub.pip()).poke_with_int(Wad.from_number(new_price).value).transact()

    def open_cdp(self, deployment: Deployment, eth_amount, sai_amount):
        # given
        deployment.tub.mold_mat(Ray.from_number(2.0)).transact()
        deployment.tub.mold_cap(Wad.from_number(100000000)).transact()

        # and
        self.set_price(deployment, 500)

        # and
        deployment.tub.open().transact()
        deployment.tub.join(Wad.from_number(eth_amount)).transact()
        deployment.tub.lock(1, Wad.from_number(eth_amount)).transact()
        deployment.tub.draw(1, Wad.from_number(sai_amount)).transact()

        # and
        assert deployment.tub.ink(1) == Wad.from_number(eth_amount)
        assert deployment.tub.tab(1) == Wad.from_number(sai_amount)

    @staticmethod
    def sai_balance(deployment: Deployment, balance):
        if deployment.sai.balance_of(deployment.our_address) < Wad.from_number(balance):
            deployment.sai.mint(Wad.from_number(balance) - deployment.sai.balance_of(deployment.our_address)).transact()
        else:
            deployment.sai.transfer(Address('0x0000000000111111111100000000001111111111'),
                                    deployment.sai.balance_of(deployment.our_address) - Wad.from_number(balance)).transact()

    def test_should_not_crash_on_empty_cdps(self, deployment: Deployment):
        # given
        deployment.tub.open().transact()

        # and
        keeper = CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                     f"--tub-address {deployment.tub.address} "
                                     f"--min-margin 0.2 --top-up-margin 0.45 --max-sai 3000 --avg-sai 2000"),
                           web3=deployment.web3)
        keeper.approve()

        # when
        self.set_price(deployment, 276)
        # and
        keeper.check_all_cups()

        # then
        # [nothing bad happens]

    #
    # For all tests liquidation ratio is 200% and `--min-margin` is 0.2,
    # so we try to maintain collateralization ratio of at least 220%.
    #
    # As `--top-up-margin` is 0.45, every time collateralization ratio
    # falls under 220% the keeper will try to being it to 245%.
    #

    #
    # TEST CASE #1
    #
    # We have 40 ETH locked, 5000 SAI debt and 2500 SAI in our account.
    # If price is 276 the collateralization ratio is 220,8%, but when price falls
    # to 274 the collateralization ratio falls to 219,2% which is below minimum.
    #
    # The amount of SAI we hold (2500 SAI) is less than `--max-sai`, so the keeper does not
    # wipe our debt but locks additional collateral so the collateralization level becomes 245%.
    #
    def test_should_top_up_if_collateralization_too_low_and_sai_below_max(self, deployment: Deployment):
        # given
        self.open_cdp(deployment, eth_amount=40, sai_amount=5000)
        self.sai_balance(deployment, balance=2500)

        # and
        keeper = CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                     f"--tub-address {deployment.tub.address} "
                                     f"--min-margin 0.2 --top-up-margin 0.45 --max-sai 3000 --avg-sai 2000"),
                           web3=deployment.web3)
        keeper.approve()

        # when
        self.set_price(deployment, 276)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad.from_number(40)
        assert deployment.tub.tab(1) == Wad.from_number(5000)

        # when
        self.set_price(deployment, 274)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad(44708029197080290000)
        assert deployment.tub.tab(1) == Wad.from_number(5000)

    #
    # TEST CASE #2
    #
    # We have 40 ETH locked, 5000 SAI debt and 3500 SAI in our account.
    # If price is 276 the collateralization ratio is 220,8%, but when price falls
    # to 274 the collateralization ratio falls to 219,2% which is below minimum.
    #
    # The amount of SAI we hold (3500 SAI) is more than `--max-sai`, so the keeper wipes
    # 1500 SAI debt to bring us to `--avg-sai` which is 2000 SAI. This way our debt falls
    # to 3500 SAI, collateralization ratio is now way above 220% so no need to lock
    # additional collateral.
    #
    def test_should_wipe_if_collateralization_too_low_and_sai_above_max(self, deployment: Deployment):
        # given
        self.open_cdp(deployment, eth_amount=40, sai_amount=5000)
        self.sai_balance(deployment, balance=3500)

        # and
        keeper = CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                     f"--tub-address {deployment.tub.address} "
                                     f"--min-margin 0.2 --top-up-margin 0.45 --max-sai 3000 --avg-sai 2000"),
                           web3=deployment.web3)
        keeper.approve()

        # when
        self.set_price(deployment, 276)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad.from_number(40)
        assert deployment.tub.tab(1) == Wad.from_number(5000)
        assert deployment.sai.balance_of(deployment.our_address) == Wad.from_number(3500)

        # when
        self.set_price(deployment, 274)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad.from_number(40)
        assert deployment.tub.tab(1) == Wad.from_number(3500)
        assert deployment.sai.balance_of(deployment.our_address) == Wad.from_number(2000)

    #
    # TEST CASE #3
    #
    # We have 40 ETH locked, 5000 SAI debt and 3500 SAI in our account.
    # If price is 276 the collateralization ratio is 220,8%, but when price falls
    # to 120 the collateralization ratio falls to 96% which is way below minimum.
    #
    # The amount of SAI we hold (3500 SAI) is more than `--max-sai`, so the keeper wipes
    # 1500 SAI debt to bring us to `--avg-sai` which is 2000 SAI. Our debt falls
    # to 3500 SAI, the collateralization ratio is now at ~ 137%, which is still below
    # minimum. So the keeper locks additional ~ 31,45 ETH collateral, which brings
    # the collateralization level to the target of 245%.
    #
    def test_should_both_wipe_and_top_up_if_collateralization_too_low(self, deployment: Deployment):
        # given
        self.open_cdp(deployment, eth_amount=40, sai_amount=5000)
        self.sai_balance(deployment, balance=3500)

        # and
        keeper = CdpKeeper(args=args(f"--eth-from {deployment.web3.eth.defaultAccount} "
                                     f"--tub-address {deployment.tub.address} "
                                     f"--min-margin 0.2 --top-up-margin 0.45 --max-sai 3000 --avg-sai 2000"),
                           web3=deployment.web3)
        keeper.approve()

        # when
        self.set_price(deployment, 276)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad.from_number(40)
        assert deployment.tub.tab(1) == Wad.from_number(5000)
        assert deployment.sai.balance_of(deployment.our_address) == Wad.from_number(3500)

        # when
        self.set_price(deployment, 120)
        # and
        keeper.check_all_cups()
        # then
        assert deployment.tub.ink(1) == Wad(71458333333333333000)
        assert deployment.tub.tab(1) == Wad.from_number(3500)
        assert deployment.sai.balance_of(deployment.our_address) == Wad.from_number(2000)
