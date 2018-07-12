#!/usr/bin/python
#
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: send_traffic 
version_added: "2.7"
author: "Deepak Agrawal (@dagrawal)"
short_description: send traffic from device as per given packet header
description:
  - This module sends traffic from a port on a device with given
    packet headers in JSON list
options:
    src:
      description: path of file containing packet header dictionary
      required: true
    port:
      description: port on device which can reach DUT to send traffic.
      required: true

version_added: "2.7"
notes:
"""

EXAMPLES = """
- name: Send traffc
  send_traffic
    src: ~/net_op/packet_dict.json
    port: enp0s16
"""

RETURN = """
"""
import re
import q
import sys
import os
import json
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text
from ansible.utils.path import unfrackpath, makedirs_safe

class TrafficGen(object):
    def __init__(self, module, pd_path, port):
        self._pd = pd_path
        self._port = port
        self._module = module

    def load_packets(self, packet_src):
        if os.path.exists(packet_src):
            with open(packet_src, 'r') as f:
                packet_content = f.read()
            packet_d = json.loads(packet_content)
            self._packets = packet_d
        else:
            raise IOError("src file not found")

    def send_packets(self):
        from scapy.all import *

        for packet in self._packets:
            if packet['src']:
                frame = IP(src=str(packet['src']))

    def main(self):
        try:
            self.load_packets(self._pd)
        except Exception as e:
            raise e

def main():
    """main entry point for module execution
    """
    argument_spec = dict(
        src=dict(required=True, type='path'),
        port=dict(required=True),
    )
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    p = module.params
    tg = TrafficGen(module, p['src'], p['port'])
    try:
        tg.main()
    except Exception as e:
        module.fail_json(msg=to_text(e))

    warnings = list()
    result = dict(changed=False, warnings=warnings)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
