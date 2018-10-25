# (c) 2018, Ansible Inc,
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import os
import time
import re
import hashlib
import json

from ansible.module_utils._text import to_bytes, to_text
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.path import unfrackpath

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        play_context = copy.deepcopy(self._play_context)

        result = super(ActionModule, self).run(task_vars=task_vars)

        self.any_dest_ip = self._task.args.get('wildcard_host')
        try:
            flow_in = self._task.args.get('flows_sent')
        except KeyError as exc:
            return {'failed': True, 'msg': 'missing required argument: %s' % exc}

        try:
            flow_out = self._task.args.get('flows_received')
        except KeyError as exc:
            return {'failed': True, 'msg': 'missing required argument: %s' % exc}

        flow_in = to_bytes(flow_in, errors='surrogate_or_strict')
        flow_in = unfrackpath(flow_in)
        if not os.path.exists(flow_in):
            return {'failed': True, 'msg': 'flow_in path: %s does not exist.' % flow_in}

        flow_out = to_bytes(flow_out, errors='surrogate_or_strict')
        flow_out = unfrackpath(flow_out)
        if not os.path.exists(flow_out):
            return {'failed': True, 'msg': 'flow_out path: %s does not exist.' % flow_out}

        with open(flow_in, 'r') as f:
            flow_in_dict = json.loads(f.read())

        with open(flow_out, 'r') as f:
            flow_out_dict = json.loads(f.read())

        self.analyze_flows(flow_in_dict, flow_out_dict)

        if self.anamolies:
           result['anamolies'] = self.anamolies
           result['passed_flows'] = self.passed_flows
        else:
           result['passed_flows'] = self.passed_flows

        result['changed'] = True
        return result

    def find_match(self, flowd, src, dst, dst_port=None, src_port=None):
        for flows in flowd:
            if dst == 'any':
                dst = self.any_dest_ip
            if src_port and flows[src_port]:
                if flows['src'] == src and (flows['dst'] == dst and
                   (flows['src_port'] == src_port and
                   flows['dst_port'] == dst_port)) :
                   return flows['num_packets']
            elif flows['src'] == src and (flows['dst'] == dst and 
                 flows['dst_port'] == dst_port) :
                 return flows['num_packets']
        return 0

    def analyze_flows(self, fin, fout):
        self.anamolies = []
        self.passed_flows = []
        for flow_in in fin:
            n = self.find_match(fout, flow_in['src'], flow_in['dst'],
                           flow_in['dst_port'], flow_in.get('src_port'))
            if flow_in['action'] == 'deny' and n > 0:
               self.anamolies.append("Found packet on sink which should be"
                       " rejected - %s" % json.dumps(flow_in))
            elif flow_in['action'] == 'permit' and n == 0:
               self.anamolies.append("Could not find packet on sink which"
                       " should be passed - %s" % json.dumps(flow_in))
            else:
               self.passed_flows.append(" PASSED TESTS : %s" % json.dumps(flow_in)) 


