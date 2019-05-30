# Yandex Transport Proxy

**Build status:** ![Build Status](http://owlsoul.biz.tm/YandexTransportProxy/status.php?test=build)

A proxy server to work in conjunction with [YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python).

Прокси сервер для работы в паре с [YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python).

*This project is for "Yandex.Maps" and "Yandex.Transport" services, so it's expected that majority of potential users are from Russian Federation, thus the README is written in russian language.*

![Yandex Transport Proxy Logo](https://raw.githubusercontent.com/OwlSoul/Images/master/YandexTransportProxy/yandex_transport_logo.png)


## Что это за зверь и чего он делает?
На данный момент Яндекс не дает свободный доступ к API Яндекс.Транспорт/Masstransit API (не следует путать с API Яндекс.Расписания, там доступ как раз есть). Этот прокси-сервер представляет из себя хитрую конструкцию для относительного исправления этого недостатка. 

Получить данные вроде "покажи координаты всего общественного транспорта в таком-то районе" или "выдай мне данные о координатах транспорта по всему городу в данный момент" с помощью этой штуковины просто так нельзя. Зато с ее помощью можно автоматизировать получение данных  по конкретной остановке, или по конкретному маршруту, и получить их именно в том формате в котором Яндекс их пересылает - здоровенные такие JSON-структуры (до 150 килобайт и больше). 

Полученные данные можно использовать для сбора статистики по конкретному маршруту, создания своего собственного табло для конкретной остановки, и автоматизации каких-либо событий на основе данных о транспорте (редко ходящий, но жизненно важный автобус вышел на маршрут - включаем будильник).

## Как эта штука работает?
Предыдущая версия, [Yandex Transport Monitor](https://github.com/OwlSoul/YandexTransportMonitor), использовала Selenium Webdriver и Chromium, получала страницу Яндекс.Карт с информацией об остановке, и дальше в ход шел обычный парсинг. Решение имело право на жизнь, но любой редизайн карт приводил к приятным вечерам и переписыванию проекта под новую реальность. К тому же Карты показывают лишь малую часть приходящей от Masstransit API информации, а приходит ее там... очень прилично так.

Новая версия, [Yandex Transport Proxy](https://github.com/OwlSoul/YandexTransportProxy), идет гораздо дальше. Все так же используется Selenium Webdriver в связке с Chromium, и вместо парсинга страницы она бесцеремонно вытаскивает из кэша браузера те самые JSON-результаты Masstransit API, приходящие от Яндекса. Дополнительно данный прокси-сервер контролирует задержки между запросами к Яндекс.Картам, и следит чтобы оно выполнялось в один поток (а то Яндекс разозлится и всем будет плохо).

Почему используется связка "Selenium Webdriver + Chromium", а не cURL? cURL очень быстро натыкался на бан со стороны Яндекса, и ловил себе CAPTCHA, а еще Yandex.Maps запрешивает данные у Masstransit API через AJAX-запросы, и нужно знать какие именно данные есть по данной остановке/маршруту и какие запросы делать. Браузер берет эту работу на себя, имитируя действия пользователя, и прокси-серверу остается только вытащить из кэша результаты.

Сам Chromium работает в headless режиме, так он потребляет меньше ресурсов и делает возможным запуск этой штуковины на сервере и/или в Docker-контейнере. Прокси-сервер сам по себе вполне stateless, так что никто не запрещает создать Kubernetes-кластер и вот тут уже мониторить весь город (если он небольшой, как какой-нибудь Долгопрудный), чувствуя **"ВЛАСТЬ"** (и молиться чтобы Яндекс не одурел от такой наглости).

**В общем, вот так это работает:** \
Прокси-сервер получает от пользователя запрос "*Вот у меня тут URL Яндекса, давай мне всю (или выборочно, по конкретному методу) информацию что там есть касаемо публичного транспорта*", и сервер отвечает "*Aye aye, captain!*", и ~~крашится~~ выдает в ответ JSON полученный от Yandex.Masstransit API. Для работы с прокси-сервером используется вот эта штука [YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python), а сам прокси-сервер просто должен быть где-то запущен и доступен по сети, самый простой вариант - на этой же машине.

## Что делать с полученными JSON
У Яндекс Masstransit API на данный момент выявлены следующие методы:

| Метод | Что делает? |
| ----- | ----- |
| getStopInfo | Выдает всю информацию об остановке, расчетное время прибытия транспорта - здесь. |
| getLine | Выдает всю информацию о маршруте, в основном остановки через которые он проходит. Очень много данных, обычно это самый толстый и упитанный JSON из всех. |
| getVehiclesInfo | Выдает всю информацию о транспорте на маршруте, координаты автобусов это здесь.|
| getVehiclesInfoWithRegion | Выдает всю информацию о маршруте, и еще какую-то информацию о регионе. Возможно сменит предыдущий (он тут относительно недавно) |
| getLayerRegions | Если честно на данный момент я абсолютно без понятия что он делает, но дергается оно по поводу и без. |

В целом JSONы достаточно интуитивно понятные (кроме _getLayerRegions_, серьезно, что это за штука вообще?), но информации там очень сильно много. Примеры получаемых JSON можно посмотреть в [wiki](https://github.com/OwlSoul/YandexTransportProxy/wiki) к этому проекту.

## Установка
Очень рекомендуется использовать эту штуку внутри Docker-контейнера. CI/CD система, привязанная, к этому проекту автоматически выкладывает на Dockerhub dev и stable образы, содержащие в себе Chromium, Selenium Webdriver и сам прокси-сервер.

### Вариант 1. Установка с DockerHub
Стабильная последняя версия:

```docker pull owlsoul/ytproxy:latest```

Определенная стабильная версия:

```docker pull owlsoul/ytproxy:1.0.0```

Нестабильная истекающая багами "Dev" версия:

```docker pull owlsoul/ytproxy:dev```

### Вариант 2. Используя Dockerfile
Нужно сохранить себе этот проект ("git clone" или [cкачать релиз](https://github.com/OwlSoul/YandexTransportProxy/releases)), и в "корне" выполнить команду:

```docker build -t "owlsoul/ytproxy:dev" .```

### Вариант 3. Old School, без использования контейнеров
Не рекомендуется, проект использует Chromium, и если тот в системе основной браузер - может быть неприятно и неудобно. Инструкция только для Linux Ubuntu.

Ставим необходимые пакеты:
```
apt-get update && \
    apt-get install -y \
    locales \
    tzdata \
    chromium-browser \
    chromium-chromedriver \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    python3 \
    python3-pip
```

Ставим дополнительные пакеты из pip:
```
pip3 install psycopg2-binary \
             selenium \
             setproctitle \
             beautifulsoup4 \
             lxml
```

Готово. Прокси-сервер написан на Python, больше ничего не требуется, только запустить его.

## Запуск прокси-сервера
По умолчанию при запуске из Docker-контейнера сервер будет ждать запросы на 0.0.0.0:25555.

Запуск докер-контейнера:

```docker run -it -p 25555:25555 owlsoul/ytproxy:latest```

**Параметры командной строки:**
*  --host - адрес на котором сервер будет ожидать запросы
*  --port - порт, на котором сервер будет ожидать запросы
*  --verbose - "разговорчивость", 0 - зловещая тишина, 1 - сообщения об ошибках, 2 - ошибки и предупреждения, 3 - ошибки, предупреждения, информация, 4 - Debug
*  --delay - задержка между выполнением сервером запросов.

**Примеры:**

*Запуск докер-контейнера, порт 30000, полная отладка, задержка между запросами 30 секунд.*
```docker run -it -p 30000:30000 owlsoul/ytproxy:latest "./transport_proxy --port 30000 --verbose 4 --delay 30"```

*Запуск докер-контейнера, порт 44444, только сообщения об ошибках и предупреждения, в фоне, не меняя порт самого прокси-сервера, а перенаправляя порт хоста через Docker, задержка между запросами 10 секунд.*
```docker run -dt -p 44444:25555 owlsoul/ytproxy:latest "./transport_proxy --delay 10 --verbose 2"```

*Запуск через docker-compose*

Пример файла docker-compose.yml
```
version: "3.0"

networks:
  transport-proxy:
    external: false

services:
  server:
    image: owlsoul/ytproxy:latest
    restart: unless-stopped
    container_name: "ytproxy"
    environment:
      - PYTHONUNBUFFERED=1
    networks:
      - transport-proxy
    ports:
      - "25555:25555"
    command: ./transport_proxy.py --delay 10 --verbose 4

```
Запуск:
```
docker-compose up -d 
```

*Запуск сервера без докер-контейнера (не рекомендуется)*

Ждать запросов на 127.0.0.1, порт 35555, задержка между выполнением запросов 15 секунд, полный дебаг:

```./transport-proxy --host 127.0.0.1 --port 35555 --delay 15 --verbose 4```

## Остановка прокси-сервера

Прокси-сервер прекращает свою жизнедеятельность при получении сигнала SIGINT или SIGTERM. В случае с Docker'изированным приложением можно его просто остановить (```docker stop```), вы все равно не услышите как прокси-сервер горит в аду завершающегося контейнера.

## Поддержка и обратная связь.
Гарантий что эта штука будет работать долго и счастливо - никаких. Яндекс может в любой момент устроить что-нибудь что сделает работу этого проекта невозможным. Проект находится на постоянной системе мониторинга, и если что-то отваливается или перестает работать - автор об этом оперативно узнает, и поправит, если это возможно.

В любом случае, сообщить о возникшей проблеме всегда можно здесь: \
https://github.com/OwlSoul/YandexTransportProxy/issues/new

## Лицензия / License
Исходный код распространяется под лицензией MIT, "как есть (as is)", автор ответственности за возможные проблемы при его использовании не несет (но будет глубоко расстроен).

The code is distributed under MIT licence, AS IS, author do not bear any responsibility for possible problems with usage of this project (but he will be very sad).

## Зал славы / Credits
__Project author:__ [Yury D.](https://github.com/OwlSoul) (TheOwlSoul@gmail.com) \
__PEP-8 Evangelist, Good Cop:__ [Pavel Lutskov](https://github.com/ltskv) \
__PEP-8 Evangelist, Bad Cop:__ [Yury Alexeev](https://github.com/Kuma-San0217)

----

