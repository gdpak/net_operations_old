net_operations
=========

This Ansible network role provides functionality to verify operational health of a service using simulated traffic. It does following tasks
- prepares a list of flows by parsing a service configurations
- sends flows from a traffic source
- captures flows metadata on a remote device
- verifies if flows meet the intent of service

It is also possible to run only subset of above operations by setting role variables as described in below section.

Topology
---------
To verify sanity of data flows, traffic should be sent from a source that is in same network zone as of a normal user of the service. Similarily based on data-path of flows, packet capture device(s) should be selected. A typical use-case of a enterprise providing internet/intranet service to its user might place a traffic generator and packet capture devices as below -




Requirements
------------

- Ansible 2.5 or later
- 

Role Variables
--------------

```
# defaults vars for net_operations
{
  "net_operation": {
    "services" : {
        "l3acl" : {
            "id" : 193
        },
        "output" : {
            "filename" : "packet_dict_193.json",
            "path"     : "~/net_op/"
        }
    },
    "source" : {
        "port" : 'enp0s16',
        "gateway" : '12.1.1.20',
        "wildcard_dest" : '216.58.196.174'
    }
    "sink": {
       "capture_interface": "Ethernet2"
       "capture_function": "acl_catch_all_logs"
       "flows": "~/net_op/packet_dict_193.json" 
    }
  }
}
```

Dependencies
------------

- network-engine

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

```
---
- hosts: ios01
  roles:
    - net_operations
  vars:
    device_role: 'dut'

- hosts: centos1
  roles:
    - net_operations
  vars:
    device_role: 'source'
    
- hosts: ios02
  roles:
    - net_operations
  vars:
    device_role: 'sink'
    
```

License
-------

Apache

Author Information
------------------
