username: MY_USER
password: MY_PASSWORD
api-backend: https://api.grid5000.fr/
ssh_key_file_public: /home/nherbaut/.ssh/g5k.pub
ssh_key_file_private: /home/nherbaut/.ssh/g5k
mailto: nicolas.herbaut@gmail.com
environment: debian9-x64-base
default_site: nancy

#salt specific configuration, if required
salt_host_control_iface: eth0
salt_host_data_iface: eth0
salt_minion_template: /home/nherbaut/tmp/minion.tpl
salt_master_template: /home/nherbaut/tmp/master.tpl
salt_states_repo_url: git@gricad-gitlab.univ-grenoble-alpes.fr:vqgroup/salt-master.git
salt_states_repo_branch: auto_install
