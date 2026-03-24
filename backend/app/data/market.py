MARKET_DATA = {
    "logistics": {
        "name": "Рынок складской недвижимости и логистики России",
        "size_2025_trln": 4.5,
        "cagr_pct": 9.0,
        "size_history": [
            {"year": 2021, "size": 3.1},
            {"year": 2022, "size": 3.4},
            {"year": 2023, "size": 3.7},
            {"year": 2024, "size": 4.1},
            {"year": 2025, "size": 4.5},
        ],
        "segments": [
            {"name": "Автомобильная логистика", "share": 55, "margin": "8-12%"},
            {"name": "Железнодорожная логистика", "share": 25, "margin": "10-15%"},
            {"name": "Складская недвижимость", "share": 12, "margin": "25-35%"},
            {"name": "Курьерская доставка", "share": 8, "margin": "3-7%"},
        ],
        "players": [
            {"name": "Деловые Линии", "share": 8.5, "revenue": 145},
            {"name": "ПЭК", "share": 6.2, "revenue": 105},
            {"name": "СДЭК", "share": 5.8, "revenue": 98},
            {"name": "Wildberries Logistics", "share": 5.0, "revenue": 85},
            {"name": "Ozon Logistics", "share": 4.5, "revenue": 76},
            {"name": "Почта России", "share": 12.0, "revenue": 204},
        ],
        "warehouse_metrics": {
            "total_stock_mln_sqm": 42.5,
            "vacancy_rate_pct": 3.2,
            "avg_rent_class_a": 6800,
            "new_supply_2025_mln_sqm": 4.8,
            "moscow_share_pct": 45,
        },
        "ma_deals": [
            {"year": 2024, "buyer": "Ozon", "target": "складские площади A Plus Park", "value": "12 млрд руб."},
            {"year": 2024, "buyer": "Wildberries", "target": "логистические центры FM Logistic", "value": "8 млрд руб."},
            {"year": 2025, "buyer": "Сбер", "target": "доля в PickPoint", "value": "5 млрд руб."},
        ],
        "trends": [
            "E-commerce остается главным драйвером роста: +25% год к году",
            "Дефицит складских площадей класса А — вакансия на историческом минимуме (3.2%)",
            "Консолидация рынка: крупные маркетплейсы строят собственную логистику",
            "Автоматизация складов: роботизация, WMS-системы, IoT-мониторинг",
            "Рост ставок аренды на 15-20% в 2024-2025 гг. из-за дефицита предложения",
            "Смещение спроса в регионы: Екатеринбург, Казань, Новосибирск",
        ],
        "risks": [
            "Замедление e-commerce может снизить спрос на складские площади",
            "Рост ставки ЦБ РФ увеличивает стоимость заемного финансирования",
            "Дефицит рабочей силы в логистике и строительстве",
        ],
    },
}

# Keywords for matching market requests
MARKET_KEYWORDS = {
    "logistics": ["логистик", "склад", "warehouse", "складск", "транспорт", "доставк"],
}
