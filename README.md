# monitoring-plugins

## Installation

### Linux
Create file /etc/sudoers.d/username_here with mod 0440 root:root
%username_here ALL=(ALL) NOPASSWD:/bin/kill -0 [0-9]*

### FreeBSD

Create file /usr/local/etc/sudoers.d/username_here with mod 0440 root:wheel
%username_here ALL=(ALL) NOPASSWD:/bin/kill -0 [0-9]*

## Plugins

### Process

check_process.sh - reads pid file and sends kill -0 to the process

### RabbitMQ

Extended version of original sensu rabbitmq plugins: https://github.com/sensu-plugins/sensu-plugins-rabbitmq
check_rabbitmq_amqp_alive.py
check_rabbitmq_rate.py
check_rabbitmq_per_queue_rate.py

### Kibana
check_kibana.py

