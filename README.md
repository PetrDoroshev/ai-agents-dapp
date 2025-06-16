# ai-agents-dapp

## Как запустить
1) Склонировать проект
2) Запустить локальный инстанс ganache
3) Создать виртуальную среду venv
4) Установить зависимости из requirements.txt
5) Скомпилировать смарт-контракты при помощи truffle (compile, migrate)
6) Обновить переменные окружения в файле .env
7) Опционально. Добавить API ключ DeepSeek ```DEEPSEEK_API_KEY={}``` https://openrouter.ai/  вставить API ключ с этого сайта, как бесплатный (model deepseek free - deepseek-r1-0528:free)
8) Запустить сервер ```uvicorn app.main:app --reload``` из КОРНЕВОЙ папки репо
