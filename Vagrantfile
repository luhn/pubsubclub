# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "ubuntu/trusty64"

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  config.vm.box_check_update = false

	config.vm.provision "shell", inline: <<-SHELL
		sudo apt-get install -y supervisor
		sudo apt-get install -y python-pip
		sudo apt-get install -y python-dev
		sudo pip install virtualenv
		virtualenv env
		. env/bin/activate
		cd /vagrant
		python setup.py install
		cp supervisor.conf /etc/supervisor/conf.d/pubsubclub.conf
		supervisorctl reread && supervisorctl update
	SHELL

	config.vm.provision "shell", privileged: true, inline: <<-SHELL
		apt-get install -y unzip
		cd /usr/local/bin
		wget https://dl.bintray.com/mitchellh/consul/0.5.2_linux_amd64.zip
		unzip *.zip
		rm *.zip
		mkdir /etc/consul.d/
		cp /vagrant/consul.json /etc/consul.d/
		mkdir /var/consul
		chown vagrant:vagrant /var/consul
		cp /vagrant/consul.conf /etc/init/
	SHELL

	config.vm.define "box1", primary: true do |box1|
		box1.vm.network "private_network", ip: "192.168.50.100"
		box1.vm.provision "shell", privileged: true, inline: <<-SHELL
			hostname box1
			hostname > /etc/hostname
			echo "{\\"bind_addr\\":\\"192.168.50.100\\"}" > /etc/consul.d/bind.json
			cp /vagrant/consul-leader.json /etc/consul.d/
			service consul start
		SHELL
		box1.vm.provision "shell", privileged: true, inline: ""
	end

	config.vm.define "box2", primary: true do |box2|
		box2.vm.network "private_network", ip: "192.168.50.101"
		box2.vm.provision "shell", privileged: true, inline: <<-SHELL
			hostname box2
			hostname > /etc/hostname
			echo "{\\"bind_addr\\":\\"192.168.50.101\\"}" > /etc/consul.d/bind.json
			service consul start
		SHELL
	end

	config.vm.define "box3", primary: true do |box3|
		box3.vm.network "private_network", ip: "192.168.50.102"
		box3.vm.provision "shell", privileged: true, inline: <<-SHELL
			hostname box3
			hostname > /etc/hostname
			echo "{\\"bind_addr\\":\\"192.168.50.102\\"}" > /etc/consul.d/bind.json
			service consul start
		SHELL
	end

	config.vm.define "box4", primary: true do |box4|
		box4.vm.network "private_network", ip: "192.168.50.103"
		box4.vm.provision "shell", privileged: true, inline: <<-SHELL
			hostname box4
			hostname > /etc/hostname
			echo "{\\"bind_addr\\":\\"192.168.50.103\\"}" > /etc/consul.d/bind.json
			service consul start
		SHELL
	end

  # config.vm.provision "shell", inline: <<-SHELL
  #   sudo apt-get update
  #   sudo apt-get install -y apache2
  # SHELL

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder "../data", "/vagrant_data"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  # config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
  #   vb.memory = "1024"
  # end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Define a Vagrant Push strategy for pushing to Atlas. Other push strategies
  # such as FTP and Heroku are also available. See the documentation at
  # https://docs.vagrantup.com/v2/push/atlas.html for more information.
  # config.push.define "atlas" do |push|
  #   push.app = "YOUR_ATLAS_USERNAME/YOUR_APPLICATION_NAME"
  # end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  # config.vm.provision "shell", inline: <<-SHELL
  #   sudo apt-get update
  #   sudo apt-get install -y apache2
  # SHELL
end
