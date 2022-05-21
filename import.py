from IM.classes.Func import str2time
from IM.classes.Obscurer import *
from IM.models import *
from tinkoff.invest import Client
from datetime import datetime as dt
import pytz
from django.core.cache import cache



# Получение списка портфелей по токену
def GetAccounts(tinkoffToken: str):
    with Client(tinkoffToken) as client:
        getAccountsRes = client.users.get_accounts()

        res = []
        for account in getAccountsRes.accounts:
            res.append({'id': account.id, 'name': account.name})
    return res


# Сорханение Tinkoff Token
def saveToken(portf: Portfolio, tinkoffToken: str, accountId: int):
    # Зашифровываем токен
    encToken = pack(tinkoffToken)
    portf.tt = encToken + '|ai:' + str(accountId)
    portf.broker = 'tink'
    portf.save(update_fields=['tt', 'broker'])


# Получение списка сделок
def getOperations(tinkoffToken: str, account_id, from_dt, to_dt):
    # Получаем список сделок
    ops = []
    with Client(tinkoffToken) as client:
        getOperationsRes = client.operations.get_operations(account_id=account_id, from_=from_dt, to=to_dt)
        ops = getOperationsRes.operations
    return ops


# Получение бумаги по FIGI
def figi2paper(tinkoffToken: str, figi: str):
    cache_key = hash_str('figi2paper:' + figi)
    paper = cache.get(cache_key)
    if paper:
        return paper

    paper = {}
    with Client(tinkoffToken) as client:
        getInstrumentByRes = client.instruments.get_instrument_by(id_type=1, id=figi)
        instr = getInstrumentByRes.instrument
        paper['figi'] = instr.figi
        paper['isin'] = instr.isin
        paper['ticker'] = instr.ticker
        paper['class_code'] = instr.class_code
        paper['currency'] = instr.currency
        paper['exchange'] = instr.exchange

    cache.set(cache_key, paper)
    return paper


# Обновление сделок
def updateTrades(portf: Portfolio):
    if not portf.tt:
        raise Exception('No Tinkoff Api Token in choosen portfolio')
    # Получаем номер аккаунта и токен
    tmp = portf.tt.split('|ai:')
    tinkoffToken = unpack(tmp[0])
    account_id = tmp[1]
    from_timestamp = str2time('2010-01-01')
    to_timestamp = dt.now(pytz.utc)
    # Получаем список сделок
    operations = getOperations(tinkoffToken, account_id, from_timestamp, to_timestamp)

    ops = []
    child_ops = []
    ops_ids = {}

    for op in operations:
        t = {}
        t['id'] = op.id
        t['currency'] = op.currency
        m = op.payment
        t['payment'] = m.units + m.nano / 1000000000
        m = op.price
        t['price'] = m.units + m.nano / 1000000000
        t['state'] = op.state
        t['quantity'] = op.quantity
        t['quantity_rest'] = op.quantity_rest
        t['figi'] = op.figi

        if t['figi'] != '':
            t['paper'] = figi2paper(tinkoffToken=tinkoffToken, figi=t['figi'])
        else:
            t['paper'] = {}

        t['instrument_type'] = op.instrument_type
        t['date'] = op.date
        t['type'] = op.type
        t['operation_type'] = op.operation_type.name
        t['commission'] = 0
        t['commission_currency'] = t['currency']
        parentId = op.parent_operation_id
        if parentId != '' and op.operation_type != 'TAX':
            t['parent_operation_id'] = op.parent_operation_id
            child_ops.append(t)
        else:
            ops.append(t)
            ops_ids[op.id] = len(ops) - 1

    for op in child_ops:
        if op['parent_operation_id'] in ops_ids:
            ops[ops_ids[op['parent_operation_id']]]['commission'] = op['payment']
            ops[ops_ids[op['parent_operation_id']]]['commission_currency'] = op['currency']

        # Если есть хоть одна сделка, создаём новый импорт
    if len(ops) == 0:
        return

    files_names = 'Tinkoff API'
    parser_type = 'tink_api'
    broker = parser_dict[parser_type][2]
    trImport = TrImport(portfolio=portf, broker=broker, parser=parser_type, fileNames=files_names)
    trImport.save()
    cnt = 0

    avaiable_types = list(map(lambda el: el[0], transaction_vars))

    # Перебираем полученные сделки
    for tr in ops:
        # Конвертируем тип операции из Tinkoff API в один их системных
        optype = typeConverter(tr['operation_type'])

        if not optype or optype not in avaiable_types:
            continue

        # Пропускаем отменённые сделки
        if tr['state'] == 2:
            continue

        quantity = tr['quantity'] - tr['quantity_rest']

        # Пропускаем сделки, если кол-во нулевое
        if optype in ('BUY', 'SELL', 'PAPER_IN', 'PAPER_OUT') and not quantity:
            continue

        security = None
        nkd = 0
        summa = tr['payment']
        price = tr['price']

        # Если сделка привязана к бумаге
        if tr['paper']:
            src = 'moex' if 'MOEX' in tr['paper']['exchange'] else 'yahoo'
            tr['paper']['ticker'] = tr['paper']['ticker'].replace("old", "")
            # Для валют выставляем источник moex
            if tr['paper']['class_code'] == 'CETS':
                src = 'moex'
            # Ищем бумагу в базе данных
            security = Security.objects.filter(
                (Q(ticker=tr['paper']['ticker']) | Q(isin=tr['paper']['isin'])) & Q(src=src)).first()
            # Если не найдена - пропускаем сделку
            if not security:
                continue
            if security.type == 'bond' and optype in ('BUY', 'SELL'):
                summa = quantity * price
                nkd = abs(tr['payment']) - abs(summa)
                pass

        if optype == 'TAX':
            quantity = 1
            price = summa
            if summa > 0:
                optype = 'INCOME'

        currency = tr['currency'].upper()
        commission_currency = tr['commission_currency'].upper()
        if currency not in currency_dict:
            currency = CURRENCY_DEFAULT
        if commission_currency not in currency_dict:
            commission_currency = CURRENCY_DEFAULT
        tr['commission'] = abs(tr['commission'])

        transaction = Transaction(
            portfolio=portf,
            transaction_id=tr['id'],
            type=optype,
            title=tr['type'],
            security=security,
            quantity=quantity,
            price=price,
            accruedint=nkd,
            summa=summa,
            commission=tr['commission'],
            currency=currency,
            commission_currency=commission_currency,
            dateTime=tr['date'],
            trimport=trImport
        )

        try:
            transaction.save()
            cnt += 1
        except Exception as e:

            pass

    if cnt > 0:
        trImport.counter = cnt
        trImport.save(update_fields=['counter'])
    else:
        trImport.delete()
    pass


# Не поддерживаемые операции. Пока не знаю что это и как обрабатывать
# OVERNIGHT, ACCRUING_VARMARGIN, WRITING_OFF_VARMARGIN, DIV_EXT

types_converter = {
    'INPUT': 'INPUT',
    'OUTPUT': 'OUTPUT',
    'OUTPUT_SECURITIES': 'PAPER_OUT',
    'INPUT_SECURITIES': 'PAPER_IN',
    'DIVIDEND': 'DIVIDEND',
    'DIVIDEND_TRANSFER': 'DIVIDEND',
    'COUPON': 'COUPON'
}


# Конвертирование типов операций Tinkoff API в IM
# https://tinkoff.github.io/investAPI/operations/#operationtype
def typeConverter(optype: str):
    optype = optype[15:]

    if optype in types_converter:
        return types_converter[optype]

    if 'TAX' in optype:
        return 'TAX'

    if 'REPAYMENT' in optype:
        return 'AMORT'

    if 'SELL' in optype:
        return 'SELL'

    if 'BUY' in optype:
        return 'BUY'

    if 'FEE' in optype:
        return 'COMMISSION'
    pass
