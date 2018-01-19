rejected_retry: True
mine_interval: 1
hostsfile:
  alias: controlpath_ip
mine_functions:
  datapath_ip:
    - mine_function: network.ip_addrs
    - {{ salt_host_data_iface }}
  controlpath_ip:
    - mine_function: network.ip_addrs
    - {{ salt_host_control_iface }}
  dockerbridge_ip:
    - mine_function: cmd.run
    - docker network inspect -f '{{range $p, $conf := .IPAM.Config}}{{(index $conf "Gateway")}}{{end}}' bridge
  docker_spy:
    - mine_function: dspy.dump
    - {{ salt_host_data_iface }}
