import random
import math
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from db import (
    SessionLocal, Base, engine,
    User, Category, Transaction, Budget, Goal,
    AIForecast, AIAnomaly, AIBudgetRecommendation
)
from utils import get_password_hash

USERS_COUNT = 10
TRANSACTIONS_COUNT = 1000
CHUNK_SIZE = 100

FIRST_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Анна", "Мария", "Екатерина", "Ольга", "Наталья",
    "Ирина", "Елена", "Юлия", "Татьяна", "Светлана",
]

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев",
    "Петров", "Соколов", "Михайлов", "Новиков", "Фёдоров",
    "Иванова", "Смирнова", "Кузнецова", "Попова", "Васильева",
    "Петрова", "Соколова", "Михайлова", "Новикова", "Фёдорова",
]

EXPENSE_CATEGORIES = [
    ("Продукты питания", 3000, 15000),
    ("Транспорт", 1000, 5000),
    ("Рестораны и кафе", 500, 8000),
    ("ЖКХ и коммунальные", 2000, 7000),
    ("Одежда и обувь", 1000, 20000),
    ("Здоровье и медицина", 500, 10000),
    ("Развлечения", 500, 6000),
    ("Связь и интернет", 300, 2000),
    ("Образование", 1000, 15000),
    ("Спорт и фитнес", 500, 5000),
    ("Путешествия", 5000, 80000),
    ("Техника и электроника", 2000, 60000),
    ("Домашние животные", 500, 5000),
    ("Красота и уход", 300, 5000),
    ("Подарки", 500, 10000),
]

INCOME_CATEGORIES = [
    ("Зарплата", 40000, 150000),
    ("Фриланс", 5000, 80000),
    ("Подработка", 3000, 30000),
    ("Инвестиции и дивиденды", 1000, 50000),
    ("Аренда", 10000, 40000),
    ("Продажа имущества", 5000, 200000),
    ("Государственные выплаты", 5000, 20000),
    ("Подарки и переводы", 1000, 30000),
]

EXPENSE_DESCRIPTIONS = {
    "Продукты питания": ["Покупка в Пятёрочке", "Закупка в Магните", "ВкусВилл", "Перекрёсток", "Ашан", "Лента"],
    "Транспорт": ["Проездной на месяц", "Такси Яндекс", "Бензин", "Парковка", "Каршеринг"],
    "Рестораны и кафе": ["Обед в кафе", "Ужин с семьёй", "Кофе в Starbucks", "Доставка еды", "Бизнес-ланч"],
    "ЖКХ и коммунальные": ["Оплата электричества", "Квартплата", "Газ", "Водоснабжение", "Интернет домой"],
    "Одежда и обувь": ["Зимняя куртка", "Спортивные кроссовки", "Джинсы", "Рубашка", "Летнее платье"],
    "Здоровье и медицина": ["Аптека", "Приём врача", "Анализы", "Стоматолог", "Витамины"],
    "Развлечения": ["Кино", "Театр", "Концерт", "Зоопарк", "Боулинг"],
    "Связь и интернет": ["Мобильная связь МТС", "Билайн тариф", "Мегафон", "Домашний интернет"],
    "Образование": ["Онлайн-курс", "Учебники", "Репетитор", "Подписка Coursera", "Языковые курсы"],
    "Спорт и фитнес": ["Абонемент в спортзал", "Бассейн", "Йога", "Теннис", "Велосипед"],
    "Путешествия": ["Авиабилеты", "Отель", "Экскурсия", "Страховка для путешествий", "Визовый сбор"],
    "Техника и электроника": ["Наушники", "Смартфон", "Ноутбук", "Планшет", "Смарт-часы"],
    "Домашние животные": ["Корм для кошки", "Ветеринар", "Наполнитель", "Игрушки для собаки"],
    "Красота и уход": ["Парикмахерская", "Маникюр", "Косметика", "Шампунь и уход", "Массаж"],
    "Подарки": ["День рождения друга", "Новый год", "8 марта", "Свадебный подарок", "23 февраля"],
}

INCOME_DESCRIPTIONS = {
    "Зарплата": ["Зарплата за месяц", "Аванс", "Зарплата + премия", "Квартальная премия"],
    "Фриланс": ["Разработка сайта", "Дизайн логотипа", "Написание текстов", "Консультация", "Переводы"],
    "Подработка": ["Подработка в выходные", "Доставка", "Репетиторство", "Работа в праздники"],
    "Инвестиции и дивиденды": ["Дивиденды по акциям", "Проценты по вкладу", "Купоны по облигациям"],
    "Аренда": ["Аренда квартиры", "Сдача гаража", "Аренда склада"],
    "Продажа имущества": ["Продажа авто", "Продажа техники", "Авито", "Продажа мебели"],
    "Государственные выплаты": ["Налоговый вычет", "Пособие", "Субсидия на ЖКХ"],
    "Подарки и переводы": ["Перевод от родителей", "Подарок на ДР", "Помощь от родственников"],
}

GOAL_TEMPLATES = [
    ("Покупка автомобиля", 800000, 1500000),
    ("Первоначальный взнос на ипотеку", 500000, 2000000),
    ("Отпуск за границей", 80000, 300000),
    ("Ремонт квартиры", 150000, 600000),
    ("Покупка ноутбука", 60000, 150000),
    ("Свадьба", 200000, 800000),
    ("Образование ребёнка", 100000, 500000),
    ("Финансовая подушка безопасности", 200000, 1000000),
    ("Покупка смартфона", 30000, 120000),
    ("Инвестиционный капитал", 300000, 2000000),
]

RECOMMENDATION_TYPES = ["INCREASE", "DECREASE", "CREATE"]

RECOMMENDATION_TEXTS = {
    "INCREASE": [
        "Расходы по этой категории систематически превышают лимит. Рекомендуется увеличить бюджет для снижения стресса.",
        "Средние расходы выше установленного лимита. Увеличение бюджета сделает планирование реалистичнее.",
    ],
    "DECREASE": [
        "Расходы по категории значительно ниже лимита последние 3 месяца. Можно снизить бюджет и перераспределить средства.",
        "Анализ показывает переизбыток бюджета. Рекомендуется оптимизировать для более точного финансового планирования.",
    ],
    "CREATE": [
        "Обнаружены регулярные расходы без бюджетного плана. Создание лимита поможет контролировать эту статью расходов.",
        "Выявлена новая категория трат. Рекомендуется установить бюджетный лимит для лучшего контроля.",
    ],
}


def random_date(start: date, end: date) -> str:
    delta = end - start
    return str(start + timedelta(days=random.randint(0, delta.days)))


def clear_database(db: Session):
    print("Clearing existing data...")
    db.query(AIBudgetRecommendation).delete()
    db.query(AIAnomaly).delete()
    db.query(AIForecast).delete()
    db.query(Budget).delete()
    db.query(Goal).delete()
    db.query(Transaction).delete()
    db.query(Category).delete()
    db.query(User).delete()
    db.commit()
    print("Database cleared.")


def seed_users(db: Session) -> list[User]:
    print(f"Seeding {USERS_COUNT} users...")
    users = []
    used_emails = set()
    for i in range(USERS_COUNT):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{last} {first}"
        base_email = f"user{i + 1:02d}@financetracker.ru"
        while base_email in used_emails:
            base_email = f"user{i + 1:02d}_{random.randint(10, 99)}@financetracker.ru"
        used_emails.add(base_email)
        user = User(
            full_name=full_name,
            email=base_email,
            password=get_password_hash(f"password{i + 1}"),
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 730)),
        )
        db.add(user)
        users.append(user)
    db.commit()
    for u in users:
        db.refresh(u)
    print(f"  -> {len(users)} users created.")
    return users


def seed_categories(db: Session, users: list[User]) -> dict[int, dict]:
    print("Seeding categories...")
    user_categories = {}
    for user in users:
        expense_sample = random.sample(EXPENSE_CATEGORIES, k=random.randint(5, 8))
        income_sample = random.sample(INCOME_CATEGORIES, k=random.randint(2, 4))
        expense_cats = []
        income_cats = []
        for name, low, high in expense_sample:
            cat = Category(user_id=user.id, name=name, type="expense")
            db.add(cat)
            expense_cats.append((cat, low, high))
        for name, low, high in income_sample:
            cat = Category(user_id=user.id, name=name, type="income")
            db.add(cat)
            income_cats.append((cat, low, high))
        db.commit()
        for cat, low, high in expense_cats + income_cats:
            db.refresh(cat)
        user_categories[user.id] = {
            "expense": expense_cats,
            "income": income_cats,
        }
    total_cats = sum(
        len(v["expense"]) + len(v["income"]) for v in user_categories.values()
    )
    print(f"  -> {total_cats} categories created.")
    return user_categories


def seed_transactions(db: Session, users: list[User], user_categories: dict) -> list[Transaction]:
    print(f"Seeding {TRANSACTIONS_COUNT} transactions in chunks of {CHUNK_SIZE}...")
    start_date = date(2024, 1, 1)
    end_date = date(2025, 12, 31)
    all_transactions = []
    chunk = []

    for i in range(TRANSACTIONS_COUNT):
        user = users[i % len(users)]
        cats = user_categories[user.id]
        use_expense = random.random() < 0.72
        category_pool = cats["expense"] if use_expense and cats["expense"] else cats["income"]
        cat_entry = random.choice(category_pool)
        cat, low, high = cat_entry
        amount = round(random.uniform(low, high), 2)
        tx_type = cat.type
        tx_date = random_date(start_date, end_date)
        desc_pool = (EXPENSE_DESCRIPTIONS if tx_type == "expense" else INCOME_DESCRIPTIONS).get(cat.name, ["Операция"])
        description = random.choice(desc_pool)
        anomaly_score = round(random.uniform(0.6, 0.99), 4) if random.random() < 0.05 else round(random.uniform(0.0, 0.15), 4)
        is_anomaly = anomaly_score >= 0.6
        confidence = round(random.uniform(0.75, 0.99), 4)
        tx = Transaction(
            user_id=user.id,
            category_id=cat.id,
            amount=amount,
            type=tx_type,
            transaction_date=tx_date,
            description=description,
            ai_predicted_category=cat.name,
            ai_confidence=confidence,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365)),
        )
        chunk.append(tx)
        if len(chunk) >= CHUNK_SIZE:
            db.add_all(chunk)
            db.commit()
            all_transactions.extend(chunk)
            print(f"  -> Inserted {len(all_transactions)}/{TRANSACTIONS_COUNT} transactions...")
            chunk = []

    if chunk:
        db.add_all(chunk)
        db.commit()
        all_transactions.extend(chunk)

    for tx in all_transactions:
        db.refresh(tx)

    print(f"  -> {len(all_transactions)} transactions created.")
    return all_transactions


def seed_budgets(db: Session, users: list[User], user_categories: dict):
    print("Seeding budgets...")
    budgets = []
    periods = [
        f"2024-{m:02d}" for m in range(1, 13)
    ] + [f"2025-{m:02d}" for m in range(1, 13)]

    for user in users:
        expense_cats = user_categories[user.id]["expense"]
        selected_cats = random.sample(expense_cats, k=min(4, len(expense_cats)))
        selected_periods = random.sample(periods, k=random.randint(6, 12))
        for cat, low, high in selected_cats:
            for period in selected_periods:
                limit = round(random.uniform(low * 2, high * 3), 2)
                budgets.append(Budget(
                    user_id=user.id,
                    category_id=cat.id,
                    limit_amount=limit,
                    period=period,
                ))
    db.add_all(budgets)
    db.commit()
    print(f"  -> {len(budgets)} budgets created.")


def seed_goals(db: Session, users: list[User]):
    print("Seeding goals...")
    goals = []
    for user in users:
        selected = random.sample(GOAL_TEMPLATES, k=random.randint(2, 4))
        for name, low, high in selected:
            target = round(random.uniform(low, high), 2)
            current = round(random.uniform(0, target * 0.7), 2)
            years_ahead = random.randint(1, 4)
            target_date = str(date.today().replace(year=date.today().year + years_ahead))
            goals.append(Goal(
                user_id=user.id,
                name=name,
                target_amount=target,
                current_amount=current,
                target_date=target_date,
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 500)),
            ))
    db.add_all(goals)
    db.commit()
    print(f"  -> {len(goals)} goals created.")


def seed_ai_forecasts(db: Session, users: list[User]):
    print("Seeding AI forecasts...")
    forecasts = []
    periods = [f"2024-{m:02d}" for m in range(1, 13)] + [f"2025-{m:02d}" for m in range(1, 13)]
    for user in users:
        for period in random.sample(periods, k=random.randint(6, 12)):
            balance = round(random.gauss(25000, 15000), 2)
            forecasts.append(AIForecast(
                user_id=user.id,
                period=period,
                forecasted_balance=balance,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365)),
            ))
    db.add_all(forecasts)
    db.commit()
    print(f"  -> {len(forecasts)} AI forecasts created.")


def seed_ai_anomalies(db: Session, transactions: list[Transaction]):
    print("Seeding AI anomalies...")
    anomalous = [tx for tx in transactions if tx.is_anomaly]
    anomalies = []
    reasons = [
        "Сумма транзакции значительно превышает средний показатель по категории",
        "Нетипичное время суток для данного типа расходов",
        "Дублирующая транзакция обнаружена в течение 24 часов",
        "Расход в нетипичной категории для данного пользователя",
        "Сумма превышает трёхкратное стандартное отклонение по категории",
        "Подозрительно высокая частота транзакций в данный период",
    ]
    for tx in anomalous:
        anomalies.append(AIAnomaly(
            transaction_id=tx.id,
            anomaly_score=tx.anomaly_score,
            reason=random.choice(reasons),
            detected_at=datetime.utcnow() - timedelta(days=random.randint(0, 300)),
        ))
    db.add_all(anomalies)
    db.commit()
    print(f"  -> {len(anomalies)} AI anomalies created.")


def seed_ai_recommendations(db: Session, users: list[User], user_categories: dict):
    print("Seeding AI budget recommendations...")
    recommendations = []
    for user in users:
        expense_cats = user_categories[user.id]["expense"]
        selected = random.sample(expense_cats, k=min(3, len(expense_cats)))
        for cat, low, high in selected:
            rec_type = random.choice(RECOMMENDATION_TYPES)
            current_limit = round(random.uniform(low * 2, high * 2), 2)
            if rec_type == "INCREASE":
                proposed_limit = round(current_limit * random.uniform(1.2, 1.6), 2)
            elif rec_type == "DECREASE":
                proposed_limit = round(current_limit * random.uniform(0.5, 0.8), 2)
            else:
                proposed_limit = round(random.uniform(low, high), 2)
                current_limit = None
            justification = random.choice(RECOMMENDATION_TEXTS[rec_type])
            recommendations.append(AIBudgetRecommendation(
                user_id=user.id,
                category_id=cat.id,
                recommendation_type=rec_type,
                current_limit=current_limit,
                proposed_limit=proposed_limit,
                justification=justification,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 180)),
            ))
    db.add_all(recommendations)
    db.commit()
    print(f"  -> {len(recommendations)} AI recommendations created.")


def print_summary(db: Session):
    print("\n" + "=" * 50)
    print("DATABASE SEEDING SUMMARY")
    print("=" * 50)
    print(f"  Users:                   {db.query(User).count()}")
    print(f"  Categories:              {db.query(Category).count()}")
    print(f"  Transactions:            {db.query(Transaction).count()}")
    print(f"  Budgets:                 {db.query(Budget).count()}")
    print(f"  Goals:                   {db.query(Goal).count()}")
    print(f"  AI Forecasts:            {db.query(AIForecast).count()}")
    print(f"  AI Anomalies:            {db.query(AIAnomaly).count()}")
    print(f"  AI Recommendations:      {db.query(AIBudgetRecommendation).count()}")
    total = (
        db.query(User).count()
        + db.query(Category).count()
        + db.query(Transaction).count()
        + db.query(Budget).count()
        + db.query(Goal).count()
        + db.query(AIForecast).count()
        + db.query(AIAnomaly).count()
        + db.query(AIBudgetRecommendation).count()
    )
    print("=" * 50)
    print(f"  TOTAL RECORDS:           {total}")
    print("=" * 50)

    anomaly_count = db.query(Transaction).filter(Transaction.is_anomaly == True).count()
    expense_count = db.query(Transaction).filter(Transaction.type == "expense").count()
    income_count = db.query(Transaction).filter(Transaction.type == "income").count()
    print(f"\n  Transaction breakdown:")
    print(f"    Expenses:              {expense_count}")
    print(f"    Income:                {income_count}")
    print(f"    Anomalous:             {anomaly_count}")
    print("\nDatabase seeding completed successfully!")


def main():
    print("Starting database seeding...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        clear_database(db)
        users = seed_users(db)
        user_categories = seed_categories(db, users)
        transactions = seed_transactions(db, users, user_categories)
        seed_budgets(db, users, user_categories)
        seed_goals(db, users)
        seed_ai_forecasts(db, users)
        seed_ai_anomalies(db, transactions)
        seed_ai_recommendations(db, users, user_categories)
        print_summary(db)
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
