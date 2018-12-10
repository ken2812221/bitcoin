#!/usr/bin/env python3
# Copyright (c) 2014-2018 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the listreceivedbyaddress RPC."""
from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_array_result,
    assert_equal,
    assert_raises_rpc_error,
    sync_blocks,
)


class ReceivedByTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def run_test(self):
        # Generate block to get out of IBD
        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # save the number of coinbase reward addresses so far
        num_cb_reward_addresses = len(self.nodes[1].listreceivedbyaddress(minconf=0, include_empty=True, include_watchonly=True))

        self.log.info("listreceivedbyaddress Test")

        # Send from node 0 to 1
        addr = self.nodes[1].getnewaddress()
        txid = self.nodes[0].sendtoaddress(addr, 0.1)
        self.sync_all()

        # Check not listed in listreceivedbyaddress because has 0 confirmations
        assert_array_result(self.nodes[1].listreceivedbyaddress(),
                            {"address": addr},
                            {},
                            True)
        # Bury Tx under 10 block so it will be returned by listreceivedbyaddress
        self.nodes[1].generate(10)
        self.sync_all()
        assert_array_result(self.nodes[1].listreceivedbyaddress(),
                            {"address": addr},
                            {"address": addr, "label": "", "amount": Decimal("0.1"), "confirmations": 10, "txids": [txid, ]})
        # With min confidence < 10
        assert_array_result(self.nodes[1].listreceivedbyaddress(5),
                            {"address": addr},
                            {"address": addr, "label": "", "amount": Decimal("0.1"), "confirmations": 10, "txids": [txid, ]})
        # With min confidence > 10, should not find Tx
        assert_array_result(self.nodes[1].listreceivedbyaddress(11), {"address": addr}, {}, True)

        # Empty Tx
        empty_addr = self.nodes[1].getnewaddress()
        assert_array_result(self.nodes[1].listreceivedbyaddress(0, True),
                            {"address": empty_addr},
                            {"address": empty_addr, "label": "", "amount": 0, "confirmations": 0, "txids": []})

        # Test Address filtering
        # Only on addr
        expected = {"address": addr, "label": "", "amount": Decimal("0.1"), "confirmations": 10, "txids": [txid, ]}
        res = self.nodes[1].listreceivedbyaddress(minconf=0, include_empty=True, include_watchonly=True, address_filter=addr)
        assert_array_result(res, {"address": addr}, expected)
        assert_equal(len(res), 1)
        # Test for regression on CLI calls with address string (#14173)
        cli_res = self.nodes[1].cli.listreceivedbyaddress(0, True, True, addr)
        assert_array_result(cli_res, {"address": addr}, expected)
        assert_equal(len(cli_res), 1)
        # Error on invalid address
        assert_raises_rpc_error(-4, "address_filter parameter was invalid", self.nodes[1].listreceivedbyaddress, minconf=0, include_empty=True, include_watchonly=True, address_filter="bamboozling")
        # Another address receive money
        res = self.nodes[1].listreceivedbyaddress(0, True, True)
        assert_equal(len(res), 2 + num_cb_reward_addresses)  # Right now 2 entries
        other_addr = self.nodes[1].getnewaddress()
        txid2 = self.nodes[0].sendtoaddress(other_addr, 0.1)
        self.nodes[0].generate(1)
        self.sync_all()
        # Same test as above should still pass
        expected = {"address": addr, "label": "", "amount": Decimal("0.1"), "confirmations": 11, "txids": [txid, ]}
        res = self.nodes[1].listreceivedbyaddress(0, True, True, addr)
        assert_array_result(res, {"address": addr}, expected)
        assert_equal(len(res), 1)
        # Same test as above but with other_addr should still pass
        expected = {"address": other_addr, "label": "", "amount": Decimal("0.1"), "confirmations": 1, "txids": [txid2, ]}
        res = self.nodes[1].listreceivedbyaddress(0, True, True, other_addr)
        assert_array_result(res, {"address": other_addr}, expected)
        assert_equal(len(res), 1)
        # Should be two entries though without filter
        res = self.nodes[1].listreceivedbyaddress(0, True, True)
        assert_equal(len(res), 3 + num_cb_reward_addresses)  # Became 3 entries

        # Not on random addr
        other_addr = self.nodes[0].getnewaddress()  # note on node[0]! just a random addr
        res = self.nodes[1].listreceivedbyaddress(0, True, True, other_addr)
        assert_equal(len(res), 0)

        self.log.info("getreceivedbyaddress Test")

        # Send from node 0 to 1
        addr = self.nodes[1].getnewaddress()
        txid = self.nodes[0].sendtoaddress(addr, 0.1)
        self.sync_all()

        # Check balance is 0 because of 0 confirmations
        balance = self.nodes[1].getreceivedbyaddress(addr)
        assert_equal(balance, Decimal("0.0"))

        # Check balance is 0.1
        balance = self.nodes[1].getreceivedbyaddress(addr, 0)
        assert_equal(balance, Decimal("0.1"))

        # Bury Tx under 10 block so it will be returned by the default getreceivedbyaddress
        self.nodes[1].generate(10)
        self.sync_all()
        balance = self.nodes[1].getreceivedbyaddress(addr)
        assert_equal(balance, Decimal("0.1"))

        # Trying to getreceivedby for an address the wallet doesn't own should return an error
        assert_raises_rpc_error(-4, "Address not found in wallet", self.nodes[0].getreceivedbyaddress, addr)

        self.log.info("listreceivedbylabel + getreceivedbylabel Test")

        # set pre-state
        label = ''
        address = self.nodes[1].getnewaddress()
        assert_equal(self.nodes[1].getaddressinfo(address)['label'], label)
        received_by_label_json = [r for r in self.nodes[1].listreceivedbylabel() if r["label"] == label][0]
        balance_by_label = self.nodes[1].getreceivedbylabel(label)

        txid = self.nodes[0].sendtoaddress(addr, 0.1)
        self.sync_all()

        # listreceivedbylabel should return received_by_label_json because of 0 confirmations
        assert_array_result(self.nodes[1].listreceivedbylabel(),
                            {"label": label},
                            received_by_label_json)

        # getreceivedbyaddress should return same balance because of 0 confirmations
        balance = self.nodes[1].getreceivedbylabel(label)
        assert_equal(balance, balance_by_label)

        self.nodes[1].generate(10)
        self.sync_all()
        # listreceivedbylabel should return updated received list
        assert_array_result(self.nodes[1].listreceivedbylabel(),
                            {"label": label},
                            {"label": received_by_label_json["label"], "amount": (received_by_label_json["amount"] + Decimal("0.1"))})

        # getreceivedbylabel should return updated receive total
        balance = self.nodes[1].getreceivedbylabel(label)
        assert_equal(balance, balance_by_label + Decimal("0.1"))

        # Create a new label named "mynewlabel" that has a 0 balance
        address = self.nodes[1].getnewaddress()
        self.nodes[1].setlabel(address, "mynewlabel")
        received_by_label_json = [r for r in self.nodes[1].listreceivedbylabel(0, True) if r["label"] == "mynewlabel"][0]

        # Test includeempty of listreceivedbylabel
        assert_equal(received_by_label_json["amount"], Decimal("0.0"))

        # Test getreceivedbylabel for 0 amount labels
        balance = self.nodes[1].getreceivedbylabel("mynewlabel")
        assert_equal(balance, Decimal("0.0"))

        self.run_include_coinbase_test()

    def run_include_coinbase_test(self):
        # Generate block reward to address with label
        label = "label"
        address = self.nodes[0].getnewaddress(label)
        reward = Decimal("25")
        self.nodes[0].generatetoaddress(1, address)
        hash = self.nodes[0].getbestblockhash()

        # Test getreceivedbyaddress returns nothing with defaults
        balance = self.nodes[0].getreceivedbyaddress(address)
        assert_equal(balance, 0)

        # Test getreceivedbyaddress returns block reward when including immature coinbase
        balance = self.nodes[0].getreceivedbyaddress(address=address, include_immature=True)
        assert_equal(balance, reward)

        # Test getreceivedbylabel returns nothing with defaults
        balance = self.nodes[0].getreceivedbylabel("label")
        assert_equal(balance, 0)

        # Test getreceivedbylabel returns block reward when including immature coinbase
        balance = self.nodes[0].getreceivedbylabel(label="label", include_immature=True)
        assert_equal(balance, reward)

        # Test listreceivedbyaddress doesn't include address with defaults
        assert_array_result(self.nodes[0].listreceivedbyaddress(),
                            {"address": address},
                            {}, True)

        # Test listreceivedbyaddress includes address when including immature coinbase
        assert_array_result(self.nodes[0].listreceivedbyaddress(minconf=1, include_immature=True),
                            {"address": address},
                            {"address": address, "amount": reward})

        # Test listreceivedbylabel doesn't include label with defaults
        assert_array_result(self.nodes[0].listreceivedbylabel(),
                            {"label": label},
                            {}, True)

        # Test listreceivedbylabel includes label when including immature coinbase
        assert_array_result(self.nodes[0].listreceivedbylabel(minconf=1, include_immature=True),
                            {"label": label},
                            {"label": label, "amount": reward})

        # Generate 100 more blocks
        self.nodes[0].generate(100)

        # Test getreceivedbyaddress returns rewared with defaults
        balance = self.nodes[0].getreceivedbyaddress(address)
        assert_equal(balance, reward)

        # Test getreceivedbyaddress returns nothing when not including coinbase
        balance = self.nodes[0].getreceivedbyaddress(address=address, include_coinbase=False)
        assert_equal(balance, 0)

        # Test getreceivedbylabel returns reward with defaults
        balance = self.nodes[0].getreceivedbylabel("label")
        assert_equal(balance, reward)

        # Test getreceivedbylabel returns nothing when not including coinbase
        balance = self.nodes[0].getreceivedbylabel(label="label", include_coinbase=False)
        assert_equal(balance, 0)

        # Test listreceivedbyaddress includes address with defaults
        assert_array_result(self.nodes[0].listreceivedbyaddress(),
                            {"address": address},
                            {"address": address, "amount": reward})

        # Test listreceivedbyaddress doesn't include address when not including coinbase
        assert_array_result(self.nodes[0].listreceivedbyaddress(include_coinbase=False),
                            {"address": address},
                            {}, True)

        # Test listreceivedbylabel includes label with defaults
        assert_array_result(self.nodes[0].listreceivedbylabel(),
                            {"label": label},
                            {"label": label, "amount": reward})

        # Test listreceivedbylabel doesn't include label when not including coinbase
        assert_array_result(self.nodes[0].listreceivedbylabel(include_coinbase=False),
                            {"label": label},
                            {}, True)

        # Orphan block that paid to address
        self.nodes[0].invalidateblock(hash)

        # Test getreceivedbyaddress doesn't include orphan when minconf is 0 when including immature
        balance = self.nodes[0].getreceivedbyaddress(address=address, minconf=0, include_immature=True)
        assert_equal(balance, 0)

        # Test getreceivedbylabel doesn't include orphan when minconf is 0 when including immature
        balance = self.nodes[0].getreceivedbylabel(label="label", minconf=0, include_immature=True)
        assert_equal(balance, 0)

        # Test listreceivedbyaddress doesn't include orphan when minconf is 0 when including immature
        assert_array_result(self.nodes[0].listreceivedbyaddress(minconf=0, include_immature=True),
                            {"address": address},
                            {}, True)

        # Test listreceivedbylabel doesn't include orphan when minconf is 0 when including immature
        assert_array_result(self.nodes[0].listreceivedbylabel(minconf=0, include_immature=True),
                            {"label": label},
                            {}, True)

if __name__ == '__main__':
    ReceivedByTest().main()
