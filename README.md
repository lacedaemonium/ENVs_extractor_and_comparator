# Скрипт сравнения переменных между Gitlab и Consul
## Описание
Скрипт ходит в main ветку gitlab и в consul окружения QA, достает оттуда текущие переменные (env) запрошенного микросервиса указанной версии и выводит их сравнение. 

Вывод в формате "добавлено (added)" означает, что разработчик добавил некие новые переменные и они присутствуют в ветке main в gitlab, но в consul QA их еще нет; соответственно, вывод "удалено (removed)" означает, что разработчик удалил некие переменные, но они пока еще присутствуют в consul QA.

Сервисы с общей кодовой базой имеют отдельную обработку внутри кода из-за внутренних сложностей, связанных с историей развития микросервисов, и особенностей хранения переменных окружения (общие + специфичные для отдельного протокола).

## Подготовка к запуску:
Положить токены для доступа в Gitlab и Consul в файл config.yaml.
Указать значения переменных в main.py:
    gitlab_address = ''
    project_name = ''

## Запуск:
```
# python3 main.py -n ИМЯ_МИКРОСЕРВИСА -v ВЕРСИЯ_МИКРОСЕРВИСА
```
например
```
# python3 main.py -n user-api -v 0.10.0
```
По необходимости можно включить дебаг-режим, указав дополнительный ключ **-l=debug**

### ВНИМАНИЕ WARNING ACHTUNG УВАГА ###
В среде (системе), где происходит запуск программы, сертификаты внутренних сервисов (consul и gitab) должны быть доверенными!
