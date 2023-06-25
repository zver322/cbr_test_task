import requests
import time
import pandas as pd
import yaml
from pathlib import Path
import os
import threading
import csv
import logging


def get_telegram_info_from_config(path: str) -> [str, str]:
    """
    Функция, работающая с config.yml файлом для получения chat_id
    и telegram_token бота. Данная функция нужна, чтобы нельзя было
    в GitHub прочитать token и chat_id, так как они в виде str
    хранятся в конфиге, которы не загружается на GitHub.

    Args:
        path (str): Путь до config.yml

    Returns:
        [str, str]: telegram_token и chat_id
    """
    with open(path) as file:
        config = yaml.safe_load(file)
        return config['telegram_token'], config['telegram_chat_id']


def send_telegram_message(message: str) -> None:
    """
    Функция, отправляющая сообщение с помощью telegram_token
    в чат с chat_id  с помощью GET метода.

    Args:
        message (str): Сообщение, которое будет отправлено в Telegram

    Returns:
        None
    """
    base_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    parameters = {
        "chat_id": telegram_chat_id,
        "text": message
    }
    requests.get(base_url, data=parameters)


def send_telegram_csv_document(file) -> None:
    """
    Функция, отправляющая ежедневный отчет формата .csv в Telegram

    Args:
        file: Путь до отчет.csv

    Returns:
        None
    """
    base_url = f"https://api.telegram.org/bot{telegram_token}/sendDocument"
    my_file = open(f"{file}", "rb")
    parameters = {
        "chat_id": telegram_chat_id,
        "caption": "This is daily report"
    }
    files = {
        "document": my_file
    }
    requests.get(base_url, data=parameters, files=files)


path_to_config = 'config.yml'
telegram_token, telegram_chat_id = get_telegram_info_from_config(path_to_config)
logging.basicConfig(level=logging.INFO)

# Список организаций.
organizations = [
    {
        'organisation_name': 'Сбербанк',
        'service_name': 'Кредиты на любые цели',
        'service_link': 'https://www.sberbank.com/ru/person/credits/money',
        'mobile_service_link': 'https://online.sberbank.ru/CSAFront/index.do'
    },
    {
        'organisation_name': 'Альфа-Банк',
        'service_name': 'Потребительские кредиты',
        'service_link': 'https://www.sberbank.com/ru/person/credits/money',
        'mobile_service_link': 'https://business.auth.alfabank.ru/passport/cerberus-mini-blue/dashboard-blue/corp-username?response_type=code&client_id=corp-albo&scope=openid%20corp-albo&acr_values=corp-username&non_authorized_user=true',
    },
    {
        'organisation_name': 'ВБРР',
        'service_name': 'Потребительские кредиты',
        'service_link': 'https://www.vbrr.ru/private/credits/loan/',
        'mobile_service_link': 'https://online.vbrr.ru/#/',
    },
    {
        'organisation_name': 'Банк Открытие',
        'service_name': 'Кредит на любые цели',
        'service_link': 'https://www.open.ru/credits/cash?from=main_menu',
        'mobile_service_link': 'https://ib.open.ru/webbank/#/login',
    },
    {
        'organisation_name': 'ВТБ',
        'service_name': 'Потребительские кредиты',
        'service_link': 'https://www.vtb.ru/personal/kredit/',
        'mobile_service_link': 'https://online.vtb.ru/login',
    },
    {
        'organisation_name': 'ИНГОССТРАХ',
        'service_name': 'Страхование для путешествия за границу',
        'service_link': 'https://www.ingos.ru/travel/abroad',
        'mobile_service_link': 'https://www.ingos.ru/cabinet',
    },
    {
        'organisation_name': 'Ренессанс_страхование',
        'service_name': 'Онлайн страхование путешественников',
        'service_link': 'https://www.renins.ru/iris/di/process/travelinsurance/ZDM-200623-621#TravelSegmentationStep',
        'mobile_service_link': 'https://lk.renins.ru/login',
    },
    {
        'organisation_name': 'РЕСО-Гарантия',
        'service_name': 'Туристическая страховка',
        'service_link': 'https://reso.ru/individual/travel/',
        'mobile_service_link': 'https://client.reso.ru/wp-reso-ru/login.xhtml',
    },
    {
        'organisation_name': 'АльфаСтрахование',
        'service_name': 'Туристическая страховка',
        'service_link': 'https://www.alfastrah.ru/individuals/travel/',
        'mobile_service_link': 'https://www.alfastrah.ru/login/',
    },
    {
        'organisation_name': 'Сбербанк_страхование',
        'service_name': 'Страхование путешественников',
        'service_link': 'https://sberbankins.ru/products/travel-online/',
        'mobile_service_link': 'https://auth.sberbankins.ru/auth/realms/insure-app/protocol/openid-connect/auth?client_id=lk-app&redirect_uri=https%3A%2F%2Fonline.sberbankins.ru%2Fnewlk%2F&state=c82d0192-48bd-48cc-a5bd-adaca1f4a030&response_mode=fragment&response_type=code&scope=openid&nonce=c5a0c6b6-6cc9-42fc-a1da-5af9df23ee9c',
    }
]


def check_organisation_service_link(organisation: dict, day: int, start_time: float) -> None:
    """
    Функция, которая проверяет доступность ссылки веб-сайта, каждые 10 секунд, если выдается ошибка, то
    тогда проверяется тогда ссылка, проверяется, каждые 5 секунд. Данные события также записываются
    в текстовые файлы в определенном формате, чтобы потом можно было из них сделать отчет. Данная функция
    включает в себя бесконечный цикл, который прерывается после того как проходит 24 часа. В случае возникновения
    ошибки приходит сообщение в телеграм, когда работа сервиса восстанавливается, то приходит сообщение о восстановлении.
    Также, чтобы не присылать только первое уведомление, что произошел сбой, а затем только при восстановлении была
    сделана условная конструкция. Также в ходе работы логи выводятся в консоль.

    Args:
        organisation (dict): Словарь вида {наименование организации: "str", наименование сервиса: "str",
                                           ссылка на веб-сайт: "str", ссылка на мобильное приложение: "str"}
        day (int): День, для которого формируется отчет. То есть день 1, день 2 и т.п.
        start_time (float): Начальное время, которые используется для засечения таймера на 24 часа
    Returns:
        None
    """
    timeout, sleep_time, connection_error_time, error_count = 2, 10, 0, 0
    while True:
        if time.time() - start_time >= 86400:
            if connection_error_time != 0:
                with open(f"logs{day}/website/total_time_errors_{organisation['organisation_name']}.txt", "a") as b:
                    b.write(f'{str(connection_error_time)}\n')
            break
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            status_code = requests.get(organisation['service_link'], timeout=timeout).status_code
            if status_code:
                logging.info(f"{organisation['service_link']} - {status_code} - {now}")

            if connection_error_time != 0:
                error_count = 0
                message = f"{organisation['organisation_name']} - {organisation['service_name']} - {organisation['service_link']} - {now} - Восстановление"
                send_telegram_message(message)
                with open(f"logs{day}/website/errors_{organisation['organisation_name']}.txt", "a") as f:
                    f.write(f'{message}\n')
                with open(f"logs{day}/website/total_time_errors_{organisation['organisation_name']}.txt", "a") as b:
                    b.write(f'{str(connection_error_time)}\n')
                connection_error_time, sleep_time = 0, 10

        except requests.exceptions.RequestException as e:
            logging.info(f"{e} {now}")
            error_count += 1
            connection_error_time += 7
            if error_count == 1:
                message = f"{organisation['organisation_name']} - {organisation['service_name']} - {organisation['service_link']} - {now} - {e}"
                send_telegram_message(message)
                with open(f"logs{day}/website/errors_{organisation['organisation_name']}.txt", "a") as f:
                    f.write(f'{message}\n')
            sleep_time = 5
        time.sleep(sleep_time)


def check_organisation_mobile_service_link(organisation: dict, day: int, start_time: float) -> None:
    """
    Функция, которая проверяет доступность ссылки аутентификации, каждые 10 секунд, если выдается ошибка, то
    тогда проверяется тогда ссылка, проверяется, каждые 5 секунд. Данные события также записываются
    в текстовые файлы в определенном формате, чтобы потом можно было из них сделать отчет. Данная функция
    включает в себя бесконечный цикл, который прерывается после того как проходит 24 часа. В случае возникновения
    ошибки приходит сообщение в телеграм, когда работа сервиса восстанавливается, то приходит сообщение о восстановлении.
    Также, чтобы не присылать только первое уведомление, что произошел сбой, а затем только при восстановлении была
    сделана условная конструкция. Также в ходе работы логи выводятся в консоль.

    Args:
        organisation (dict): Словарь вида {наименование организации: "str", наименование сервиса: "str",
                                           ссылка на веб-сайт: "str", ссылка на мобильное приложение: "str"}
        day (int): День, для которого формируется отчет. То есть день 1, день 2 и т.п.
        start_time (float): Начальное время, которые используется для засечения таймера на 24 часа
    Returns:
        None
    """
    timeout, sleep_time, connection_error_time, error_count = 2, 10, 0, 0
    while True:
        if time.time() - start_time >= 86400:
            if connection_error_time != 0:
                with open(f"logs{day}/mobile/total_time_errors_{organisation['organisation_name']}.txt", "a") as b:
                    b.write(f'{str(connection_error_time)}\n')
            break
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            status_code = requests.get(organisation['mobile_service_link'], timeout=timeout).status_code
            if status_code:
                logging.info(f"{organisation['service_link']} - {status_code} - {now}")

            if connection_error_time != 0:
                error_count = 0
                message = f"{organisation['organisation_name']} - {organisation['service_name']} - {organisation['mobile_service_link']} - {now} - Восстановление"
                send_telegram_message(message)
                with open(f"logs{day}/mobile/errors_{organisation['organisation_name']}.txt", "a") as f:
                    f.write(f'{message}\n')
                with open(f"logs{day}/mobile/total_time_errors_{organisation['organisation_name']}.txt", "a") as b:
                    b.write(f'{str(connection_error_time)}\n')
                connection_error_time, sleep_time = 0, 10

        except requests.exceptions.RequestException as e:
            logging.info(f"{e} {now}")
            error_count += 1
            connection_error_time += 7
            if error_count == 1:
                message = f"{organisation['organisation_name']} - {organisation['service_name']} - {organisation['mobile_service_link']} - {now} - {e}"
                send_telegram_message(message)
                with open(f"logs{day}/mobile/errors_{organisation['organisation_name']}.txt", "a") as f:
                    f.write(f'{message}\n')
            sleep_time = 5
        time.sleep(sleep_time)


def create_files_for_logs(day: int) -> None:
    """
    Функция, создающая папку log{day}/, в которой хранятся логи работы
    вебсайта и ссылки на аутентификацию

    Args:
        day (int): День, для которого формируется отчет. То есть день 1, день 2 и т.п.

    Returns:
        None
    """
    if not os.path.exists(f'logs{day}'):
        os.mkdir(f'logs{day}')
    if not os.path.exists(f'logs{day}/website'):
        os.mkdir(f'logs{day}/website')
    if not os.path.exists(f'logs{day}/mobile'):
        os.mkdir(f'logs{day}/mobile')
    for i in range(len(organizations)):
        f = Path(f'logs{day}/website/errors_{organizations[i]["organisation_name"]}.txt')
        f.touch(exist_ok=True)
        f = open(f, "w+")
        b = Path(f'logs{day}/website/total_time_errors_{organizations[i]["organisation_name"]}.txt')
        b.touch(exist_ok=True)
        b = open(b, "w+")
        f = Path(f'logs{day}/mobile/errors_{organizations[i]["organisation_name"]}.txt')
        f.touch(exist_ok=True)
        f = open(f, "w+")
        b = Path(f'logs{day}/mobile/total_time_errors_{organizations[i]["organisation_name"]}.txt')
        b.touch(exist_ok=True)
        b = open(b, "w+")


def generate_report(day: int) -> None:
    """
    Функция, которая генерирует отчет и отправляет его в Telegram канал. Отчет формируется в формате .csv
    таблицы. Содержит в себе по вертикали 10 строк, которые представляют отчетность работы сервиса кампании.
    Столбцы имеют название: перечень организаций, uptime сайта, uptime мобильного приложения, время недоступности сайта,
    время недоступности мобильного приложения, суммарное время недоступности сервиса.
    Пояснение: uptime - результат деления времени непрерывной работы на время в сутках умноженное на 100 с точностью до
    2 знаков после запятой, например: 99,98%
    Пояснение:   время недоступности конкретного сервиса в формате – «Наименование сервиса – timestamp прекращения
    работы сервиса – timestamp восстановления работы сервиса – timestamp прекращения работы сервиса»

    Args:
        day (int): День, для которого формируется отчет. То есть день 1, день 2 и т.п.

    Returns:
        None
    """
    organisation_names = []
    for organisation in organizations:
        organisation_names.append(organisation['organisation_name'])

    uptime_website, total_website_time_errors = [], [0] * 10
    for i in range(len(organizations)):
        if os.path.getsize(f'logs{day}/website/total_time_errors_{organizations[i]["organisation_name"]}.txt') == 0:
            uptime_website.append(100)
        else:
            with open(f'logs{day}/website/total_time_errors_{organizations[i]["organisation_name"]}.txt', 'r') as f:
                reader = csv.reader(f)
                total_time_errors = 0
                for row in reader:
                    total_time_errors += int(row[0])
                total_website_time_errors[i] = total_time_errors
                uptime_website.append(float("{:.2f}".format((86400 - total_time_errors) / 86400 * 100)))

    uptime_mobile, total_mobile_time_errors = [], [0] * 10
    for i in range(len(organizations)):
        if os.path.getsize(f'logs{day}/mobile/total_time_errors_{organizations[i]["organisation_name"]}.txt') == 0:
            uptime_mobile.append(100)
        else:
            with open(f'logs{day}/mobile/total_time_errors_{organizations[i]["organisation_name"]}.txt', 'r') as f:
                reader = csv.reader(f)
                total_time_errors = 0
                for row in reader:
                    total_time_errors += int(row[0])
                total_mobile_time_errors[i] = total_time_errors
                uptime_mobile.append(float("{:.2f}".format((86400 - total_time_errors) / 86400 * 100)))

    errors_mobile_info = ['-'] * 10
    for i in range(len(organizations)):
        if os.path.getsize(f'logs{day}/mobile/errors_{organizations[i]["organisation_name"]}.txt'):
            with open(f'logs{day}/mobile/errors_{organizations[i]["organisation_name"]}.txt', 'r') as f:
                starting_string = f'{organizations[i]["service_name"]} - '
                reader = csv.reader(f)
                counter = 0
                for row in reader:
                    counter += 1
                    if counter % 2 == 1:
                        starting_string += f"{row[0].split(' - ')[3]} прекращения работы сервиса - "
                    else:
                        starting_string += f"{row[0].split(' - ')[3]} восстановления работы сервиса - "
                starting_string = starting_string.split(' - ')[:-1]
                starting_string = ' - '.join(starting_string)
                errors_mobile_info[i] = starting_string

    errors_website_info = ['-'] * 10
    for i in range(len(organizations)):
        if os.path.getsize(f'logs{day}/website/errors_{organizations[i]["organisation_name"]}.txt'):
            with open(f'logs{day}/website/errors_{organizations[i]["organisation_name"]}.txt', 'r') as f:
                starting_string = f'{organizations[i]["service_name"]} - '
                reader = csv.reader(f)
                counter = 0
                for row in reader:
                    counter += 1
                    if counter % 2 == 1:
                        starting_string += f"{row[0].split(' - ')[3]} прекращения работы сервиса - "
                    else:
                        starting_string += f"{row[0].split(' - ')[3]} восстановления работы сервиса - "
                starting_string = starting_string.split(' - ')[:-1]
                starting_string = ' - '.join(starting_string)
                errors_website_info[i] = starting_string

    total_mobile_and_website_time_errors = []
    for i in range(len(organizations)):
        total_mobile_and_website_time_errors.append(total_website_time_errors[i] + total_mobile_time_errors[i])

    final_table = {'Перечень организаций': organisation_names,
                   'Uptime сайта': uptime_website,
                   'Uptime мобильного приложения': uptime_mobile,
                   'Время недоступности сайта': errors_website_info,
                   'Время недоступности мобильного приложения': errors_mobile_info,
                   'Суммарное время недоступности сервиса': total_mobile_and_website_time_errors}
    df = pd.DataFrame(final_table)
    df.to_csv(f"report_{day}.csv", index=False)
    send_telegram_csv_document(f"report_{day}.csv")


def main() -> None:
    """
    Основная функция, которая запускает всю программу. Она создает 20 потоков, которые параллельно
    ведут в течение 24 часов мониторинг и отправляют уведомления в Telegram. Программа ждет, когда
    закончатся все потоки, чтобы сформировать ежедневный отчет.

    Returns:
        None
    """
    day = 2
    create_files_for_logs(day)
    threads = []
    for organisation in organizations:
        a = threading.Thread(target=check_organisation_service_link, args=(organisation, day, time.time()))
        b = threading.Thread(target=check_organisation_mobile_service_link, args=(organisation, day, time.time()))
        threads.append(a)
        threads.append(b)
        a.start()
        b.start()
    for t in threads:
        t.join()
    generate_report(day)


if __name__ == '__main__':
    main()
