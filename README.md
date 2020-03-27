# taximaster

## РАЗВЁРТЫВАНИЕ
Разертывание производилось на debian-10
Оптимальнее всего на системе с действующим freeswitch

- sudo apt install docker-compose docker
- sudo systemctl start docker
- git clone https://github.com/andrewisakov/freeswitch_originator_proxy

## СБОРКА
- cd taximaster
- docker-compose build
- sudo cp callback_script.py /usr/share/freeswitch/scripts.py

## ЗАПУСК
- docker-compose up -d  (запуск)
- docker-compose logs (посмотреть не упало ли что)

## ОСТАНОВ
- docker-compose down

## ЛОГИ
- /var/log
