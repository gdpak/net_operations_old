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
import q

from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.connection import Connection
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.module_utils.six.moves.urllib.parse import urlsplit
from ansible.utils.path import unfrackpath

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        socket_path = None
        play_context = copy.deepcopy(self._play_context)
        play_context.network_os = self._get_network_os(task_vars)

        result = super(ActionModule, self).run(task_vars=task_vars)

        if play_context.connection != 'network_cli':
            # It is supported only with network_cli
            result['failed'] = True
            result['msg'] = ('please use network_cli connection type for this'
                    'role')
            return result

        try:
            path = self._task.args.get('path')
        except KeyError as exc:
            return {'failed': True, 'msg': 'missing required argument: %s' % exc}

        try:
            filename = self._task.args.get('filename')
        except KeyError as exc:
            return {'failed': True, 'msg': 'missing required argument: %s' % exc}

        try:
            command = self._task.args.get('command')
        except KeyError as exc:
            return {'failed': True, 'msg': 'missing required argument: %s' % exc}

        path = to_bytes(path, errors='surrogate_or_strict')
        path = unfrackpath(path)
        if not os.path.exists(path):
            return {'failed': True, 'msg': 'path: %s does not exist.' % path}
        filename = to_bytes(filename, errors='surrogate_or_strict')
        dest = os.path.join(path, filename)

        if socket_path is None:
            socket_path = self._connection.socket_path

        conn = Connection(socket_path)

        try:
            out = conn.send_command(command)
        except Exception as exc:
            result['failed'] = True
            result['msg'] = ('Exception received : %s' % exc)
        
        if out == None:
            result['failed'] = True
            result['msg'] = ('service is not configured on device')

        pd_json = self._create_packet_dict(out)

        try:
            changed = self._write_packet_dict(dest, pd_json) 
        except IOError as exc:
            result['failed'] = True
            result['msg'] = ('Exception received : %s' % exc)
   
        result['changed'] = changed
        if changed:
            result['destination'] = dest
        else:
            result['dest_unchanged'] = dest
        
        return result

    def _create_packet_dict(self, cmd_out):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from trigger.acl import parse
        import netaddr
        import json
        import uuid

        # pd is list of dictionary of packets
        pd = []
        lines = cmd_out.split('\n')
        for index, line in enumerate(lines):
            line = to_bytes(line, errors='surrogate_or_strict')
            pd_it = {}
            try:
                p = parse(line)
            except Exception as e:
                q(e)
                continue

            if p.terms:
                match = p.terms[0].match
                for key in match:
                    if key == 'source-address':
                        for m in match["source-address"]:
                            v = netaddr.IPNetwork(str(m))
                            # Return the host in middle of subnet
                            size_subnet = v.size
                            host_index = int(size_subnet/2)
                            pd_it["src"] = str(v[host_index])
                    if key == 'destination-address':
                        for m in match["destination-address"]:
                            v = netaddr.IPNetwork(str(m))
                            # Return the host in middle of subnet
                            size_subnet = v.size
                            host_index = int(size_subnet/2)
                            pd_it["dst"] = str(v[host_index])
                    if key == 'protocol':
                        for m in match['protocol']:
                            pd_it["proto"] = str(m)
                    if key == 'destination-port':
                        for m in match["destination-port"]:
                            pd_it['dst_port'] = str(m)
                    if key == 'source-port':
                        for m in match["source-port"]:
                            pd_it['src_port'] = str(m)

                action = p.terms[0].action
                for act in action:
                    pd_it["action"] = act

            if pd_it is not None:
                if not "dst" in pd_it:
                    pd_it["dst"] = "any"
                if not "src" in pd_it:
                    pd_it["src"] = "any"
                pd_it["id"] = str(index) + '-' + str(uuid.uuid4())[:8]
                pd.append(pd_it)

        return json.dumps(pd, indent=4)


    def _write_packet_dict(self, dest, contents):
        # Check for Idempotency
        if os.path.exists(dest):
            try:
                with open(dest, 'r') as f:
                    old_content = f.read()
            except IOError as ioexc:
                raise IOError(ioexc)
            sha1 = hashlib.sha1()
            old_content_b = to_bytes(old_content, errors='surrogate_or_strict')
            sha1.update(old_content_b)
            checksum_old = sha1.digest()

            sha1 = hashlib.sha1()
            new_content_b = to_bytes(contents, errors='surrogate_or_strict')
            sha1.update(new_content_b)
            checksum_new = sha1.digest()
            if checksum_old == checksum_new:
               return (False)

        try:
            with open(dest, 'w') as f:
                f.write(contents)
        except IOError as ioexc:
            raise IOError(ioexc)

        return (True) 

    def _get_network_os(self, task_vars):
        if 'network_os' in self._task.args and self._task.args['network_os']:
            display.vvvv('Getting network OS from task argument')
            network_os = self._task.args['network_os']
        elif self._play_context.network_os:
            display.vvvv('Getting network OS from inventory')
            network_os = self._play_context.network_os
        elif 'network_os' in task_vars.get('ansible_facts', {}) and task_vars['ansible_facts']['network_os']:
            display.vvvv('Getting network OS from fact')
            network_os = task_vars['ansible_facts']['network_os']
        else:
            raise AnsibleError('ansible_network_os must be specified on this host to use platform agnostic modules')

        return network_os
