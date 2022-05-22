# tinkoffOpenAPI2.0
Использование API Тинькофф Инвестиций в Invest Monitoring

# Что это такое?
[Invest Monitoring](https://investmonitoring.ru) - это система для учета инвестиций со всех брокерских, банковских счетов и крипто-кошельков 

# Для кого
1. Владельцы более одного брокерского счёта
2. Частные инвесторы, которым нужна продвинутая портфельная аналитика

# User case
У Ивана есть брокерский счет в Тинькофф и ВТБ, есть вклад в банке, криптокошелек. Из-за разброса активов и волательности рынка Ивану трудно контролировать доходность всех инвестиций и проводить ребалансировку портфеля. <br/><br/>
А из-за санкций на крупные банки ситуация усложнилась еще сильнее: из брокерского счета ВТБ все ценные бумаги кроме валюты перешли в Альфа банк, а далее иностранные активы (по решению Ивана) перевелись в Тинькофф. Российские активы Ивана остались в Альфа банке. <br/><br/>
В [Invest Monitoring](https://investmonitoring.ru) Иван может 
* импортировать отчеты брокера ВТБ и Альфа банка, 
* вручную добавить криптовалюту и банковские вклады,
* импортировать историю сделок Тинькофф по API и в дальнейшем легко синхронизировать информацию.

Таким образом Иван сможет контролировать весь портфель в одном сервисе

# Возможности системы
1. Импорт отчетов 20 брокеров
2. Импорт сделок по Tinkoff Open API
3. Ручное добавление сделок с акциями, облигациями, ETF, криптовалютой и фиатом
4. Ведение сводного портфеля инвестиций
5. Расчет доходности портфеля (XIRR) с учетом налогов, комиссий и курсовой разницы

# Приеимущества Tinkoff Open API 2.0 для учета инвестиций
1. Интеграция по API позволяет мгновенно обновлять историю сделок нажатием одной кнопки (в отличии от импорта отчетов и ручного ввода). Это преимущество Тинькофф над остальными российскими брокерами
2. в Tinkoff Open API 2.0 добавлена возможно генерации токена **только на чтение**, что гарантирует безопасность (нет доступа к совершению сделок) при использовании токена в сторонних сервисах

# Репозиторий
> В github приведена только часть исходного кода, относящегося к интеграции с Tinkoff Open API 2.0
* tinkoff - использованная SDK https://github.com/Tinkoff/invest-python
* import.py - получение списка счетов, получение сделок

