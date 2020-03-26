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

## ЗАПУСК
- docker-compose up -d  (запуск)
- docker-compose logs (посмотреть не упало ли что и последние строки логов)

## ОСТАНОВ
- docker-compose down

## ЛОГИ
- /var/log
